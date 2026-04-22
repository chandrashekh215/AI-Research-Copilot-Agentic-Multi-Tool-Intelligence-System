"""
Research Agent — Core orchestration layer.

The ResearchAgent class drives the full research pipeline:
  1. Plans research strategy based on topic + depth
  2. Executes LangChain tool-calling loop (web search, ArXiv, URL reader, Wikipedia)
  3. Records every action as an AgentStep in the job for frontend tracing
  4. Stores all fetched content in vector memory
  5. Hands off to ReportSynthesizer to generate the final report

Uses: LangChain create_openai_tools_agent + AgentExecutor
"""

import os
import time
import asyncio
from datetime import datetime
from typing import List

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_core.callbacks import BaseCallbackHandler

from models.schemas import AgentStep, Report, ReportDepth, ResearchJob, Source
from agent.tools import ALL_TOOLS, web_search, read_url, arxiv_search, wikipedia_search
from agent.memory import SessionMemory, VectorMemory
from agent.synthesizer import ReportSynthesizer


# ─── Depth configuration ─────────────────────────────────────────────────────

# Iterations reduced to stay within Gemini free tier (15 RPM).
# Each iteration = 1 LLM call. Add RATE_LIMIT_DELAY between tool calls.
DEPTH_CONFIG = {
    ReportDepth.QUICK:  {"max_iterations": 4,  "search_rounds": 1},
    ReportDepth.NORMAL: {"max_iterations": 6,  "search_rounds": 2},
    ReportDepth.DEEP:   {"max_iterations": 10, "search_rounds": 3},
}

# Seconds to wait after each tool call — keeps calls well under 15 RPM
RATE_LIMIT_DELAY = 4


# ─── Step-tracking Callback ───────────────────────────────────────────────────

class StepTrackerCallback(BaseCallbackHandler):
    """
    LangChain callback that intercepts every tool call and records it
    as an AgentStep in the job object — enabling live frontend tracing.
    """

    def __init__(self, job: ResearchJob, session_memory: SessionMemory):
        self.job = job
        self.session = session_memory
        self._step_counter = 0

    def on_tool_start(self, serialized: dict, input_str: str, **kwargs):
        tool_name = serialized.get("name", "unknown_tool")
        self._step_counter += 1

        step = AgentStep(
            step_number=self._step_counter,
            action=tool_name,
            input=input_str[:300],
            output="⏳ running...",
            timestamp=datetime.utcnow(),
        )
        self.job.steps.append(step)

        # Update session memory so agent avoids repeats
        if tool_name == "web_search":
            self.session.record_search(input_str)
        elif tool_name == "read_url":
            self.session.record_url(input_str)

    def on_tool_end(self, output: str, **kwargs):
        """Update the last step's output with the actual result."""
        if self.job.steps:
            last_step = self.job.steps[-1]
            last_step.output = str(output)[:500]
        # Pace requests to stay within Gemini free tier (15 RPM)
        time.sleep(RATE_LIMIT_DELAY)

    def on_tool_error(self, error: Exception, **kwargs):
        if self.job.steps:
            self.job.steps[-1].output = f"ERROR: {str(error)[:200]}"


# ─── System Prompt ────────────────────────────────────────────────────────────

def build_system_prompt(topic: str, depth: ReportDepth, session: SessionMemory) -> str:
    depth_instructions = {
        ReportDepth.QUICK: (
            "Perform a focused, efficient research run. "
            "Do 1-2 web searches, read 1-2 URLs, and optionally check Wikipedia. "
            "Prioritise the most relevant results."
        ),
        ReportDepth.NORMAL: (
            "Perform thorough research. "
            "Do 3-4 web searches from different angles, read 3-5 URLs, "
            "search ArXiv for academic papers, and use Wikipedia for context."
        ),
        ReportDepth.DEEP: (
            "Perform exhaustive research. "
            "Do 5+ web searches covering different sub-topics and time periods, "
            "read 6-10 URLs for full article content, "
            "search ArXiv with multiple queries, "
            "and use Wikipedia for all key concepts encountered."
        ),
    }

    prior_searches = session.all_searches()
    search_context = (
        f"You have already searched: {', '.join(prior_searches)}"
        if prior_searches else "No searches performed yet."
    )

    return f"""You are an autonomous research agent specialised in gathering comprehensive, 
accurate information on any topic using your available tools.

YOUR RESEARCH MISSION: "{topic}"

DEPTH LEVEL: {depth.value.upper()}
INSTRUCTIONS: {depth_instructions[depth]}

TOOLS AVAILABLE:
- web_search: Search the live web for current information, news, and articles
- read_url: Read the full content of any URL (use after web_search to get complete articles)
- arxiv_search: Find peer-reviewed academic papers and research (use for scientific topics)
- wikipedia_search: Get background context and definitions for key concepts

RESEARCH STRATEGY:
1. Start with web_search for a broad overview
2. Use read_url on the most promising 2-3 results to get full content
3. Run arxiv_search for academic/scientific depth
4. Use wikipedia_search for any key concepts needing definition
5. Run additional targeted web searches to fill knowledge gaps
6. Cover multiple angles: current state, trends, challenges, future outlook

MEMORY: {search_context}
Do NOT repeat searches you have already done. If you have good coverage, stop and finalize.

Return a final message: "RESEARCH COMPLETE - [brief summary of what was collected]"
Do NOT attempt to write the report yourself — the synthesizer will handle that after you finish."""


# ─── Main Agent Class ─────────────────────────────────────────────────────────

