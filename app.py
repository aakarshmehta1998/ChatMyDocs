import streamlit as st
import os
from rag_core import process_and_store_documents, create_conversational_chain
from style import CSS_CODE

st.set_page_config(
    page_title="ChatMyDocs",
    page_icon="🤖",
    layout="wide"
)

st.markdown(CSS_CODE, unsafe_allow_html=True)

st.title("📄 ChatMyDocs")
st.caption("Your intelligent document assistant, powered by AWS Bedrock's Claude 3.")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "rag_chain" not in st.session_state:
    st.session_state.rag_chain = None
if "uploaded_file_names" not in st.session_state:
    st.session_state.uploaded_file_names = []

with st.sidebar:
    st.header("1. Upload Documents")

    allowed_types = ["pdf", "docx", "pptx", "xlsx", "jpeg", "png", "jpg", "txt"]
    uploaded_files = st.file_uploader(
        "Upload one or more documents. The knowledge base will be created from all files combined.",
        type=allowed_types,
        accept_multiple_files=True
    )

    if uploaded_files:
        st.subheader("Your Documents:")
        st.session_state.uploaded_file_names = [file.name for file in uploaded_files]
        for name in st.session_state.uploaded_file_names:
            st.write(f"📁 {name}")

        st.header("2. Process Documents")
        if st.button("Create Knowledge Base"):
            with st.spinner("Reading and indexing documents... This may take a moment."):

                temp_dir = "temp_docs"
                if not os.path.exists(temp_dir):
                    os.makedirs(temp_dir)

                saved_file_paths = []
                for uploaded_file in uploaded_files:
                    file_path = os.path.join(temp_dir, uploaded_file.name)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getvalue())
                    saved_file_paths.append(file_path)

                vector_store = process_and_store_documents(saved_file_paths)
                st.session_state.rag_chain = create_conversational_chain(vector_store)
                st.session_state.messages = []
                st.success("Knowledge Base created! You can now ask questions.")

if not st.session_state.rag_chain:
    st.info("Welcome to ChatMyDocs! Please upload and process your documents in the sidebar to get started.")

for message in st.session_state.messages:
    avatar = "👤" if message["role"] == "user" else "🤖"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask a question about your documents..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    if st.session_state.rag_chain is None:
        with st.chat_message("assistant", avatar="🤖"):
            st.warning("Please create a Knowledge Base from your documents first.")
    else:
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Thinking..."):
                response = st.session_state.rag_chain.invoke({"input": prompt})
                answer = response["answer"]
                st.markdown(answer)

        st.session_state.messages.append({"role": "assistant", "content": answer})