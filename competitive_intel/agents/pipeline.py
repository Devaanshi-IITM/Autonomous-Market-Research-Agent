# agents/pipeline.py
# =============================================
# LangGraph Pipeline — Competitive Intelligence
# =============================================
# Upgraded with:
#   - Langfuse tracing (every step timed + logged)
#   - Hybrid RAG (BM25 + vector + reranking)

# agents/pipeline.py
from typing import TypedDict, List
import time
from langgraph.graph import StateGraph, END

from agents.scraper import run_scraper
from agents.agents import run_analyzer, run_scorer, run_reporter
from utils.observability import PipelineTrace


class IntelState(TypedDict):
    competitors:    List[str]
    focus_area:     str
    your_company:   str
    scraped_data:   str
    analysis_data:  str
    scores_data:    str
    final_brief:    str
    history:        List[str]
    status:         str
    timings:        dict


def scraper_node(state: IntelState) -> IntelState:
    print("▶ Running Scraper...")
    t = time.time()
    result = run_scraper(state["competitors"], state["focus_area"])
    elapsed = round(time.time() - t, 2)
    timings = dict(state.get("timings", {}))
    timings["scraper"] = f"{elapsed}s"
    return {
        **state,
        "scraped_data": result,
        "history": list(state.get("history", [])) + ["✅ Scraper completed"],
        "status":  "Scraping complete — analyzing now...",
        "timings": timings,
    }


def analyzer_node(state: IntelState) -> IntelState:
    time.sleep(10)
    print("▶ Running Analyzer...")
    t = time.time()
    result = run_analyzer(state["scraped_data"], state["competitors"])
    elapsed = round(time.time() - t, 2)
    timings = dict(state.get("timings", {}))
    timings["analyzer"] = f"{elapsed}s"
    return {
        **state,
        "analysis_data": result,
        "history": list(state.get("history", [])) + ["✅ Analyzer completed"],
        "status":  "Analysis complete — scoring threats...",
        "timings": timings,
    }


def scorer_node(state: IntelState) -> IntelState:
    time.sleep(10)
    print("▶ Running Scorer...")
    t = time.time()
    result = run_scorer(state["analysis_data"])
    elapsed = round(time.time() - t, 2)
    timings = dict(state.get("timings", {}))
    timings["scorer"] = f"{elapsed}s"
    return {
        **state,
        "scores_data": result,
        "history": list(state.get("history", [])) + ["✅ Scorer completed"],
        "status":  "Scoring complete — writing brief...",
        "timings": timings,
    }


def reporter_node(state: IntelState) -> IntelState:
    time.sleep(10)
    print("▶ Running Reporter...")
    t = time.time()
    result = run_reporter(
        scraped_data=state["scraped_data"],
        analysis_data=state["analysis_data"],
        scores_data=state["scores_data"],
        competitors=state["competitors"],
        focus_area=state["focus_area"],
    )
    elapsed = round(time.time() - t, 2)
    timings = dict(state.get("timings", {}))
    timings["reporter"] = f"{elapsed}s"
    return {
        **state,
        "final_brief": result,
        "history": list(state.get("history", [])) + ["✅ Reporter completed"],
        "status":  "Brief ready!",
        "timings": timings,
    }


def build_pipeline():
    graph = StateGraph(IntelState)
    graph.add_node("scraper",  scraper_node)
    graph.add_node("analyzer", analyzer_node)
    graph.add_node("scorer",   scorer_node)
    graph.add_node("reporter", reporter_node)
    graph.set_entry_point("scraper")
    graph.add_edge("scraper",  "analyzer")
    graph.add_edge("analyzer", "scorer")
    graph.add_edge("scorer",   "reporter")
    graph.add_edge("reporter", END)
    return graph.compile()


def run_intelligence_pipeline(
    competitors: List[str],
    focus_area:  str,
    your_company: str = "Our Company",
) -> dict:

    trace = PipelineTrace(
        "competitive_intel_run",
        competitors=competitors,
        focus_area=focus_area,
        company=your_company,
    )

    pipeline = build_pipeline()

    initial_state: IntelState = {
        "competitors":   competitors,
        "focus_area":    focus_area,
        "your_company":  your_company,
        "scraped_data":  "",
        "analysis_data": "",
        "scores_data":   "",
        "final_brief":   "",
        "history":       [],
        "status":        "Starting pipeline...",
        "timings":       {},
    }

    print("DEBUG: invoking pipeline...")
    t = time.time()

    # LangGraph 1.2.0 compatible — use stream() to collect full state
    final_state = dict(initial_state)
    for chunk in pipeline.stream(initial_state):
        print(f"DEBUG chunk: {list(chunk.keys())}")
        for node_name, node_output in chunk.items():
            if isinstance(node_output, dict):
                final_state.update(node_output)

    elapsed = round(time.time() - t, 2)
    print(f"⏱ full_pipeline: {elapsed}s")
    print(f"DEBUG final_state keys: {list(final_state.keys())}")
    print(f"DEBUG final_brief preview: {str(final_state.get('final_brief', ''))[:100]}")

    #-------------evaluation -------------------------
    #-------------evaluation -------------------------
    eval_scores = {}
    try:
        from utils.evaluator import evaluate_retrieval_quality
        from vectordb.chroma_store import hybrid_search, get_document_count

        if get_document_count() > 0:
            retrieved = hybrid_search(
                f"competitive analysis {' '.join(competitors)} {focus_area}", k=5
            )
            contexts = [doc.page_content for doc in retrieved] if retrieved else []

            if contexts:
                retrieval_eval = evaluate_retrieval_quality(
                    query=focus_area,
                    retrieved_chunks=contexts,
                )
                eval_scores = {
                    "evaluated": True,
                    "retrieval": retrieval_eval,
                    "faithfulness": None,
                    "answer_relevancy": None,
                    "overall": None,
                    "grade": f"Retrieval Score: {retrieval_eval['retrieval_score']}",
                }
            else:
                eval_scores = {"evaluated": False, "error": "No chunks retrieved"}
        else:
            eval_scores = {"evaluated": False, "error": "No internal docs uploaded"}

    except Exception as e:
        eval_scores = {"evaluated": False, "error": str(e)}
        print(f"Evaluation error: {e}")

    timing_summary = trace.finish()

    return {
        "final_brief":   final_state.get("final_brief", ""),
        "scraped_data":  final_state.get("scraped_data", ""),
        "analysis_data": final_state.get("analysis_data", ""),
        "scores_data":   final_state.get("scores_data", ""),
        "history":       final_state.get("history", []),
        "timings":       final_state.get("timings", {}),
        "eval_scores":   eval_scores,
        "total_time":    timing_summary.get("total_seconds", 0),
    }