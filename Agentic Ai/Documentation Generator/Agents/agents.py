from agno.agent import Agent
from agno.models.google import Gemini
from tools import knowledge_base
import os 
from dotenv import load_dotenv

load_dotenv() 




"""Github Api agent"""
github_agent=Agent(
    model=Gemini(id="gemini-2.5-flash",api_key=os.getenv("GEMINI_API_KEY")),
    tools=[],
    knowledge=knowledge_base,
    markdown=True,    
)

