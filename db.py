import os
import psycopg
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Set DATABASE_URL in .env")

def connect():
    return psycopg.connect(DATABASE_URL, connect_timeout=8)

def fetch_rows(sql: str, params=()):
    # The application uses a dedicated PostgreSQL READ-ONLY account.
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")
            if params:
                cur.execute(sql, params)
            else:
                cur.execute(sql)
            cols = [d.name for d in cur.description] if cur.description else []
            rows = cur.fetchall() if cur.description else []
    return cols, rows
