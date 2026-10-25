import os
SECRET = os.getenv("SECRET_KEY", "change-me-in-production")
DB_PATH = os.getenv("DB_PATH", "smartaudit.db")
TOKEN_HOURS = 12
MAX_UPLOAD_BYTES = 25_000_000
