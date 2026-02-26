import os
import sys

# Allow `from config import config` inside the package
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app

app = create_app("development")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print(f"\n  Expense Tracker  ->  http://127.0.0.1:{port}\n")
    from waitress import serve
    serve(app, host="0.0.0.0", port=port)
