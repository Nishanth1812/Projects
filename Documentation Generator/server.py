from mcp.server.fastmcp import FastMCP
from groq import Groq
from utils.utils import clone_repo,parse_file,get_project_data,get_deps,get_file_summary,load_contact_info,format_analysis
import shutil
import os


# initialising the server
mcp=FastMCP(
    name="document_gen",
    host="0.0.0.0",
    port=5000
) 


# Setting up llm 
client=Groq(api_key=os.getenv("API_KEY"))


#---Adding tools---#

# TOOL-1: Codebase Analyser
@mcp.tool()
def analyse_codebase(path:str,type:str) ->dict:
    
    if type=="github":
        root,files=clone_repo(path)    
    else:
        files=[]
        
        for root,_,file in os.walk(path):
            for fname in file:
                if not fname.startswith('.') and not fname.endswith(('.pyz','.log')):
                    files.append(os.path.join(root,fname))
                    
    file_summaries=[]
    languages={}
    for f_path in files:
        file_info=parse_file(file_path=f_path)
        summary=get_file_summary(file_info["content"],file_info["path"])
        
        file_info.update({
            "summary":summary,
            "complexity score": len(file_info["content"].splitlines())
        })
        file_summaries.append(file_info)   
        lang=file_info["language"]
        languages[lang]=languages.get(lang,0)+1 
        
    entry_points,project_type,architecture,features=get_project_data(file_summaries)
    dependencies=get_deps(path=path)
    
    if type=='github':
    # deleting the temporary folders after use
        shutil.rmtree(root)
        
    return {
        "project_metadata": {
            "name": os.path.basename(path),
            "type": project_type,
            "language_breakdown": languages,
            "total_files": len(files),
            "main_entry_points": entry_points,
            "dependencies": dependencies
        },
        "file_summaries": file_summaries,
        "architecture_overview": architecture,
        "main_features": features,
        "setup_requirements": dependencies
    }
    
# TOOL-2: 

@mcp.tool()
def generate_documentation(analysis_data: dict,contact_info_path:str,documentation_style:str ="comprehensive",target_audience:str ="developers",custom_instructions:str="") -> str:
    
    # load contact info and format analysis data
    contact_info=load_contact_info(contact_info_path)
    analysis_summary=format_analysis(analysis=analysis_data)
    
    persona_map={"developers": "technical, detailed, API-first",
        "users": "simple, task-oriented, beginner-friendly",
        "mixed": "balanced, explanatory, clear and engaging"}
    
    persona_style= persona_map.get(target_audience.lower(),"adaptive")
    
    prompt=f"""You are a documentation expert writing an adaptive README.md file for a software project.

    ### Guidelines:
    - Format it in valid and clean **Markdown**
    - Use proper tone for: **{target_audience}** (style: {persona_style})
    - Style: **{documentation_style}**
    - Dynamically generate section titles (not fixed ones like  'Installation' or 'Features' unless truly relevant)
    - Ensure each README is unique based on the project data
    - Use the **custom instructions** from the user
    - Embed contact info at the end

    ### Project Analysis:
    {analysis_summary}

    ### Contact Info:
    {contact_info}

    ### Custom Instructions from User:
    {custom_instructions}

    Generate the complete README.md content below:
    """
    try:
        response = client.chat.completions.create(
        model="mixtral-8x7b-32768",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        )
        return response.choices[0].message.content.strip() # type: ignore
    
    except Exception as e:
        return f"Error generating documentation: {e}"


@mcp.tool()
def output_documentation(content:str,format:str="ask",file_name:str="README.md",save_path:str="./output/") -> dict:
    
    # Creating the output folder (if it does not exist)
    
    os.makedirs(save_path,exist_ok=True)
    path=os.path.join(save_path,file_name) 
    
    with open(path,"w") as f:
        f.write(content)
        
    user_preference=format
    if format=="ask":
        prompt=f"""The following markdown documentation has been generated and saved as '{file_name}' . 
        
        Ask the user what do they want to do with it.
        Options:
        
        1.) Display it now in the chat interface with proper format
        2.) Give a download link
        3.) Do Both
        
        Respond only with the user's preference as a single word: "display","download", or "both" ."""
        
        try:
            user_preference = client.chat.completions.create(
        model="mixtral-8x7b-32768",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        ).strip().lower() # type: ignore
        except Exception as e:
            user_preference="display"
            
    response = {
        "display_content": content if user_preference in ["display", "both"] else None,
        "download_link": path if user_preference in ["download", "both"] else None,
        "file_save  d": True,
        "output_path": path
        }
        
    return response


# Running the server
if __name__=="__main__":
    transport="sse"
    if transport=="sse":
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")