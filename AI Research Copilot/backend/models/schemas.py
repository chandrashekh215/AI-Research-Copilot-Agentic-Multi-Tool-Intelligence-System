from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime


# ─── Enums ────────────────────────────────────────────────────────────────────

class JobStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"


class ReportDepth(str, Enum):
    QUICK  = "quick"    # 2-3 sources, fast
    NORMAL = "normal"   # 5-7 sources
    DEEP   = "deep"     # 10+ sources, thorough


# ─── Request Models ───────────────────────────────────────────────────────────

class ResearchRequest(BaseModel):
    topic: str = Field(
        ...,
        min_length=5,
        max_length=300,
        description="The research topic or question",
        examples=["Impact of AI on Healthcare in 2025"]
    )
    depth: ReportDepth = Field(
        default=ReportDepth.NORMAL,
        description="How deep the research should go"
    )
    include_arxiv: bool = Field(
        default=True,
        description="Whether to include academic papers from ArXiv"
    )


# ─── Agent Trace Models ───────────────────────────────────────────────────────

class AgentStep(BaseModel):
    step_number: int
    action: str          # e.g. "web_search", "read_url", "arxiv_search"
    input: str           # what was passed to the tool
    output: str          # summary of what came back
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ─── Report Models ────────────────────────────────────────────────────────────

class Source(BaseModel):
    title: str
    url: Optional[str] = None
    source_type: str    # "web", "arxiv", "wikipedia"
    snippet: str


class Report(BaseModel):
    id: str
    topic: str
    depth: ReportDepth
    executive_summary: str
    key_findings: List[str]
    detailed_analysis: str
    follow_up_questions: List[str]
    sources: List[Source]
    full_markdown: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ─── Job / Status Models ──────────────────────────────────────────────────────

class ResearchJob(BaseModel):
    job_id: str
    topic: str
    depth: ReportDepth
    status: JobStatus = JobStatus.PENDING
    steps: List[AgentStep] = Field(default_factory=list)
    report: Optional[Report] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


# ─── API Response Wrappers ────────────────────────────────────────────────────

class ResearchResponse(BaseModel):
    job_id: str
    message: str
    status: JobStatus


class StatusResponse(BaseModel):
    job_id: str
    topic: str
    status: JobStatus
    steps_completed: int
    latest_action: Optional[str] = None
    error: Optional[str] = None


class ReportListItem(BaseModel):
    job_id: str
    topic: str
    depth: ReportDepth
    status: JobStatus
    sources_count: int
    created_at: datetime


class ReportListResponse(BaseModel):
    total: int
    reports: List[ReportListItem]
