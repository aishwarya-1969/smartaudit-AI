import sqlite3
from .config import DB_PATH

def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init():
    with conn() as c:
        c.execute("create table if not exists history(k text primary key, id text, date text, vendor text, employee text, amount real, invoice text, label real, source text, loaded_by text)")
        c.execute("create table if not exists history_files(name text, user text, rows int, added int, skipped int, loaded_at text)")
        c.execute("create table if not exists users(name text primary key, pw text not null, role text not null)")
