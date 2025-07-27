import os
import subprocess
import tempfile

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

def get_file_summary(content:str,file_path:str) -> str:
    
    return ""
            
        
            
        