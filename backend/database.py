
import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).parent / "supportiq.db"


def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            message TEXT NOT NULL,
            category TEXT NOT NULL,
            priority TEXT NOT NULL,
            sentiment TEXT NOT NULL,
            ai_reply TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Open',
            source TEXT NOT NULL DEFAULT 'chat',
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()

    print("SupportIQ database initialized successfully!")
