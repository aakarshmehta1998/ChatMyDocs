
import os
import re
import uuid
import shutil
import json
import streamlit as st
import streamlit_authenticator as stauth
import bcrypt

from rag_core import process_and_store_documents, create_conversational_chain, load_vector_store
from style import CSS_CODE
from auth import load_config, save_config
import s3_utils

# Page Configuration & Global CSS
st.set_page_config(page_title="ChatMyDocs", page_icon="🤖", layout="wide")
st.markdown(CSS_CODE, unsafe_allow_html=True)

# Load Auth Config & Authenticator
config = load_config()
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# Helper Functions
def sanitize_filename(name: str) -> str:
    """Converts a string to a safe, usable directory name."""
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name).lower()


def save_chat_history(username: str, kb_name: str, messages: list):
    """Saves the chat history to a JSON file."""
    if not kb_name or not username: return
    history_path = os.path.join(f"data/{username}/{kb_name}", "chat_history.json")
    with open(history_path, 'w') as f:
        json.dump(messages, f)


def load_chat_history(username: str, kb_name: str) -> list:
    """Loads the chat history from a JSON file."""
    history_path = os.path.join(f"data/{username}/{kb_name}", "chat_history.json")
    if os.path.exists(history_path):
        with open(history_path, 'r') as f:
            return json.load(f)
    return []

def get_kb_documents(username: str, kb_name: str) -> list:
    """Reads the list of source documents for a given KB."""
    doc_list_path = os.path.join(f"data/{username}/{kb_name}", "source_documents.json")
    if os.path.exists(doc_list_path):
        with open(doc_list_path, 'r') as f:
            return json.load(f)
    return []

# Wizard State Management
def _init_wizard_state():
    st.session_state.setdefault("wizard_step", 1)
    st.session_state.setdefault("upload_buffer", [])
    st.session_state.setdefault("saved_file_paths", [])
    st.session_state.setdefault("rag_chain", None)
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("current_kb_name", None)
    st.session_state.setdefault("current_kb_sanitized_name", None)

def _reset_wizard(clear_chain=True):
    st.session_state.wizard_step = 1
    st.session_state.upload_buffer = []
    st.session_state.saved_file_paths = []
    if clear_chain:
        st.session_state.rag_chain = None
        st.session_state.messages = []
        st.session_state.current_kb_name = None
        st.session_state.current_kb_sanitized_name = None

# UI Rendering Functions
def _sidebar_header(username: str, is_guest: bool):
    with st.sidebar:
        if is_guest:
            st.subheader("🚀 Welcome, Guest!")
            st.info("Your session is temporary. Sign up to save your knowledge bases.")
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
                st.session_state.view = 'dashboard'
                st.rerun()


def step_upload(username: str):
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
    st.header("2. Process Documents")
    if not st.session_state.upload_buffer:
        st.warning("No files found. Please upload documents first.")
        if st.button("← Back to Upload", key="btn_back_to_upload_empty"):
            st.session_state.wizard_step = 1
            st.rerun()
        return

    st.subheader("Your Documents")
    for it in st.session_state.upload_buffer:
        st.write(f"📁 {it['name']}")

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
            base_dir = f"data/{username}/{kb_name_sanitized}"
            os.makedirs(base_dir, exist_ok=True)

            # Upload to S3 and save locally for processing
            s3_bucket = st.secrets["S3_BUCKET_NAME"]
            saved_paths = []
            source_filenames = [item['name'] for item in st.session_state.upload_buffer]

            for item in st.session_state.upload_buffer:
                s3_object_name = f"{username}/{kb_name_sanitized}/{item['name']}"
                s3_utils.upload_file_to_s3(item['data'], s3_bucket, s3_object_name)

                local_path = os.path.join(base_dir, "temp_docs", item["name"])
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                with open(local_path, "wb") as f:
                    f.write(item["data"])
                saved_paths.append(local_path)

            # Save metadata about source documents
            with open(os.path.join(base_dir, 'source_documents.json'), 'w') as f:
                json.dump(source_filenames, f)

            # Process documents and create vector store
            db_dir = os.path.join(base_dir, "db")
            st.session_state.saved_file_paths = saved_paths
            vector_store = process_and_store_documents(saved_paths, db_dir)

            # Update session state for chat
            st.session_state.rag_chain = create_conversational_chain(vector_store)
            st.session_state.messages = []
            st.session_state.current_kb_name = kb_name
            st.session_state.current_kb_sanitized_name = kb_name_sanitized

            st.success(f"Knowledge Base '{kb_name}' created and documents stored in S3!")
            st.session_state.wizard_step = 3
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    c1, c2, _ = st.columns([1, 1, 6])
    with c1:
        if st.button("← Back", key="btn_process_back"):
            st.session_state.wizard_step = 1
            st.rerun()


def step_chat(username: str, is_guest: bool):
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
        st.success("Knowledge Base ready. Ask away!")

    for message in st.session_state.messages:
        avatar = "👤" if message["role"] == "user" else "🤖"
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask a question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        if not is_guest:
            save_chat_history(username, st.session_state.current_kb_sanitized_name, st.session_state.messages)

        if st.session_state.rag_chain is None:
            with st.chat_message("assistant", avatar="🤖"):
                st.warning("Please create a Knowledge Base first.")
        else:
            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("Thinking..."):
                    response = st.session_state.rag_chain.invoke({"input": prompt})
                    answer = response.get("answer", "")
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                    if not is_guest:
                        save_chat_history(username, st.session_state.current_kb_sanitized_name,
                                          st.session_state.messages)


def render_main_app(username: str, is_guest: bool = False):
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


def get_user_kbs(username: str) -> list:
    """Lists all knowledge bases for a given user."""
    user_dir = f"data/{username}"
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
        return []

    kbs = []
    for kb_name in os.listdir(user_dir):
        if os.path.isdir(os.path.join(user_dir, kb_name, "db")):
            kbs.append(kb_name)
    return kbs

def render_dashboard(username: str):
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
                        db_path = os.path.join(f"data/{username}/{kb_name}", "db")
                        vector_store = load_vector_store(db_path)
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
                    kb_dir = os.path.join(f"data/{username}", kb_name)
                    if os.path.exists(kb_dir):
                        shutil.rmtree(kb_dir)
                        st.rerun()

# Application Router
is_guest = st.session_state.get('guest_mode', False)

if is_guest:
    render_main_app(st.session_state.get('guest_uuid', str(uuid.uuid4())), is_guest=True)

elif st.session_state.get("authentication_status"):
    username = st.session_state.get("username")
    st.session_state.setdefault('view', 'dashboard')

    if st.session_state.view == 'dashboard':
        _sidebar_header(username, is_guest=False)
        render_dashboard(username)
    else:
        render_main_app(username, is_guest=False)

else:
    if 'page' not in st.session_state:
        st.session_state.page = 'login'

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
                elif username in config.get("credentials", {}).get("usernames", {}):
                    st.error("That username is already taken.")
                else:
                    hashed_pw = bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    config.setdefault("credentials", {}).setdefault("usernames", {})
                    config["credentials"]["usernames"][username] = {
                        "email": email,
                        "name": full_name,
                        "password": hashed_pw,
                    }
                    save_config(config)
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