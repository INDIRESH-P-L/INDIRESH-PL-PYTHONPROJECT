import os
import sys
import importlib

# Ensure the app can find modules in the root directory
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from dotenv import load_dotenv
# Load env variables from .env BEFORE importing anything from the app
load_dotenv()

# Force reimport of modules to avoid caching issues
if 'app' in sys.modules:
    del sys.modules['app']
if 'app.models' in sys.modules:
    del sys.modules['app.models']

from app import create_app

print(f"DEBUG: GROQ_API_KEY loaded? {'Yes' if os.environ.get('GROQ_API_KEY') else 'No'}")

env = os.environ.get("FLASK_ENV", "development")
app = create_app(env)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    
    if env == "production":
        from waitress import serve
        print(f"\n  TrackEx (Production)  ->  http://0.0.0.0:{port}\n")
        serve(app, host="0.0.0.0", port=port)
    else:
        print(f"\n  TrackEx (Development)  ->  http://127.0.0.1:{port}\n")
        app.run(host="0.0.0.0", port=port, debug=True, use_reloader=True)
