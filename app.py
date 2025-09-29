import os
import re
import uuid
import json
import shutil
import streamlit as st
import streamlit_authenticator as stauth
import bcrypt
from rag_core import process_and_store_documents, create_conversational_chain, load_vector_store, delete_knowledge_base
from style import CSS_CODE
from auth import load_credentials_from_db, save_new_user_to_db
import s3_utils

st.set_page_config(page_title="ChatMyDocs", page_icon="🤖", layout="wide")
st.markdown(CSS_CODE, unsafe_allow_html=True)
credentials = load_credentials_from_db()
authenticator = stauth.Authenticate(
    credentials,
    "chatmydocs_cookie",
    "abcdef",
    30
)

def sanitize_filename(name: str) -> str:
    """Sanitizes a string to be used as a valid S3 prefix or filename."""
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name).lower()

def get_kb_documents(username: str, kb_name: str) -> list:
    """Retrieves the list of source document names from a JSON file in S3."""
    s3_bucket = st.secrets["S3_BUCKET_NAME"]
    s3_key = f"{username}/{kb_name}/source_documents.json"
    doc_list = s3_utils.load_json_from_s3(s3_bucket, s3_key)
    return doc_list if doc_list else []

def save_chat_history(username: str, kb_name: str, messages: list):
    """Saves the chat history list as a JSON file to S3."""
    if not kb_name or not username: return
    s3_bucket = st.secrets["S3_BUCKET_NAME"]
    s3_key = f"{username}/{kb_name}/chat_history.json"
    s3_utils.save_json_to_s3(messages, s3_bucket, s3_key)

def load_chat_history(username: str, kb_name: str) -> list:
    """Loads chat history from a JSON file in S3."""
    s3_bucket = st.secrets["S3_BUCKET_NAME"]
    s3_key = f"{username}/{kb_name}/chat_history.json"
    history = s3_utils.load_json_from_s3(s3_bucket, s3_key)
    return history if history else []

def _init_wizard_state():
    """Initializes session state variables for the app."""
    st.session_state.setdefault("wizard_step", 1)
    st.session_state.setdefault("upload_buffer", [])
    st.session_state.setdefault("rag_chain", None)
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("current_kb_name", None)
    st.session_state.setdefault("current_kb_sanitized_name", None)

def _reset_wizard(clear_chain=True):
    """Resets the wizard and chat state."""
    st.session_state.wizard_step = 1
    st.session_state.upload_buffer = []
    if clear_chain:
        st.session_state.rag_chain = None
        st.session_state.messages = []
        st.session_state.current_kb_name = None
        st.session_state.current_kb_sanitized_name = None

def _sidebar_header(username: str, is_guest: bool):
    """Renders the sidebar header and navigation."""
    with st.sidebar:
        if is_guest:
            st.subheader("🚀 Welcome, Guest!")
            st.info("Your session is temporary. Sign up to save your knowledge bases.")
            if st.button("Sign Up / Login", key="btn_guest_to_login"):
                st.session_state['guest_mode'] = False
                st.session_state['authentication_status'] = None
                _reset_wizard()
                st.rerun()
        else:
            st.subheader(f'Welcome, {st.session_state.get("name", username)}!')
            authenticator.logout(location="sidebar")
            if st.button("⬅️ Back to Dashboard", key="btn_back_to_dash"):
                st.session_state.view = 'dashboard'
                _reset_wizard()
                st.rerun()

        st.markdown("---")
        if st.session_state.get('view', 'dashboard') == 'wizard':
            st.markdown("### Progress")
            steps = ["1. Upload", "2. Process", "3. Chat"]
            active = st.session_state.get("wizard_step", 1)
            for i, label in enumerate(steps, start=1):
                bullet = "✅" if active > i else ("🟢" if active == i else "⚪️")
                st.write(f"{bullet} {label}")

            if st.button("Start Over", key="btn_reset_wizard_sidebar"):
                _reset_wizard()
                # For a registered user, "Start Over" returns to the dashboard.
                if 'username' in st.session_state and st.session_state['username']:
                    st.session_state.view = 'dashboard'
                st.rerun()

