import ollama
from rich.progress import Progress
from src.core.db import get_client
from src.core.config import settings
from src.ingest.chunker import chunk_pages
from src.ingest.embedder import embed_batch
from src.ingest.parser import parse_pdf
from src.ingest.figures import process_figures

def run(pdf_path: str, pages: list[int] = None, force: bool = False) -> int:
    client = get_client()
    if force:
        # Simplistic truncate; real systems might drop/create or filter by source
        client.table("chunks").delete().neq("id", -1).execute()
        
    print("Pass 1: Parsing PDF text and tables...")
    parsed_pages = parse_pdf(pdf_path, pages)
    
    print("Pass 1: Chunking text...")
    chunks = chunk_pages(parsed_pages)
    
    print("Pass 2: Processing figures...")
    fig_chunks = process_figures(pdf_path, pages)
    chunks.extend(fig_chunks)
    
    print("Unloading VLM to free VRAM...")
    ollama_client = ollama.Client(host=settings.ollama_host)
    try:
        ollama_client.generate(model=settings.vlm_model, prompt="", keep_alive=0)
    except Exception:
        pass

    rows = []
    print("Pass 3: Embedding and storing chunks...")
    with Progress() as progress:
        task = progress.add_task("[cyan]Embedding...", total=len(chunks))
        
        batch_size = 50
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            texts = [c.content for c in batch]
            embeddings = embed_batch(texts)
            
            batch_rows = []
            for c, emb in zip(batch, embeddings):
                c.embedding = emb
                batch_rows.append({
                    "section_no": c.section_no,
                    "section_title": c.section_title,
                    "paragraph_id": c.paragraph_id,
                    "content_type": c.content_type,
                    "table_no": c.table_no,
                    "figure_no": c.figure_no,
                    "page_start": c.page_start,
                    "page_end": c.page_end,
                    "content": c.content,
                    "embedding": c.embedding,
                })
            
            client.table("chunks").insert(batch_rows).execute()
            progress.update(task, advance=len(batch))
            rows.extend(batch_rows)

    return len(rows)
