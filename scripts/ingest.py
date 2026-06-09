import sys

from src.ingest.pipeline import run

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/bki_hull_2026.pdf"
    count = run(path)
    print(f"ingested {count} chunks")
