import sqlite3
import os
from flask import g, current_app


def get_db():
    """Return a database connection, reusing it within a request context."""
    if "db" not in g:
        db_path = current_app.config["DATABASE"]
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    """Create tables if they don't exist."""
    with app.app_context():
        db = get_db()
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT,
                google_id TEXT UNIQUE,
                email TEXT UNIQUE
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER NOT NULL,
                type      TEXT    NOT NULL CHECK(type IN ('income','expense')),
                category  TEXT    NOT NULL,
                amount    REAL    NOT NULL CHECK(amount > 0),
                note      TEXT    DEFAULT '',
                date      TEXT    NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );

            CREATE TABLE IF NOT EXISTS limits (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id        INTEGER NOT NULL,
                category       TEXT    NOT NULL,
                monthly_limit  REAL    NOT NULL CHECK(monthly_limit > 0),
                UNIQUE(user_id, category),
                FOREIGN KEY (user_id) REFERENCES users (id)
            );

            CREATE TABLE IF NOT EXISTS ai_memory (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL,
                key          TEXT    NOT NULL, -- 'instruction', 'goal', 'preference'
                content      TEXT    NOT NULL,
                created_at   TEXT    DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, key, content),
                FOREIGN KEY (user_id) REFERENCES users (id)
            );

            CREATE INDEX IF NOT EXISTS idx_tx_user ON transactions(user_id);
            CREATE INDEX IF NOT EXISTS idx_tx_type ON transactions(type);
            CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(date);
        """)
        # Migration: Add Google columns if they don't exist
        try:
            db.execute("ALTER TABLE users ADD COLUMN google_id TEXT UNIQUE")
            db.execute("ALTER TABLE users ADD COLUMN email TEXT UNIQUE")
        except sqlite3.OperationalError:
            # Columns probably already exist
            pass
        
        db.commit()
