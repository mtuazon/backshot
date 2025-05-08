# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import uuid
import bcrypt
import jwt
import datetime
from datetime import datetime as dt

app = Flask(__name__)
CORS(app)

# ─── CONFIG ────────────────────────────────────────────────────────────────────
app.config['SECRET_KEY'] = 'your_secret_key_here'  # change in production!

# ─── DATABASE HELPERS ───────────────────────────────────────────────────────────
def get_inventory_conn():
    conn = sqlite3.connect("bfp_inventory.db")
    conn.row_factory = sqlite3.Row
    return conn

def get_user_conn():
    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row
    return conn

# ─── INITIALIZE USERS TABLE ────────────────────────────────────────────────────
def init_user_db():
    conn = get_user_conn()
    cur = conn.cursor()
    cur.execute("""
      CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT UNIQUE NOT NULL,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password BLOB NOT NULL,
        refresh_token TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    """)
    conn.commit()
    conn.close()

init_user_db()

# ─── AUTH HELPERS ──────────────────────────────────────────────────────────────
def gen_tokens(user_id):
    access = jwt.encode(
      {'user_id': user_id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=15)},
      app.config['SECRET_KEY'], algorithm="HS256"
    )
    refresh = jwt.encode(
      {'user_id': user_id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)},
      app.config['SECRET_KEY'], algorithm="HS256"
    )
    return access, refresh

# ─── AUTH ROUTES ───────────────────────────────────────────────────────────────
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    if not all(k in data for k in ("username","email","password","confirmPassword")):
        return jsonify(error="All fields required"),400
    if data["password"] != data["confirmPassword"]:
        return jsonify(error="Passwords must match"),400

    hashed = bcrypt.hashpw(data["password"].encode(), bcrypt.gensalt())
    user_id = str(uuid.uuid4())
    conn = get_user_conn(); cur = conn.cursor()
    try:
        cur.execute(
          "INSERT INTO users (user_id,username,email,password) VALUES (?,?,?,?)",
          (user_id,data["username"],data["email"],hashed)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify(error="Username or email already exists"),400
    conn.close()
    return jsonify(message="User registered successfully"),201

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    conn = get_user_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=?", (data.get("username"),))
    user = cur.fetchone()
    if not user or not bcrypt.checkpw(data["password"].encode(), user["password"]):
        conn.close()
        return jsonify(error="Invalid username or password"),401

    access, refresh = gen_tokens(user["user_id"])
    cur.execute("UPDATE users SET refresh_token=? WHERE user_id=?", (refresh,user["user_id"]))
    conn.commit(); conn.close()
    return jsonify(access_token=access, refresh_token=refresh),200

@app.route("/refresh", methods=["POST"])
def refresh():
    token = request.json.get("refresh_token")
    if not token:
        return jsonify(error="Refresh token required"),400
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return jsonify(error="Refresh token expired"),401
    except jwt.InvalidTokenError:
        return jsonify(error="Invalid refresh token"),403

    conn = get_user_conn(); cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE user_id=? AND refresh_token=?", (payload["user_id"],token))
    if not cur.fetchone():
        conn.close()
        return jsonify(error="Invalid refresh token"),403
    new_access, _ = gen_tokens(payload["user_id"])
    conn.close()
    return jsonify(access_token=new_access),200

# ─── INVENTORY ROUTES ─────────────────────────────────────────────────────────
@app.route('/offices', methods=['GET'])
def get_offices():
    conn = get_inventory_conn(); cur = conn.cursor()
    cur.execute("SELECT property,office_name FROM offices")
    offs = [{"id":r["property"],"name":r["office_name"]} for r in cur.fetchall()]
    conn.close()
    return jsonify(offs),200

@app.route('/items', methods=['GET'])
def get_items():
    conn = get_inventory_conn(); cur = conn.cursor()
    cur.execute("""
      SELECT i.id,i.pc_name,i.brand_model,i.processor,i.motherboard,i.ram,
             i.graphics_processing,i.internal_memory,i.mac_address,
             i.operating_system,i.microsoft_office,i.antivirus_software,
             i.status,i.timestamp,i.computer_device,i.office_id,o.office_name
      FROM inventory i
      JOIN offices o ON i.office_id=o.property
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows),200

@app.route('/items', methods=['POST'])
def add_item():
    data = request.json
    ts = dt.now().strftime("%Y-%m-%d %H:%M:%S")
    iid = str(uuid.uuid4())
    conn = get_inventory_conn(); cur = conn.cursor()
    try:
        cur.execute("""
          INSERT INTO inventory (
            id,office_id,computer_device,pc_name,brand_model,processor,motherboard,
            ram,graphics_processing,internal_memory,mac_address,operating_system,
            microsoft_office,antivirus_software,status,timestamp
          ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
          iid,data["office_id"],data["computer_device"],data["pc_name"],data["brand_model"],
          data["processor"],data["motherboard"],data["ram"],data["graphics_processing"],
          data["internal_memory"],data["mac_address"],data["operating_system"],
          data["microsoft_office"],data["antivirus_software"],data["status"],ts
        ))
        conn.commit()
        return jsonify(message="Item added successfully", id=iid),201
    except sqlite3.IntegrityError as e:
        return jsonify(error=str(e)),400
    finally:
        conn.close()

@app.route('/items/<string:item_id>', methods=['GET'])
def get_item(item_id):
    conn = get_inventory_conn(); cur = conn.cursor()
    cur.execute("""
      SELECT i.*,o.office_name
      FROM inventory i
      JOIN offices o ON i.office_id=o.property
      WHERE i.id=?
    """,(item_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return jsonify(error="Item not found"),404
    return jsonify(dict(row)),200

@app.route('/items/<string:item_id>', methods=['PUT'])
def update_item(item_id):
    data = request.json
    ts = dt.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_inventory_conn(); cur = conn.cursor()
    cur.execute("SELECT 1 FROM inventory WHERE id=?", (item_id,))
    if not cur.fetchone():
        conn.close()
        return jsonify(error="Item not found"),404

    cur.execute("""
      UPDATE inventory
      SET office_id=?,computer_device=?,pc_name=?,brand_model=?,processor=?,
          motherboard=?,ram=?,graphics_processing=?,internal_memory=?,
          mac_address=?,operating_system=?,microsoft_office=?,antivirus_software=?,
          status=?,timestamp=?
      WHERE id=?
    """,(
      data["office_id"],data["computer_device"],data["pc_name"],data["brand_model"],
      data["processor"],data["motherboard"],data["ram"],data["graphics_processing"],
      data["internal_memory"],data["mac_address"],data["operating_system"],
      data["microsoft_office"],data["antivirus_software"],data["status"],ts,
      item_id
    ))
    conn.commit(); conn.close()
    return jsonify(message="Item updated successfully"),200

@app.route('/items/<string:item_id>', methods=['DELETE'])
def delete_item(item_id):
    conn = get_inventory_conn(); cur = conn.cursor()
    cur.execute("DELETE FROM inventory WHERE id=?", (item_id,))
    conn.commit(); conn.close()
    return jsonify(message="Item deleted successfully"),200

# ─── RUN APP ──────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True)
