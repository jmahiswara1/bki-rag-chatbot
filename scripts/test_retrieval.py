import sys
sys.stdout.reconfigure(encoding='utf-8')
import time
from src.retrieval.query import retrieve_context
from src.retrieval.rerank import rerank_chunks
from src.retrieval.search import hybrid_search
from src.ingest.embedder import embed

def print_chunks(chunks, top=5):
    for i, r in enumerate(chunks[:top]):
        print(f"  {i+1}. [Score: {r.score:.3f}] {r.content[:80].replace(chr(10), ' ')}...")

def test_retrieval():
    print("=== Test 1: Relevansi (Top 3) ===")
    q1 = "What is the minimum plate thickness for bilge strake?"
    print(f"Query: {q1}")
    start_t = time.time()
    res1 = retrieve_context(q1, mode="default")
    print(f"Latency: {time.time() - start_t:.3f}s")
    print_chunks(res1, 3)
    
    print("\n=== Test 2: Cross-lingual via Vektor ===")
    q2 = "berapa ketebalan minimum pelat lambung kapal?"
    print(f"Query (ID): {q2}")
    start_t = time.time()
    res2 = retrieve_context(q2, mode="default")
    print(f"Latency: {time.time() - start_t:.3f}s")
    print_chunks(res2, 3)

    print("\n=== Test 3 & 4: Rerank mengubah urutan & Latency < 3 detik ===")
    q3 = "How to calculate the section modulus of a longitudinal frame?"
    print(f"Query: {q3}")
    q3_embed = embed(q3)
    
    start_t = time.time()
    candidates = hybrid_search(q3_embed, q3, top_k=20)
    print(f"Retrieval latency (hybrid): {time.time() - start_t:.3f}s")
    
    print("\nTop 5 SEBELUM Rerank (hybrid score):")
    print_chunks(candidates, 5)
    
    # Reranking
    start_t = time.time()
    reranked = rerank_chunks(q3, candidates, top_k=5)
    rerank_latency = time.time() - start_t
    print(f"\nRerank latency: {rerank_latency:.3f}s (Target: < 3s)")
    
    print("\nTop 5 SESUDAH Rerank (cross-encoder score):")
    print_chunks(reranked, 5)

    print("\n=== Test 5: Out of Domain Query (skor rendah) ===")
    q4 = "How to bake a chocolate cake in an oven?"
    print(f"Query: {q4}")
    start_t = time.time()
    res4 = retrieve_context(q4, mode="default")
    print(f"Latency: {time.time() - start_t:.3f}s")
    
    if res4:
        print(f"Top 1 Score: {res4[0].score:.3f} (Lower cross-encoder scores indicate less relevance)")
        print_chunks(res4, 3)
    else:
        print("No results found.")

if __name__ == "__main__":
    test_retrieval()
