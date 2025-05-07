import sqlite3

# Path to your SQLite database
db_path = r"D:\OJT_INVENTORY\finalCrud\backend\backshot\bfpInventoryBackend\APIs\bfp_inventory.db"

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Try to add the 'status' column as a TEXT (string) type
try:
    cursor.execute("ALTER TABLE inventory ADD COLUMN status TEXT")
    print("✅ 'status' column added successfully.")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("ℹ️ 'status' column already exists.")
    else:
        raise

# Commit and close
conn.commit()
conn.close()
