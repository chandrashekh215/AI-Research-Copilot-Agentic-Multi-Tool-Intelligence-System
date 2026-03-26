"""
FastAPI application — Autonomous Research & Report Agent
Skeleton with all routes defined. Logic wired in after agents are built.
"""

import uuid
import asyncio
from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

from models.schemas import (
    ResearchRequest,
    ResearchResponse,
    StatusResponse,
    ReportListResponse,
    ReportListItem,
    ResearchJob,
    JobStatus,
    Report,
)

load_dotenv()

# ─── In-memory job store (replaced with Redis in production) ──────────────────
jobs: Dict[str, ResearchJob] = {}


# ─── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Research Agent API starting up...")
    yield
    print("🛑 Research Agent API shutting down...")


# ─── App Init ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Autonomous Research & Report Agent",
    description="An agentic AI system that researches any topic and generates structured reports.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Background task that runs the agent ─────────────────────────────────────
async def run_research_job(job_id: str, request: ResearchRequest):
    """
    Runs the full research pipeline in the background.
    Imports are deferred here to avoid circular deps at startup.
    """
    from agent.researcher import ResearchAgent

    job = jobs[job_id]
    job.status = JobStatus.RUNNING

    try:
        agent = ResearchAgent(job=job)
        report: Report = await agent.run(topic=request.topic, depth=request.depth)

        job.report = report
        job.status = JobStatus.COMPLETED
        from datetime import datetime
        job.completed_at = datetime.utcnow()

    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        print(f"[ERROR] Job {job_id} failed: {e}")


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "Research Agent API is running"}


@app.post("/research", response_model=ResearchResponse, tags=["Research"])
async def start_research(request: ResearchRequest, background_tasks: BackgroundTasks):
    """
    Submit a new research job. Returns a job_id immediately.
    The agent runs asynchronously in the background.
    """
    job_id = str(uuid.uuid4())
    job = ResearchJob(job_id=job_id, topic=request.topic, depth=request.depth)
    jobs[job_id] = job

    background_tasks.add_task(run_research_job, job_id, request)

    return ResearchResponse(
        job_id=job_id,
        message=f"Research started for topic: '{request.topic}'",
        status=JobStatus.PENDING,
    )


@app.get("/status/{job_id}", response_model=StatusResponse, tags=["Research"])
async def get_status(job_id: str):
    """
    Poll the status of a running or completed research job.
    Returns current step count and latest agent action.
    """
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    latest_action = job.steps[-1].action if job.steps else None

    return StatusResponse(
        job_id=job_id,
        topic=job.topic,
        status=job.status,
        steps_completed=len(job.steps),
        latest_action=latest_action,
        error=job.error,
    )


@app.get("/steps/{job_id}", tags=["Research"])
async def get_steps(job_id: str):
    """
    Returns the full agent reasoning trace (all steps) for a job.
    """
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    return {"job_id": job_id, "steps": [s.model_dump() for s in job.steps]}


@app.get("/report/{job_id}", tags=["Report"])
async def get_report(job_id: str):
    """
    Returns the full structured report for a completed job.
    """
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed yet. Current status: {job.status}"
        )

    return job.report.model_dump()


@app.get("/report/{job_id}/markdown", response_class=PlainTextResponse, tags=["Report"])
async def get_report_markdown(job_id: str):
    """
    Returns the raw Markdown text of the report.
    """
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    if job.status != JobStatus.COMPLETED or not job.report:
        raise HTTPException(status_code=400, detail="Report not ready yet")

    return job.report.full_markdown


@app.get("/reports", response_model=ReportListResponse, tags=["Report"])
async def list_reports():
    """
    Returns a list of all research jobs (their summary info).
    """
    items = [
        ReportListItem(
            job_id=j.job_id,
            topic=j.topic,
            depth=j.depth,
            status=j.status,
            sources_count=len(j.report.sources) if j.report else 0,
            created_at=j.created_at,
        )
        for j in jobs.values()
    ]
    items.sort(key=lambda x: x.created_at, reverse=True)

    return ReportListResponse(total=len(items), reports=items)


@app.delete("/report/{job_id}", tags=["Report"])
async def delete_report(job_id: str):
    """
    Deletes a job and its report from memory.
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    del jobs[job_id]
    return {"message": f"Job '{job_id}' deleted successfully"}
