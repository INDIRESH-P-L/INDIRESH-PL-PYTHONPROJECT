import os
import secrets
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    # Security: Require SECRET_KEY in production, generate secure fallback for dev
    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        if os.environ.get("FLASK_ENV") == "production":
            raise RuntimeError("SECRET_KEY environment variable must be set in production")
        # Generate a secure random key for development
        SECRET_KEY = secrets.token_hex(32)

    # Session security
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    SESSION_COOKIE_SECURE = True  # Only sent over HTTPS
    SESSION_COOKIE_HTTPONLY = True  # Not accessible via JavaScript
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    
    if SQLALCHEMY_DATABASE_URI:
        # 1. Fix prefix for SQLAlchemy 1.4+
        if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
            SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)
        
        # 2. Automatically encode '@' in password if present
        # This fixes common connection issues with passwords like INDIRESH@2007
        if "@" in SQLALCHEMY_DATABASE_URI:
            parts = SQLALCHEMY_DATABASE_URI.split("://")
            if len(parts) > 1:
                credentials, host_info = parts[1].rsplit("@", 1)
                if ":" in credentials:
                    user, password = credentials.split(":", 1)
                    if "@" in password:
                        from urllib.parse import quote_plus
                        encoded_password = quote_plus(password)
                        SQLALCHEMY_DATABASE_URI = f"{parts[0]}://{user}:{encoded_password}@{host_info}"
    
    # 3. Safety fallback to prevent app crash on start if DB drops out
    if not SQLALCHEMY_DATABASE_URI:
        # Fall back to a local SQLite database for local testing
        SQLALCHEMY_DATABASE_URI = "sqlite:///local_fallback.db"
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DATABASE   = None
    DEBUG      = False
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "YOUR_GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "YOUR_GOOGLE_CLIENT_SECRET")
    GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
    GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "http://127.0.0.1:5001/auth/google/callback")

class DevelopmentConfig(Config):
    DEBUG = True
    # Relax cookie security for local development (HTTP)
    SESSION_COOKIE_SECURE = False

class ProductionConfig(Config):
    DEBUG = False
    # All security settings inherited from base Config

config = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "default":     DevelopmentConfig,
}
