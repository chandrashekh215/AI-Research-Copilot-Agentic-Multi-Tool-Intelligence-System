"""
Memory Layer — Two-tier memory system for the Research Agent.

Tier 1 — Session Memory (in-process):
  Tracks what the agent has already searched/visited in the current job.
  Prevents duplicate searches and tool calls.

Tier 2 — Vector Memory (ChromaDB):
  Stores all fetched content as embeddings.
  Agent can semantically query the store to retrieve relevant
  context before making new tool calls — avoiding redundant fetches.
"""

import os
import hashlib
from typing import List, Optional
from datetime import datetime

import chromadb
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_classic.memory import ConversationSummaryBufferMemory


# ─── Session Memory ───────────────────────────────────────────────────────────

class SessionMemory:
    """
    Lightweight in-process memory for a single research job.
    Tracks searches performed and URLs already read so the agent
    does not repeat the same tool calls.
    """

    def __init__(self):
        self._searches: list[str]  = []   # queries already searched
        self._urls_read: set[str]  = set() # URLs already scraped
        self._facts: list[dict]    = []   # key facts noted during research

    # ── Search tracking ───────────────────────────────────────────────────────

    def record_search(self, query: str) -> None:
        self._searches.append(query.lower().strip())

    def already_searched(self, query: str) -> bool:
        q = query.lower().strip()
        # True if an identical or highly similar query was already run
        return any(q in s or s in q for s in self._searches)

    # ── URL tracking ──────────────────────────────────────────────────────────

    def record_url(self, url: str) -> None:
        self._urls_read.add(url.strip())

    def already_read(self, url: str) -> bool:
        return url.strip() in self._urls_read

    # ── Fact notes ────────────────────────────────────────────────────────────

    def note_fact(self, fact: str, source: str = "") -> None:
        self._facts.append({"fact": fact, "source": source, "ts": datetime.utcnow().isoformat()})

    def get_facts(self) -> list[dict]:
        return list(self._facts)

    # ── Summary ───────────────────────────────────────────────────────────────

    def summary(self) -> str:
        return (
            f"Searches performed ({len(self._searches)}): {', '.join(self._searches[:10])}\n"
            f"URLs read ({len(self._urls_read)}): {len(self._urls_read)} pages\n"
            f"Facts noted: {len(self._facts)}"
        )

    def all_searches(self) -> list[str]:
        return list(self._searches)


# ─── Vector Memory (ChromaDB) ─────────────────────────────────────────────────

class VectorMemory:
    """
    Persistent semantic memory backed by ChromaDB + Gemini embeddings.
    Each research job gets its own isolated collection.

    Usage:
      - add_documents(docs)  → embed and store scraped content
      - query(text, k)       → retrieve top-k semantically similar chunks
      - has_content(topic)   → check if we already have content on a topic
    """

    def __init__(self, job_id: str):
        self.job_id = job_id
        self.collection_name = f"research_{job_id[:8]}"
        db_dir = os.getenv("CHROMA_DB_DIR", "./chroma_db")

        self._embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
        )

        self._chroma_client = chromadb.PersistentClient(path=db_dir)

        self._store = Chroma(
            client=self._chroma_client,
            collection_name=self.collection_name,
            embedding_function=self._embeddings,
        )

        self._doc_count = 0

    def add_documents(self, texts: List[str], metadatas: Optional[List[dict]] = None) -> int:
        """
        Embed and store a list of text chunks.
        Returns the number of documents successfully added.
        """
        if not texts:
            return 0

        docs = []
        for i, text in enumerate(texts):
            if not text or not text.strip():
                continue
            meta = metadatas[i] if metadatas and i < len(metadatas) else {}
            # Add a content hash to detect duplicates
            content_hash = hashlib.md5(text.encode()).hexdigest()
            meta["content_hash"] = content_hash
            meta["job_id"] = self.job_id
            docs.append(Document(page_content=text.strip(), metadata=meta))

        if not docs:
            return 0

        self._store.add_documents(docs)
        self._doc_count += len(docs)
        return len(docs)

    def add_single(self, text: str, source: str = "", source_type: str = "web") -> None:
        """Convenience method to add one piece of content."""
        self.add_documents(
            texts=[text],
            metadatas=[{"source": source, "source_type": source_type}]
        )

    def query(self, query_text: str, k: int = 4) -> List[Document]:
        """
        Retrieve the top-k most semantically relevant stored documents.
        Returns empty list if collection is empty.
        """
        if self._doc_count == 0:
            return []
        try:
            return self._store.similarity_search(query_text, k=k)
        except Exception:
            return []

    def query_as_context(self, query_text: str, k: int = 4) -> str:
        """
        Returns retrieved documents as a formatted string for LLM context.
        """
        docs = self.query(query_text, k=k)
        if not docs:
            return "No relevant context found in memory."

        parts = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "unknown")
            source_type = doc.metadata.get("source_type", "")
            parts.append(
                f"[Retrieved Context {i}] (source: {source} | type: {source_type})\n"
                f"{doc.page_content[:600]}\n"
            )
        return "\n".join(parts)

    def has_content(self, topic: str, threshold: int = 1) -> bool:
        """
        Returns True if the vector store already has content related to the topic.
        """
        results = self.query(topic, k=threshold)
        return len(results) >= threshold

    def cleanup(self) -> None:
        """Delete this job's collection from ChromaDB to free space."""
        try:
            self._chroma_client.delete_collection(self.collection_name)
        except Exception:
            pass


# ─── Conversation Buffer Memory (for LangChain agent) ────────────────────────

def build_conversation_memory(llm=None) -> ConversationSummaryBufferMemory:
    """
    Returns a ConversationSummaryBufferMemory instance.
    This keeps the last N tokens verbatim and summarises older turns —
    balancing detail vs. context-window efficiency.
    """
    if llm is None:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
        )

    return ConversationSummaryBufferMemory(
        llm=llm,
        max_token_limit=2000,
        memory_key="chat_history",
        return_messages=True,
    )
