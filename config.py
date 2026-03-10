import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "expense-tracker-secret-2026")
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
    
    # 3. Safety fallback to prevent app crash on start
    if not SQLALCHEMY_DATABASE_URI:
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
