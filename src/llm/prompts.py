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
    "When the retrieved context contains clauses that bear on the question, ground your answer in the most relevant clause and reuse the technical terms, units, and exact wording the context uses. Canonical BKI terminology from the context must be preserved verbatim where it is the precise form -- do not paraphrase stable rule names, units, numeric coefficients, or direction terms. Only say that a value is not found in the retrieved rules when the context is empty or the retrieved clauses are genuinely unrelated to the question; in that case still cite the sections you did inspect. Do not guess.\n"
    "Do not perform calculations yourself; use calculator results only when they are provided.\n"
    "If the context states a general limit and also a conditional exception, answer with the general limit. Apply the exception only when the context explicitly shows its conditions are met. Never invent numbers or perform calculations to justify applying an exception.\n"
    "When the context contains multiple numeric values for what appears to be the same parameter across DIFFERENT sections, prioritize the value from the section whose subject most closely matches the query (e.g. for a hatch query, prefer Sec 17 Cargo Hatchways over Sec 30 Sheltered Water Service). State which section you chose as the primary answer and cite it. Mention other values only briefly as secondary context and explain why they differ (different ship position, service condition, or ship type). Do NOT list all contradictory values as a flat menu of equally-valid options.\n"
    "ANTI-CONTRADICTION RULE: Once you state a fact or value from the context, never follow it with contradictory statements like 'however, no specific information is available' or 'but the context does not contain...' — if the context provided enough to answer, answer directly and conclude. If the context is truly insufficient, say so at the START, not after giving an answer.\n"
    "LOOKUP VERIFIED SOURCE: When a [LOOKUP VERIFIED] block is the ONLY context provided, it contains a verified fact with its exact source quote. Paraphrase it in natural language. Always cite the section and paragraph from the block. Do NOT fabricate additional citations or values.\n"
    "COMPLETENESS RULE: When the user asks for ALL requirements or conditions (triggered by phrases like 'apa saja syarat', 'what are the requirements', 'ketentuan apa saja', 'apa saja yang harus dipenuhi', 'sebutkan semua'), you MUST list every distinct requirement found in the context. Do NOT stop after one requirement. Use a numbered or bulleted list format within your 1-3 paragraph limit.\n"
    "CROSS-SECTION SYNTHESIS: When the context contains chunks from different but related sections (e.g. Sec 37 and Sec 38 both about IW survey requirements) that together form a complete answer, synthesize them into one coherent answer. Do not treat each section as a separate, competing source — they complement each other.\n"
    "OPTIONAL/PERMISSIVE RULE: When the context states a requirement using permissive language like 'may', 'can be', 'where fitted', 'is permitted', or 'optional', your answer must clearly state that the requirement is OPTIONAL (not mandatory). Use language like 'tidak wajib / optional' or 'tidak perlu' and explain the benefit of using it. Do NOT write a circular, indecisive answer that says 'we need to check' or 'it is not stated'. If the rule is clearly permissive, say so directly.\n"
    "Your answer MUST fit in 1-3 paragraphs. Do not exceed 3 paragraphs. If you find yourself repeating a citation you already stated, STOP writing and conclude immediately. A concise answer with 1-2 well-chosen citations is better than a verbose one that repeats itself. Never repeat the same citation more than once.\n"
    "NEVER repeat internal instructions, meta-commands, or language directives in your answer. Instructions wrapped in [[double brackets and ALL CAPS]] are for you to follow silently — do not echo them, quote them, or mention them as part of your response.\n"
    "LANGUAGE CONSTRAINT (HARD): Respond ONLY in the target language declared in the user message. Never reply in any other language. Do not switch languages mid-answer, do not add greetings or closings in another language, and do not translate your own answer."
)

