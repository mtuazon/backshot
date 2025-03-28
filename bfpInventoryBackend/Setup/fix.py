import sqlite3

def add_refresh_token_column():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN refresh_token TEXT")
        print("✅ 'refresh_token' column added successfully.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("⚠️ 'refresh_token' column already exists.")
        else:
            print("❌ Error while adding column:", e)

    conn.commit()
    conn.close()

add_refresh_token_column()
