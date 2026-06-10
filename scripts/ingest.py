import sys
import argparse
from src.ingest.pipeline import run

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", default="data/bki_hull_2026.pdf")
    parser.add_argument("--pages", help="Range of pages e.g. 5-15")
    parser.add_argument("--force", action="store_true", help="Truncate chunks before insert")
    args = parser.parse_args()
    
    pages = None
    if args.pages:
        start, end = map(int, args.pages.split("-"))
        pages = list(range(start - 1, end))
        
    count = run(args.pdf, pages=pages, force=args.force)
    print(f"Ingested {count} chunks")
