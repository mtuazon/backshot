import sqlite3

def create_database():
    # Connect to (or create) the database file
    conn = sqlite3.connect("bfp_inventory.db")
    cursor = conn.cursor()
    
    # Create the 'inventory' table with all the fields required by your Add.jsx form.
    # Note the 'property' column will be used as the Property ID.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            property INTEGER PRIMARY KEY AUTOINCREMENT,
            office_id TEXT,                       -- Office identifier (if needed)
            office_name TEXT,                     -- Office name
            computer_device TEXT,
            pc_name TEXT,
            brand_model TEXT,
            processor TEXT,
            motherboard TEXT,
            ram TEXT,
            graphics_processing TEXT,
            internal_memory TEXT,
            mac_address TEXT,
            operating_system TEXT,
            microsoft_office TEXT,
            antivirus_software TEXT
        )
    ''')
    
    # Create the 'offices' table with columns 'property' and 'office_name'
    # Here, 'property' is the auto-increment primary key.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS offices (
            property INTEGER PRIMARY KEY AUTOINCREMENT,
            office_name TEXT NOT NULL UNIQUE
        )
    ''')
    
    # Seed the 'offices' table with your provided list if it's empty.
    cursor.execute("SELECT COUNT(*) FROM offices")
    if cursor.fetchone()[0] == 0:
        offices = [
            ("SAO",),
            ("FSED",),
            ("FINANCE",),
            ("CRS",),
            ("HSU",),
            ("ACCOUNTING",),
            ("BUDGET",),
            ("ADMIN",),
            ("PLANS",),
            ("RD",),
            ("ARDA",),
            ("ARDO",),
            ("RCS",),
            ("ITCU/FCOS",),
            ("ROD",),
            ("CHAPLAIN",),
            ("LEGAL",),
            ("HEARING",),
            ("RLD",),
            ("GSS",),
            ("PIU",),
            ("IAS",),
            ("IIS",)
        ]
        cursor.executemany("INSERT INTO offices (office_name) VALUES (?)", offices)
    
    conn.commit()
    conn.close()
    print("Database created successfully with the required tables and fields.")

if __name__ == "__main__":
    create_database()
