
def load_users():
    try:
        with get_db_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT username, email, password_hash FROM users")
                return {r['username']: {'email': r['email'], 'password': r['password_hash']} for r in cur.fetchall()} 
    except Exception as e:
        print(f"Error while loading users: {e}")
        return {} 
    

def save_user(username,email,password_hash=None):
    try:
        with get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (username, email, password_hash)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (username) DO UPDATE SET
                        email = EXCLUDED.email,
                        password_hash = COALESCE(EXCLUDED.password_hash, users.password_hash),
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                """, (username, email, password_hash))
                return cur.fetchone()[0]
    
    except Exception as e:
        print(f"Error while saving the user: {e}")
        return None  
    
    
def user_exists(username):
    try:
        with get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM users WHERE username = %s LIMIT 1", (username,))
                return cur.fetchone() is not None 
    
    except Exception as e:
        print(f"Error with the database: {e}")
        return False 