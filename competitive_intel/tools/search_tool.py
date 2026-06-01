# tools/search_tool.py
# Tavily web search — searches for competitor info

# tools/search_tool.py
import os
from dotenv import load_dotenv
from langchain_tavily import TavilySearch

load_dotenv()


def search_competitor(query: str, max_results: int = 5) -> str:
    """
    Searches the web for a specific competitor query.
    Returns formatted results as a string.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY not found in .env")

    search = TavilySearch(
        api_key=api_key,
        max_results=max_results,
        search_depth="advanced",
    )

    response = search.invoke({"query": query})

    # langchain-tavily returns a dict with 'results' key
    if isinstance(response, dict):
        results = response.get("results", [])
    elif isinstance(response, list):
        results = response
    else:
        return f"Unexpected response format: {type(response)}"

    if not results:
        return f"No results found for: {query}"

    formatted = []
    for i, r in enumerate(results[:max_results], 1):
        if isinstance(r, dict):
            formatted.append(
                f"[Result {i}]\n"
                f"Title: {r.get('title', 'N/A')}\n"
                f"URL: {r.get('url', 'N/A')}\n"
                f"Content: {r.get('content', 'N/A')}\n"
            )
        else:
            formatted.append(f"[Result {i}]\n{str(r)}\n")

    return "\n---\n".join(formatted)


def search_all_competitors(competitors: list, focus_area: str) -> str:
    """
    Searches for all competitors and returns combined results.
    """
    all_results = []

    for competitor in competitors:
        print(f"🔍 Searching: {competitor}...")

    # Focus area gets the most searches
        focused_1 = search_competitor(f"{competitor} {focus_area} 2025", max_results=3)
        focused_2 = search_competitor(f"{competitor} {focus_area} latest update", max_results=2)
    # General context
        news     = search_competitor(f"{competitor} latest news 2025", max_results=2)

        all_results.append(
            f"\n{'='*50}\n"
            f"COMPETITOR: {competitor}\n"
            f"{'='*50}\n\n"
            f"## {focus_area} (Primary Focus):\n{focused_1}\n\n"
            f"## {focus_area} (Additional):\n{focused_2}\n\n"
            f"## General News:\n{news}\n"
        )
    return "\n".join(all_results)