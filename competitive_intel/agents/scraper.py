# agents/scraper.py
from utils.llm import get_llm
from utils.prompts import SCRAPER_PROMPT
from tools.search_tool import search_all_competitors


def run_scraper(competitors: list, focus_area: str) -> str:
    """Searches web for all competitors and summarizes findings."""
    llm = get_llm()
    print(f"🔍 Scraper searching for: {competitors}")

    # Step 1: Get raw search results
    raw_results = search_all_competitors(competitors, focus_area)

    # Step 2: Ask LLM to summarize and structure the raw results
    prompt = SCRAPER_PROMPT.format(
        competitors=", ".join(competitors),
        focus_area=focus_area,
    )
    full_prompt = f"{prompt}\n\n## Raw Search Results:\n{raw_results}\n\nNow summarize and structure these findings:"
    response = llm.invoke(full_prompt)
    result = response.content

    # Store in ChromaDB for RAG retrieval
    try:
        from vectordb.chroma_store import add_documents
        add_documents(
            texts=[result],
            metadatas=[{
                "source": f"scraper_{','.join(competitors)}",
                "focus_area": focus_area,
                "type": "scraped_intel",
            }]
        )
        print(f"✅ Stored scraper results in ChromaDB")
    except Exception as e:
        print(f"⚠️ Could not store in ChromaDB: {e}")
        
    return response.content
