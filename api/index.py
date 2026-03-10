import os
import sys

# Ensure the root directory is in the path so we can find the 'app' package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    # Create the app instance for Vercel
    app = create_app("production")
except Exception as e:
    print(f"CRITICAL ERROR during app creation: {e}")
    # Create a dummy app to display the error if possible
    from flask import Flask
    app = Flask(__name__)
    @app.route("/(.*)")
    def error(path):
        return f"App Initialization Error: {e}", 500

# Vercel needs 'app' to be exposed
app = app
