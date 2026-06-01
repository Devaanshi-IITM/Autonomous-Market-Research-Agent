# import streamlit as st
# st.write("hello")

# from tools.search_tool import search_competitor
# result = search_competitor("Linear app pricing 2025", max_results=2)
# print("TYPE:", type(result))
# print("RESULT:", result[:300])


# from utils.pdf_generator import generate_pdf
# pdf = generate_pdf('Test brief content.\nSection One:\nThis is a test.', ['Linear'], 'pricing')
# open('test_output.pdf', 'wb').write(pdf)
# print('PDF generated successfully, size:', len(pdf), 'bytes')

# test.py — Tests hybrid search, reranking, and retrieval quality

from vectordb.chroma_store import get_document_count, hybrid_search
from utils.evaluator import evaluate_retrieval_quality

print("=" * 50)
print("CompeteIQ — System Test")
print("=" * 50)

# Test 1: Document count
print("\n📚 Test 1: Database")
count = get_document_count()
print(f"Documents in ChromaDB: {count}")
if count == 0:
    print("⚠️  No docs found — upload a document first")
else:
    print("✅ Database has documents")

# Test 2: Hybrid search (BM25 + Vector)
print("\n🔍 Test 2: Hybrid Search (BM25 + Vector)")
results = hybrid_search("competitive strategy pricing features", k=5)
print(f"Chunks retrieved: {len(results)}")
for i, r in enumerate(results, 1):
    source = r.metadata.get("source", "unknown")
    print(f"  [{i}] Source: {source} | Preview: {r.page_content[:80].strip()}...")

# Test 3: Reranking (cross-encoder)
print("\n🎯 Test 3: Cross-Encoder Reranking")
from sentence_transformers import CrossEncoder
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
if results:
    query = "competitive strategy pricing"
    pairs = [(query, r.page_content) for r in results]
    scores = reranker.predict(pairs)
    ranked = sorted(zip(scores, results), key=lambda x: x[0], reverse=True)
    print("Reranked scores (higher = more relevant):")
    for score, doc in ranked:
        print(f"  Score: {round(float(score), 3)} | {doc.page_content[:60].strip()}...")
    print("✅ Reranking working")

# Test 4: Retrieval quality evaluation
print("\n📊 Test 4: Retrieval Quality Evaluation")
if results:
    contexts = [r.page_content for r in results]
    eval_result = evaluate_retrieval_quality(
        query="AI features pricing competitive strategy",
        retrieved_chunks=contexts,
    )
    print(f"  Retrieval Score:  {eval_result['retrieval_score']}")
    print(f"  Keyword Coverage: {eval_result['keyword_coverage']}")
    print(f"  Chunk Diversity:  {eval_result['chunk_diversity']}")
    print(f"  Avg Chunk Length: {eval_result['avg_chunk_length']}")
    print(f"  Issues: {eval_result['issues']}")
    if eval_result['retrieval_score'] >= 0.7:
        print("✅ Retrieval quality is good")
    else:
        print("⚠️  Retrieval quality needs improvement")

print("\n" + "=" * 50)
print("All tests complete")
print("=" * 50)
