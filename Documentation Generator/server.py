from mcp.server.fastmcp import FastMCP
import gitpython as ghub  # type: ignore
from utils.utils import summary_gen # type: ignore
import shutil



# initialising the server
mcp=FastMCP(
    name="document_gen",
    host="0.0.0.0",
    port=5000
) 




# Adding tools 

# TOOL-1: Codebase Analyser
@mcp.tool()
def analyse_codebase(path:str,type:str) ->dict:
    
    
    # deleting the temporary folders after use
    t_path=""
    shutil.rmtree(t_path)
    return {}
    

# Running the server
if __name__=="__main__":
    transport="sse"
    if transport=="sse":
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")