def step_upload(username: str):
    """UI for Step 1: Document Upload."""
    st.header("1. Upload Documents")
    st.caption("Upload documents to a new Knowledge Base.")
    allowed_types = ["pdf", "docx", "pptx", "xlsx", "jpeg", "png", "jpg", "txt"]
    uploads = st.file_uploader(
        "Drag and drop files here",
        type=allowed_types,
        accept_multiple_files=True,
        key="uploader_docs"
    )

    if uploads:
        st.subheader("Selected files")
        for f in uploads:
            st.write(f"📁 {f.name}")

    c1, c2, _ = st.columns([1, 1, 6])
    with c1:
        disabled = not uploads
        if st.button("Save & Continue →", key="btn_upload_continue", disabled=disabled):
            st.session_state.upload_buffer = [{"name": f.name, "data": f.getvalue()} for f in uploads]
            st.session_state.wizard_step = 2
            st.rerun()
    with c2:
        if st.button("Clear", key="btn_upload_clear"):
            st.session_state.upload_buffer = []
            st.rerun()

    if not uploads and not st.session_state.upload_buffer:
        st.info("Select at least one file to continue.")

def step_process(username: str):
    """UI for Step 2: Document Processing."""
    st.header("2. Process Documents")
    if not st.session_state.upload_buffer:
        st.warning("No files found. Please upload documents first.")
        if st.button("← Back to Upload", key="btn_back_to_upload_empty"):
            st.session_state.wizard_step = 1
            st.rerun()
        return

    st.subheader("Your Documents")
    for item in st.session_state.upload_buffer:
        st.write(f"📁 {item['name']}")

    st.markdown("---")
    kb_name = st.text_input(
        "Enter a name for your new Knowledge Base:",
        placeholder="e.g., Biology Midterm Notes",
        key="kb_name_input"
    )
    st.markdown('<div class="cta-wrap">', unsafe_allow_html=True)
    disabled = not kb_name.strip()
    if st.button("Create Knowledge Base", key="btn_create_kb", disabled=disabled):
        with st.spinner("Processing documents... This may take a moment."):
            kb_name_sanitized = sanitize_filename(kb_name)
            s3_bucket = st.secrets["S3_BUCKET_NAME"]

            for item in st.session_state.upload_buffer:
                s3_object_name = f"{username}/{kb_name_sanitized}/{item['name']}"
                s3_utils.upload_file_to_s3(item['data'], s3_bucket, s3_object_name)

            source_filenames = [item['name'] for item in st.session_state.upload_buffer]
            s3_utils.save_json_to_s3(source_filenames, s3_bucket,
                                     f"{username}/{kb_name_sanitized}/source_documents.json")

            namespace = f"{username}-{kb_name_sanitized}"
            vector_store = process_and_store_documents(st.session_state.upload_buffer, namespace=namespace)

            st.session_state.rag_chain = create_conversational_chain(vector_store)
            st.session_state.messages = []
            st.session_state.current_kb_name = kb_name
            st.session_state.current_kb_sanitized_name = kb_name_sanitized

            st.success(f"Knowledge Base '{kb_name}' created!")
            st.session_state.wizard_step = 3
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    c1, c2, _ = st.columns([1, 1, 6])
    with c1:
        if st.button("← Back", key="btn_process_back"):
            st.session_state.wizard_step = 1
            st.rerun()

