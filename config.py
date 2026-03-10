import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "expense-tracker-secret-2026")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    
    # 1. Fix prefix for SQLAlchemy 1.4+
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)
    
    # 2. Safety fallback to prevent app crash on start
    if not SQLALCHEMY_DATABASE_URI:
        # If missing, use a dummy to allow the health check to load
        SQLALCHEMY_DATABASE_URI = "postgresql://user:pass@localhost/db"
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DATABASE   = None
    DEBUG      = False
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "YOUR_GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "YOUR_GOOGLE_CLIENT_SECRET")
    GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "default":     DevelopmentConfig,
}
