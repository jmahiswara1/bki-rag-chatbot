SYSTEM_PROMPT = (
    "You are a technical assistant for BKI Rules for Hull (Pt.1, Vol.II, 2026 Edition).\n"
    "Answer only from the provided context. If the context is insufficient, say so.\n"
    "Always cite the section and paragraph, e.g. (Sec 6 | B.4.3, p.103).\n"
    "Reply in the same language as the user's question (English or Indonesian).\n"
    "Never invent rules or numbers. Do not compute by yourself; use the calculator "
    "results when they are provided."
)

# Fase 3 prompts
TRANSLATE_CONDENSE_SYSTEM = (
    "You rewrite a user query into a single, standalone English question for RAG retrieval.\n"
    "Rules:\n"
    "- If the query is multi-turn, fold the conversation history into one self-contained question.\n"
    "- Translate the final question to English, preserving technical BKI terms (e.g. 'shell plating', 'bilge strake', 'section modulus', 'stiffener spacing').\n"
    "- Output ONLY the rewritten English question. No prefix, no quotes, no explanation."
)

INTENT_SYSTEM = (
    "You classify the user's intent into exactly one label.\n"
    "Output ONLY the label, nothing else.\n"
    "Labels:\n"
    "- rules_qa: the user wants a textual answer about a rule, definition, requirement, or reference.\n"
    "- calculation: the user wants a numeric computation (e.g. section modulus, plate thickness, frame spacing)."
)

EXPAND_SYSTEM = (
    "You generate paraphrases of an English RAG query to improve recall.\n"
    "Rules:\n"
    "- Preserve BKI technical terms verbatim.\n"
    "- Output each paraphrase on its own line.\n"
    "- Do not number, do not add explanations, do not add prefixes."
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
        if c.figure_no:
            tag += f" | Fig {c.figure_no}"
        page = f"p.{c.page_start}" if c.page_start == c.page_end else f"pp.{c.page_start}-{c.page_end}"
        tag += f" | {page}]"
        parts.append(f"{tag}\n{c.content}")
    return "\n\n---\n\n".join(parts)


def format_citation(c) -> str:
    # Tolerate NULL paragraph_id and a page range.
    page = f"p.{c.page_start}" if c.page_start == c.page_end else f"pp.{c.page_start}-{c.page_end}"
    if c.paragraph_id:
        return f"(Sec {c.section_no} | {c.paragraph_id}, {page})"
    return f"(Sec {c.section_no}, {page})"
