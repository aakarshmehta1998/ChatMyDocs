# rag_core.py

import os
from langchain_community.chat_models import BedrockChat
from langchain_community.embeddings import BedrockEmbeddings
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_community.document_loaders import UnstructuredFileLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate


# --- FIX: Function now accepts a user-specific database path ---
def process_and_store_documents(file_paths, db_path):
    all_documents = []
    for file_path in file_paths:
        loader = UnstructuredFileLoader(file_path)
        documents = loader.load()
        all_documents.extend(documents)

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = text_splitter.split_documents(all_documents)

    embeddings = BedrockEmbeddings(model_id="amazon.titan-embed-text-v1")

    # --- FIX: Use the provided path for the persistent directory ---
    vector_store = Chroma.from_documents(docs, embeddings, persist_directory=db_path)

    return vector_store


def create_conversational_chain(vector_store):
    llm = BedrockChat(model_id="anthropic.claude-3-sonnet-20240229-v1:0")
    retriever = vector_store.as_retriever()

    # ---- MODIFICATION START: Stricter System Prompt ----
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