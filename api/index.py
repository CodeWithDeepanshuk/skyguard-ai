import sys
from pathlib import Path

# Add src to python path for Vercel serverless environment
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from skyguard.api.app import app

# Export the FastAPI app for Vercel
# Vercel's @vercel/python automatically detects 'app'