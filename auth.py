import os
import jwt
import datetime
import hashlib
from functools import wraps
from flask import Flask, request, jsonify, g

# === CONFIGURATION ===
SECRET_KEY = os.environ.get("OVERLORD_SECRET", "dev-secret-key-change-in-prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

app = Flask(__name__)

# === UTILS ===
def hash_password(password):
    """Secure password hashing using salt."""
    salt = os.environ.get("SALT", "static-salt") 
    return hashlib.sha256((password + salt).encode()).hexdigest()

def generate_token(user_id):
    """Generates a JWT token for the user."""
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)

def require_auth(f):
    """Decorator to protect routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            auth_header = request.headers["Authorization"]
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
        
        if not token:
            return jsonify({"error": "Missing token"}), 401
        
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
            g.user_id = payload["user_id"]
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
            
        return f(*args, **kwargs)
    return decorated

# === ROUTES ===
@app.route("/auth/login", methods=["POST"])
def login():
    """Mock login returning a JWT."""
    data = request.json
    username = data.get("username")
    password = data.get("password")
    
    # In a real app, query DB here using hash_password(password)
    # Mocking successful login for user_id=1 if password matches 'admin'
    if username == "admin" and password == "overlord":
        token = generate_token(1)
        return jsonify({"token": token, "user_id": 1})
        
    return jsonify({"error": "Invalid credentials"}), 401

@app.route("/auth/register", methods=["POST"])
def register():
    """Register a new user."""
    data = request.json
    # Insert into users table logic would go here
    return jsonify({"message": "User registered", "user_id": 123}), 201

if __name__ == "__main__":
    app.run(port=5000, debug=True)
