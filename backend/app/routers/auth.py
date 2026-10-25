from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from ..db import conn
from ..security import admin_only, check_pw, current_user, hash_pw, make_token

router = APIRouter()

class Cred(BaseModel):
    username: str = Field(min_length=2, max_length=40)
    password: str = Field(min_length=4, max_length=128)

class RoleIn(BaseModel):
    role: Literal["Admin", "Auditor", "Viewer"]

@router.post("/register")
def register(b: Cred):
    name = b.username.strip().lower()
    with conn() as c:
        if c.execute("select 1 from users where name=?", (name,)).fetchone():
            raise HTTPException(409, "That user already exists")
        role = "Admin" if c.execute("select count(*) from users").fetchone()[0] == 0 else "Auditor"
        c.execute("insert into users values(?,?,?)", (name, hash_pw(b.password), role))
    return {"token": make_token(name), "user": {"name": name, "role": role}}

@router.post("/login")
def login(b: Cred):
    name = b.username.strip().lower()
    with conn() as c:
        row = c.execute("select * from users where name=?", (name,)).fetchone()
    if not row or not check_pw(b.password, row["pw"]):
        raise HTTPException(401, "Invalid username or password")
    return {"token": make_token(name), "user": {"name": name, "role": row["role"]}}

@router.get("/me")
def me(user=Depends(current_user)):
    return user

@router.get("/users")
def list_users(_=Depends(admin_only)):
    with conn() as c:
        return [dict(r) for r in c.execute("select name, role from users order by name")]

@router.patch("/users/{name}")
def set_role(name: str, b: RoleIn, admin=Depends(admin_only)):
    if name == admin["name"]:
        raise HTTPException(400, "You cannot change your own role")
    with conn() as c:
        c.execute("update users set role=? where name=?", (b.role, name))
    return {"ok": True}

@router.delete("/users/{name}")
def delete_user(name: str, admin=Depends(admin_only)):
    if name == admin["name"]:
        raise HTTPException(400, "You cannot remove yourself")
    with conn() as c:
        c.execute("delete from users where name=?", (name,))
    return {"ok": True}
