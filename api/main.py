import sys
import os

# Add backend/src to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend", "src"))

from app.main import app
