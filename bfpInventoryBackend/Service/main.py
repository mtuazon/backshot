# app.py
import os
import uuid
import bcrypt
import jwt
import datetime
from datetime import datetime as dt

from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
CORS(app)

# ─── CONFIG ────────────────────────────────────────────────────────────────────
app.config['SECRET_KEY'] = os.getenv("JWT_SECRET", "change_this_in_prod")

# ─── DB CONNECTION ─────────────────────────────────────────────────────────────
def get_db_connection():
    """
    Uses the DATABASE_URL env var. Example:
      postgres://user:password@host:5432/dbname
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set")
    conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor, sslmode="require")
    return conn

# ─── INITIALIZE USERS TABLE ────────────────────────────────────────────────────
def init_user_db():
    conn = get_db_connection()
    with conn, conn.cursor() as cur:
        cur.execute("""
          CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            user_id UUID UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password BYTEA NOT NULL,
            refresh_token TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
          );
        """)
    conn.close()

# ─── INITIALIZE INVENTORY & OFFICES TABLES ────────────────────────────────────
def init_inventory_db():
    conn = get_db_connection()
    with conn, conn.cursor() as cur:
        cur.execute("""
          CREATE TABLE IF NOT EXISTS offices (
            property SERIAL PRIMARY KEY,
            office_name TEXT NOT NULL
          );
        """)
        cur.execute("""
          CREATE TABLE IF NOT EXISTS inventory (
            id UUID PRIMARY KEY,
            office_id INTEGER REFERENCES offices(property),
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
            antivirus_software TEXT,
            status TEXT,
            timestamp TIMESTAMP
          );
        """)
    conn.close()

# Run initializers at startup
init_user_db()
init_inventory_db()

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
    data = request.json or {}
    if not all(k in data for k in ("username","email","password","confirmPassword")):
        return jsonify(error="All fields required"), 400
    if data["password"] != data["confirmPassword"]:
        return jsonify(error="Passwords must match"), 400

    hashed = bcrypt.hashpw(data["password"].encode(), bcrypt.gensalt())
    user_id = str(uuid.uuid4())

    conn = get_db_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
              "INSERT INTO users (user_id,username,email,password) VALUES (%s,%s,%s,%s)",
              (user_id, data["username"], data["email"], hashed)
            )
    except psycopg2.IntegrityError:
        conn.close()
        return jsonify(error="Username or email already exists"), 400
    conn.close()
    return jsonify(message="User registered successfully"), 201

@app.route("/login", methods=["POST"])
def login():
    data = request.json or {}
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE username=%s", (data.get("username"),))
        user = cur.fetchone()
    conn.close()

    if not user or not bcrypt.checkpw(data["password"].encode(), user["password"].tobytes()):
        return jsonify(error="Invalid username or password"), 401

    access, refresh = gen_tokens(user["user_id"])
    conn = get_db_connection()
    with conn, conn.cursor() as cur:
        cur.execute("UPDATE users SET refresh_token=%s WHERE user_id=%s", (refresh, user["user_id"]))
    conn.close()

    return jsonify(access_token=access, refresh_token=refresh), 200

@app.route("/refresh", methods=["POST"])
def refresh():
    token = (request.json or {}).get("refresh_token")
    if not token:
        return jsonify(error="Refresh token required"), 400
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return jsonify(error="Refresh token expired"), 401
    except jwt.InvalidTokenError:
        return jsonify(error="Invalid refresh token"), 403

    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM users WHERE user_id=%s AND refresh_token=%s",
                    (payload["user_id"], token))
        valid = cur.fetchone()
    conn.close()
    if not valid:
        return jsonify(error="Invalid refresh token"), 403

    new_access, _ = gen_tokens(payload["user_id"])
    return jsonify(access_token=new_access), 200

# ─── INVENTORY ROUTES ─────────────────────────────────────────────────────────
@app.route('/offices', methods=['GET'])
def get_offices():
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT property, office_name FROM offices")
        offs = cur.fetchall()
    conn.close()
    return jsonify([{"id": r["property"], "name": r["office_name"]} for r in offs]), 200

@app.route('/items', methods=['GET'])
def get_items():
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
          SELECT i.id, i.pc_name, i.brand_model, i.processor, i.motherboard, i.ram,
                 i.graphics_processing, i.internal_memory, i.mac_address,
                 i.operating_system, i.microsoft_office, i.antivirus_software,
                 i.status, i.timestamp, i.computer_device, i.office_id, o.office_name
          FROM inventory i
          JOIN offices o ON i.office_id=o.property;
        """)
        rows = cur.fetchall()
    conn.close()
    return jsonify(rows), 200

@app.route('/items', methods=['POST'])
def add_item():
    data = request.json or {}
    ts = dt.now()
    iid = str(uuid.uuid4())

    conn = get_db_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute("""
              INSERT INTO inventory (
                id, office_id, computer_device, pc_name, brand_model, processor, motherboard,
                ram, graphics_processing, internal_memory, mac_address, operating_system,
                microsoft_office, antivirus_software, status, timestamp
              ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
              iid, data.get("office_id"), data.get("computer_device"), data.get("pc_name"),
              data.get("brand_model"), data.get("processor"), data.get("motherboard"),
              data.get("ram"), data.get("graphics_processing"), data.get("internal_memory"),
              data.get("mac_address"), data.get("operating_system"), data.get("microsoft_office"),
              data.get("antivirus_software"), data.get("status"), ts
            ))
    except psycopg2.IntegrityError as e:
        conn.close()
        return jsonify(error=str(e)), 400
    conn.close()
    return jsonify(message="Item added successfully", id=iid), 201

@app.route('/items/<string:item_id>', methods=['GET'])
def get_item(item_id):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
          SELECT i.*, o.office_name
          FROM inventory i
          JOIN offices o ON i.office_id=o.property
          WHERE i.id=%s
        """, (item_id,))
        row = cur.fetchone()
    conn.close()
    if not row:
        return jsonify(error="Item not found"), 404
    return jsonify(row), 200

@app.route('/items/<string:item_id>', methods=['PUT'])
def update_item(item_id):
    data = request.json or {}
    ts = dt.now()

    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM inventory WHERE id=%s", (item_id,))
        if not cur.fetchone():
            conn.close()
            return jsonify(error="Item not found"), 404

        cur.execute("""
          UPDATE inventory
          SET office_id=%s, computer_device=%s, pc_name=%s, brand_model=%s, processor=%s,
              motherboard=%s, ram=%s, graphics_processing=%s, internal_memory=%s,
              mac_address=%s, operating_system=%s, microsoft_office=%s, antivirus_software=%s,
              status=%s, timestamp=%s
          WHERE id=%s
        """, (
          data.get("office_id"), data.get("computer_device"), data.get("pc_name"),
          data.get("brand_model"), data.get("processor"), data.get("motherboard"),
          data.get("ram"), data.get("graphics_processing"), data.get("internal_memory"),
          data.get("mac_address"), data.get("operating_system"), data.get("microsoft_office"),
          data.get("antivirus_software"), data.get("status"), ts, item_id
        ))
        conn.commit()
    conn.close()
    return jsonify(message="Item updated successfully"), 200

@app.route('/items/<string:item_id>', methods=['DELETE'])
def delete_item(item_id):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM inventory WHERE id=%s", (item_id,))
        conn.commit()
    conn.close()
    return jsonify(message="Item deleted successfully"), 200

# ─── RUN APP ──────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True)
