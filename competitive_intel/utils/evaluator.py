# =============================================
# Ragas RAG Evaluation
# =============================================
# Ragas automatically scores your RAG pipeline on:
#
#   faithfulness     — Is the answer supported by the retrieved docs?
#                      (0 = hallucinated, 1 = fully grounded)
#
#   answer_relevancy — Does the answer actually address the question?
#                      (0 = off-topic, 1 = perfectly relevant)
#
#   context_precision — Are the retrieved chunks actually useful?
#                       (0 = retrieved junk, 1 = perfect retrieval)


# utils/evaluator.py
from typing import List
from dotenv import load_dotenv
import os

load_dotenv()


def evaluate_retrieval_quality(
    query: str,
    retrieved_chunks: List[str],
) -> dict:
    """
    Evaluates hybrid retrieval quality — no LLM needed, runs instantly.

    Checks:
    - Keyword coverage: do retrieved chunks contain query terms?
    - Chunk diversity: are chunks varied or all the same?
    - Average chunk length: are chunks meaningful size?
    """
    if not retrieved_chunks:
        return {"retrieval_score": 0.0, "issues": ["No chunks retrieved"]}

    issues = []

    # Check 1: chunk length
    avg_length = sum(len(c) for c in retrieved_chunks) / len(retrieved_chunks)
    if avg_length < 100:
        issues.append("Chunks too short — consider larger chunk_size")

    # Check 2: keyword coverage
    query_words = set(query.lower().split())
    combined_text = " ".join(retrieved_chunks).lower()
    covered = sum(1 for w in query_words if w in combined_text)
    keyword_coverage = covered / max(len(query_words), 1)
    if keyword_coverage < 0.5:
        issues.append("Low keyword coverage — BM25 may not have indexed this content")

    # Check 3: diversity
    unique_chunks = set(c[:50] for c in retrieved_chunks)
    diversity = len(unique_chunks) / len(retrieved_chunks)
    if diversity < 0.5:
        issues.append("Low diversity — chunks may be too similar")

    retrieval_score = round((keyword_coverage + diversity) / 2, 3)

    return {
        "retrieval_score":  retrieval_score,
        "keyword_coverage": round(keyword_coverage, 3),
        "chunk_diversity":  round(diversity, 3),
        "avg_chunk_length": round(avg_length, 1),
        "chunks_retrieved": len(retrieved_chunks),
        "issues":           issues if issues else ["No issues found"],
    }


def _grade(score: float) -> str:
    if score >= 0.9: return "A — Excellent"
    if score >= 0.7: return "B — Good"
    if score >= 0.5: return "C — Fair"
    return "D — Needs improvement"