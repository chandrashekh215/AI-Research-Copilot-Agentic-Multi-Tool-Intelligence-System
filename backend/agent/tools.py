"""
Agent Tools — All LangChain tools the Research Agent can call.

Tools defined here:
  1. web_search        — Tavily real-time web search
  2. read_url          — Scrape and extract clean text from any URL
  3. arxiv_search      — Fetch academic papers from ArXiv
  4. wikipedia_search  — Quick factual context from Wikipedia
"""

import os
import asyncio
import textwrap
from typing import Optional

import arxiv
import aiohttp
import requests
from bs4 import BeautifulSoup
from langchain.tools import tool
from tavily import TavilyClient

# ─── Clients (initialized lazily) ────────────────────────────────────────────
_tavily_client: Optional[TavilyClient] = None


def _get_tavily() -> TavilyClient:
    global _tavily_client
    if _tavily_client is None:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY not set in environment")
        _tavily_client = TavilyClient(api_key=api_key)
    return _tavily_client


# ─── Tool 1: Web Search ───────────────────────────────────────────────────────

@tool
def web_search(query: str) -> str:
    """
    Search the web for up-to-date information on a topic using Tavily.
    Returns a list of results with title, URL, and content snippet.
    Use this for recent news, articles, and general information.
    Input: a plain-English search query string.
    """
    try:
        client = _get_tavily()
        max_results = int(os.getenv("MAX_SEARCH_RESULTS", "5"))

        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_answer=True,
            include_raw_content=False,
        )

        output_parts = []

        # Include Tavily's synthesized answer if available
        if response.get("answer"):
            output_parts.append(f"SYNTHESIZED ANSWER:\n{response['answer']}\n")

        for i, result in enumerate(response.get("results", []), 1):
            title   = result.get("title", "No title")
            url     = result.get("url", "")
            content = result.get("content", "No content")
            score   = result.get("score", 0)
            output_parts.append(
                f"[{i}] {title}\n"
                f"    URL: {url}\n"
                f"    Relevance: {score:.2f}\n"
                f"    Content: {textwrap.shorten(content, width=400)}\n"
            )

        return "\n".join(output_parts) if output_parts else "No results found."

    except Exception as e:
        return f"Web search failed: {str(e)}"


# ─── Tool 2: URL Reader / Scraper ─────────────────────────────────────────────

@tool
def read_url(url: str) -> str:
    """
    Fetch and extract the full readable text content from a given URL.
    Use this after web_search to read the full article or page content.
    Input: a valid URL string (must start with http:// or https://).
    Returns the cleaned text content up to 3000 characters.
    """
    if not url.startswith(("http://", "https://")):
        return "Invalid URL: must start with http:// or https://"

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        # Remove noise tags
        for tag in soup(["script", "style", "nav", "footer", "header",
                          "aside", "form", "iframe", "noscript"]):
            tag.decompose()

        # Extract main content — prefer <article> or <main>, fallback to <body>
        main = soup.find("article") or soup.find("main") or soup.find("body")
        if not main:
            return "Could not extract content from this URL."

        text = main.get_text(separator="\n", strip=True)

        # Clean up excessive blank lines
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        clean_text = "\n".join(lines)

        # Truncate to keep context window manageable
        return clean_text[:3000] + ("..." if len(clean_text) > 3000 else "")

    except requests.exceptions.Timeout:
        return f"Timeout while reading URL: {url}"
    except requests.exceptions.HTTPError as e:
        return f"HTTP error {e.response.status_code} while reading: {url}"
    except Exception as e:
        return f"Failed to read URL '{url}': {str(e)}"


# ─── Tool 3: ArXiv Academic Paper Search ─────────────────────────────────────

@tool
def arxiv_search(query: str) -> str:
    """
    Search ArXiv for academic research papers on a topic.
    Use this to find peer-reviewed research, studies, and scientific findings.
    Input: a search query string (e.g. 'large language models in healthcare').
    Returns paper titles, authors, published dates, abstracts, and ArXiv links.
    """
    try:
        max_results = int(os.getenv("MAX_ARXIV_RESULTS", "3"))

        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
        )

        output_parts = []
        for i, paper in enumerate(client.results(search), 1):
            authors = ", ".join(a.name for a in paper.authors[:3])
            if len(paper.authors) > 3:
                authors += " et al."

            abstract = textwrap.shorten(paper.summary, width=500)

            output_parts.append(
                f"[{i}] {paper.title}\n"
                f"    Authors: {authors}\n"
                f"    Published: {paper.published.strftime('%Y-%m-%d')}\n"
                f"    ArXiv URL: {paper.entry_id}\n"
                f"    Abstract: {abstract}\n"
            )

        if not output_parts:
            return f"No ArXiv papers found for query: '{query}'"

        return "\n".join(output_parts)

    except Exception as e:
        return f"ArXiv search failed: {str(e)}"


# ─── Tool 4: Wikipedia Summary ────────────────────────────────────────────────

@tool
def wikipedia_search(topic: str) -> str:
    """
    Get a concise factual summary of a topic from Wikipedia.
    Use this to establish background context and definitions.
    Input: a topic name or concept (e.g. 'machine learning', 'CRISPR').
    Returns a 3–5 paragraph summary with the Wikipedia page URL.
    """
    try:
        # Use Wikipedia's REST API — no key needed
        search_url = "https://en.wikipedia.org/api/rest_v1/page/summary/"
        # URL-encode the topic and try it directly
        import urllib.parse
        encoded = urllib.parse.quote(topic.replace(" ", "_"))
        resp = requests.get(
            f"{search_url}{encoded}",
            headers={"User-Agent": "ResearchAgent/1.0 (educational project)"},
            timeout=8,
        )

        if resp.status_code == 404:
            # Try search API to find best matching article
            search_resp = requests.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": topic,
                    "format": "json",
                    "srlimit": 1,
                },
                timeout=8,
            )
            results = search_resp.json().get("query", {}).get("search", [])
            if not results:
                return f"No Wikipedia article found for: '{topic}'"

            best_title = results[0]["title"]
            encoded = urllib.parse.quote(best_title.replace(" ", "_"))
            resp = requests.get(
                f"{search_url}{encoded}",
                headers={"User-Agent": "ResearchAgent/1.0"},
                timeout=8,
            )

        resp.raise_for_status()
        data = resp.json()

        title   = data.get("title", topic)
        extract = data.get("extract", "No summary available.")
        page_url = data.get("content_urls", {}).get("desktop", {}).get("page", "")

        return (
            f"Wikipedia: {title}\n"
            f"URL: {page_url}\n\n"
            f"{extract[:2000]}"
        )

    except Exception as e:
        return f"Wikipedia search failed: {str(e)}"


# ─── Tool Registry ────────────────────────────────────────────────────────────

ALL_TOOLS = [web_search, read_url, arxiv_search, wikipedia_search]
