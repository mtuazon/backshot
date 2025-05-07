from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import uuid

app = Flask(__name__)
CORS(app)

def get_db_connection():
    conn = sqlite3.connect("bfp_inventory.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/offices', methods=['GET'])
def get_offices():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT property, office_name FROM offices")
    offices = cursor.fetchall()
    conn.close()
    return jsonify([{"id": row["property"], "name": row["office_name"]} for row in offices]), 200

@app.route('/items', methods=['GET'])
def get_items():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT inventory.id AS id, inventory.pc_name, inventory.brand_model, 
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
            "id": row["id"],
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

@app.route('/items', methods=['POST'])
def add_item():
    data = request.json
    office_id = data.get("office_id")
    computer_device = data.get("computer_device")
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

    if not office_id or not computer_device or not mac_address or not pc_name or not brand_model:
        return jsonify({"error": "Missing required fields"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT property FROM offices WHERE property = ?", (office_id,))
    office = cursor.fetchone()
    if not office:
        conn.close()
        return jsonify({"error": "Invalid office ID"}), 400

    item_id = str(uuid.uuid4())

    try:
        cursor.execute("""
            INSERT INTO inventory (id, office_id, computer_device, pc_name, brand_model, processor, motherboard, 
                                  ram, graphics_processing, internal_memory, mac_address, operating_system, 
                                  microsoft_office, antivirus_software)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (item_id, office_id, computer_device, pc_name, brand_model, processor, motherboard, ram,
              graphics_processing, internal_memory, mac_address, operating_system, microsoft_office, antivirus_software))
        conn.commit()
        conn.close()
        return jsonify({"message": "Item added successfully"}), 201
    except sqlite3.IntegrityError as e:
        conn.close()
        return jsonify({"error": str(e)}), 400

@app.route('/items/<string:item_id>', methods=['DELETE'])
def delete_item(item_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM inventory WHERE id=?", (item_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Item not found"}), 404

    cursor.execute("DELETE FROM inventory WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Item deleted successfully"}), 200

@app.route('/items/<string:item_id>', methods=['GET'])
def get_item_details(item_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT inventory.id, inventory.pc_name, inventory.brand_model, 
               inventory.processor, inventory.motherboard, inventory.ram, 
               inventory.graphics_processing, inventory.internal_memory, 
               inventory.mac_address, inventory.operating_system, 
               inventory.microsoft_office, inventory.antivirus_software, 
               inventory.computer_device, offices.office_name, inventory.office_id
        FROM inventory
        JOIN offices ON inventory.office_id = offices.property
        WHERE inventory.id = ?
    """, (item_id,))
    item = cursor.fetchone()
    conn.close()

    if item is None:
        return jsonify({"error": "Item not found"}), 404

    return jsonify(dict(item)), 200

@app.route('/items/<string:item_id>', methods=['PUT'])
def update_item(item_id):
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM inventory WHERE id = ?", (item_id,))
    if cursor.fetchone() is None:
        conn.close()
        return jsonify({"error": "Item not found"}), 404

    try:
        cursor.execute("""
            UPDATE inventory
            SET office_id = ?, computer_device = ?, pc_name = ?, brand_model = ?, processor = ?,
                motherboard = ?, ram = ?, graphics_processing = ?, internal_memory = ?, mac_address = ?,
                operating_system = ?, microsoft_office = ?, antivirus_software = ?
            WHERE id = ?
        """, (
            data.get("office_id"), data.get("computer_device"), data.get("pc_name"),
            data.get("brand_model"), data.get("processor"), data.get("motherboard"),
            data.get("ram"), data.get("graphics_processing"), data.get("internal_memory"),
            data.get("mac_address"), data.get("operating_system"),
            data.get("microsoft_office"), data.get("antivirus_software"),
            item_id
        ))
        conn.commit()
        conn.close()
        return jsonify({"message": "Item updated successfully"}), 200
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
