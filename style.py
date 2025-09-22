CSS_CODE = """
<style>
    /* General body styling */
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    /* Main container styling */
    .stApp {
        background-color: #1a1a2e; /* Dark blue background */
        color: #e0e0e0; /* Light text color for readability */
    }

    /* Sidebar styling */
    .st-emotion-cache-16txtl3 {
        background-color: #162447; /* Slightly lighter blue for the sidebar */
        border-right: 2px solid #1f4068;
    }

    .st-emotion-cache-16txtl3 h1, .st-emotion-cache-16txtl3 h2, .st-emotion-cache-16txtl3 h3 {
        color: #e43f5a; /* Red accent color for headers */
    }

    /* File uploader styling */
    .st-emotion-cache-1fttcpj {
        border: 2px dashed #e43f5a;
        border-radius: 10px;
        background-color: #1b1b3a;
    }

    /* Button styling */
    .stButton>button {
        background-color: #e43f5a;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 20px;
        font-weight: bold;
        transition: background-color 0.3s ease;
    }

    .stButton>button:hover {
        background-color: #b33044; /* Darker red on hover */
    }

    /* --- CHAT MESSAGE STYLING --- */

    /* General styling for all chat messages */
    .stChatMessage {
        border-radius: 10px;
        padding: 16px;
        margin: 8px 0;
    }

    /* Specific styling for the ASSISTANT's message */
    [data-testid="stChatMessage"]:has([data-testid="stAvatarIcon-assistant"]) {
        background-color: #2e2e5a; /* A lighter purple-blue */
        border-left: 5px solid #e43f5a; /* Red accent border */
    }

    /* --- FIX: Added a background color for the USER's message --- */
    /* Specific styling for the USER's message */
    [data-testid="stChatMessage"]:has([data-testid="stAvatarIcon-user"]) {
        background-color: #1f4068; /* A different, distinct blue */
        border-right: 5px solid #5a7bb0; /* A lighter blue accent border */
    }

    /* Chat input styling */
    .st-emotion-cache-sno5eb {
        border-top: 2px solid #1f4068;
        background-color: #1a1a2e;
    }
</style>
"""