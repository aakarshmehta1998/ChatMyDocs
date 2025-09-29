import os
import streamlit as st
import boto3
import tempfile
from langchain_community.chat_models import BedrockChat
from langchain_community.embeddings import BedrockEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.chains import RetrievalQA
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import UnstructuredFileLoader
from PIL import Image
import pytesseract
from pinecone import Pinecone
from langchain.prompts import PromptTemplate

def get_bedrock_client():
    """Initializes and returns a boto3 client for Bedrock Runtime."""
    return boto3.client(
        "bedrock-runtime",
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
        region_name=st.secrets["AWS_REGION"],
    )

def _embeddings():
    """Creates and returns BedrockEmbeddings using the Titan model."""
    return BedrockEmbeddings(
        client=get_bedrock_client(),
        model_id="amazon.titan-embed-text-v1",
    )

def _load_and_split(in_memory_files):
    """
    Loads documents from in-memory data, saves them to a temporary directory
    for processing, and then splits them into chunks.
    """
    docs = []
    img_ext = {".png", ".jpg", ".jpeg"}

    with tempfile.TemporaryDirectory() as temp_dir:
        for file_data in in_memory_files:
            file_name = file_data["name"]
            file_bytes = file_data["data"]

            temp_path = os.path.join(temp_dir, file_name)

            with open(temp_path, "wb") as f:
                f.write(file_bytes)

            ext = os.path.splitext(temp_path)[1].lower()
            if ext in img_ext:
                try:
                    text = pytesseract.image_to_string(Image.open(temp_path))
                    docs.append(Document(page_content=text, metadata={"source": file_name}))
                except Exception as e:
                    st.error(f"OCR error on {file_name}: {e}")
            else:
                try:
                    loader = UnstructuredFileLoader(temp_path)
                    loaded_docs = loader.load()
                    for doc in loaded_docs:
                        doc.metadata["source"] = file_name
                    docs.extend(loaded_docs)
                except Exception as e:
                    st.error(f"Failed to load {file_name}: {e}")

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    return splitter.split_documents(docs)

def process_and_store_documents(in_memory_files, namespace: str):
    """Processes in-memory documents and stores their embeddings in Pinecone."""
    with st.spinner("Extracting text and creating embeddings..."):
        docs = _load_and_split(in_memory_files)
        em = _embeddings()
        index_name = st.secrets["PINECONE_INDEX_NAME"]

    with st.spinner(f"Storing {len(docs)} document chunks in the knowledge base..."):
        PineconeVectorStore.from_documents(
            documents=docs,
            embedding=em,
            index_name=index_name,
            namespace=namespace,
            batch_size=64  # OPTIMIZATION: Process documents in larger batches
        )

    return load_vector_store(namespace=namespace)

def load_vector_store(namespace: str):
    """Loads an existing vector store from Pinecone by namespace."""
    em = _embeddings()
    index_name = st.secrets["PINECONE_INDEX_NAME"]

    return PineconeVectorStore.from_existing_index(
        embedding=em,
        index_name=index_name,
        namespace=namespace
    )

def delete_knowledge_base(namespace: str):
    """Deletes all vectors from a specific namespace in the Pinecone index."""
    try:
        pc = Pinecone(api_key=st.secrets["PINECONE_API_KEY"])
        index = pc.Index(st.secrets["PINECONE_INDEX_NAME"])
        index.delete(namespace=namespace, delete_all=True)
        return True
    except Exception as e:
        st.error(f"Error deleting knowledge base from Pinecone: {e}")
        return False

def create_conversational_chain(vector_store):
    """Creates the LangChain conversational retrieval chain with a custom prompt."""
    llm = BedrockChat(
        client=get_bedrock_client(),
        model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        model_kwargs={"temperature": 0.1}
    )
    prompt_template = """
    You are a friendly and helpful assistant for answering questions based on the provided text.

    Use the following context to answer the user's question.

    - If the user asks a question that can be answered from the context, provide a clear and direct answer based ONLY on that context.
    - If the answer is not available in the context, politely state that the document does not contain that information. Do not use your external knowledge.
    - For simple greetings or conversational phrases (like "hello", "thank you"), respond naturally and politely.

    Context: {context}
    Question: {question}

    Helpful Answer:"""

    PROMPT = PromptTemplate(
        template=prompt_template, input_variables=["context", "question"]
    )

    retriever = vector_store.as_retriever(
        search_type="mmr",
        search_kwargs={'k': 5, 'fetch_k': 50}
    )

    qa = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        return_source_documents=True,
        chain_type="stuff",
        chain_type_kwargs={"prompt": PROMPT}
    )
    return qa