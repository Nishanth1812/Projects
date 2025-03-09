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
<<<<<<< HEAD
import time
from database import init_db, doc_save, get_doc

# Initialize the database
init_db()

# Load environment variables
load_dotenv()

# Get API keys from environment
gemini_api_key = os.getenv("GEMINI_API_KEY")
groq_api_key = os.getenv("GROQ_API_KEY")

<<<<<<< HEAD
if not gemini_api_key or not groq_api_key:
    st.error("Missing API keys! Check your .env file.")
=======
# Check API keys
if not gemini_api_key:
    st.error("❌ ERROR: Missing GEMINI_API_KEY! Check your .env file.")
    st.stop()
if not groq_api_key:
    st.error("❌ ERROR: Missing GROQ_API_KEY! Check your .env file.")
>>>>>>> f8e3b8238bc7eb0e67d1599e1b97a07dc0b1c71b
    st.stop()

st.title(" Q&A Chatbot")

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
def generate_embeddings():
    if "vectors" not in st.session_state:
<<<<<<< HEAD
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
=======
        try:
            # Initialize embeddings
            st.session_state.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001", google_api_key=gemini_api_key
            )

            # Load PDF documents
            data_folder = os.path.join(os.path.dirname(__file__), "Data")
            if not os.path.exists(data_folder):
                st.error(f"❌ ERROR: Data folder not found at {data_folder}")
                return

            st.session_state.loader = PyPDFDirectoryLoader(data_folder)
            st.session_state.docs = st.session_state.loader.load()

            if not st.session_state.docs:
                st.error("❌ ERROR: No PDFs found in the 'Data' folder!")
                return

            # Initialize text splitter
            st.session_state.text_splitter = RecursiveCharacterTextSplitter()
            st.session_state.final_documents = st.session_state.text_splitter.split_documents(st.session_state.docs[:20])

            if not st.session_state.final_documents:
                st.error("❌ ERROR: No text extracted from PDFs!")
                return

            # Debugging - Check document structure
            st.write(f"📄 Documents loaded!")
            

            # Create FAISS vector store
>>>>>>> f8e3b8238bc7eb0e67d1599e1b97a07dc0b1c71b
            st.session_state.vectors = FAISS.from_documents(
                st.session_state.final_documents,
                st.session_state.embeddings.embed_query,
            )
<<<<<<< HEAD
            st.success("Vector Store database is ready!")
        else:
            st.error("Embedding model is invalid. Check API key or setup.")
=======
            st.success("✅ Vector Store database is ready!")
        except Exception as e:
            st.error(f"❌ ERROR: Failed to process documents - {e}")
>>>>>>> f8e3b8238bc7eb0e67d1599e1b97a07dc0b1c71b

# User input field
user_question = st.text_input("💬 Ask a Question")

# Button to generate embeddings
if st.button("🔄 Generate Document Embeddings"):
    generate_embeddings()

# Handle question input
if user_question:
    if "vectors" not in st.session_state:
<<<<<<< HEAD
        st.error("Please run 'Document Embeddings' first.")
=======
        st.error("❌ ERROR: Please generate document embeddings first.")
>>>>>>> f8e3b8238bc7eb0e67d1599e1b97a07dc0b1c71b
    else:
        start_time = time.process_time()

<<<<<<< HEAD
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
=======
        try:
            # Create retrieval-based Q&A chain
            document_chain = create_stuff_documents_chain(llm, prompt)
            retriever = st.session_state.vectors.as_retriever()
            retrieval_chain = create_retrieval_chain(retriever, document_chain)

            # Get response
            response = retrieval_chain.invoke({"input": user_question})
            elapsed_time = time.process_time() - start_time

            # Debugging - Print response structure
            st.write("⏱️ Response Time:", elapsed_time)
            print("DEBUG RESPONSE:", response)

            # Display answer
            answer = response.get("answer", response.get("output", "⚠️ No answer found."))
            st.write("💡 **Answer:**", answer)

            # Show document similarity results
            if "context" in response and response["context"]:
                with st.expander("📄 Relevant Documents"):
                    for doc in response["context"]:
                        st.write(doc.page_content)
                        st.write("-------------------")
        except Exception as e:
            st.error(f"❌ ERROR: Failed to retrieve answer - {e}")
>>>>>>> f8e3b8238bc7eb0e67d1599e1b97a07dc0b1c71b
