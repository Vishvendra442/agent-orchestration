import httpx
from langchain_core.tools import tool

from app.runtime.tools.registry import register_tool


@tool
def web_search(query: str) -> str:
    """Search the web for information using DuckDuckGo. Returns top results as text."""
    try:
        resp = httpx.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            timeout=15,
        )
        data = resp.json()
        results = []
        if data.get("AbstractText"):
            results.append(data["AbstractText"])
        for topic in data.get("RelatedTopics", [])[:5]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(topic["Text"])
        return "\n\n".join(results) if results else f"No results found for: {query}"
    except Exception as exc:
        return f"Search failed: {exc}"


register_tool("web_search", web_search)
