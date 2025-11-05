from agno.agent import Agent
from agno.team import Team 
from agno.models.google import Gemini
from agno.vectordb.qdrant import Qdrant
from agno.knowledge import Knowledge
from agno.knowledge.embedder.google import GeminiEmbedder
import os 
from dotenv import load_dotenv
import asyncio 

load_dotenv() 




# Initialising the vectordb

vector_db=Qdrant(
    collection="Doc_storage",
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
    embedder=GeminiEmbedder(api_key=os.getenv("EMBEDDINGS_API_KEY"))
    ) 


# Setting up knowledge base 

knowledge_base=Knowledge(
    name="Simple rag knowledge base",
    vector_db=vector_db,
)

# Creating retriever agent 

retriever=Agent(
    name="Retriever",
    knowledge=knowledge_base,
    model=Gemini(api_key=os.getenv("GEMINI_API_KEY"),id="gemini-2.5-flash"),
    instructions="Act as an intelligent retriever agent responsible for accurately identifying and extracting the most contextually relevant and semantically aligned information from the knowledge base. Ensure that all retrieved data directly supports the user's intent, enhances reasoning depth, and maximizes retrieval precision and response relevance."
) 

# Creating the team

rag_team=Team(
    members=[retriever],
    model=Gemini(api_key=os.getenv("GEMINI_API_KEY"),id="gemini-2.5-pro"),
    # knowledge=knowledge_base,
    show_members_responses=True,
    instructions= [
    "Accurately interpret the user's query to understand their intent, context, and underlying goal.",
    "Retrieve the most contextually relevant and semantically aligned information from the knowledge base with high precision and relevance.",
    "Ensure that all retrieved information directly supports the user's intent, enhances reasoning quality, and provides a strong foundation for response generation.",
    "Present the retrieved context in a structured, clear, and concise format to maximize its usefulness for downstream processing or direct user delivery."
]

) 


# Uploading doc to knowledge base 

# asyncio.run(
#     knowledge_base.add_content_async(
#         name="WeKan Paper",
#         path=r"C:\Users\Devab\Downloads\139_dbgdgm_dynamic_brain_graph_dee.pdf",
#         metadata={"User tag":"Nishanth"}
#     )
# )


# Testing the team
asyncio.run(
    rag_team.aprint_response("What is the main purpose of the DBGDGM model and how does it improve over previous brain graph methods?",markdown=True)
)
