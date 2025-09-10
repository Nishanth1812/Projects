from langchain_community.document_loaders import PyPDFLoader,Docx2txtLoader 
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.schema import Document
from langchain_pinecone import PineconeVectorStore
import os 
from dotenv import load_dotenv
import re 
import uuid
import datetime

load_dotenv()

def process_doc(file_path,doc_type):
    
    # Minimal Preprocessing
    def clean_text(text): 
        text=re.sub(r"\s+"," ",text)
        text = text.replace("“", '"').replace("”", '"')
        text = text.replace("‘", "'").replace("’", "'")
        text = text.replace("–", "-").replace("—", "-")
        return text.strip()
    
    
    pages=[]
    if doc_type=="pdf":
        loader=PyPDFLoader(file_path=file_path)
        for page in loader.lazy_load(): 
            doc=clean_text(page.page_content)
            pages.append(Document(page_content=doc,metadata=page.metadata))
    elif doc_type=="docx":
        loader=Docx2txtLoader(file_path=file_path)
        page=loader.load()[0]
        doc=clean_text(page.page_content)
        pages.append(Document(page_content=doc,metadata=page.metadata))
        
    
    # Chunking 
    
    splitter=RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100
    )
    chunks=splitter.split_documents(pages)
    
    # Useful for tbe metadata of the embeddings
    batch_id = str(uuid.uuid4())
    upload_time = datetime.datetime.utcnow().isoformat()
    
    for idx, chunk in enumerate(chunks):
        chunk.metadata.update({
        "source_file": os.path.basename(file_path),
        "page_number": idx + 1,
        "doc_type": doc_type,
        "upload_batch_id": batch_id,
        "upload_time": upload_time
        })
    
    # Generating embeddings
    
    model=GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")
    
    # Using pinecone to store the embeddings
    
    vstore=PineconeVectorStore(index_name=os.getenv('INDEX_NAME'),embedding=model)
    vstore.add_documents(chunks)