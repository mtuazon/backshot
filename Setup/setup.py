import sqlite3

# List of office names from the provided image
office_names = [
    "ITCU/FCOS", "ROD", "CHAPLAIN", "FSED", "LEGAL", "HEARING", "ENGINEERING",
    "GSS", "PIU", "IAS", "IIS", "ADMIN", "ACCOUNTING", "BUDGET", "PLANS",
    "ARDA", "RD", "ARDO", "ARCS", "FINANCE", "SAO", "CRS", "HSU"
]

# Connect to SQLite database (or create it)
conn = sqlite3.connect("inventory.db")
cursor = conn.cursor()

# Create Offices Table (Stores office information)
cursor.execute("""
CREATE TABLE IF NOT EXISTS offices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    office_name TEXT UNIQUE NOT NULL
)
""")

# Create Inventory Table (Stores computer details and links to offices)
cursor.execute("""
CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    office_id INTEGER NOT NULL,
    computer_device TEXT NOT NULL,
    pc_name TEXT NOT NULL,
    brand_model TEXT,
    processor TEXT,
    motherboard TEXT,
    ram TEXT,
    graphics_processing TEXT,
    internal_memory TEXT,
    mac_address TEXT UNIQUE NOT NULL,
    operating_system TEXT,
    microsoft_office TEXT,
    antivirus_software TEXT,
    FOREIGN KEY (office_id) REFERENCES offices (id) ON DELETE CASCADE
)
""")

# Insert Offices (if not exists)
for office in office_names:
    cursor.execute("INSERT OR IGNORE INTO offices (office_name) VALUES (?)", (office,))

# Commit and close connection
conn.commit()
conn.close()

print("Database and tables created successfully! Offices added.")
