import sqlite3
import os

DB_PATH = 'instance/local_fallback.db'

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get existing columns
    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]

    new_columns = [
        ('full_name', 'TEXT'),
        ('bio', 'TEXT'),
        ('phone', 'TEXT'),
        ('avatar_url', 'TEXT'),
        ('currency', 'TEXT DEFAULT "INR"'),
        ('created_at', 'DATETIME')
    ]

    for col_name, col_type in new_columns:
        if col_name not in columns:
            try:
                print(f"Adding column {col_name}...")
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                conn.commit()
            except Exception as e:
                print(f"Error adding {col_name}: {e}")
        else:
            print(f"Column {col_name} already exists.")

    conn.close()
    print("Migration completed.")

if __name__ == "__main__":
    migrate()
