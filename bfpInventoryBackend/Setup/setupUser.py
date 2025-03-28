import sqlite3
import bcrypt
import uuid
from datetime import datetime

# Database Initialization
def initialize_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    
    # Create users table with refresh_token
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT UNIQUE NOT NULL,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        refresh_token TEXT,  -- ✅ Added refresh_token column
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # If the table already exists, try to add refresh_token column (safe fallback)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN refresh_token TEXT")
    except sqlite3.OperationalError:
        pass  # Column may already exist

    conn.commit()
    conn.close()

# Generate a unique user ID
def generate_user_id():
    return str(uuid.uuid4())  # Generates a random UUID

# Register a new user
def register_user(username, email, password, confirm_password):
    if password != confirm_password:
        print("❌ Error: Passwords do not match.")
        return False
    
    user_id = generate_user_id()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    try:
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO users (user_id, username, email, password) 
            VALUES (?, ?, ?, ?)
        """, (user_id, username, email, hashed_password))
        
        conn.commit()
        conn.close()
        print(f"✅ User registered successfully! User ID: {user_id}")
        return True

    except sqlite3.IntegrityError:
        print("⚠️ Error: Username or Email already exists.")
        return False

# Run database initialization
initialize_db()

# Example usage (Replace with actual user input or integrate with a form)
register_user("testuser", "test@example.com", "securepassword", "securepassword")
