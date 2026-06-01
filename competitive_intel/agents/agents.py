# agents/analyzer.py
from utils.llm import get_llm
from utils.prompts import ANALYZER_PROMPT
from vectordb.chroma_store import get_internal_context


def run_analyzer(scraped_data: str, competitors: list) -> str:
    """Compares scraped data against internal company documents."""
    llm = get_llm()
    print("🧠 Analyzer comparing against internal docs...")

    # Get internal context from ChromaDB
    query = f"competitive strategy product features pricing {' '.join(competitors)}"
    internal_context = get_internal_context(query)

    prompt = ANALYZER_PROMPT.format(
        scraped_data=scraped_data,
        internal_context=internal_context,
    )
    response = llm.invoke(prompt)
    return response.content


# agents/scorer.py
from utils.llm import get_llm
from utils.prompts import SCORER_PROMPT


def run_scorer(analysis_data: str) -> str:
    """Scores each competitor on threat level 1-10."""
    llm = get_llm()
    print("📊 Scorer rating threat levels...")

    prompt = SCORER_PROMPT.format(analysis_data=analysis_data)
    response = llm.invoke(prompt)
    return response.content


# agents/reporter.py
from utils.llm import get_llm
from utils.prompts import REPORTER_PROMPT
from datetime import datetime


def run_reporter(
    scraped_data: str,
    analysis_data: str,
    scores_data: str,
    competitors: list,
    focus_area: str,
) -> str:
    """Writes the final structured intelligence briefing."""
    llm = get_llm(temperature=0.3)
    print("✍️ Reporter writing intelligence brief...")

    prompt = REPORTER_PROMPT.format(
        date=datetime.now().strftime("%B %d, %Y"),
        competitors=", ".join(competitors),
        focus_area=focus_area,
        scraped_data=scraped_data[:1000],   # trim to avoid token limits
        analysis_data=analysis_data[:1000],
        scores_data=scores_data,
    )
    response = llm.invoke(prompt)
    return response.content
