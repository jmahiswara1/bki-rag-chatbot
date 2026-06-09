from src.core.models import Chunk
from src.ingest.parser import PageContent


def chunk_pages(pages: list[PageContent]) -> list[Chunk]:
    # Structure-aware chunking by section and paragraph id.
    # Keep formulas with their variable definitions in one chunk.
    # Keep each table intact; repeat the header if a table is split.
    raise NotImplementedError("Phase 1: implement structure-aware chunking")
