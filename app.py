"""
Root-level ASGI application for Render deployment.
This imports the actual FastAPI app from backend.main
"""

import sys
import os

# Ensure backend is importable
sys.path.insert(0, os.path.dirname(__file__))

try:
    from backend.main import app
    print("✅ Successfully imported FastAPI app from backend.main")
except Exception as e:
    print(f"❌ Failed to import app: {e}")
    raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
