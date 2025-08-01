import os
import subprocess
import tempfile
from groq import Groq


# Setting up client 
client=Groq(api_key=os.getenv("API_KEY"))

"""Utility functions for TOOL-1"""

# Cloning the repo into a temporary directory and return the filepaths 
def clone_repo(repo_link:str)-> tuple[str,list[str]]:
    
    # Cloning the repo into a temp folder
    temp_dir=tempfile.mkdtemp()
    subprocess.run(["git","clone",repo_link,temp_dir],check=True)
    
    # Return the file paths excluding the types that are to be ignored
    files=[]
    
    for root,_,file in os.walk(temp_dir):
        for fname in file:
            if not fname.startswith(".") and not fname.endswith((".pyc",".log")):
                files.append(os.path.join(root,fname))
                
    return temp_dir,files 

# Parse individual files and get the important data
def parse_file(file_path:str) -> dict:

    extension_map={".py":"python",".js":"javascript",".ts":"typescript",".java":"Java",".cpp":"c++",".c":"C",".json":"JSON",".yml":"Yaml",".md":"MarkDown",".html":"HTML",".css":"CSS",".toml":"Toml",".rs":"rust",".go":"GO"} 
        
    ext=os.path.splitext(file_path)[1] # extension of file 
    
    # Getting the language using the extension map

    lang=extension_map.get(ext.lower(),"Unknown")
    
    # Getting the file type    
    if "test" in file_path.lower():
        f_type="test"
    elif "config" in file_path.lower() or file_path.endswith((".yml",".json",".yaml")):
        f_type="config"
    elif file_path.endswith(".md"):
        f_type="Documentation"
    elif "scripts" in file_path.lower():
        f_type="Script"
    else:
        f_type="Source"

    
    try:
        with open(file_path,"r") as f:
            content=f.read()
            f.close()
    except Exception as e:
        content=""
        
    func=[]
    classes=[]
    imports=[]
    for line in content.splitlines():
        
    # getting the key functions 
        if line.strip().startswith("def"):
            func.append(line.strip())
            
    # getting the key classes 
        elif line.strip().startswith("class"):
            classes.append(line.strip())
            
    # getting the imports 
        for i in line:
            if "import" in i:
                imports.append(i)
        
    # Returning the metadata 

    return {
        "path":file_path,
        "type":f_type,
        "language":lang,
        "key_functions":func,
        "key_classes":classes,
        "imports":imports,
        "content":content
    }

# Getting the dependencies 
def get_deps(path:str) -> list:
    deps=[]
    req_path=os.path.join(path,"requirements.txt")
    if os.path.exists(req_path):
        with open(req_path,"r") as f:
            content=f.read()
            
            for line in content.splitlines():
                if line.strip() and not line.strip().startswith("#"):
                    deps.append(line.strip())
    return deps
                
# Getting all the project level data
def get_project_data(f_summaries:list) -> tuple:
    
    entry_points=[]
    frameworks=[]
    features=[]
    
    for f in f_summaries:
        content=f.get("content","")
        
        # Getting the entry points and the project type
        
        if "main" in f["path"] or "__main__" in content:
            entry_points.append(f["path"])
            
        if "flask" in content or "fastapi" in content:
            project_type="Web App"
        else:
            project_type="Library" 
            
        # Getting the frameworks and features
        
        if "flask" in content:
            frameworks.append("Flask")
        if "fastapi" in content:
            frameworks.append("FastApi")
        if "torch" in content or "tensorflow" in content:
            features.append("machine learning support")
        if "openai" in content or "groq" in content:
            features.append("LLM Integration")
            
    f_works=", ".join(set(frameworks)) or "Standard Application"
    features=list(set(features))
    return entry_points,project_type,f_works,features

# Getting the summary of each file 
def get_file_summary(content:str,file_path:str) -> str:
    
    try:
        api_key=os.getenv("API_KEY")
        if not api_key:
            return "Error: Api Key does not exist"
    
    
        # Chunking the content
        def chunk_content(content:str,max_chunk_size:int =4000) -> list:
            chunk=[]
            for i in range(0,len(content),max_chunk_size):
                chunk.append(content[i:i+max_chunk_size])
            return chunk
    
        chunks=chunk_content(content=content)
    
        # Getting summaries for each chunk
        summaries=[]
        for i,chunk in enumerate(chunks):
            prompt=(
                f"This is chunk {i+1} of a source file.\n\n"
                f"Filepath: {file_path}\n"
                f"Chunk:\n{chunk}\n"
                f"Please generate a clear and concise summary of this chunk based on its purpose and functionality."
                )
            
            
            response=client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[{"role":"user","content":prompt}],
                temperature=0.5,
                top_p=0.95,
            max_tokens=1024
            )
        
            chunk_summary= response.choices[0].message.content.strip() # type: ignore
            summaries.append(f"Chunk {i+1} Summary:\n{chunk_summary}\n")
        
        # Getting the final combined summary 
    
        combined_summaries="\n".join(summaries)
    
        final_prompt=(
            f"You are a technical documentation assistant.\n"
            f"The following are summaries of chunks from a file named {file_path}:\n\n"
            f"{combined_summaries}\n\n"
            f"Based on these, generate a final, cohesive summary that captures the full file's purpose and functionality."
        )
    
        final_response= client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[{"role":"user","content":final_prompt}],
            temperature=0.5,
            top_p=0.95,
            max_tokens=1024
            )

        return final_response.choices[0].message.content.strip()  # type: ignore
    
    except Exception as e:
        return f"[Error in LLM summarization: {e}]"

"""Utility functions for TOOL-2"""

# Loading the contact info
def load_contact_info(path:str) -> dict:
    info={}
    
    with open(path,'r') as f:
        for line in f:
            if "=" in line:
                key, val = line.strip().split('=', 1)
                info[key.strip()] = val.strip()
        
        f.close()
    return info 


# Formatting the project analysis data into a proper string to give to the llm 
def format_analysis(analysis:dict) -> str:
    
    summary=[]
    
    meta_data=analysis.get("Project metadata", {})
    
    summary.append(f"**Project Name**: {meta_data.get('name', 'N/A')}")
    summary.append(f"**Project Type**: {meta_data.get('type', 'N/A')}")
    summary.append(f"**Total Files**: {meta_data.get('total_files', 'N/A')}")
    summary.append(f"**Main Entry Points**: {', '.join(meta_data.get('main_entry_points', []))}")
    summary.append(f"**Dependencies**: {', '.join(meta_data.get('dependencies', []))}")
    summary.append(f"**Framework/Architecture**: {analysis.get('architecture_overview', 'Unknown')}")
    summary.append(f"Main Features**: {', '.join(analysis.get('main_features', []))}")
    summary.append("**File Summaries**:\n") 
    
    for f in analysis.get("file_summaries", [])[:10]:
        summary.append(f"- `{f['path']}` [{f['language']}] → {f['summary']}")
    
    return "\n".join(summary)


