import streamlit as st 
import os 
from langchain_groq import ChatGroq
from langchain_openai import OpenAIEmbeddings 
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain_core.prompts import ChatPromptTemplate  
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv 
import time

# Load environment variables
load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")
groq_api_key = os.getenv("GROQ_API_KEY")

# Ensure API keys are available
if not openai_api_key:
    st.error("❌ ERROR: Missing OPENAI_API_KEY! Check your .env file.")
if not groq_api_key:
    st.error("❌ ERROR: Missing GROQ_API_KEY! Check your .env file.")

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
        st.session_state.embeddings = OpenAIEmbeddings()
        st.session_state.loader = PyPDFDirectoryLoader("./Data")
        st.session_state.docs = st.session_state.loader.load()

        # Initialize text splitter correctly
        st.session_state.text_splitter = RecursiveCharacterTextSplitter()
        st.session_state.final_documents = st.session_state.text_splitter.split_documents(st.session_state.docs[:20])

        # Create FAISS vector store
        st.session_state.vectors = FAISS.from_documents(st.session_state.final_documents, st.session_state.embeddings)

# User input field
prompt1 = st.text_input("Enter your Question")

# Button to generate embeddings
if st.button("Document Embeddings"):
    vector_embeddings()
    st.write("✅ Vector Store database is ready!")

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

        # Display answer
        answer = response.get("answer", "⚠️ No answer found.")
        st.write("💬 **Answer:**", answer)

        # Display document similarity results
        if "context" in response and response["context"]:
            with st.expander("📄 Document Similarity Search"):
                for doc in response["context"]:
                    st.write(doc.page_content)
                    st.write("-------------------")
