# ChatMyDocs: An Intelligent, Context-Aware Document Assistant

[![Python Version](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![Framework](https://img.shields.io/badge/Framework-Streamlit-red.svg)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An intelligent web application that allows you to have conversational Q&A sessions with your own documents. Upload your files, create a secure knowledge base, and get accurate, context-aware answers without worrying about information leaks or AI hallucinations.



## 📜 Overview

In an age of information overload, students, researchers, and professionals struggle to efficiently find specific information within their personal digital repositories. Standard keyword searches (`Ctrl+F`) lack semantic understanding, while general-purpose AI assistants have no access to your private documents and are prone to making things up ("hallucinating").

**ChatMyDocs** solves this by leveraging a powerful **Retrieval-Augmented Generation (RAG)** architecture. It creates a temporary, "personalized brain" for the AI composed exclusively of the information within your uploaded files, ensuring every answer is grounded in your provided material.

## ✨ Key Features

* **Conversational Q&A**: Ask complex, natural language questions and receive nuanced answers that understand the context of your documents.
* **Multi-Format Document Support**: Ingest a wide array of file types, including PDF, DOCX, PPTX, TXT, and even images (JPG, PNG) using Optical Character Recognition (OCR).
* **Secure User Accounts**: A full login/signup system allows users to save documents, manage multiple knowledge bases, and preserve chat histories for future reference.
* **Isolated Knowledge Bases**: Registered users can create multiple, distinct "Knowledge Bases" to keep conversations and contexts completely separate (e.g., one for "Biology Notes" and another for "Project Reports").
* **Frictionless Guest Mode**: A temporary, session-based guest mode provides a full-featured trial experience without requiring an account.
* **Trust and Verifiability**: By grounding every answer in the source material, the risk of AI hallucination is drastically reduced. The system will state when an answer cannot be found rather than inventing one.

## ⚙️ Technical Architecture & Stack

The application is built on a modern, scalable, and serverless stack, primarily leveraging AWS.

* **Frontend**: **Streamlit**
* **AI Orchestration**: **LangChain**
* **AI Models (via AWS Bedrock)**:
    * **Reasoning/Generation**: Anthropic Claude 3 Sonnet
    * **Embeddings**: Amazon Titan Embeddings
* **Vector Database**: **Pinecone**
* **Document Storage**: **Amazon S3**
* **User Authentication Database**: **Amazon DynamoDB**
* **Cloud Security**: **AWS IAM**
* **Deployment**: **Streamlit Community Cloud**

## 🚀 Getting Started

Follow these instructions to set up and run the project locally.

### Prerequisites

* Python 3.9 or higher
* Git
* **Tesseract OCR**: The application uses `pytesseract` for OCR on images. You may need to install the Tesseract engine on your system.
    * **macOS**: `brew install tesseract`
    * **Ubuntu/Debian**: `sudo apt-get install tesseract-ocr`
    * **Windows**: Download and run the installer from the [official Tesseract repository](https://github.com/UB-Mannheim/tesseract/wiki).

### 1. Clone the Repository

```bash
git clone [https://github.com/your-username/ChatMyDocs.git](https://github.com/your-username/ChatMyDocs.git)
cd ChatMyDocs
```

### 2. Create and Activate a Virtual Environment

```bash
# Create the virtual environment
python3 -m venv .venv

# Activate it (macOS/Linux)
source .venv/bin/activate

# Activate it (Windows)
.\.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Your Secrets

The application requires credentials for AWS and Pinecone. Create a file at `.streamlit/secrets.toml` and populate it with the following information:

```toml
# .streamlit/secrets.toml

# AWS Credentials for your IAM User
AWS_ACCESS_KEY_ID = "YOUR_AWS_ACCESS_KEY_ID"
AWS_SECRET_ACCESS_KEY = "YOUR_AWS_SECRET_ACCESS_KEY"
AWS_REGION = "us-east-1"  # Or your preferred region

# AWS S3 Bucket Name for document storage
S3_BUCKET_NAME = "your-unique-s3-bucket-name"

# Pinecone Credentials
PINECONE_API_KEY = "YOUR_PINECONE_API_KEY"
PINECONE_INDEX_NAME = "your-pinecone-index-name"
```

**Important**: Ensure your IAM user has the necessary permissions for Bedrock, S3 (GetObject, PutObject, DeleteObject, ListBucket), and DynamoDB (GetItem, PutItem, Scan).

### 5. Run the Application

Once your dependencies are installed and secrets are configured, run the following command in your terminal:

```bash
streamlit run app.py
```

The application should now be running and accessible in your web browser!

## ☁️ Deployment

This application is designed to be deployed on **Streamlit Community Cloud**. The deployment process seamlessly uses the `.streamlit/secrets.toml` file to provide the necessary credentials to the live application.

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.
