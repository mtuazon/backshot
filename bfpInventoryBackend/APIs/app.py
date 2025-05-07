from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import uuid
from datetime import datetime

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
        SELECT inventory.id, inventory.pc_name, inventory.brand_model,
               inventory.processor, inventory.motherboard, inventory.ram, inventory.graphics_processing,
               inventory.internal_memory, inventory.mac_address, inventory.operating_system,
               inventory.microsoft_office, inventory.antivirus_software, inventory.status, inventory.timestamp,
               inventory.computer_device, inventory.office_id, offices.office_name
        FROM inventory
        JOIN offices ON inventory.office_id = offices.property
    """)
    items = cursor.fetchall()
    conn.close()

    return jsonify([dict(row) for row in items]), 200

@app.route('/items', methods=['POST'])
def add_item():
    data = request.json
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    item_id = str(uuid.uuid4())

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO inventory (
                id, office_id, computer_device, pc_name, brand_model, processor, motherboard,
                ram, graphics_processing, internal_memory, mac_address, operating_system,
                microsoft_office, antivirus_software, status, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item_id,
            data.get("office_id"),
            data.get("computer_device"),
            data.get("pc_name"),
            data.get("brand_model"),
            data.get("processor"),
            data.get("motherboard"),
            data.get("ram"),
            data.get("graphics_processing"),
            data.get("internal_memory"),
            data.get("mac_address"),
            data.get("operating_system"),
            data.get("microsoft_office"),
            data.get("antivirus_software"),
            data.get("status"),
            timestamp
        ))
        conn.commit()
        return jsonify({"message": "Item added successfully", "id": item_id}), 201
    except sqlite3.IntegrityError as e:
        return jsonify({"error": str(e)}), 400
    finally:
        conn.close()

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
               inventory.computer_device, inventory.status, inventory.timestamp,
               inventory.office_id, offices.office_name
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
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
                operating_system = ?, microsoft_office = ?, antivirus_software = ?, status = ?, timestamp = ?
            WHERE id = ?
        """, (
            data.get("office_id"),
            data.get("computer_device"),
            data.get("pc_name"),
            data.get("brand_model"),
            data.get("processor"),
            data.get("motherboard"),
            data.get("ram"),
            data.get("graphics_processing"),
            data.get("internal_memory"),
            data.get("mac_address"),
            data.get("operating_system"),
            data.get("microsoft_office"),
            data.get("antivirus_software"),
            data.get("status"),
            timestamp,
            item_id
        ))
        conn.commit()
        return jsonify({"message": "Item updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/items/<string:item_id>', methods=['DELETE'])
def delete_item(item_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Item deleted successfully"}), 200

if __name__ == '__main__':
    app.run(debug=True)
