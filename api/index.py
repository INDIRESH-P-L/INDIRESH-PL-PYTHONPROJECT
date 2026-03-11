import os
import sys

# Ensure the root directory is in the path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

from app import create_app

try:
    # Create the app instance for Vercel
    app = create_app("production")
except Exception as e:
    print(f"CRITICAL ERROR during app creation: {e}")
    from flask import Flask
    app = Flask(__name__)
    @app.route("/", defaults={"path": ""})
    @app.route("/health")
    def health():
        import os
        # Only show partials for security
        db_url = os.environ.get("DATABASE_URL", "NOT FOUND")
        return {
            "status": "online",
            "db_found": db_url != "NOT FOUND",
            "db_prefix": db_url[:15] if db_url != "NOT FOUND" else None,
            "groq_found": bool(os.environ.get("GROQ_API_KEY")),
            "env": os.environ.get("FLASK_ENV", "not_set")
        }
    @app.route("/<path:path>")
    def error(path):
        import os
        return f"Initialization Error: {e}<br><br><b>DEBUG INFO:</b><br>DATABASE_URL Set? {'Yes' if os.environ.get('DATABASE_URL') else 'No'}", 500

# Vercel needs 'app' to be exposed
app = app
