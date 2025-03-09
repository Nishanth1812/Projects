import streamlit as st
import os
import time
from langchain_groq import ChatGroq
from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.document_loaders import PyPDFDirectoryLoader, PyPDFLoader
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv
from database import init_db, doc_save, get_doc

# Initialize the database
init_db()

# Load environment variables
load_dotenv()

# Get API keys from environment
gemini_api_key = os.getenv("GEMINI_API_KEY")
groq_api_key = os.getenv("GROQ_API_KEY")

# Check API keys
if not gemini_api_key or not groq_api_key:
    st.error("❌ ERROR: Missing API keys! Check your .env file.")
    st.stop()

st.title("📌 Q&A Chatbot")

# Initialize LLM
llm = ChatGroq(groq_api_key=groq_api_key, model_name="Llama3-8b-8192")

# Define Prompt
prompt = ChatPromptTemplate.from_template(
    """
    Answer the questions based on the provided context only.
    Please provide the most accurate response based on the question.
    <context>
    {context}
    </context>
    Question: {input}
    """
)

# File Upload Button
uploaded_file = st.file_uploader("📂 Upload a PDF file", type=["pdf"])

if uploaded_file:
    # Save uploaded file to the "Data" directory
    os.makedirs("Data", exist_ok=True)
    file_path = os.path.join("Data", uploaded_file.name)

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    st.success(f"✅ File '{uploaded_file.name}' uploaded successfully!")

    # Load and save to the database
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    
    for doc in documents:
        doc_save(uploaded_file.name, doc.page_content)
    
    st.success("✅ Document saved in the database!")

# Function to generate vector embeddings
def generate_embeddings():
    if "vectors" not in st.session_state:
        try:
            # Initialize embeddings
            st.session_state.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001", google_api_key=gemini_api_key
            )
            st.success("✅ Embeddings initialized successfully!")
        except Exception as e:
            st.error(f"❌ ERROR: Failed to initialize embeddings: {str(e)}")

# Call function to generate embeddings
generate_embeddings()
