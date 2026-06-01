# vectordb/chroma_store.py
# =============================================
# Production RAG — Hybrid Retrieval + Reranking
# =============================================
#
# UPGRADE from basic AgentIQ vector-only search:
#
# OLD:  query → vector search → top-k results
#
# NEW:  query → vector search (semantic)  ─┐
#              → BM25 search (keyword)    ─┤ merge → cross-encoder rerank → top results
#
# Why hybrid?
#   Vector search finds semantically similar docs ("car" ≈ "automobile")
#   BM25 finds exact keyword matches ("MSSQL" won't be found semantically)
#   Together they cover both cases — this is what production systems use.
#
# Why rerank?
#   First-pass retrieval returns ~20 candidates.
#   Cross-encoder reads query+doc TOGETHER and scores relevance precisely.
#   Much more accurate than embedding similarity alone.

import os
import json
from typing import List, Tuple
from dotenv import load_dotenv

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"

load_dotenv()

# ── Models (loaded once, reused) ──────────
_embeddings = None
_reranker   = None
_bm25_index = None
_bm25_docs  = []   # stores Document objects parallel to BM25 index


def get_embeddings() -> HuggingFaceEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings


def get_reranker() -> CrossEncoder:
    """
    Cross-encoder reranker.
    Unlike bi-encoders (which embed query and doc separately),
    cross-encoders read query + doc together — much more accurate.
    Model: ms-marco-MiniLM-L-6-v2 — small, fast, free.
    """
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _reranker


def get_vector_store() -> Chroma:
    return Chroma(
        collection_name="competitive_intel_docs",
        embedding_function=get_embeddings(),
        persist_directory="./chroma_db",
    )


# ── BM25 index management ─────────────────

def _save_bm25_docs(docs: List[Document]):
    """Persist BM25 doc texts to disk so they survive restarts."""
    os.makedirs("./chroma_db", exist_ok=True)
    data = [{"text": d.page_content, "metadata": d.metadata} for d in docs]
    with open("./chroma_db/bm25_docs.json", "w") as f:
        json.dump(data, f)


def _load_bm25_docs() -> List[Document]:
    """Load persisted BM25 docs from disk."""
    path = "./chroma_db/bm25_docs.json"
    if not os.path.exists(path):
        return []
    with open(path) as f:
        data = json.load(f)
    return [Document(page_content=d["text"], metadata=d["metadata"]) for d in data]


def _build_bm25_index(docs: List[Document]) -> BM25Okapi:
    """
    Build a BM25 index from a list of documents.
    BM25 tokenizes each doc into words and builds an inverted index.
    """
    tokenized = [doc.page_content.lower().split() for doc in docs]
    return BM25Okapi(tokenized)


def _get_bm25(docs: List[Document]) -> Tuple[BM25Okapi, List[Document]]:
    global _bm25_index, _bm25_docs
    if _bm25_index is None or len(_bm25_docs) != len(docs):
        _bm25_index = _build_bm25_index(docs)
        _bm25_docs  = docs
    return _bm25_index, _bm25_docs


# ── Core functions ─────────────────────────

def add_documents(texts: List[str], metadatas: List[dict] = None) -> int:
    """
    Splits texts into chunks and adds to:
    1. ChromaDB (for vector search)
    2. BM25 index on disk (for keyword search)
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )
    all_chunks = []
    for i, text in enumerate(texts):
        if not text or len(text.strip()) < 20:
            continue
        meta = metadatas[i] if metadatas else {"source": f"doc_{i}"}
        chunks = splitter.create_documents([text.strip()], metadatas=[meta])
        all_chunks.extend(chunks)

    if not all_chunks:
        return 0

    # 1. Add to ChromaDB
    store = get_vector_store()
    store.add_documents(all_chunks)

    # 2. Persist for BM25
    existing = _load_bm25_docs()
    _save_bm25_docs(existing + all_chunks)

    return len(all_chunks)


def hybrid_search(query: str, k: int = 5) -> List[Document]:
    """
    PRODUCTION RAG: Hybrid retrieval + cross-encoder reranking.

    Step 1 — Vector search: find top-20 semantically similar docs
    Step 2 — BM25 search:   find top-20 keyword-matching docs
    Step 3 — Merge & dedupe both result sets
    Step 4 — Rerank with cross-encoder: score each doc against query
    Step 5 — Return top-k highest scoring docs

    Args:
        query: search query
        k: number of final results to return

    Returns:
        List of most relevant Document objects
    """
    store   = get_vector_store()
    n_fetch = 20  # fetch more candidates, reranker will trim to k

    # ── Step 1: Vector search ────────────
    try:
        vector_results = store.similarity_search(query, k=n_fetch)
    except Exception:
        vector_results = []

    # ── Step 2: BM25 search ──────────────
    bm25_results = []
    try:
        all_docs = _load_bm25_docs()
        if all_docs:
            bm25, docs = _get_bm25(all_docs)
            tokenized_query = query.lower().split()
            scores = bm25.get_scores(tokenized_query)
            # Get top-n_fetch indices sorted by score
            top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:n_fetch]
            bm25_results = [docs[i] for i in top_indices if scores[i] > 0]
    except Exception:
        bm25_results = []

    # ── Step 3: Merge & deduplicate ──────
    seen_texts = set()
    candidates = []
    for doc in vector_results + bm25_results:
        # Use first 100 chars as fingerprint to deduplicate
        fingerprint = doc.page_content[:100]
        if fingerprint not in seen_texts:
            seen_texts.add(fingerprint)
            candidates.append(doc)

    if not candidates:
        return []

    # ── Step 4: Cross-encoder reranking ──
    try:
        reranker = get_reranker()
        # Feed [query, doc_text] pairs to cross-encoder
        pairs  = [(query, doc.page_content) for doc in candidates]
        scores = reranker.predict(pairs)
        # Sort by reranker score descending
        ranked = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)
        return [doc for _, doc in ranked[:k]]
    except Exception:
        # Fallback to vector results if reranker fails
        return candidates[:k]


def get_internal_context(query: str, k: int = 5) -> str:
    """
    Returns formatted internal context using hybrid search.
    Used by the Analyzer agent.
    """
    try:
        count = get_document_count()
        if count == 0:
            return "No internal documents uploaded. Analysis based on general market knowledge."

        results = hybrid_search(query, k=k)
        if not results:
            return "No relevant internal context found."

        chunks = []
        for i, doc in enumerate(results, 1):
            source = doc.metadata.get("source", "internal doc")
            chunks.append(f"[{i}] Source: {source}\n{doc.page_content.strip()}")

        return "\n\n".join(chunks)

    except Exception as e:
        return f"Could not retrieve internal context: {e}"


def get_document_count() -> int:
    try:
        return get_vector_store()._collection.count()
    except Exception:
        return 0
