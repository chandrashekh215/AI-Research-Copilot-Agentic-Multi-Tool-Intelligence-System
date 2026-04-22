# Render Platform Configuration Guide

## Deployment Instructions

### Step 1: Update CORS Settings
In `backend/main.py`, update the CORS allowed origins to include your Render frontend URL:

```python
allow_origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://your-frontend-url.onrender.com"  # Add your frontend URL
]
```

### Step 2: Connect Your Git Repository
1. Push this repository to GitHub
2. Go to https://dashboard.render.com
3. Click "New +" and select "Web Service" or "Static Site"

### Step 3: Deploy Backend Service
**Service Name:** ai-research-copilot-backend
- **Environment:** Python 3.11
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT backend.main:app`
- **Environment Variables:**
  - `OPENAI_API_KEY` (required)
  - `GOOGLE_API_KEY` (required)
  - `TAVILY_API_KEY` (required)

### Step 4: Deploy Frontend Service (Static Site)
**Service Name:** ai-research-copilot-frontend
- **Build Command:** `cd frontend && npm install && npm run build`
- **Publish Directory:** `frontend/dist`
- **Environment Variables:**
  - `VITE_API_URL=https://your-backend-url.onrender.com` (the backend service URL)

### Step 5: Update Frontend API Client
In `frontend/src/api/client.ts`, configure the API base URL:

```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
```

## Files Created

- **requirements.txt** - Root-level dependencies for Render
- **render.yaml** - Render infrastructure configuration (alternative to web UI setup)
- **.env.example** - Example environment variables
- **build.sh** - Build script for local testing
- **.renderignore** - Files to exclude from Render deployments

## Notes

- The backend uses `gunicorn` with Uvicorn workers for production
- The frontend is built as a static site and served separately
- Make sure all API keys are set as secure environment variables
- The Chroma vector database will be ephemeral on Render (add Redis or persistent storage if needed)
