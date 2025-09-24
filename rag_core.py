import os
import streamlit as st
import boto3
from requests_aws4auth import AWS4Auth
from opensearchpy import OpenSearch, RequestsHttpConnection
from langchain_community.chat_models import BedrockChat
from langchain_community.embeddings import BedrockEmbeddings
from langchain_community.vectorstores import OpenSearchVectorSearch
from langchain.chains import RetrievalQA
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import UnstructuredFileLoader
from PIL import Image
import pytesseract

def get_bedrock_client():
    return boto3.client(
        "bedrock-runtime",
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
        region_name=st.secrets["AWS_REGION"],
    )

def _embeddings():
    return BedrockEmbeddings(
        client=get_bedrock_client(),
        model_id="amazon.titan-embed-text-v1",
    )

def get_opensearch_client():
    region = st.secrets["AWS_REGION"]
    host = st.secrets["OPENSEARCH_ENDPOINT"]

    session = boto3.Session(
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
        region_name=region,
    )
    creds = session.get_credentials().get_frozen_credentials()
    awsauth = AWS4Auth(
        creds.access_key, creds.secret_key, region, "aoss", session_token=creds.token
    )

    return OpenSearch(
        hosts=[{"host": host.replace("https://", "").replace("http://", ""), "port": 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
    )

def _ensure_index(index_name: str, dim: int):
    client = get_opensearch_client()
    if not client.indices.exists(index=index_name):
        mapping = {
            "settings": {"index": {"knn": True}},
            "mappings": {
                "properties": {
                    "text": {"type": "text"},
                    "source": {"type": "keyword"},
                    "vector": {"type": "knn_vector", "dimension": dim},
                }
            },
        }
        client.indices.create(index=index_name, body=mapping)

def _load_and_split(file_paths):
    docs = []
    img_ext = {".png", ".jpg", ".jpeg"}
    for fp in file_paths:
        ext = os.path.splitext(fp)[1].lower()
        if ext in img_ext:
            try:
                text = pytesseract.image_to_string(Image.open(fp))
                docs.append(Document(page_content=text, metadata={"source": os.path.basename(fp)}))
            except Exception as e:
                print(f"OCR error {fp}: {e}")
        else:
            docs.extend(UnstructuredFileLoader(fp).load())

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    return splitter.split_documents(docs)

def process_and_store_documents(file_paths, db_path, *, index_name: str):
    docs = _load_and_split(file_paths)
    em = _embeddings()
    dim = len(em.embed_query("dimension probe"))
    _ensure_index(index_name, dim)
    vs = OpenSearchVectorSearch.from_documents(
        documents=docs,
        embedding=em,
        client=get_opensearch_client(),
        index_name=index_name,
        vector_field="vector",
        text_field="text",
    )
    return vs

def load_vector_store(db_path, *, index_name: str):
    em = _embeddings()
    _ensure_index(index_name, len(em.embed_query("dimension probe")))
    return OpenSearchVectorSearch(
        embedding_function=em,
        client=get_opensearch_client(),
        index_name=index_name,
        vector_field="vector",
        text_field="text",
    )

def create_conversational_chain(vector_store):
    llm = BedrockChat(
        client=get_bedrock_client(),
        model_id="anthropic.claude-3-sonnet-20240229-v1:0",
    )
    system_prompt = (
        "You are a specialized assistant for answering questions based ONLY on the provided context from a user's documents. "
        "Under no circumstances should you use general knowledge. "
        "If the answer cannot be found in the provided context, respond exactly with: "
        "'I'm sorry, but the answer to that question is not available in the provided documents.' "
        "Context: {context}"
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
        ]
    )
    qa = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=vector_store.as_retriever(),
        return_source_documents=True,
        chain_type="stuff",
    )
    return qa