import os
import re
import time
import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Set DATABASE_URL in .env")

def connect():
    return psycopg.connect(DATABASE_URL, connect_timeout=15)

def fetch_rows(sql: str, params=(), retries: int = 2):
    """
    Executes a read-only query against PostgreSQL with automatic pooler retry.
    """
    last_err = None
    for attempt in range(retries):
        try:
            with connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SET TRANSACTION READ ONLY")
                    if params:
                        cur.execute(sql, params)
                    else:
                        # Escape % to %% so psycopg does not treat literal ILIKE '%' as parameter placeholders
                        cur.execute(sql.replace("%", "%%"))
                    cols = [d.name for d in cur.description] if cur.description else []
                    rows = cur.fetchall() if cur.description else []
            return cols, rows
        except Exception as e:
            last_err = e
            # Small pause before retry if connection dropped
            time.sleep(1)

    err_msg = str(last_err)
    if DATABASE_URL and "@" in DATABASE_URL:
        err_msg = re.sub(r'://[^@]+@', '://***:***@', err_msg)
    raise RuntimeError(f"Database query failed: {err_msg}") from None
