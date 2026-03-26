# Autonomous Research & Report Agent

An end-to-end agentic AI system that takes a research topic, autonomously searches the web and academic sources, stores knowledge in a vector database, and synthesizes a structured, cited report — all with zero human intervention between question and final output.

Built as a portfolio project for an **Agentic Systems** role, demonstrating production patterns: multi-tool LLM agents, async job orchestration, real-time UI streaming, and a two-stage synthesis pipeline.

---

## Demo

> Enter a topic → watch the agent reason and call tools live → receive a full cited report

**Live agent trace while the job runs:**

```
[1] web_search        → "recent advances in transformer architecture 2024"
[2] read_url          → https://arxiv.org/abs/2401.04088
[3] arxiv_search      → "attention mechanism optimization"
[4] web_search        → "transformer inference latency benchmarks"
[5] wikipedia_search  → "Transformer (deep learning)"
[6] read_url          → https://towardsdatascience.com/...
```

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   REACT FRONTEND                    │
│  ResearchForm → AgentTrace → ReportViewer → History │
│           2-second polling via Axios                │
└────────────────────┬────────────────────────────────┘
                     │ REST API
┌────────────────────▼────────────────────────────────┐
│                  FASTAPI BACKEND                    │
│  POST /research → background job → returns job_id  │
│  GET  /status   → pending | running | completed    │
│  GET  /steps    → live agent reasoning trace       │
│  GET  /report   → final structured report          │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│           LANGGRAPH REACT AGENT (GPT-4o)            │
│  web_search · read_url · arxiv_search · wikipedia  │
│  StepTrackerCallback → real-time step recording    │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│                  MEMORY LAYER                       │
│  SessionMemory  → dedup (searched / read URLs)     │
│  VectorMemory   → ChromaDB semantic store          │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│               REPORT SYNTHESIZER                    │
│  Stage 1: GPT-4o → structured JSON analysis        │
│  Stage 2: GPT-4o → full Markdown document          │
└─────────────────────────────────────────────────────┘
```

---

## Features

- **Autonomous multi-tool agent** — LangGraph ReAct loop decides which tools to call, in what order, for how long
- **Live reasoning trace** — every tool call (action + input + output) streamed to the UI via 2-second polling
- **Three research depths** — Quick (6 iterations), Normal (12), Deep (20)
- **Two-tier memory** — SessionMemory prevents duplicate work; ChromaDB stores and semantically retrieves content
- **Two-stage synthesis** — first pass produces structured JSON (summary, findings, analysis), second pass renders full Markdown with citations
- **Async job queue** — API returns immediately with a `job_id`; research runs in background
- **Report history** — all past jobs persisted and accessible from the UI

---

## Tech Stack

### Backend
| | Technology | Purpose |
|---|---|---|
| 🐍 | Python 3.14 + FastAPI | Async REST API, auto OpenAPI docs |
| 🤖 | LangGraph 1.1 + GPT-4o | ReAct agent loop, tool orchestration |
| 🔗 | LangChain Core 1.2 | Tool definitions, prompt templates, output parsers |
| 🧠 | ChromaDB 1.5 | Local persistent vector store for semantic memory |
| 🔍 | Tavily API | AI-optimized web search (relevance-ranked results) |
| 📄 | ArXiv API | Free academic paper search |
| ✅ | Pydantic V2 | Runtime validation, JSON schema, OpenAPI integration |

### Frontend
| | Technology | Purpose |
|---|---|---|
| ⚛️ | React 18 + TypeScript | Component model, type-safe API layer |
| ⚡ | Vite 5 | Instant HMR, fast builds |
| 📡 | Axios | HTTP client with proxy to FastAPI |
| 📝 | react-markdown + remark-gfm | Renders the agent's Markdown report |

---

## Project Structure

```
project_agentic_ai/
│
├── .env                        ← API keys (not committed)
├── README.md
├── PROJECT_GUIDE.md            ← Full technical deep-dive + interview prep
├── reports/                    ← Auto-saved .md report files
├── chroma_db/                  ← Local vector store (auto-created)
│
├── backend/
│   ├── main.py                 ← FastAPI app + 8 API routes
│   ├── requirements.txt
│   ├── models/
│   │   └── schemas.py          ← All Pydantic models
│   └── agent/
│       ├── tools.py            ← @tool: web_search, read_url, arxiv_search, wikipedia
│       ├── memory.py           ← SessionMemory + VectorMemory (ChromaDB)
│       ├── synthesizer.py      ← Two-stage LLM synthesis chain
│       └── researcher.py       ← ResearchAgent orchestrator + callback
│
└── frontend/
    ├── vite.config.ts
    ├── package.json
    └── src/
        ├── App.tsx             ← Root: job state, routing, polling loop
        ├── api/client.ts       ← Axios client + TypeScript types
        └── components/
            ├── ResearchForm.tsx
            ├── AgentTrace.tsx
            ├── ReportViewer.tsx
            └── ReportHistory.tsx
