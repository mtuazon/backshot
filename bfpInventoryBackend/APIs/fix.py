# main.py
import os
import uuid
import bcrypt
import jwt
import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
CORS(app)

# ─── CONFIG ────────────────────────────────────────────────────────────────────
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev_secret")

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres.bdhxijjoorknsaappwrt:ghVpgGeIGWqvx7M6@"
    "aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"
)

# ─── DATABASE HELPERS ───────────────────────────────────────────────────────────
def get_db_connection():
    """
    Uses DATABASE_URL to open a psycopg2 connection.
    Returns a connection whose cursor() yields dict-rows.
    """
    conn = psycopg2.connect(DATABASE_URL, sslmode="require", cursor_factory=RealDictCursor)
    return conn

# ─── AUTH HELPERS ──────────────────────────────────────────────────────────────
def gen_tokens(user_id):
    access = jwt.encode(
        {"user_id": user_id, "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=15)},
        app.config["SECRET_KEY"],
        algorithm="HS256"
    )
    refresh = jwt.encode(
        {"user_id": user_id, "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)},
        app.config["SECRET_KEY"],
        algorithm="HS256"
    )
    return access, refresh

# ─── AUTH ROUTES ───────────────────────────────────────────────────────────────
@app.route("/register", methods=["POST"])
def register():
    data = request.json or {}
    for k in ("username", "email", "password", "confirmPassword"):
        if not data.get(k):
            return jsonify(error="All fields required"), 400
    if data["password"] != data["confirmPassword"]:
        return jsonify(error="Passwords must match"), 400

    hashed = bcrypt.hashpw(data["password"].encode(), bcrypt.gensalt())
    user_id = str(uuid.uuid4())
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (user_id, username, email, password) VALUES (%s,%s,%s,%s)",
            (user_id, data["username"], data["email"], hashed)
        )
        conn.commit()
    except psycopg2.IntegrityError:
        conn.rollback()
        return jsonify(error="Username or email already exists"), 400
    finally:
        cur.close()
        conn.close()

    return jsonify(message="User registered successfully"), 201

@app.route("/login", methods=["POST"])
def login():
    data = request.json or {}
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = %s", (data.get("username"),))
    user = cur.fetchone()
    if not user or not bcrypt.checkpw(
        data.get("password", "").encode(),
        user["password"] if isinstance(user["password"], (bytes, bytearray)) else user["password"].encode()
    ):
        cur.close()
        conn.close()
        return jsonify(error="Invalid username or password"), 401

    access, refresh = gen_tokens(user["user_id"])
    cur.execute("UPDATE users SET refresh_token = %s WHERE user_id = %s", (refresh, user["user_id"]))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify(access_token=access, refresh_token=refresh), 200

@app.route("/refresh", methods=["POST"])
def refresh_token():
    token = request.json.get("refresh_token")
    if not token:
        return jsonify(error="Refresh token required"), 400

    try:
        payload = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return jsonify(error="Refresh token expired"), 401
    except jwt.InvalidTokenError:
        return jsonify(error="Invalid refresh token"), 403

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM users WHERE user_id = %s AND refresh_token = %s",
        (payload["user_id"], token)
    )
    if not cur.fetchone():
        cur.close()
        conn.close()
        return jsonify(error="Invalid refresh token"), 403

    new_access, _ = gen_tokens(payload["user_id"])
    cur.close()
    conn.close()
    return jsonify(access_token=new_access), 200

# ─── INVENTORY ROUTES ─────────────────────────────────────────────────────────
@app.route("/offices", methods=["GET"])
def get_offices():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT property AS id, office_name AS name FROM offices")
    out = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(out), 200

@app.route("/items", methods=["GET"])
def get_items():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
      SELECT i.*, o.office_name
      FROM inventory i
      JOIN offices o ON i.office_id = o.property
      ORDER BY i.timestamp DESC
    """)
    out = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(out), 200

@app.route("/items", methods=["POST"])
def add_item():
    data = request.json or {}
    ts = datetime.datetime.utcnow()
    iid = str(uuid.uuid4())
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
          INSERT INTO inventory (
            id, office_id, computer_device, pc_name, brand_model, processor, motherboard,
            ram, graphics_processing, internal_memory, mac_address, operating_system,
            microsoft_office, antivirus_software, status, timestamp
          ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            iid, data["office_id"], data["computer_device"], data["pc_name"],
            data["brand_model"], data["processor"], data["motherboard"], data["ram"],
            data["graphics_processing"], data["internal_memory"], data["mac_address"],
            data["operating_system"], data["microsoft_office"], data["antivirus_software"],
            data["status"], ts
        ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify(error=str(e)), 400
    finally:
        cur.close()
        conn.close()

    return jsonify(message="Item added successfully", id=iid), 201

@app.route("/items/<string:item_id>", methods=["GET"])
def get_item(item_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
      SELECT i.*, o.office_name
      FROM inventory i
      JOIN offices o ON i.office_id = o.property
      WHERE i.id = %s
    """, (item_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return jsonify(error="Item not found"), 404
    return jsonify(row), 200

@app.route("/items/<string:item_id>", methods=["PUT"])
def update_item(item_id):
    data = request.json or {}
    ts = datetime.datetime.utcnow()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM inventory WHERE id = %s", (item_id,))
    if not cur.fetchone():
        cur.close()
        conn.close()
        return jsonify(error="Item not found"), 404

    cur.execute("""
      UPDATE inventory
      SET office_id=%s, computer_device=%s, pc_name=%s, brand_model=%s,
          processor=%s, motherboard=%s, ram=%s, graphics_processing=%s,
          internal_memory=%s, mac_address=%s, operating_system=%s,
          microsoft_office=%s, antivirus_software=%s, status=%s, timestamp=%s
      WHERE id = %s
    """, (
        data["office_id"], data["computer_device"], data["pc_name"],
        data["brand_model"], data["processor"], data["motherboard"], data["ram"],
        data["graphics_processing"], data["internal_memory"], data["mac_address"],
        data["operating_system"], data["microsoft_office"], data["antivirus_software"],
        data["status"], ts, item_id
    ))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify(message="Item updated successfully"), 200

@app.route("/items/<string:item_id>", methods=["DELETE"])
def delete_item(item_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM inventory WHERE id = %s", (item_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify(message="Item deleted successfully"), 200

# ─── RUN APP ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    debug = os.environ.get("FLASK_ENV") != "production"
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=debug)
