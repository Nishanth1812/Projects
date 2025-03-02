import streamlit as st
import os
from langchain_groq import ChatGroq
from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")
groq_api_key = os.getenv("GROQ_API_KEY")

# Ensure API keys are available
if not gemini_api_key:
    st.error("❌ ERROR: Missing GEMINI_API_KEY! Check your .env file.")
    st.stop()

if not groq_api_key:
    st.error("❌ ERROR: Missing GROQ_API_KEY! Check your .env file.")
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


# Function to generate vector embeddings
def vector_embeddings():
    if "vectors" not in st.session_state:
        st.session_state.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001", google_api_key=gemini_api_key
        )

        # Load PDF documents
        st.session_state.loader = PyPDFDirectoryLoader("./Data")
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
        print(f"Documents loaded: {len(st.session_state.final_documents)}")
        print(f"Sample document: {st.session_state.final_documents[0].page_content[:300]}")

        # Ensure embeddings exist before creating FAISS store
        if hasattr(st.session_state.embeddings, "embed_query"):
            st.session_state.vectors = FAISS.from_documents(
                st.session_state.final_documents,
                st.session_state.embeddings.embed_query,  # Pass function instead of object
            )
            st.write("✅ Vector Store database is ready!")
        else:
            st.error("❌ ERROR: Embedding model is invalid. Check API key or setup.")
            return


# User input field
prompt1 = st.text_input("Enter your Question")

# Button to generate embeddings
if st.button("Document Embeddings"):
    vector_embeddings()

# Handle question input
if prompt1:
    if "vectors" not in st.session_state:
        st.error("❌ ERROR: Please run 'Document Embeddings' first.")
    else:
        start = time.process_time()

        # Create chains
        d_chain = create_stuff_documents_chain(llm, prompt)
        retriever = st.session_state.vectors.as_retriever()
        r_chain = create_retrieval_chain(retriever, d_chain)

        # Get response
        response = r_chain.invoke({"input": prompt1})
        st.write("⏱️ Response Time:", time.process_time() - start)

        # Debugging - Print response structure
        print("DEBUG RESPONSE:", response)

        # Display answer
        answer = response.get("answer", response.get("output", "⚠️ No answer found."))
        st.write("💬 **Answer:**", answer)

        # Display document similarity results
        if "context" in response and response["context"]:
            with st.expander("📄 Document Similarity Search"):
                for doc in response["context"]:
                    st.write(doc.page_content)
                    st.write("-------------------")
