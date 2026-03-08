from .extensions import db
import os

def init_db(app):
    """Initialize the database and create tables."""
    with app.app_context():
        # Only try to create directories if we are using SQLite
        if "sqlite" in app.config.get("SQLALCHEMY_DATABASE_URI", "").lower():
            db_path = app.config.get("DATABASE")
            if db_path:
                try:
                    os.makedirs(os.path.dirname(db_path), exist_ok=True)
                except OSError:
                    # Likely on a read-only filesystem (like Vercel)
                    print("Warning: Could not create directory for SQLite. Ensure DATABASE_URL is set.")
        
        # This will create tables if they don't exist
        db.create_all()
        print("Database initialized (SQLAlchemy).")

def get_db():
    """Keep for backward compatibility if any raw SQL is still used."""
    return db.session

def close_db(e=None):
    """SQLAlchemy handles its own session closing."""
    pass
