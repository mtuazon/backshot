import sqlite3

def recreate_inventory_table():
    conn = sqlite3.connect("bfp_inventory.db")
    cursor = conn.cursor()
    
    # Drop the existing inventory table if it exists
    cursor.execute("DROP TABLE IF EXISTS inventory")
    
    # Create the inventory table with an 'id' column (using TEXT for UUID)
    cursor.execute("""
        CREATE TABLE inventory (
            id TEXT PRIMARY KEY,
            office_id TEXT,
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
    """)
    
    conn.commit()
    conn.close()
    print("Inventory table re-created with column 'id'.")

if __name__ == '__main__':
    recreate_inventory_table()
