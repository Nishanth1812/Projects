import sqlite3 

# Function to initialise the database and create the document storing table 

def init_db():
    con=sqlite3.connect("database.db") 
    cur=con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            content TEXT
        )
    """)
    con.commit()
    con.close() 
    
    
# Function to save the uploaded document into the database 
def doc_save(name,content):
    con=sqlite3.connect("database.db") 
    cur=con.cursor()
    cur.execute("INSERT INTO documents (name, content) VALUES (?, ?)", (name, content))
    con.commit()
    con.close() 
    
    
# Function to get all the stored documents 

def get_doc(name: str | None = None):
    """Retrieve document content.

    If `name` is provided, return the concatenated content for that document name.
    If `name` is None, return a list of all document contents.
    """
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    if name:
        cur.execute("SELECT content FROM documents WHERE name = ?", (name,))
        rows = cur.fetchall()
        # Concatenate multiple rows (e.g., pages) into a single string
        content = "\n".join(row[0] for row in rows)
        con.close()
        return content
    else:
        cur.execute("SELECT content FROM documents")
        doc = [row[0] for row in cur.fetchall()]
        con.close()
        return doc
