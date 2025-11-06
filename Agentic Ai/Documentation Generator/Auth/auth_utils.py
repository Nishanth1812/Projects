from psycopg2.pool import SimpleConnectionPool
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import os 
from dotenv import load_dotenv 

load_dotenv()


def validate_username(username):
    if not username:
        return ("Error: Username invalid", False)
    if len(username) < 5 or len(username) > 20:
        return ("Error: The username should be between 5 and 20 characters", False)
    if not username.replace("_", "").isalnum():
        return ("Error: Username must contain only letters, numbers and underscores", False)
    return ("Valid username", True)


def validate_password(password):
    if not password:
        return ("Error: Password invalid", False)
    if len(password) < 8:
        return ("Error: Password must be at least 8 characters long", False)
    if not any(c.isupper() for c in password):
        return ("Error: Password must contain at least one uppercase letter", False)
    # if not any(c.islower() for c in password):
    #     return ("Error: Password must contain at least one lowercase letter", False)
    # if not any(c.isdigit() for c in password):
    #     return ("Error: Password must contain at least one number", False)
    # if not any(c in "!@#$%^&*()-_=+[]{};:,.<>?/" for c in password):
    #     return ("Error: Password must contain at least one special character", False)
    return ("Valid password", True)




def secure_token():
    pass 

"""Database Utils"""

database_url=os.getenv("DATABASE_URL")
_pool=None

def init_pool():
    
    global _pool
    if _pool is None:
        _pool=SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=database_url
        )
        
    return _pool 

@contextmanager
def get_db_conn():
    pool=init_pool()
    conn=pool.getconn()
    
    try:
        yield conn 
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)
        
        
def init_database():
    
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name='users' AND column_name='password_hash'
                    ) THEN
                        ALTER TABLE users ADD COLUMN password_hash TEXT;
                    END IF;
                END $$;
            """) 
                


def save_user(username, email, password_hash):
    try:
        with get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) "
                    "ON CONFLICT (username) DO UPDATE SET "
                    "email = EXCLUDED.email, password_hash = EXCLUDED.password_hash, updated_at = CURRENT_TIMESTAMP",
                    (username, email, password_hash)
                )
    except Exception as e:
        if "relation \"users\" does not exist" in str(e):
            init_database()
            with get_db_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) "
                        "ON CONFLICT (username) DO UPDATE SET "
                        "email = EXCLUDED.email, password_hash = EXCLUDED.password_hash, updated_at = CURRENT_TIMESTAMP",
                        (username, email, password_hash)
                    )
        else:
            raise


def load_user(username):
    try:
        with get_db_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, username, email, password_hash, created_at, updated_at FROM users WHERE username = %s", (username,))
                return cur.fetchone()
    except Exception as e:
        if "relation \"users\" does not exist" in str(e):
            init_database()
            with get_db_conn() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT id, username, email, password_hash, created_at, updated_at FROM users WHERE username = %s", (username,))
                    return cur.fetchone()
        else:
            raise


def user_exists(username):
    try:
        with get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM users WHERE username = %s", (username,))
                return cur.fetchone() is not None
    except Exception as e:
        if "relation \"users\" does not exist" in str(e):
            init_database()
            with get_db_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM users WHERE username = %s", (username,))
                    return cur.fetchone() is not None
        else:
            raise 
