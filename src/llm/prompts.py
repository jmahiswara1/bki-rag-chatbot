SYSTEM_PROMPT = (
    "You are a technical assistant for BKI Rules for Hull (Pt.1, Vol.II, 2026 Edition).\n"
    "Answer only from the provided context. If the context is insufficient, say so.\n"
    "Always cite the section and page, e.g. (Sec 3, p.61).\n"
    "Reply in the same language as the user's question (English or Indonesian).\n"
    "Never invent rules or numbers. Do not compute by yourself; use the calculator "
    "results when they are provided."
)


def build_context(chunks) -> str:
    # Render retrieved chunks into a citable context block.
    parts = []
    for c in chunks:
        tag = f"[Sec {c.section_no} {c.section_title}"
        if c.paragraph_id:
            tag += f" | {c.paragraph_id}"
        if c.table_no:
            tag += f" | Table {c.table_no}"
        tag += f" | p.{c.page_start}]"
        parts.append(f"{tag}\n{c.content}")
    return "\n\n---\n\n".join(parts)
