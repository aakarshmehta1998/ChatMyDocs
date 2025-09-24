# rag_core.py

import os
import streamlit as st # <-- ADD IMPORT
import boto3 # <-- ADD IMPORT
from langchain_community.chat_models import BedrockChat
from langchain_community.embeddings import BedrockEmbeddings
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_community.document_loaders import UnstructuredFileLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from PIL import Image
import pytesseract
from langchain_core.documents import Document

# --- NEW HELPER FUNCTION TO GET BEDROCK CLIENT ---
def get_bedrock_client():
    """Initializes and returns a boto3 Bedrock runtime client."""
    return boto3.client(
        'bedrock-runtime',
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
        region_name=st.secrets["AWS_REGION"]
    )

def process_and_store_documents(file_paths, db_path):
    all_documents = []
    image_extensions = ['.png', '.jpeg', '.jpg']
    for file_path in file_paths:
        file_extension = os.path.splitext(file_path)[1].lower()

        if file_extension in image_extensions:
            try:
                image = Image.open(file_path)
                extracted_text = pytesseract.image_to_string(image)
                metadata = {"source": os.path.basename(file_path)}
                ocr_document = Document(page_content=extracted_text, metadata=metadata)
                all_documents.append(ocr_document)
            except Exception as e:
                print(f"Error processing image {file_path} with OCR: {e}")
        else:
            loader = UnstructuredFileLoader(file_path)
            documents = loader.load()
            all_documents.extend(documents)

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = text_splitter.split_documents(all_documents)

    # --- UPDATED: Pass the client to the embeddings model ---
    bedrock_client = get_bedrock_client()
    embeddings = BedrockEmbeddings(
        client=bedrock_client,
        model_id="amazon.titan-embed-text-v1"
    )
    vector_store = Chroma.from_documents(docs, embeddings, persist_directory=db_path)

    return vector_store


def load_vector_store(db_path):
    """Loads an existing ChromaDB vector store from a directory."""
    if not os.path.exists(db_path):
        return None
    # --- UPDATED: Pass the client to the embeddings model ---
    bedrock_client = get_bedrock_client()
    embeddings = BedrockEmbeddings(
        client=bedrock_client,
        model_id="amazon.titan-embed-text-v1"
    )
    return Chroma(persist_directory=db_path, embedding_function=embeddings)

def create_conversational_chain(vector_store):
    # --- UPDATED: Pass the client to the chat model ---
    bedrock_client = get_bedrock_client()
    llm = BedrockChat(
        client=bedrock_client,
        model_id="anthropic.claude-3-sonnet-20240229-v1:0"
    )
    retriever = vector_store.as_retriever()

    system_prompt = (
        "You are a specialized assistant for answering questions based ONLY on the provided context from a user's documents. "
        "Your role is to find and present information found within that text. "
        "Under no circumstances should you use your own general knowledge. "
        "If the answer to the question cannot be found in the provided context, you MUST respond with the exact phrase: "
        "'I'm sorry, but the answer to that question is not available in the provided documents.' "
        "Do not add any other information or explanation. "
        "If the answer is in the context, provide it directly based on the text."
        "\n\n"
        "Context: {context}"
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
        ]
    )
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)
    return rag_chain