import os
import sys

# Ensure the root directory is in the path so we can find the 'app' package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create the app instance for Vercel
app = create_app("production")

# Vercel needs 'app' to be exposed
app = app
