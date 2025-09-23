# app.py

import os
import uuid
import streamlit as st
import streamlit_authenticator as stauth
import bcrypt  # <-- 1. ADD THIS IMPORT

from rag_core import process_and_store_documents, create_conversational_chain
from style import CSS_CODE  # <- all CSS comes from here
from auth import load_config, save_config

# -------------------------------
# Page Configuration & Global CSS
# -------------------------------
st.set_page_config(page_title="ChatMyDocs", page_icon="🤖", layout="wide")
st.markdown(CSS_CODE, unsafe_allow_html=True)  # <- only style injection

# -------------------------------
# Load Auth Config & Authenticator
# -------------------------------
config = load_config()
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)


# -------------------------------
# Wizard helpers
# -------------------------------
def _init_wizard_state():
    st.session_state.setdefault("wizard_step", 1)  # 1=Upload, 2=Process, 3=Chat
    st.session_state.setdefault("upload_buffer", [])  # [{'name': str, 'data': bytes}]
    st.session_state.setdefault("saved_file_paths", [])  # absolute paths saved to disk
    st.session_state.setdefault("rag_chain", None)
    st.session_state.setdefault("messages", [])


def _reset_wizard(clear_chain=True):
    st.session_state.wizard_step = 1
    st.session_state.upload_buffer = []
    st.session_state.saved_file_paths = []
    if clear_chain:
        st.session_state.rag_chain = None
        st.session_state.messages = []


def _sidebar_header(username: str, is_guest: bool):
    with st.sidebar:
        if is_guest:
            st.subheader("🚀 Welcome, Guest!")
            st.info("Your session is temporary. Sign up to save your knowledge bases.")
        else:
            st.subheader(f'Welcome, {st.session_state.get("name", username)}!')
            authenticator.logout(location="sidebar")

        st.markdown("### Progress")
        steps = ["1. Upload", "2. Process", "3. Chat"]
        active = st.session_state.get("wizard_step", 1)
        for i, label in enumerate(steps, start=1):
            bullet = "✅" if active > i else ("🟢" if active == i else "⚪️")
            st.write(f"{bullet} {label}")

        if st.button("Start Over", key="btn_reset_wizard_sidebar"):
            _reset_wizard()
            st.rerun()


# -------------------------------
# Step 1 — Upload
# -------------------------------
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


# -------------------------------
# Step 2 — Process
# -------------------------------
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

    st.markdown('<div class="cta-wrap">', unsafe_allow_html=True)
    if st.button("Create Knowledge Base", key="btn_create_kb"):
        with st.spinner("Processing documents..."):
            base_dir = f"data/{username}"
            temp_dir = os.path.join(base_dir, "temp_docs")
            db_dir = os.path.join(base_dir, "db")
            os.makedirs(temp_dir, exist_ok=True)

            saved_paths = []
            for it in st.session_state.upload_buffer:
                p = os.path.join(temp_dir, it["name"])
                with open(p, "wb") as f:
                    f.write(it["data"])
                saved_paths.append(p)

            st.session_state.saved_file_paths = saved_paths
            vector_store = process_and_store_documents(saved_paths, db_dir)
            st.session_state.rag_chain = create_conversational_chain(vector_store)
            st.session_state.messages = []
            st.success("Knowledge Base created!")
            st.session_state.wizard_step = 3
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    c1, c2, _ = st.columns([1, 1, 6])
    with c1:
        if st.button("← Back", key="btn_process_back"):
            st.session_state.wizard_step = 1
            st.rerun()
    with c2:
        if st.button("Skip to Chat", key="btn_process_skip", disabled=st.session_state.rag_chain is None):
            st.session_state.wizard_step = 3
            st.rerun()


# -------------------------------
# Step 3 — Chat
# -------------------------------
def step_chat():
    st.header("3. Chat")
    st.title("📄 ChatMyDocs")
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

    c1, c2, _ = st.columns([1, 1, 6])
    with c1:
        if st.button("← Back to Process", key="btn_chat_back"):
            st.session_state.wizard_step = 2
            st.rerun()
    with c2:
        if st.button("Start a New KB", key="btn_chat_new"):
            _reset_wizard(clear_chain=True)
            st.rerun()


# -------------------------------
# Main Application View (Wizard)
# -------------------------------
def render_main_app(username: str, is_guest: bool = False):
    _init_wizard_state()
    _sidebar_header(username, is_guest)

    step = st.session_state.wizard_step
    if step == 1:
        step_upload(username)
    elif step == 2:
        step_process(username)
    else:
        step_chat()


# -------------------------------
# Router: Guest / Authenticated / Login-Register
# -------------------------------
if st.session_state.get('guest_mode', False):
    render_main_app(st.session_state.get('guest_uuid', str(uuid.uuid4())), is_guest=True)

elif st.session_state.get("authentication_status"):
    render_main_app(st.session_state.get("username", "user"))

else:
    if 'page' not in st.session_state:
        st.session_state.page = 'login'

    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        # stable hook so style.py can target the auth UI
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
                    # ---- 2. REPLACE THE BROKEN LINE WITH THIS ----
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

        st.markdown('</div>', unsafe_allow_html=True)  # close #login-card