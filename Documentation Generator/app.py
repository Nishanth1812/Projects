import streamlit as st 
import os 
import asyncio
import re
import groq 
from mcp.client.sse import sse_client
from mcp import ClientSession
from dotenv import load_dotenv

load_dotenv()


st.set_page_config(page_title="Doc_Gen")

st.title("Documentation Generator")


# Groq llm wrapper
def groq_llm(prompt:str):
    client=groq.Client(api_key=os.getenv("MAIN_API_KEY"))  
    
    response=client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role":"user","content":prompt}],
        temperature=0.5,
        max_tokens=1024
    )   
    return response.choices[0].message.content 

# Setting the session state 

if "chat_history" not in st.session_state:
    st.session_state.chat_history=[]
if "doc_output" not in st.session_state:
    st.session_state.doc_output=""
if "download_path" not in st.session_state:
    st.session_state.download_path=""
    
    
# Setting the reset logic 
def reset_state():
    st.session_state.chat_history.clear()
    st.session_state.doc_output=""
    st.session_state.download_path=""
    
st.button("Reset",on_click=reset_state) 


user_prompt=st.text_area("Enter your prompt:")
contact_file=st.file_uploader("Upload contact info",type=".txt")
submit=st.button("Generate Documentation")


# Displaying chat history 
st.subheader("Chat History")

for msg in st.session_state.chat_history:
    st.markdown(f"**{msg['role'].capitalize()}:**{msg['content']}")
    
    
# MAIN

if submit and user_prompt and contact_file:
    st.session_state.chat_history.append({"role": "user", "content": user_prompt})
    
    async def orchestrate():
        async with sse_client("http://localhost:5000/sse") as (read_stream,write_stream):
            async with ClientSession(read_stream=read_stream,write_stream=write_stream) as session:
                await session.initialize() 
                
                
                # Extract repo/path link from prompt 
                extract_prompt=f"""
                You are a smart parser. Extract from the text below:

                1. The repo URL (if it's a GitHub link) as "repo"
                2. The file path (if it's a local directory) as "path"
                Only one of these will be present. Output JSON like:
                {{
                    "path": "...", or "repo": "..."
                }}

                Input:
                {user_prompt}
                """ 
                
                try:
                    extract_response=groq_llm(extract_prompt)
                    matches = re.findall(r'"(repo|path)"\s*:\s*"([^"]+)"', extract_response) # type: ignore
                    extracted = {k: v for k, v in matches}
                except:
                    st.error("Failed to extract repo link or path")
                    return 
                
                if "repo" in extracted:
                    input_type="github"
                    input_path=extracted['repo']
                elif "path" in extracted:
                    input_type="local"
                    input_path=extracted['path']
                else:
                    st.error("Could not extract a valid path or repp link.")
                    return
                
                
                # Analyse the codebase 
                
                st.info("Analysing the Codebase ...")
                tool_call=await session.call_tool("analyse_codebase",{
                    "path":input_path,
                    "type":input_type
                })
                
                analysis_data=tool_call.content[0].json
                st.session_state.chat_history.append({"role":"assistant","content":"Succesfully Analysed Codebase"})
                
                # Save contact info 
                
                contactinfo_path=os.path.join("tmp","contact_info.txt")
                os.makedirs("tmp",exist_ok=True)
                with open(contactinfo_path,'wb') as f:
                    f.write(contact_file.read()) # type: ignore
                    
                
                # Generating Documentation
                
                st.info("Generating Documentation...")
                doc_call= await session.call_tool("generate_documentation",{
                    "analysis_data":analysis_data,
                    "contact_info_path":contactinfo_path,
                    "Instructions":user_prompt
                })
                
                doc_text=doc_call.content[0].text # type: ignore 
                st.session_state.chat_history.append({"role": "assistant", "content": "README generated."}) 
                
                # Outputting the Documentation
                
                st.info("Finalizing output...")
                
                output_call= await session.call_tool("output_documentation",{
                    "content":doc_text
                })
                
                
                result=output_call.content[0].json 
                if result.get("display_content"): # type: ignore
                    st.session_state.doc_output=result["display content"] # type: ignore
                if result.get("download_link"): # type: ignore
                    st.session_state.download_path=result["download_link"] # type: ignore
    
    asyncio.run(orchestrate())
    
# Display Output              

if st.session_state.doc_output:
    st.subheader("Final Readme")
    st.code(st.session_state.doc_output,language="markdown")
    
# Download Button 

if st.session_state.download_path and os.path.exists(st.session_state.download_path):
    with open(st.session_state.download_path, "rb") as f:
        st.download_button(
            label="Download README.md",
            data=f.read(),
            file_name="README.md",
            mime="text/markdown"
        )