# style.py

CSS_CODE = """
<style>
/* 1. Root Variables & Theme Palette
-------------------------------------------------- */
:root {
  /* Color Palette */
  --bg-1: #0B0D19;
  --bg-2: #090B16;
  --card: rgba(18, 22, 39, 0.70);
  --card-border: rgba(255, 255, 255, 0.08);
  --text: #EAF0FF;
  --muted: #A7B2CB;
  --primary: #6AA9FF;
  --primary-2: #8FD0FF;
  --secondary: #4F6BFF;
  --success: #32D0A0;
  --danger: #FF5F7A;

  /* Sizing & Effects */
  --radius-lg: 18px;
  --radius-sm: 12px;
  --shadow-1: 0 14px 42px rgba(6, 8, 16, 0.55);
  --shadow-soft: 0 10px 28px rgba(9, 11, 22, 0.55);
  --cta-scale: 1.0;
  --cta-scale-hover: 1.035;
  --input-h: 44px;
}


/* 2. Global Styles & App Background
-------------------------------------------------- */
.stApp {
  color: var(--text);
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.04) 1px, transparent 1px),
    radial-gradient(1200px 700px at 50% -25%, rgba(255, 255, 255, 0.06), transparent 60%),
    linear-gradient(180deg, var(--bg-1) 0%, var(--bg-2) 100%);
  background-size: 40px 40px, 40px 40px, cover, 100% 100%;
  background-attachment: fixed, fixed, fixed, fixed;
  filter: saturate(105%);
}
.stApp:before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  background: radial-gradient(1200px 800px at 50% 10%, rgba(0, 0, 0, 0.18), transparent 70%);
}


/* 3. Layout Components
-------------------------------------------------- */
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(13, 16, 29, 0.95), rgba(9, 11, 22, 0.95));
  border-right: 1px solid var(--card-border);
  box-shadow: var(--shadow-1);
}
.block-container {
  padding-top: 3rem;
}
.login-card {
  background: var(--card);
  padding: 30px 34px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--card-border);
  box-shadow: var(--shadow-soft);
  position: relative;
  z-index: 1;
}


/* 4. Core UI Elements
-------------------------------------------------- */
h1, h2, h3 { color: var(--text); letter-spacing: .3px; }
h1 { font-size: 2.2rem !important; font-weight: 850; }
h2 { font-size: 1.55rem !important; font-weight: 750; }
h3 { font-size: 1.12rem !important; font-weight: 700; }
p, label, span, div { color: var(--text); }
.login-card h1 { 
  background: linear-gradient(90deg, #FFFFFF, #DDE6FF);
  -webkit-background-clip: text; background-clip: text;
  color: transparent; text-align: left; margin-bottom: 18px;
}

input, textarea, .stTextInput input, .stTextArea textarea {
  background: rgba(255, 255, 255, 0.07) !important;
  border: 1px solid rgba(255, 255, 255, 0.12) !important;
  color: var(--text) !important;
  border-radius: 12px !important;
}
.stTextInput > div > div:focus-within, .stTextArea > div > div:focus-within {
  box-shadow: 0 0 0 2px rgba(106, 169, 255, 0.45);
}

.cta-wrap, .cta-wrap-small { text-align: center; }
.cta-wrap .stButton > button, .login-card [data-testid="stFormSubmitter"] button {
  background: linear-gradient(90deg, var(--primary), var(--primary-2));
  color: #0b0f1a;
  border: none;
  padding: 12px 22px;
  border-radius: 14px;
  font-weight: 800;
  letter-spacing: .2px;
  transition: transform .14s ease, box-shadow .18s ease, filter .14s ease;
  box-shadow: 0 10px 28px rgba(106, 169, 255, 0.35);
  transform: scale(var(--cta-scale));
  min-width: 240px;
}
.cta-wrap .stButton > button:hover, .login-card [data-testid="stFormSubmitter"] button:hover {
  transform: scale(var(--cta-scale-hover)) translateY(-1px);
  filter: brightness(1.06);
  box-shadow: 0 18px 46px rgba(106, 169, 255, 0.55), 0 0 0 2px rgba(255, 255, 255, 0.10) inset;
}
.cta-wrap + .cta-wrap .stButton > button {
  background: linear-gradient(90deg, var(--secondary), #6F86FF);
  color: #f5f7ff;
  box-shadow: 0 10px 28px rgba(79, 107, 255, 0.35);
}
.cta-wrap-small .stButton > button {
  background: rgba(255, 255, 255, 0.08);
  color: var(--text);
  border: 1px solid rgba(255, 255, 255, 0.16);
  padding: 10px 18px;
  border-radius: 12px;
  font-weight: 700;
  transition: transform .14s ease, box-shadow .18s ease, filter .14s ease;
  transform: scale(1.0);
}
.cta-wrap-small .stButton > button:hover {
  transform: scale(1.03) translateY(-1px);
  box-shadow: 0 14px 36px rgba(111, 134, 255, 0.30);
}
button:has(span:contains("Create Knowledge Base")) {
  background: linear-gradient(90deg, var(--primary), var(--primary-2)) !important;
  color: #0b0f1a !important;
  border: none !important;
  border-radius: 12px !important;
  box-shadow: 0 10px 28px rgba(106, 169, 255, 0.35) !important;
  transition: transform .14s ease, box-shadow .18s ease, filter .14s ease !important;
}
button:has(span:contains("Create Knowledge Base")):hover {
  transform: scale(1.03) translateY(-1px);
  filter: brightness(1.06);
  box-shadow: 0 18px 46px rgba(106, 169, 255, 0.55) !important;
}


/* 5. Application-Specific Components
-------------------------------------------------- */
[data-testid="stFileUploader"] {
  background: rgba(255, 255, 255, 0.05);
  border: 1px dashed rgba(255, 255, 255, 0.18);
  border-radius: var(--radius-lg);
  padding: 16px;
}
[data-testid="stFileUploader"]:hover {
  border-color: rgba(106, 169, 255, 0.55);
  box-shadow: 0 0 0 2px rgba(106, 169, 255, 0.22) inset;
}

[data-testid="stChatMessage"]:has([data-testid="stAvatarIcon-assistant"]) {
  background: rgba(106, 169, 255, 0.10);
  border-left: 4px solid #7FB8FF;
  border-radius: 14px;
}
[data-testid="stChatMessage"]:has([data-testid="stAvatarIcon-user"]) {
  background: rgba(255, 255, 255, 0.05);
  border-right: 4px solid rgba(255, 255, 255, 0.20);
  border-radius: 14px;
}
[data-testid="stChatInput"] > div {
  background: rgba(12, 15, 27, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.10);
  border-radius: 16px;
  box-shadow: var(--shadow-1);
}


/* 6. Utilities & Overrides
-------------------------------------------------- */
hr, .stDivider {
  border: none;
  height: 1px;
  background: linear-gradient(90deg, rgba(255, 255, 255, 0), rgba(255, 255, 255, 0.18), rgba(255, 255, 255, 0));
}

::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, rgba(106, 169, 255, .45), rgba(79, 107, 255, .45));
  border-radius: 10px;
}
::-webkit-scrollbar-track { background: rgba(255, 255, 255, 0.06); }

.login-card [data-testid="stForm"] [data-testid="stElementContainer"]:has([data-testid="stFormSubmitButton"]) {
  margin-left: auto;
  margin-right: auto;
}

[data-testid="stTextInput"] > *:not(label):not([data-testid="stTextInputRootElement"]),
[data-testid="stTextArea"] > *:not(label):not([data-testid="stTextAreaRootElement"]) {
  display: none !important;
}

.stTextInput:has(input[type="password"]) button:focus-visible {
  outline: none !important;
  box-shadow: none !important;
}

*:has(> #login-card) > :not(#login-card) { display: none !important; }
#login-card.login-card {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
}
#login-card.login-card > h1 { margin-top: 0 !important; }

</style>
"""