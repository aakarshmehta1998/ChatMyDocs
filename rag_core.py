import os
from langchain_community.chat_models import BedrockChat
from langchain_community.embeddings import BedrockEmbeddings
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_community.document_loaders import UnstructuredFileLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate


# --- FIX: Function now accepts a list of file paths ---
def process_and_store_documents(file_paths):
    all_documents = []
    # --- FIX: Load each document from the provided paths ---
    for file_path in file_paths:
        loader = UnstructuredFileLoader(file_path)
        documents = loader.load()
        all_documents.extend(documents)

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    # --- FIX: Split the combined documents ---
    docs = text_splitter.split_documents(all_documents)

    embeddings = BedrockEmbeddings(model_id="amazon.titan-embed-text-v1")

    # Create the vector store from all chunks of all documents
    vector_store = Chroma.from_documents(docs, embeddings, persist_directory="./db")

    return vector_store


def create_conversational_chain(vector_store):
    llm = BedrockChat(model_id="anthropic.claude-3-sonnet-20240229-v1:0")
    retriever = vector_store.as_retriever()

    system_prompt = (
        "You are an intelligent assistant for question-answering tasks. "
        "Use the retrieved context from the user's documents to answer the question. "
        "If you don't know the answer or the context doesn't contain the answer, "
        "just say that you don't know. Do not try to make up an answer."
        "\n\n"
        "{context}"
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