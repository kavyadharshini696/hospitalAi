"""
db.py — thin SQLite helper layer.
Kept deliberately simple (plain SQL, no ORM) so it's easy to explain in a viva.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "instance", "prescriptions.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # WAL mode lets reads and writes happen concurrently instead of taking an
    # exclusive lock on the whole file — this is what causes "database is
    # locked" errors under Flask's dev server (which can handle more than one
    # request at a time). busy_timeout makes SQLite retry briefly instead of
    # failing immediately if it ever does hit a momentary lock.
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def init_db():
    conn = get_db()
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Database initialised at {DB_PATH}")
