# core/generate_schedule.py
import os
import json
import logging
from typing import Dict, Any, List

from google import genai
from langchain_pinecone import PineconeVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.schema import Document

logger = logging.getLogger(__name__)

# -------------------------------
# Gemini Client Setup
# -------------------------------
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# -------------------------------
# Parse Preferences
# -------------------------------
def parse_preferences(prefs_text: str) -> Dict[str, Any]:
    """
    Extract structured preferences/goals from free text using Gemini.
    Returns dict with goals, priorities, constraints, availability.
    """
    prompt = f"""
    You are a schedule assistant. The user gave preferences:
    ---
    {prefs_text}
    ---
    Convert this into a clean JSON object with keys:
    - goals: [list of main goals]
    - priorities: [list ranked high/medium/low]
    - constraints: [time, work, health constraints]
    - availability: [days and time blocks]
    Respond with ONLY valid JSON.
    """
    try:
        resp = gemini_client.responses.create(
            model=GEMINI_MODEL,
            input=prompt,
            max_output_tokens=800
        )
        prefs_json = resp.output_text.strip()
        logger.info("Gemini raw prefs: %s", prefs_json)
        return json.loads(prefs_json)
    except Exception as e:
        logger.exception("Failed to parse preferences: %s", e)
        return {
            "goals": [],
            "priorities": [],
            "constraints": [],
            "availability": []
        }

# -------------------------------
# Retrieve Tasks (Pinecone + LangChain)
# -------------------------------
def retrieve_tasks(prefs: Dict[str, Any]) -> List[Document]:
    """
    Retrieve relevant task chunks from Pinecone using Gemini embeddings.
    Filters by user namespace.
    """
    try:
        index_name = os.getenv("PINECONE_INDEX")
        user_id = prefs.get("user_id", "default_user")

        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        vectorstore = PineconeVectorStore(
            index_name=index_name,
            embedding=embeddings,
            namespace=user_id
        )

        query = " ".join(prefs.get("goals", [])) + " " + " ".join(prefs.get("priorities", []))
        retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
        results = retriever.get_relevant_documents(query)

        logger.info("Retrieved %d task chunks for query: %s", len(results), query)
        return results
    except Exception as e:
        logger.exception("Task retrieval failed: %s", e)
        return []

# -------------------------------
# Build Schedule
# -------------------------------
def build_schedule(prefs: Dict[str, Any], tasks: List[Document]) -> Dict[str, Any]:
    """
    Ask Gemini to generate a weekly schedule combining preferences + retrieved tasks.
    Returns a dict with structured week view.
    """
    try:
        tasks_text = "\n".join([doc.page_content for doc in tasks]) or "No retrieved tasks."
        prompt = f"""
        You are an AI schedule generator.
        User preferences:
        {json.dumps(prefs, indent=2)}
        
        Relevant tasks:
        {tasks_text}
        
        Create a detailed weekly schedule (Mon-Sun). 
        Output in JSON with structure:
        {{
            "week": [
                {{
                    "day": "Monday",
                    "blocks": [
                        {{"time": "09:00-11:00", "task": "Study AI"}},
                        ...
                    ]
                }},
                ...
            ]
        }}
        Ensure output is STRICT JSON.
        """
        resp = gemini_client.responses.create(
            model=GEMINI_MODEL,
            input=prompt,
            max_output_tokens=1500
        )
        schedule_json = resp.output_text.strip()
        logger.info("Gemini raw schedule: %s", schedule_json)
        return json.loads(schedule_json)
    except Exception as e:
        logger.exception("Schedule generation failed: %s", e)
        return {"week": []}