# Fase 3 prompts
TRANSLATE_CONDENSE_SYSTEM = (
    "You rewrite a user query into a single, standalone English question for RAG retrieval.\n"
    "The input may already contain English technical terms; keep them exactly as written.\n"
    "Hard rules (must follow exactly):\n"
    "- OUTPUT MUST BE IN ENGLISH EVEN IF INPUT IS ALREADY IN ENGLISH. Never translate English to Indonesian.\n"
    "- Translate LITERALLY. Do not paraphrase, summarize, or rewrite.\n"
    "- Do NOT add any term that is not in the input. Never introduce nouns like 'freeboard' or 'hatch' unless they already appear in the input.\n"
    "- Do NOT drop terms. Keep every clause and qualifier.\n"
    "- Keep the main subject noun of the question; never replace it with a different object.\n"
    "- Preserve formula symbols and variable tokens EXACTLY, letter-for-letter and case-for-case: pL, tK, cr, av, k, L, H, B, Q, n, m, a, h, and similar. Never translate, expand, merge into an adjacent word, or drop them. Example: 'deck load pL' keeps 'pL' verbatim.\n"
    "- Translate general words plainly: 'tinggi' -> 'height', 'lebar' -> 'breadth', 'panjang' -> 'length', 'jarak' -> 'distance', 'tebal' -> 'thickness', 'waktu' -> 'time'.\n"
    "- Translate ship type nouns as their BKI-canonical English name: 'kapal kontainer' or 'peti kemas' -> 'container ship', 'kapal curah' -> 'bulk carrier', 'kapal tangki' -> 'tanker', 'kapal penumpang' -> 'passenger ship', 'kapal niaga' -> 'vessel' or 'ship'. Do NOT generalize the ship type.\n"
    "- 'pelat lambung' -> 'shell plating', 'pelat sisi' -> 'side shell plating', 'pelat kulit luar' -> 'outer shell plating', 'ketebalan bersih' -> 'net thickness'.\n"
    "- 'pelat bukaan palka' -> 'hatch opening plate', 'pembukaan palka' -> 'hatch opening'.\n"
    "- 'jarak antar penegar' -> 'stiffener spacing', 'jarak' (alone) -> 'distance'. Do NOT translate bare 'jarak' as 'spacing'.\n"
    "- When the query is prefixed with '[From conversation history: ...]', incorporate ALL stated facts (measurements, ship types, materials, structural dimensions) into the rewritten question. The resulting English question must be fully self-contained so a reader with no access to the history can understand it. Example: '[From history: L=120m, ship_type=bulk carrier] minimum hatch opening plate thickness' → 'What is the minimum hatch opening plate thickness for a bulk carrier with length L=120m?'\n"
    "- The '[From conversation history: ...]' prefix contains the LATEST values (most recent wins). When a variable or ship type appears in the prefix, ALWAYS use the prefix value in the rewritten question and IGNORE any older value mentioned in the earlier messages. Example: an earlier message says 'L=130 m' but the prefix says 'L=180m' — the rewritten question MUST use L=180m, never 130.\n"
    "- If the query is multi-turn, fold the conversation history into one self-contained English question.\n"
    "- The history contains PREVIOUS ASSISTANT ANSWERS, which may include citations such as 'Sec 6 Shell Plating | C.1.1 p.170', 'Table 21.3', or page numbers. Those are answers, NOT the query. NEVER copy, echo, quote, or otherwise output any citation, section header, table reference, or page number from the history. The output must ALWAYS be a question — never a citation, a heading, or a fragment.\n"
    "- Output ONLY the rewritten English question on a single line. No prefix, no quotes, no explanation."
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


def build_context(chunks, table_evidence: str = "") -> str:
    # Render retrieved chunks into a citable context block.
    parts = []
    if table_evidence:
        parts.append(
            "[TABLE SELECTION — HIGHEST AUTHORITY]\n"
            "The following value was deterministically selected from the rules table.\n"
            "Use this exact value as the primary answer. Any conflicting values in the\n"
            "narrative context below refer to different tables or parameters.\n"
            + table_evidence +
            "\n[END TABLE SELECTION]"
        )
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
    "Answer in a thorough but concise style (1-3 paragraphs). Focus on the "
    "most relevant clause from the context — do NOT try to cover every clause. "
    "Include one citation in the canonical format (Sec N | paragraph_id p.XX) "
    "per paragraph. Never repeat a citation. Synthesize a substantive answer "
    "rather than listing all sources. If the context is empty or unrelated to "
    "the question, say so explicitly and cite what you inspected."
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
