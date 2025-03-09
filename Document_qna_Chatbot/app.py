import streamlit as st
import os
from langchain_groq import ChatGroq
from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.document_loaders import PyPDFDirectoryLoader, PyPDFLoader
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv
import time
from database import init_db, doc_save, get_doc

# Initialize the database
init_db()

# Load environment variables
load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")
groq_api_key = os.getenv("GROQ_API_KEY")

if not gemini_api_key or not groq_api_key:
    st.error("Missing API keys! Check your .env file.")
    st.stop()

st.title("Q&A Chatbot")

# Initialize ChatGroq
llm = ChatGroq(groq_api_key=groq_api_key, model_name="Llama3-8b-8192")

# Define Prompt
prompt = ChatPromptTemplate.from_template(
    """
Answer the questions based on the provided context only.
Please provide the most accurate response based on the question.
<context>
{context}
<context>
Question: {input}
    """
)

# File Upload Button
uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])

if uploaded_file:
    # Save uploaded file to the "Data" directory
    os.makedirs("Data", exist_ok=True)
    file_path = os.path.join("Data", uploaded_file.name)

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    st.success(f"File '{uploaded_file.name}' uploaded successfully!")

    # Load and save to the database
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    
    for doc in documents:
        doc_save(uploaded_file.name, doc.page_content)
    
    st.success("Document saved in the database!")

# Function to generate vector embeddings
def vector_embeddings():
    if "vectors" not in st.session_state:
        st.session_state.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001", google_api_key=gemini_api_key
        )

        # Load documents from the database
        doc_texts = get_doc()
        if not doc_texts:
            st.error("No documents found in the database!")
            return

        # Convert text into LangChain format
        documents = [{"page_content": text} for text in doc_texts]

        # Split documents
        st.session_state.text_splitter = RecursiveCharacterTextSplitter()
        st.session_state.final_documents = st.session_state.text_splitter.split_documents(documents[:20])

        # Ensure embeddings exist before creating FAISS store
        if hasattr(st.session_state.embeddings, "embed_query"):
            st.session_state.vectors = FAISS.from_documents(
                st.session_state.final_documents,
                st.session_state.embeddings.embed_query,
            )
            st.success("Vector Store database is ready!")
        else:
            st.error("Embedding model is invalid. Check API key or setup.")

# User input field
prompt1 = st.text_input("Enter your Question")

# Button to generate embeddings
if st.button("Document Embeddings"):
    vector_embeddings()

# Handle question input
if prompt1:
    if "vectors" not in st.session_state:
        st.error("Please run 'Document Embeddings' first.")
    else:
        start = time.process_time()

        # Create chains
        d_chain = create_stuff_documents_chain(llm, prompt)
        retriever = st.session_state.vectors.as_retriever()
        r_chain = create_retrieval_chain(retriever, d_chain)

        # Get response
        response = r_chain.invoke({"input": prompt1})
        st.write("⏱️ Response Time:", time.process_time() - start)

        # Display answer
        answer = response.get("answer", response.get("output", "No answer found."))
        st.write("💬 **Answer:**", answer)

        # Display document similarity results
        if "context" in response and response["context"]:
            with st.expander("📄 Document Similarity Search"):
                for doc in response["context"]:
                    st.write(doc.page_content)
                    st.write("-------------------")