class ResearchAgent:
    """
    Orchestrates the full research pipeline for a single ResearchJob.
    """

    def __init__(self, job: ResearchJob):
        self.job = job
        self.session_memory = SessionMemory()
        self.vector_memory = VectorMemory(job_id=job.job_id)
        self.synthesizer = ReportSynthesizer()

        self._llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
        )

    async def run(self, topic: str, depth: ReportDepth) -> Report:
        """
        Full pipeline: research → memory storage → synthesis → report.
        Runs the LangGraph agent synchronously in a thread pool to avoid
        blocking the FastAPI event loop.
        """
        config = DEPTH_CONFIG[depth]

        # Build callback and agent
        callback = StepTrackerCallback(self.job, self.session_memory)
        agent = self._build_agent(topic=topic, depth=depth)

        # Run agent in thread pool (LangGraph sync → async bridge)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: agent.invoke(
                {"messages": [("human", f"Research this topic thoroughly: {topic}")]},
                config={
                    "callbacks": [callback],
                    "recursion_limit": config["max_iterations"],
                },
            )
        )

        # Gather all content from step outputs for synthesis
        content_chunks, sources = self._extract_content_and_sources()

        # Store in vector memory for semantic retrieval
        self.vector_memory.add_documents(
            texts=content_chunks,
            metadatas=[{"source": s.url or s.title, "source_type": s.source_type} for s in sources]
        )

        # Record a synthesis step
        synth_step = AgentStep(
            step_number=len(self.job.steps) + 1,
            action="synthesize_report",
            input=f"Synthesizing report for: {topic}",
            output="Generating structured report with GPT-4o...",
        )
        self.job.steps.append(synth_step)

        # Run synthesis (also CPU-bound, offload to thread pool)
        report: Report = await loop.run_in_executor(
            None,
            lambda: self.synthesizer.synthesize(
                topic=topic,
                depth=depth,
                content_chunks=content_chunks,
                sources=sources,
            )
        )

        # Update synthesis step output
        synth_step.output = f"Report generated: {len(report.key_findings)} findings, {len(report.sources)} sources"

        # Save markdown report to disk
        await self._save_report_to_disk(report)

        return report

    # ─── Agent Builder ────────────────────────────────────────────────────────

    def _build_agent(
        self,
        topic: str,
        depth: ReportDepth,
    ):
        system_prompt = build_system_prompt(topic, depth, self.session_memory)

        agent = create_react_agent(
            model=self._llm,
            tools=ALL_TOOLS,
            prompt=system_prompt,
        )
        return agent

    # ─── Content Extraction ───────────────────────────────────────────────────

    def _extract_content_and_sources(self):
        """
        Walk through all recorded agent steps and extract:
        - content_chunks: list of text strings gathered by tools
        - sources: list of Source objects for citations
        """
        content_chunks: List[str] = []
        sources: List[Source] = []
        seen_urls: set = set()

        for step in self.job.steps:
            if step.action == "synthesize_report":
                continue

            output = step.output
            if not output or output.startswith(("ERROR:", "⏳", "No results")):
                continue

            content_chunks.append(output)

            # Build Source objects based on tool type
            if step.action == "web_search":
                # Parse URLs out of the web_search output
                for line in output.splitlines():
                    if "URL:" in line:
                        url = line.split("URL:")[-1].strip()
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            title_line = ""
                            # look for the title line just above
                            idx = output.find(line)
                            snippet_before = output[max(0, idx-200):idx]
                            for l in reversed(snippet_before.splitlines()):
                                if l.strip().startswith("["):
                                    title_line = l.strip().lstrip("[0123456789] ").strip()
                                    break
                            sources.append(Source(
                                title=title_line or url,
                                url=url,
                                source_type="web",
                                snippet=output[:150],
                            ))

            elif step.action == "arxiv_search":
                for line in output.splitlines():
                    if "ArXiv URL:" in line:
                        url = line.split("ArXiv URL:")[-1].strip()
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            sources.append(Source(
                                title=step.input,
                                url=url,
                                source_type="arxiv",
                                snippet=output[:150],
                            ))

            elif step.action == "wikipedia_search":
                url = ""
                for line in output.splitlines():
                    if line.startswith("URL:"):
                        url = line.split("URL:")[-1].strip()
                        break
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    sources.append(Source(
                        title=f"Wikipedia: {step.input}",
                        url=url,
                        source_type="wikipedia",
                        snippet=output[:150],
                    ))

        # Deduplicate chunks
        seen_hashes = set()
        unique_chunks = []
        for chunk in content_chunks:
            h = hash(chunk[:100])
            if h not in seen_hashes:
                seen_hashes.add(h)
                unique_chunks.append(chunk)

        return unique_chunks, sources

    # ─── Report Persistence ───────────────────────────────────────────────────

    async def _save_report_to_disk(self, report: Report) -> None:
        """Save the markdown report to the /reports directory."""
        try:
            reports_dir = os.getenv("REPORTS_DIR", "./reports")
            os.makedirs(reports_dir, exist_ok=True)

            safe_topic = "".join(
                c if c.isalnum() or c in " _-" else "_"
                for c in report.topic
            )[:50].strip().replace(" ", "_")

            filename = f"{safe_topic}_{report.id[:8]}.md"
            filepath = os.path.join(reports_dir, filename)

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: open(filepath, "w", encoding="utf-8").write(report.full_markdown)
            )
        except Exception as e:
            print(f"[WARN] Could not save report to disk: {e}")
