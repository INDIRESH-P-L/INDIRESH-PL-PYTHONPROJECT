import os
import sys

# Ensure the app can find modules in the root directory
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from app import create_app
from dotenv import load_dotenv

# Load env variables from .env if present
load_dotenv()
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
        app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
