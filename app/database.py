from .extensions import db
import os

def init_db(app):
    """Initialize the database and create tables."""
    with app.app_context():
        # This will create all required tables in Supabase if they don't exist
        db.create_all()
        print("Supabase database initialized and tables created.")

def get_db():
    """Keep for backward compatibility if any raw SQL is still used."""
    return db.session

def close_db(e=None):
    """SQLAlchemy handles its own session closing."""
    pass
