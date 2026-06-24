import re

SYSTEM_PROMPT = (
    "You are a technical assistant for BKI Rules for Hull (Pt.1, Vol.II, 2026 Edition).\n"
    "Answer only from the provided context. If the context is insufficient, say so.\n"
    "Always cite the section and paragraph in the canonical format (Sec N | paragraph_id p.XX) --"
    " a single space between paragraph_id and the page, NO comma. For a page range, write pp.XX-YY.\n"
    "Example: (Sec 6 | B.4.3 p.103) or (Sec 6 | C.1.1 pp.170-180) or (Sec 7 p.50) if no paragraph_id.\n"
    "ALWAYS include at least one citation for every claim drawn from the context; do not answer without citing.\n"
    "Cite only sections, paragraphs, and pages that appear in the context tags. Never fabricate a citation.\n"
    "Use only values, numbers, formulas, fractions, ratios, and units that appear verbatim in the context. Do not invent, infer, approximate, or interpolate any value or formula. Do not add requirements, conditions, or thresholds that are not stated in the context.\n"
    "If a specific value, formula, or requirement needed to answer is not present in the context, say clearly that it is not found in the retrieved rules, and answer only the parts that ARE supported. Do not guess.\n"
    "Do not perform calculations yourself; use calculator results only when they are provided.\n"
    "LANGUAGE CONSTRAINT (HARD): Respond ONLY in the target language declared in the user message. Never reply in any other language. Do not switch languages mid-answer, do not add greetings or closings in another language, and do not translate your own answer."
)

# Fase 3 prompts
TRANSLATE_CONDENSE_SYSTEM = (
    "You rewrite a user query into a single, standalone English question for RAG retrieval.\n"
    "Hard rules (must follow exactly):\n"
    "- Translate LITERALLY. Do not paraphrase, summarize, or rewrite the question.\n"
    "- Preserve every technical or domain noun verbatim (e.g. 'senta' -> 'side stringer', 'pelat alas' -> 'floor plate', 'ceruk' -> 'peak', 'gading' -> 'frame', 'pelat dek' -> 'deck plate', 'tinggi bebas' -> 'freeboard', 'palka' -> 'hatch', 'bukaan palka' -> 'hatch opening', 'tutup palka' -> 'hatch cover', 'senta sisi' -> 'side stringer', 'haluan' -> 'fore part / forepeak', 'gading besar' -> 'web frame'). When an Indonesian term maps to a specific English BKI term, use that exact English term.\n"
    "- Preserve formula symbols and variable tokens EXACTLY, letter-for-letter and case-for-case: pL, tK, cr, av, k, L, H, B, Q, n, m, a, h, and similar. These are BKI notation, not words -- never translate, expand, spell out, merge into an adjacent word, or drop them. Example: 'beban dek pL' -> 'deck load pL' (keep 'pL' verbatim); NEVER 'deck plating weight'.\n"
    "- Do NOT change the subject. Do NOT add terms that are not in the original (no invented synonyms, no substitutions like 'pelat' -> 'stiffener' or 'ceruk' -> 'bilge strake').\n"
    "- Do NOT drop terms. Keep every clause and qualifier.\n"
    "- If the query is multi-turn, fold the conversation history into one self-contained question while preserving every term above.\n"
    "- Output ONLY the rewritten English question on a single line. No prefix, no quotes, no explanation, no extra punctuation."
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
    # Canonical format: (Sec N | paragraph_id p.XX) -- single space, NO comma.
    page = f"p.{c.page_start}" if c.page_start == c.page_end else f"pp.{c.page_start}-{c.page_end}"
    if c.paragraph_id:
        return f"(Sec {c.section_no} | {c.paragraph_id} {page})"
    return f"(Sec {c.section_no}, {page})"


# Answer-style instructions appended to the user message after Context+Question.
# "detailed" (default mode): thorough multi-paragraph answer with citations on
# "concise"  (fast mode): short, direct answer that still includes citations.
_ANSWER_STYLE_DETAILED = (
    "Answer in a thorough, multi-paragraph style. Cover every relevant clause "
    "from the context. ALWAYS include at least one citation for every claim,"
    " in the canonical format (Sec N | paragraph_id p.XX) -- single space,"
    " NO comma. For a page range use pp.XX-YY. Cite ALL sections that bear"
    " on the question. If the context is insufficient, say so explicitly --"
    " but still cite the sections you did inspect."
)
_ANSWER_STYLE_CONCISE = (
    "Answer concisely (a few sentences). Use citations of the form "
    "(Sec N | paragraph_id p.XX) -- single space, NO comma -- for the key claims,"
    " but keep the answer short and direct. ALWAYS cite at least one source."
    " If the context is insufficient, say so explicitly and cite what was inspected."
)


def answer_style_instruction(answer_style: str) -> str:
    if answer_style == "concise":
        return _ANSWER_STYLE_CONCISE
    return _ANSWER_STYLE_DETAILED


# Canonical citation regex (shared by test_phase3, test_phase5a, future tools).
# Tolerates all observed citation formats from qwen2.5:3b-instruct:
#
# Format 1 (with parens):    (Sec N <anything-no-parens 1-60 chars>)
# Format 2 (without parens): Sec N <eithertitle-with-pipe> or <page-with-dots>>
#
# Concretely observed variants that all match:
#   (Sec 6 | C.1.1 p.170)              -- canonical, parens, no comma
#   (Sec 3, F.5.1.6)                  -- legacy, parens, with comma, no page
#   (Sec 6 | C.1.1, p.170)             -- legacy, parens, with comma
#   (Sec 7, pp.50-60)                 -- legacy, parens, page range
#   (Sec 6 p.50)                       -- no paragraph_id
#   Sec 6 Shell Plating | C.3.2 p.171  -- no parens, with section title
#   Sec 6 | C.1.1 p.170                -- no parens, with pipe
#
# Tests check GROUNDING (a Sec N reference is present), not punctuation.
CITATION_RE = re.compile(
    r"(?:\([Ss]ec\s+\d+(?:[^()\n]{1,60})\))"
    r"|(?:[Ss]ec\s+\d+(?:[^.()\n]{1,40}\|\s*[\w.\-]+|\s+pp?\.\d+(?:-\d+)?))"
)


def has_citation(text: str) -> bool:
    """True iff text contains at least one citation matching CITATION_RE."""
    return bool(CITATION_RE.search(text))
# Tolerates all observed citation formats from qwen2.5:3b-instruct:
#   (Sec N | PARA p.XX)              -- canonical, parens, no comma
#   (Sec N, PARA)                     -- legacy, parens, with comma, no page
#   (Sec N | PARA, p.XX)              -- legacy, parens, with comma
#   (Sec N, pp.XX-YY)                 -- legacy, page range
#   Sec N Shell Plating | PARA p.XX   -- no parens, with section title
#   Sec N | PARA p.XX                 -- no parens, with pipe
#   (Sec N p.XX)                      -- no paragraph_id
# Tests check GROUNDING (a Sec N reference is present), not punctuation.
