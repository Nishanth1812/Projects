"""GitHub Repository Ingestion Tool - fetches files from repos recursively and stores in knowledge base."""

import asyncio
import aiohttp
import base64
import time
import re
from typing import Any, Dict, List, Optional
from Agents.tools import knowledge_base

class GitHubRepoIngestTool:

    TEXT_EXTENSIONS = {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".cc", ".h", ".hpp", 
        ".cs", ".php", ".rb", ".go", ".rs", ".swift", ".kt", ".scala", ".m", ".sh",
        ".pl", ".r", ".lua", ".dart", ".hs", ".ml", ".clj", ".ex", ".erl", ".groovy",
        ".html", ".htm", ".css", ".scss", ".sass", ".vue", ".svelte",
        ".json", ".yaml", ".yml", ".xml", ".toml", ".ini", ".cfg", ".conf",
        ".csv", ".sql", ".graphql", ".proto",
        ".md", ".txt", ".rst", ".adoc", ".tex",
        ".env", ".gitignore", ".dockerignore", ".bat", ".ps1", ".bash",
        ".cmake", ".mk", ".properties", ".lock", ".mod"
    }
    
    EXCLUDED_FILES = {
        ".git", ".svn", ".hg", "node_modules", "__pycache__", ".pytest_cache",
        ".venv", "venv", "env", "dist", "build", "target", ".next", ".nuxt",
        "bower_components", ".DS_Store", "Thumbs.db", ".tox", "bin", "obj"
    }
    
    EXCLUDED_PATTERNS = [
        r"\.min\.(js|css)$", r"\.pack\.(js|css)$", r"\.map$", r"\.bundle\.(js|css)$",
        r"\.(png|jpg|jpeg|gif|bmp|svg|ico|tif|tiff|webp|avif)$",
        r"\.(mp3|wav|ogg|flac|aac|m4a)$", r"\.(mp4|avi|mkv|mov|wmv|flv|webm)$",
        r"\.(zip|rar|tar|gz|7z|bz2|xz)$", r"\.(exe|msi|dmg|pkg|deb|rpm|app)$",
        r"\.(ttf|otf|woff|woff2|eot)$", r"\.(pdf|doc|docx|xls|xlsx|ppt|pptx)$",
        r"package-lock\.json$", r"yarn\.lock$", r"composer\.lock$", r"poetry\.lock$"
    ]

    def __init__(self, github_token: Optional[str] = None, max_concurrency: int = 15, 
                 chunk_size: int = 1200, chunk_overlap: int = 150, max_blob_size: int = 2_000_000,
                 enable_progress: bool = True):
        self.github_token = github_token
        self.max_concurrency = max_concurrency
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_blob_size = max_blob_size
        self.enable_progress = enable_progress
        self._excluded_regexes = [re.compile(pat, re.IGNORECASE) for pat in self.EXCLUDED_PATTERNS]
        self._headers = {
            "Accept": "application/vnd.github.v3+json", 
            "User-Agent": "repo-ingest-tool/1.0"
        }
        if github_token:
            self._headers["Authorization"] = f"token {github_token}"

    async def _get_json(self, session: aiohttp.ClientSession, url: str, params: Optional[Dict] = None) -> Dict:
        backoff = 1.0
        max_retries = 6
        
        for attempt in range(max_retries):
            try:
                async with session.get(url, headers=self._headers, params=params) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    
                    # Rate limit handling
                    if resp.status in (403, 429):
                        if reset := resp.headers.get("X-RateLimit-Reset"):
                            delay = min(max(0, int(reset) - int(time.time())) + 1, 60)
                            await asyncio.sleep(delay)
                            continue
                    
                    # 404 - resource not found
                    if resp.status == 404:
                        raise RuntimeError(f"Resource not found: {url}")
                    
                    # Other errors - exponential backoff
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 30)
                    
            except aiohttp.ClientError as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Request failed: {e}")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)
        raise RuntimeError(f"Failed to fetch {url}")

    async def list_repo_files(self, session: aiohttp.ClientSession, full_repo_name: str, branch: str = "main") -> List[Dict]:
        data = await self._get_json(
            session, 
            f"https://api.github.com/repos/{full_repo_name}/git/trees/{branch}",
            params={"recursive": "1"}
        )
        
        tree = data.get("tree", [])
        if self.enable_progress:
            print(f"Found {len(tree)} items in repository tree")
        
        filtered_files = []
        for item in tree:
            # Only process blob (file) types, not trees (directories)
            if item.get("type") != "blob":
                continue
            
            path = item.get("path")
            if not path:
                continue
            
            # Skip excluded directories/files
            path_parts = path.split('/')
            if any(excluded in path_parts for excluded in self.EXCLUDED_FILES):
                continue
            
            # Skip excluded patterns (binary files, minified files, etc.)
            if any(regex.search(path) for regex in self._excluded_regexes):
                continue
            
            # Check if file has a text extension or is a known text file
            filename = path_parts[-1]
            if '.' in filename:
                ext = f".{filename.rsplit('.', 1)[-1].lower()}"
                if ext in self.TEXT_EXTENSIONS:
                    filtered_files.append(item)
            else:
                # Files without extension (like Dockerfile, Makefile, etc.)
                if filename.lower() in ['dockerfile', 'makefile', 'rakefile', 'gemfile', 'procfile']:
                    filtered_files.append(item)
        
        if self.enable_progress:
            print(f"Filtered to {len(filtered_files)} text/code files")
        
        return filtered_files

    async def fetch_blob_text(self, session: aiohttp.ClientSession, full_repo_name: str, sha: str, size: int) -> Optional[str]:
        if size > self.max_blob_size:
            return None
        
        data = await self._get_json(session, f"https://api.github.com/repos/{full_repo_name}/git/blobs/{sha}")
        content = data.get("content")
        
        if not content or data.get("encoding") != "base64":
            return content
        
        try:
            # Add padding if needed
            content += "=" * ((4 - len(content) % 4) % 4)
            raw = base64.b64decode(content)
            
            # Skip binary files
            if b"\x00" in raw[:2048]:
                return None
            
            # Try decoding
            for encoding in ("utf-8", "latin-1"):
                try:
                    return raw.decode(encoding)
                except UnicodeDecodeError:
                    continue
            return raw.decode("utf-8", errors="ignore")
        except Exception:
            return None

    def chunk_text(self, text: str) -> List[str]:
        text = text.strip()
        if not text or len(text) <= self.chunk_size:
            return [text] if text else []
        
        chunks, start = [], 0
        delimiters = [("\n\n", 0), (". ", 1), (".\n", 1), ("\n", 0), (" ", 0)]
        
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            
            if end >= len(text):
                chunks.append(text[start:].strip())
                break
            
            # Find best break point
            search_text = text[max(start, end - 100):min(end + 100, len(text))]
            chunk_end = end
            
            for delimiter, offset in delimiters:
                if (pos := search_text.rfind(delimiter)) != -1 and pos > len(search_text) // 2:
                    chunk_end = max(start, end - 100) + pos + offset
                    break
            
            if chunk := text[start:chunk_end].strip():
                chunks.append(chunk)
            start = max(start + 1, chunk_end - self.chunk_overlap)
        
        return chunks

    async def verify_repo_access(self, session: aiohttp.ClientSession, full_repo_name: str, branch: str = "main") -> bool:
        try:
            await self._get_json(session, f"https://api.github.com/repos/{full_repo_name}")
            return True
        except Exception as e:
            if self.enable_progress:
                print(f"Repository access failed: {e}")
            return False

    async def ingest_repo(self, full_repo_name: str, branch: str = "main", 
                         knowledge_base: Optional[Any] = None, 
                         batch_size: int = 32, include_text_sample: bool = False) -> Dict:
        if not knowledge_base:
            raise ValueError("knowledge_base required")
        
        timeout = aiohttp.ClientTimeout(total=180, connect=30, sock_read=60)
        connector = aiohttp.TCPConnector(
            limit=self.max_concurrency,
            limit_per_host=self.max_concurrency,
            force_close=False,
            enable_cleanup_closed=True,
            ttl_dns_cache=300
        )
        
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            # Verify repository access first
            if self.enable_progressx``:
                print(f"Verifying access to {full_repo_name}...")
            
            if not await self.verify_repo_access(session, full_repo_name, branch):
                return {
                    "repo": full_repo_name,
                    "branch": branch,
                    "error": "Repository not accessible",
                    "files": [],
                    "total_files": 0,
                    "total_chunks": 0
                }
            
            files = await self.list_repo_files(session, full_repo_name, branch)
            
            if not files:
                if self.enable_progress:
                    print("No files found in repository")
                return {"repo": full_repo_name, "branch": branch, "files": [], "total_files": 0, "total_chunks": 0}
            
            if self.enable_progress:
                print(f"Processing {len(files)} files from {full_repo_name}")
            
            sem = asyncio.Semaphore(self.max_concurrency)
            file_results = []
            processed_count = 0
            failed_count = 0
            
            async def process_file(file_meta: Dict) -> Optional[Dict]:
                nonlocal processed_count, failed_count
                
                async with sem:
                    path, sha, size = file_meta.get("path"), file_meta.get("sha"), int(file_meta.get("size", 0))
                    
                    if not path or not sha:
                        return None
                    
                    try:
                        text = await self.fetch_blob_text(session, full_repo_name, sha, size)
                        if not text:
                            failed_count += 1
                            return None
                        
                        chunks = self.chunk_text(text)
                        if not chunks:
                            failed_count += 1
                            return None
                        
                        stored_ids = []
                        
                        for idx, chunk_text in enumerate(chunks):
                            doc_id = f"{full_repo_name}::{path}::chunk::{idx}"
                            metadata = {
                                "repo": full_repo_name,
                                "path": path,
                                "chunk_index": idx,
                                "id": doc_id
                            }
                            if include_text_sample:
                                metadata["text_sample"] = chunk_text
                            
                            knowledge_base.add(content=chunk_text, name=doc_id, metadata=metadata)
                            stored_ids.append(doc_id)
                        
                        processed_count += 1
                        if self.enable_progress and processed_count % 10 == 0:
                            print(f"Progress: {processed_count}/{len(files)} files processed")
                        
                        return {"path": path, "chunks": len(chunks), "stored_ids": stored_ids}
                    
                    except Exception as e:
                        failed_count += 1
                        if self.enable_progress:
                            print(f"Error processing {path}: {e}")
                        return None
            
            results = await asyncio.gather(*[process_file(f) for f in files], return_exceptions=True)
            file_results = [r for r in results if isinstance(r, dict) and r]
            
            total_chunks = sum(f["chunks"] for f in file_results)
            
            if self.enable_progress:
                print(f"\n✓ Completed: {len(file_results)}/{len(files)} files successfully processed")
                print(f"✓ Total chunks created: {total_chunks}")
                print(f"✗ Failed: {failed_count} files")
            
            return {
                "repo": full_repo_name,
                "branch": branch,
                "files": file_results,
                "total_files": len(file_results),
                "total_chunks": total_chunks,
                "failed_files": failed_count
            }


# Example usage:
# import asyncio, os
# from test import GitHubRepoIngestTool
# from Agents.tools import knowledge_base
# from dotenv import load_dotenv
#
# load_dotenv()
# tool = GitHubRepoIngestTool(github_token=os.getenv("GITHUB_PAT"))
# result = asyncio.run(tool.ingest_repo("owner/repo", knowledge_base=knowledge_base))
# print(f"Processed {result['total_files']} files, {result['total_chunks']} chunks")
