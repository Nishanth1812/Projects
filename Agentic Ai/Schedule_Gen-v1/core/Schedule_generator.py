import json 
import os 
import logging
from langchain_pinecone import PineconeVectorStore #type: ignore
from langchain.schema import Document
from dotenv import load_dotenv
# LLM 
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI,GoogleGenerativeAIEmbeddings

load_dotenv()

# Setting up llm client , chat templates and prompts

# Creating the client
client=ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    api_key=os.getenv("GEMINI_API_KEY"), # type: ignore
    temperature=0.3,

)


# PROMPTS
extract_prompt="""You are a specialized scheduling assistant that processes natural language requests and converts them into structured data for calendar management systems. Your core task is to read user messages about meetings, appointments, or events and extract three specific types of information into a standardized JSON format.
Your role: Think like a professional executive assistant who needs to understand exactly what someone wants scheduled, when they're available, and how they want it arranged. You must distinguish between what's absolutely required versus what's just preferred, capture all timing constraints accurately, and note every special requirement or preference.
WHAT TO EXTRACT:
'priority' - Categorize each scheduling element by importance level:

must_have: Non-negotiable requirements (words like "need", "required", "must", "essential", "deadline")
preferred: Strong preferences but flexible (words like "prefer", "ideally", "would like", "hopefully")
nice_to_have: Optional desires (words like "if possible", "bonus", "would be nice", "maybe")

'availability' - Capture ALL time-related information:

days: Specific days of week or relative terms (today, tomorrow, next week)
times: Time ranges, specific times, or general periods (morning, afternoon, evening)
dates: Exact dates, date ranges, or relative dates
duration: How long the meeting should last
timezone: User's timezone if mentioned
blackout_periods: Times or dates to specifically avoid

'preferences' - Document HOW they want things arranged:

meeting_type: In-person, virtual, hybrid, phone call, etc.
location: Specific venues, room requirements, or location preferences
attendees: Who must attend vs who should be invited if available
recurring: If this repeats (daily, weekly, monthly, etc.)
preparation_time: Buffer time needed before or after
special_requirements: Equipment, accessibility needs, catering, room setup

CRITICAL RULES:

Extract ONLY information explicitly stated in the input - never guess or infer
Use null for any information not provided
Convert times to 24-hour format when clear (3pm → 15:00)
Preserve exact names and specific details as stated
If something is ambiguous, place it in the most logical category but don't split it
Always output valid JSON with exactly these three keys: 'priority', 'availability', 'preferences'
"""



task_gen_prompt = """# Weekly Schedule Generator  

You are a professional time management consultant that creates optimized weekly schedules from user inputs.  

## Core Function  
Transform user preferences and tasks into a realistic, time-blocked weekly calendar (Mon–Sun) that maximizes productivity while respecting all limitations.  

## Required Inputs  
- **User Preferences**:  
{prefs}  

- **Tasks**:  
{tasks_text}  

## Scheduling Logic  

### Priority Allocation  
- Schedule high-priority or deadline-driven tasks during peak energy times  
- Place routine/low-energy tasks in suboptimal slots  
- Ensure urgent items get adequate time before less critical activities  
- Balance workload across days  

### Time Optimization  
- Batch similar tasks for efficiency  
- Match task complexity to energy levels (deep work in high-energy slots, admin in low energy)  
- Include buffer time between different activity types  
- Account for dependencies and logical sequencing  
- Leave flexibility for interruptions/overruns  

### Constraint Adherence  
- Never schedule during blocked/unavailable periods  
- Respect fixed appointments and recurring commitments  
- Honor daily/weekly hour limits and availability windows  
- Consider preparation and transition times  
- Avoid overloading any single day  

## Output Format  
Generate **valid JSON** only:  

```json
{
  "week": [
    {
      "day": "Monday",
      "blocks": [
        {
          "time": "09:00 AM-10:30 AM",
          "task": "Task name/description",
          "priority": "high|medium|low",
          "notes": "additional context or requirements"
        }
      ]
    }
  ]
}
"""

logger=logging.getLogger(__name__)


def parse_preferences(prompt):
    try:
        resp=client.invoke(extract_prompt)
        prefs=resp.content
        logger.info("Preferences extracted from user prompt")
        return prefs
    except Exception as e:
        logger.exception("Failed to parse preferences: %s", e)
        return {
            "goals": [],
            "priorities": [],
            "constraints": [],
            "availability": []
        }


def retrieve_tasks(prefs):
    try:
        model=GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")
        vstore=PineconeVectorStore(index_name=os.getenv('INDEX_NAME'),embedding=model)

        query = " ".join(prefs.get("goals", [])) + " " + " ".join(prefs.get("priorities", []))
        retriever = vstore.as_retriever(search_kwargs={"k": 5})
        results = retriever.get_relevant_documents(query)
        
        logger.info("Retrieved %d task chunks for query: %s", len(results), query)
        return results
    except Exception as e:
        logger.exception("Task retrieval failed: %s", e)
        return []

def generate_schedule(prefs,tasks):
  
  try:
    tasks_text = "\n".join([doc.page_content for doc in tasks]) or "No retrieved tasks."
    resp=client.invoke(task_gen_prompt)
    schedule=resp.content
    logger.info("Succefully generated the schedule")
    return schedule
  except Exception as e:
    logger.exception("Schedule generation failed")  
    return []
