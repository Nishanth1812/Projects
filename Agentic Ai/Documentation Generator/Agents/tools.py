from agno.knowledge import Knowledge
from agno.db.postgres import PostgresDb
from agno.vectordb.pgvector import PgVector
from agno.knowledge.embedder.google import GeminiEmbedder
import os 
from dotenv import load_dotenv

import asyncio
import time 
import re 
from typing import Any,List,Dict,Optional,Callable
import aiohttp
import base64 


load_dotenv() 

"""Setting up Knowledge base for agents"""

db=PostgresDb(db_url=os.getenv("DATABASE_URL"),knowledge_table="knowledge_content")
vector_db=PgVector(db_url=os.getenv("DATABASE_URL"),table_name="repo_file_embeddings",embedder=GeminiEmbedder(api_key=os.getenv("GEMINI_API_KEY"),dimensions=768)) 

knowledge_base=Knowledge(name="file_embedding_storage",vector_db=vector_db,contents_db=db)



"""Tools"""


class GithubRepoTool:
    
    text_extentions={".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".cc", ".h", ".hpp", 
        ".cs", ".php", ".rb", ".go", ".rs", ".swift", ".kt", ".scala", ".m", ".sh",
        ".pl", ".r", ".lua", ".dart", ".hs", ".ml", ".clj", ".ex", ".erl", ".groovy",
        ".html", ".htm", ".css", ".scss", ".sass", ".vue", ".svelte",
        ".json", ".yaml", ".yml", ".xml", ".toml", ".ini", ".cfg", ".conf",
        ".csv", ".sql", ".graphql", ".proto",
        ".md", ".txt", ".rst", ".adoc", ".tex",
        ".env", ".gitignore", ".dockerignore", ".bat", ".ps1", ".bash",
        ".cmake", ".mk", ".properties", ".lock", ".mod"
    }
    
    excluded_extensions = {
        ".git", ".svn", ".hg", "node_modules", "__pycache__", ".pytest_cache",
        ".venv", "venv", "env", "dist", "build", "target", ".next", ".nuxt",
        "bower_components", ".DS_Store", "Thumbs.db", ".tox", "bin", "obj"}
    
    
    excluded_patterns=[
        r"\.min\.(js|css)$", r"\.pack\.(js|css)$", r"\.map$", r"\.bundle\.(js|css)$",
        r"\.(png|jpg|jpeg|gif|bmp|svg|ico|tif|tiff|webp|avif)$",
        r"\.(mp3|wav|ogg|flac|aac|m4a)$", r"\.(mp4|avi|mkv|mov|wmv|flv|webm)$",
        r"\.(zip|rar|tar|gz|7z|bz2|xz)$", r"\.(exe|msi|dmg|pkg|deb|rpm|app)$",
        r"\.(ttf|otf|woff|woff2|eot)$", r"\.(pdf|doc|docx|xls|xlsx|ppt|pptx)$",
        r"package-lock\.json$", r"yarn\.lock$", r"composer\.lock$", r"poetry\.lock$"
    ]
    
    
    # Initialising class 
    
    def __init__(self,github_token=None,max_concurrency=15,chunk_size=1200,chunk_overlap=200,max_blob_size=2_000_000,enable_progress=True):
        
        self.github_token=github_token
        self.max_concurrency=max_concurrency
        self.chunk_size=chunk_size
        self.chunk_overlap=chunk_overlap
        self.max_blob_size=max_blob_size
        self.enable_progress=enable_progress
        self._excluded_regexes=[re.compile(pat,re.IGNORECASE) for pat in self.excluded_patterns]
        
        self._headers={"Accept":"Application/vnd.github.v3+json","User-Agent":"repo-ingest-tool/1.0"}
        
        if github_token:
            self._headers["Authorization"]=f"token {github_token}"
            
            
    async def _get_json(self,session:aiohttp.ClientSession,url,params=None):
        backoff=1.0
        max_retries=6
        
        for attempt in range(max_retries):
            try:
                async with session.get(url,headers=self._headers,params=params) as resp:
                    if resp.status==200:
                        return await resp.json()
                    
                    # Handling rate limits
                    
                    if resp.status in (403,429):
                        if reset:=resp.headers.get("X-RateLimit-Reset"):
                            delay=min(max(0,int(reset)-int(time.time()))+1,60)
                            await asyncio.sleep(delay=delay)
                            continue
                        
                    if resp.status==404:
                        raise RuntimeError(f"Resource not found: {url}")
                    
                    # Handling other errors 
                    
                    await asyncio.sleep(backoff)
                    backoff=min(backoff*2,30)
            
            except aiohttp.ClientError as e:
                if attempt==max_retries-1:
                    raise RuntimeError(f"Request failed: {e}")
                
                await asyncio.sleep(backoff)
                backoff=min(backoff*2,30)
            
            except Exception as e:
                if attempt==max_retries-1:
                    raise
                await asyncio.sleep(backoff)
                backoff=min(backoff*2,30) 
        raise RuntimeError(f"Failed to fetch {url}")
    
    async def list_repo_files(self,session,full_repo_name,branch="main"):
        
        data=await self._get_json(session=session,url=f"https://api.github.com/repos/{full_repo_name}/git/trees/{branch}",params={"recursive":"1"}) 
        
        tree=data.get("tree",[])
        if self.enable_progress:
            print(f"Found {len(tree)} items on the repository")
            
        
        filtered_files=[]
        for i in tree:
            if i.get("type")!="blob":
                continue
            
            path=i.get("path")
            if not path:
                continue
            
            
            
            # Skipping excluded files and patterns
            
            path_parts=path.split('/')
            if any(excluded in path_parts for excluded in self.excluded_extensions):
                continue
            
            if any(regex.search(path) for regex in self._excluded_regexes):
                continue 
            
            # Checking if file type is accepted or not
            
            file_name=path_parts[-1]
            if '.' in file_name:
                ext=f".{file_name.rsplit('.',1)[-1].lower()}"
                
                if ext in self.text_extentions:
                    filtered_files.append(i)
                    
            # handling files which do not have any extensions
            
            else:
                if file_name.lower() in ['dockerfile','makefile','rakefile','gemfile','procfile']:
                    filtered_files.append(i)
                    
        
        if self.enable_progress:
            print(f"Filtered to {len(filtered_files)} text/code files")
        
        return filtered_files 
    
    
    
    async def fetch_blob_text(self,session,full_repo_name,sha,size):
        
        if size>self.max_blob_size:
            return None 
        
        data=await self._get_json(session=session,url=f"https://api.github.com/repos/{full_repo_name}/git/blobs/{sha}")
        
        content=data.get("content")
        
        if not content or data.get("encoding") !="base64":
            return content 
        
        
        try:
            content+="="*((4-len(content)%4)%4)
            raw=base64.b64decode(content)
            
            # Skip any binary files 
            
            if b"\x00" in raw[:2048]:
                return None 
            
            # Decoding to human readable form 
            
            for encoding in("utf-8","latin-1"):
                try:
                    return raw.decode(encoding=encoding)
                except UnicodeDecodeError:
                    continue
            return raw.decode("utf-8",errors="ignore")
        except Exception:
            return None 
                
                
    # Chunking the text 
        
    def chunk_text(self,text):
        text=text.strip()
        if not text or len(text)<=self.chunk_size:
            return [text] if text else [] 
        
        chunks,start=[],0
        delimiters = [("\n\n", 0), (". ", 1), (".\n", 1), ("\n", 0), (" ", 0)] 
        
        while start<=len(text):
            end=int(min(start+self.chunk_size,len(text)))
            
            if end >=len(text):
                chunks.append(text[start:].strip())
                break 
            
            search_text=text[max(start,end-100):min(end + 100,len(text))] 
            chunk_end=end 
            
            for delimiter,offset in delimiters:
                if (pos:= search_text.rfind(delimiter))!=-1 and pos > len(search_text)//2:
                    chunk_end=max(start,end-100)+pos+offset
                    break 
                
                
            if chunk:=text[start,chunk_end].strip():
                chunks.append(chunk)
            start=max(start + 1, chunk_end - self.chunk_overlap)
        
        return chunks 
    
    async def verify_repo_access(self,session,full_repo_name,branch):
        try:
            await self._get_json(session,f"https://api.github.com/repos/{full_repo_name}")
            return True 
        except Exception as e:
            if self.enable_progress:
                print(F"Access to repository failed {e}")
            return False 
                
    
    async def ingest_repo(self,full_repo_name,branch,knowledge_base,batch_size,include_text_sample):
        if not knowledge_base:
            raise ValueError("Knowledge_base_required")
        
        timeout=aiohttp.ClientTimeout(total=180,connect=30,sock_read=60)
        connector=aiohttp.TCPConnector(
            limit=self.max_concurrency,
            limit_per_host=self.max_concurrency,
            force_close=False,
            enable_cleanup_closed=True,
        ) 
        
        
        async with aiohttp.Client