def step_chat(username: str, is_guest: bool):
    """UI for Step 3: Chat Interface."""
    st.header("3. Chat")

    if not is_guest and st.session_state.current_kb_sanitized_name:
        with st.sidebar:
            with st.expander("📚 Source Documents", expanded=True):
                sanitized_name = st.session_state.current_kb_sanitized_name
                docs = get_kb_documents(username, sanitized_name)
                for doc in docs:
                    st.write(f"📄 {doc}")

    st.title(f"Chat with '{st.session_state.get('current_kb_name', 'your documents')}'")
    st.caption("Your intelligent document assistant, powered by AWS Bedrock's Claude 3.")

    if st.session_state.rag_chain is None:
        st.warning("No knowledge base yet. Go back and process your documents.")
    else:
        st.success("Knowledge Base is ready. Ask away!")

    for message in st.session_state.messages:
        avatar = "👤" if message["role"] == "user" else "🤖"
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask a question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        greetings = ["hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening"]
        normalized_prompt = ''.join(c for c in prompt if c.isalnum() or c.isspace()).lower().strip()

        if normalized_prompt in greetings:
            answer = "Hello! How can I assist you with your documents today?"
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})

        else:
            if st.session_state.rag_chain is None:
                with st.chat_message("assistant", avatar="🤖"):
                    st.warning("Please create a Knowledge Base first.")
            else:
                with st.chat_message("assistant", avatar="🤖"):
                    with st.spinner("Thinking..."):
                        result = st.session_state.rag_chain.invoke({"query": prompt})
                        answer = result.get("result", "")
                        st.markdown(answer)
                        st.session_state.messages.append({"role": "assistant", "content": answer})

                        srcs = result.get("source_documents", [])

                        # Phrases that indicate a generic or non-document-based answer
                        ignore_phrases = [
                            "don't know", "does not contain", "not found in the context",
                            "without any context", "i am an ai assistant", "i'm an ai assistant", "personal name"
                        ]

                        answer_is_generic = any(phrase in answer.lower() for phrase in ignore_phrases)

                        # Only show sources if they exist and the answer isn't generic
                        if srcs and not answer_is_generic:
                            with st.expander("Sources"):
                                for d in srcs:
                                    st.write(f"• {d.metadata.get('source', 'document')}")

        if not is_guest:
            save_chat_history(username, st.session_state.current_kb_sanitized_name, st.session_state.messages)


def get_user_kbs(username: str) -> list:
    """Lists all knowledge bases for a user by checking S3 prefixes."""
    s3_bucket = st.secrets["S3_BUCKET_NAME"]
    return s3_utils.list_folders_in_s3(s3_bucket, username)


def render_dashboard(username: str):
    """UI for the main dashboard showing all knowledge bases."""
    st.title("Your Knowledge Bases")
    st.markdown("---")

    if st.button("＋ Create New Knowledge Base", type="primary"):
        _reset_wizard()
        st.session_state.view = 'wizard'
        st.rerun()

    st.markdown("### Existing Knowledge Bases")
    user_kbs = get_user_kbs(username)

    if not user_kbs:
        st.info("You haven't created any knowledge bases yet. Click the button above to start!")
        return

    for kb_name in user_kbs:
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            with c1:
                display_name = kb_name.replace("_", " ").title()
                st.subheader(display_name)
                if st.button("Chat", key=f"chat_{kb_name}"):
                    with st.spinner(f"Loading '{display_name}'..."):
                        namespace = f"{username}-{kb_name}"
                        vector_store = load_vector_store(namespace=namespace)
                        if vector_store:
                            st.session_state.rag_chain = create_conversational_chain(vector_store)
                            st.session_state.messages = load_chat_history(username, kb_name)
                            st.session_state.current_kb_name = display_name
                            st.session_state.current_kb_sanitized_name = kb_name
                            st.session_state.wizard_step = 3
                            st.session_state.view = 'wizard'
                            st.rerun()
                        else:
                            st.error(f"Failed to load Knowledge Base '{display_name}'.")

            with c2:
                if st.button("Delete", key=f"delete_{kb_name}", type="secondary"):
                    with st.spinner(f"Deleting '{display_name}'..."):
                        s3_bucket = st.secrets["S3_BUCKET_NAME"]
                        s3_prefix = f"{username}/{kb_name}/"
                        s3_utils.delete_folder_from_s3(s3_bucket, s3_prefix)

                        namespace = f"{username}-{kb_name}"
                        delete_knowledge_base(namespace)
                    st.success(f"Successfully deleted '{display_name}'.")
                    st.rerun()

