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

def get_doc():
    con=sqlite3.connect("database.db") 
    cur=con.cursor()
    cur.execute("SELECT content FROM documents")
    doc=[]
    for row in cur.fetchall():
        doc.append(row[0])
    con.close()
    return doc