```

---

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 22+
- [OpenAI API key](https://platform.openai.com)
- [Tavily API key](https://tavily.com) (free tier: 1,000 searches/month)

### 1. Clone & configure
```bash
git clone https://github.com/your-username/project_agentic_ai.git
cd project_agentic_ai
```

Create `.env` in the root directory:
```env
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
REPORTS_DIR=./reports
CHROMA_DB_DIR=./chroma_db
```

### 2. Backend
```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r backend/requirements.txt
cd backend
uvicorn main:app --reload --port 8000
```

### 3. Frontend (new terminal)
```bash
cd frontend
npm install
npm run dev
```

### 4. Open
| | URL |
|---|---|
| App | http://localhost:3000 |
| API Docs | http://localhost:8000/docs |

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `POST` | `/research` | Start a new research job → returns `job_id` |
| `GET` | `/status/{job_id}` | Poll job state + step count |
| `GET` | `/steps/{job_id}` | Full agent reasoning trace |
| `GET` | `/report/{job_id}` | Structured report (JSON) |
| `GET` | `/report/{job_id}/markdown` | Report as raw Markdown |
| `GET` | `/reports` | List all past jobs |
| `DELETE` | `/report/{job_id}` | Delete a job |

**Example request:**
```bash
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"topic": "recent advances in multimodal LLMs", "depth": "normal", "include_arxiv": true}'
```

**Example response:**
```json
{
  "job_id": "a1b2c3d4",
  "status": "pending",
  "message": "Research job started"
}
```

---

## How the Agent Works

The core loop follows the **ReAct pattern** (Reason + Act):

```
1. LLM receives topic + system instructions (depth config)
2. LLM reasons: "I need to search the web first"
3. LLM calls: web_search("topic query")
4. Tool returns: ranked snippets + URLs
5. LLM reasons: "I should read the top URL for full content"
6. LLM calls: read_url("https://...")
7. Tool returns: scraped article text
8. SessionMemory marks URL as read → prevents re-reading
9. VectorMemory embeds + stores the content
10. Repeat from step 2 until recursion_limit or goal met
11. ReportSynthesizer processes all gathered content → Report
```

The `StepTrackerCallback` intercepts every `on_tool_start` and `on_tool_end` event, writing each step into the job's trace — which the frontend displays in real time.

---

## Design Decisions

**LangGraph over LangChain AgentExecutor** — LangGraph is the current standard; graph-based loop gives precise recursion control and is the foundation for multi-agent patterns.

**Polling over WebSocket** — 2-second polling works through all proxies/firewalls with zero connection management. WebSocket is the production upgrade path.

**ChromaDB over managed vector DBs** — Zero infrastructure for local dev and demos. One constructor change to swap for Pinecone/Qdrant in production.

**BackgroundTasks over Celery** — Sufficient for single-server demo. Production path: Celery + Redis for distributed workers and persistent job queues.

**Two-stage synthesis** — Stage 1 produces structured JSON (reliable schema), Stage 2 converts to polished Markdown. Separating concerns improves output quality vs. a single giant prompt.

---

## Limitations & Future Work

- [ ] **Redis job store** — current in-memory dict resets on server restart
- [ ] **Celery workers** — enable distributed, scalable research jobs
- [ ] **User authentication** — JWT-based multi-user support
- [ ] **Streaming synthesis** — token-by-token report generation via SSE
- [ ] **PDF export** — download reports as styled PDFs
- [ ] **Multi-agent routing** — specialist sub-agents for web, academic, and code research
- [ ] **RAG follow-up Q&A** — chat with a completed report using LlamaIndex

---

## License

MIT

---

*Built with Python · FastAPI · LangGraph · ChromaDB · React · TypeScript*
