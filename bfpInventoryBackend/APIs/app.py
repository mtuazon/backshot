from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend requests

# Function to connect to the SQLite database
def get_db_connection():
    conn = sqlite3.connect("bfp_inventory.db")  # Updated DB name
    conn.row_factory = sqlite3.Row  # Allows fetching rows as dictionaries
    return conn

# Fetch all offices
@app.route('/offices', methods=['GET'])
def get_offices():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT property, office_name FROM offices")  # Updated column names
    offices = cursor.fetchall()
    conn.close()

    return jsonify([{"id": row["property"], "name": row["office_name"]} for row in offices]), 200

# Fetch all inventory items with office names
@app.route('/items', methods=['GET'])
def get_items():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT inventory.property AS item_id, inventory.pc_name, inventory.brand_model, 
               inventory.processor, inventory.motherboard, inventory.ram, inventory.graphics_processing, 
               inventory.internal_memory, inventory.mac_address, inventory.operating_system, 
               inventory.microsoft_office, inventory.antivirus_software, offices.office_name
        FROM inventory
        JOIN offices ON inventory.office_id = offices.property
    """)

    items = cursor.fetchall()
    conn.close()

    items_list = [
        {
            "id": row["item_id"],
            "pc_name": row["pc_name"],
            "brand_model": row["brand_model"],
            "processor": row["processor"],
            "motherboard": row["motherboard"],
            "ram": row["ram"],
            "graphics_processing": row["graphics_processing"],
            "internal_memory": row["internal_memory"],
            "mac_address": row["mac_address"],
            "operating_system": row["operating_system"],
            "microsoft_office": row["microsoft_office"],
            "antivirus_software": row["antivirus_software"],
            "office_name": row["office_name"]
        }
        for row in items
    ]

    return jsonify(items_list), 200

# Add a new inventory item with office selection
@app.route('/items', methods=['POST'])
def add_item():
    data = request.json
    pc_name = data.get("pc_name")
    brand_model = data.get("brand_model")
    processor = data.get("processor")
    motherboard = data.get("motherboard")
    ram = data.get("ram")
    graphics_processing = data.get("graphics_processing")
    internal_memory = data.get("internal_memory")
    mac_address = data.get("mac_address")
    operating_system = data.get("operating_system")
    microsoft_office = data.get("microsoft_office")
    antivirus_software = data.get("antivirus_software")
    office_id = data.get("office_id")

    if not pc_name or not brand_model or not mac_address or not office_id:
        return jsonify({"error": "Missing required fields"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # Ensure the selected office exists
    cursor.execute("SELECT property FROM offices WHERE property = ?", (office_id,))
    office = cursor.fetchone()

    if not office:
        conn.close()
        return jsonify({"error": "Invalid office ID"}), 400

    item_id = str(uuid.uuid4())  # Generate unique UUID for property

    try:
        cursor.execute("""
            INSERT INTO inventory (property, office_id, computer_device, pc_name, brand_model, processor, motherboard, 
                                  ram, graphics_processing, internal_memory, mac_address, operating_system, 
                                  microsoft_office, antivirus_software)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (item_id, office_id, "Computer", pc_name, brand_model, processor, motherboard, ram,
              graphics_processing, internal_memory, mac_address, operating_system, microsoft_office, antivirus_software))

        conn.commit()
        conn.close()
        return jsonify({"message": "Item added successfully"}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Duplicate MAC address"}), 400

# Update an existing item
@app.route('/items/<string:item_id>', methods=['PUT'])
def update_item(item_id):
    data = request.json
    pc_name = data.get("pc_name")
    brand_model = data.get("brand_model")
    processor = data.get("processor")
    motherboard = data.get("motherboard")
    ram = data.get("ram")
    graphics_processing = data.get("graphics_processing")
    internal_memory = data.get("internal_memory")
    mac_address = data.get("mac_address")
    operating_system = data.get("operating_system")
    microsoft_office = data.get("microsoft_office")
    antivirus_software = data.get("antivirus_software")
    office_id = data.get("office_id")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT property FROM offices WHERE property = ?", (office_id,))
    office = cursor.fetchone()
    
    if not office:
        conn.close()
        return jsonify({"error": "Invalid office ID"}), 400

    cursor.execute("""
        UPDATE inventory 
        SET office_id=?, pc_name=?, brand_model=?, processor=?, motherboard=?, ram=?, 
            graphics_processing=?, internal_memory=?, mac_address=?, operating_system=?, 
            microsoft_office=?, antivirus_software=?
        WHERE property=?
    """, (office_id, pc_name, brand_model, processor, motherboard, ram,
          graphics_processing, internal_memory, mac_address, operating_system, 
          microsoft_office, antivirus_software, item_id))

    conn.commit()
    conn.close()

    return jsonify({"message": "Item updated successfully"}), 200

# Remove an inventory item
@app.route('/items/<string:item_id>', methods=['DELETE'])
def delete_item(item_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM inventory WHERE property=?", (item_id,))
    conn.commit()
    conn.close()

    return jsonify({"message": "Item deleted successfully"}), 200

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
