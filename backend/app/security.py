import hashlib, hmac, os, time
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from .config import SECRET, TOKEN_HOURS
from .db import conn

bearer = HTTPBearer(auto_error=False)

def hash_pw(password, salt=None):
    salt = salt or os.urandom(16).hex()
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000).hex()
    return f"{salt}${h}"

def check_pw(password, stored):
    return hmac.compare_digest(hash_pw(password, stored.split("$")[0]), stored)

def make_token(name):
    return jwt.encode({"sub": name, "exp": int(time.time()) + TOKEN_HOURS * 3600}, SECRET, algorithm="HS256")

def current_user(cred=Depends(bearer)):
    if not cred:
        raise HTTPException(401, "Not authenticated")
    try:
        name = jwt.decode(cred.credentials, SECRET, algorithms=["HS256"])["sub"]
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")
    with conn() as c:
        row = c.execute("select name, role from users where name=?", (name,)).fetchone()
    if not row:
        raise HTTPException(401, "User no longer exists")
    return {"name": row["name"], "role": row["role"]}

def admin_only(user=Depends(current_user)):
    if user["role"] != "Admin":
        raise HTTPException(403, "Admin only")
    return user