def render_main_app(username, is_guest):
    """Main application view router."""
    if 'wizard_step' not in st.session_state:
        _init_wizard_state()
    _sidebar_header(username, is_guest)
    step = st.session_state.wizard_step
    if step == 1:
        step_upload(username)
    elif step == 2:
        step_process(username)
    else:
        step_chat(username, is_guest)

# --- Main Application Logic ---

st.session_state.setdefault('active_user', None)
is_guest = st.session_state.get('guest_mode', False)

if is_guest:
    render_main_app(st.session_state.get('guest_uuid', str(uuid.uuid4())), is_guest=True)

elif st.session_state.get("authentication_status"):
    username = st.session_state.get("username")
    if st.session_state.active_user != username:
        _reset_wizard(clear_chain=True)
        st.session_state.view = 'dashboard'
        st.session_state.active_user = username

    st.session_state.setdefault('view', 'dashboard')
    if st.session_state.view == 'dashboard':
        _sidebar_header(username, is_guest=False)
        render_dashboard(username)
    else:
        render_main_app(username, is_guest=False)

else:  # Login/Register Screen
    if 'page' not in st.session_state:
        st.session_state.page = 'login'

    st.session_state.active_user = None
    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        st.markdown('<div id="login-card" class="login-card">', unsafe_allow_html=True)
        if st.session_state.page == 'login':
            st.markdown("<h1>Welcome to ChatMyDocs</h1>", unsafe_allow_html=True)
            authenticator.login(fields={'Form name': 'Login'})

            if st.session_state.get("authentication_status") is False:
                st.error('Username/password is incorrect')

            st.divider()
            if st.button("Continue as Guest", type="secondary", use_container_width=True, key="btn_guest"):
                st.session_state['guest_mode'] = True
                st.session_state['guest_uuid'] = str(uuid.uuid4())
                _reset_wizard(clear_chain=True)
                st.session_state.view = 'wizard'
                st.rerun()
            if st.button("Not a member? Register here", use_container_width=True, key="btn_go_register"):
                st.session_state.page = 'register'
                st.rerun()
        elif st.session_state.page == 'register':
            st.markdown("<h1>Register for ChatMyDocs</h1>", unsafe_allow_html=True)
            with st.form("register_form", clear_on_submit=False):
                full_name = st.text_input("Full Name", key="reg_full_name")
                email = st.text_input("Email Address", key="reg_email")
                username = st.text_input("Username", key="reg_username")
                pw = st.text_input("Password", type="password", key="reg_pw")
                pw2 = st.text_input("Confirm Password", type="password", key="reg_pw2")
                submitted = st.form_submit_button("Create account", use_container_width=False)

            if submitted:
                if not full_name or not email or not username or not pw or not pw2:
                    st.error("Please fill all fields.")
                elif pw != pw2:
                    st.error("Passwords do not match.")
                elif username in credentials.get("usernames", {}):
                    st.error("That username is already taken.")
                else:
                    hashed_pw = bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    success = save_new_user_to_db(username, full_name, email, hashed_pw)
                    if success:
                        st.success("User registered successfully! Please log in.")
                        st.session_state.page = 'login'
                        st.rerun()

            b1, b2, b3 = st.columns([1, 1, 1])
            with b2:
                st.markdown('<div class="cta-wrap-small">', unsafe_allow_html=True)
                if st.button("Back to Login", use_container_width=False, type="secondary", key="btn_back_login"):
                    st.session_state.page = 'login'
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)