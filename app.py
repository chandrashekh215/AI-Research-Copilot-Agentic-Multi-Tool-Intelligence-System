"""
Root-level ASGI application for Render deployment.
This imports the actual FastAPI app from backend.main
"""

from backend.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
