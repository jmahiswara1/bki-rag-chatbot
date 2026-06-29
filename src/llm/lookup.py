"""Deterministic lookup from lookup_rules table (Fase B).

Pure-function matching layer. No LLM, no embedding, no mutation.
designed for Fase C integration into the pre-answer pipeline.
"""

import re
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LookupRule:
    """One row from the verified lookup_rules table."""
    topic: str
    parameter: str | None
    value_text: str
    value_num: float | None
    unit: str | None
    section_no: int
    paragraph_id: str | None
    page_no: int | None
    source_quote: str
    trigger_terms: tuple[str, ...]
    value_text_en: str | None = None
    value_text_id: str | None = None
    context_note: str | None = None
    def localized_text(self, lang: str) -> str:
        """Pick the body text in the query language.
        Priority: lang-specific column ('en' -> value_text_en, else
        value_text_id) if present, else fall back to the legacy
        value_text column.  Always returns a non-empty string.
        """
        if lang == "en":
            return self.value_text_en or self.value_text_id or self.value_text
        # default to ID for any non-en lang
        return self.value_text_id or self.value_text_en or self.value_text



@dataclass(frozen=True)
class LookupMatch:
    """Successful match result."""
    rule: LookupRule
    matched_terms: tuple[str, ...]
    score: int


# ---------------------------------------------------------------------------
# Parameter disambiguation tokens
# ---------------------------------------------------------------------------

PARAM_TOKENS: dict[str, dict[str, list[str]]] = {
    "restricted_service_modulus_reduction": {
        "P": ["restricted ocean", "P"],
        "L": ["coasting service", "L"],
        "T": ["sheltered water", "T"],
    },
    "fire_door_closing_time": {
        "hinged": ["hinged", "engsel"],
        "sliding": ["sliding", "geser", "sorong"],
    },
    "modulus_of_elasticity": {
        "steel": ["steel", "baja"],
        "aluminium": ["aluminium", "aluminum", "alumunium", "aluminium alloy", "paduan aluminium"],
    },
}

# Topics that have multiple parameter rows — must be disambiguated via
# PARAM_TOKENS match. Single-parameter topics (null param or unique topic)
# skip this check.
_MULTI_PARAM_TOPICS: frozenset[str] = frozenset(PARAM_TOKENS.keys())

_PARAM_BONUS: int = 2


# ---------------------------------------------------------------------------
# Anchor terms (per-topic). Required for a topic to be eligible.
#
# The trigger_terms sets in lookup_rules include some generic phrases
# (e.g. "haluan", "collision bulkhead", "tinggi") that overlap across
# topics and with general narrative queries. The anchor gate enforces
# that the query carries at least ONE topic-distinctive phrase before
# trigger matching is even allowed, eliminating false positives on
# near-miss questions (e.g. "depth/L ratio" must not fire restricted
# service, "collision bulkhead position" must not fire forepeak).
#
# Anchor phrases are designed from the actual trigger_terms + golden-set
# positive queries so each anchor appears in the corresponding positive
# query AND is absent from the documented negative queries.
# ---------------------------------------------------------------------------
ANCHOR_TERMS: dict[str, tuple[str, ...]] = {
    # restricted service (Sec 5): modulus reduction percentages P/L/T.
    # Generics banned: "range of service", bare "l", bare "service".
    "restricted_service_modulus_reduction": (
        "section modulus",
        "modulus penampang",
        "reduction",
        "reduksi",
        "restricted ocean",
        "coasting service",
        "sheltered water",
    ),
    # forepeak (Sec 9): tiers of beams / stringer spacing.
    # Generics banned: "collision bulkhead", "forward", bare "haluan".
    "forepeak_stringer_spacing": (
        "tiers of beams",
        "stringer",
        "forepeak",
        "ceruk haluan",
        "beam spacing",
    ),
    # tug winch drum (Sec 27): winch drum vs towrope.
    "tug_winch_drum_diameter": (
        "winch",
        "drum",
        "towing",
        "tow line",
    ),
    # fire door closing time / rate (Sec 22).
    "fire_door_closing_time": (
        "fire door",
        "pintu kebakaran",
        "closing time",
        "waktu penutupan",
    ),
    # bulwark / guard rail minimum height (Sec 6).
    "bulwark_guardrail_min_height": (
        "bulwark",
        "guard rail",
        "guardrail",
    ),
    # ship rule length L definition (Sec 1 H.2.1).
    # Generics banned: bare "length l" / bare "panjang l".
    "ship_length_l_definition": (
        "rule length",
        "definisi panjang kapal",
        "definition of ship length",
        "panjang aturan",
        "scantling draught",
        "foreside of stem",
        "rudder post",
    ),
    # depth H >= L/n by range of service (Sec 1 A.1).
    # Generics banned: bare "depth" / bare "kedalaman" / bare "l" / bare "length".
    "depth_to_length_ratio": (
        "depth to length ratio",
        "kedalaman terhadap panjang",
        "rasio kedalaman",
        "ratio of depth",
        "breadth to depth",
        "depth h",
    ),
    # main vertical zone max length/width on any deck (Sec 22 B.2.1).
    # Generics banned: bare "length" / bare "maximum" / bare "panjang maksimum".
    "main_vertical_zone_dimension": (
        "main vertical zone",
        "main vertical zones",
        "zona vertikal utama",
        "mvz",
    ),
    # probability factor fQ (Table 4.2, Sec 4 E.1).
    # Generics banned: bare "fq".
    "probability_factor_fq": (
        "probability factor",
        "faktor probabilitas",
        "probability level",
        "level probabilitas",
    ),
    # material factor k (Table 2.1, Sec 2 B.2).
    # Generics banned: bare "k" alone, bare "factor" alone.
    "material_factor_k": (
        "material factor",
        "faktor material",
    ),
    # modulus of elasticity E for hull structural steel (Sec 3 F.5.1.6).
    # modulus of elasticity E for hull structural steel (Sec 3 F.5.1.6) and
    # for aluminium alloys (Sec 2 D.1.7). Single-anchor: rows differ by
    # parameter (steel vs aluminium). PARAM_TOKENS disambiguates material.
    # Generics banned: bare "modulus" / bare "e" / bare "factor".
    "modulus_of_elasticity": (
        "modulus of elasticity",
        "young's modulus",
        "modulus elastisitas",
        "elastic modulus",
    ),
    # sea water density (rho, 1.025 t/m^3) per Sec 21 F.5.3.1.
    # Generics banned: bare "density" / bare "massa jenis" / bare "sea water" / bare "air laut".
    "sea_water_density": (
        "sea water density",
        "seawater density",
        "density of sea water",
        "massa jenis air laut",
        "densitas air laut",
        "berat jenis air laut",
    ),
}
# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Lowercase, replace punctuation with spaces, collapse whitespace."""
    s = text.lower()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _term_matches(normalized_search: str, term: str) -> bool:
    """Check if a single trigger term matches the search text.

    Short tokens (≤2 chars) must match as whole words (word boundary).
    Longer tokens and multi-word phrases match as substrings.
    """
    term = _normalize(term)
    if " " not in term and len(term) <= 2:
        return bool(re.search(r"\b" + re.escape(term) + r"\b", normalized_search))
    return term in normalized_search


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_verified_rules(client) -> list[LookupRule]:
    """Load all verified rows from lookup_rules via a Supabase client.

    The client is passed in; this module never reads .env or creates its own
    connection. Only verified=True rows are returned.
    """
    resp = client.table("lookup_rules").select("*").eq("verified", True).execute()
    rules: list[LookupRule] = []

    for row in resp.data:
        topic = row.get("topic")
        source_quote = row.get("source_quote")
        section_no = row.get("section_no")
        trigger_terms = row.get("trigger_terms")

        if not topic or not isinstance(topic, str):
            raise ValueError(f"lookup_rules row {row.get('id')}: missing or invalid topic")
        if not source_quote or not isinstance(source_quote, str):
            raise ValueError(f"lookup_rules row {row.get('id')}: missing or invalid source_quote")
        if not isinstance(section_no, int):
            raise ValueError(f"lookup_rules row {row.get('id')}: section_no must be int, got {type(section_no)}")
        if not trigger_terms or not isinstance(trigger_terms, list) or len(trigger_terms) == 0:
            raise ValueError(f"lookup_rules row {row.get('id')}: trigger_terms must be a non-empty list")

        rules.append(LookupRule(
            topic=topic,
            parameter=row.get("parameter"),
            value_text=row.get("value_text", ""),
            value_text_en=row.get("value_text_en"),
            value_text_id=row.get("value_text_id"),
            value_num=row.get("value_num"),
            unit=row.get("unit"),
            section_no=section_no,
            paragraph_id=row.get("paragraph_id"),
            page_no=row.get("page_no"),
            source_quote=source_quote,
            trigger_terms=tuple(trigger_terms),
            context_note=row.get("context_note"),
        ))

    if not rules:
        raise RuntimeError("No verified rows found in lookup_rules")

    return rules


def match_lookup(
    query_id: str,
    query_en: str,
    rules: list[LookupRule],
    min_matches: int = 2,
) -> LookupMatch | None:
    """Match a query pair against the lookup_rules via trigger_terms.

    Combines the Indonesian and English queries into one search text.
    Normalises case/whitespace/punctuation.  Short trigger tokens (≤2 chars)
    must match as whole words; longer terms match as substrings.

    Topic-distinctive ANCHOR_TERMS gate: for topics registered in
    ANCHOR_TERMS the query MUST carry at least one anchor phrase before
    trigger matching runs. Topics not in ANCHOR_TERMS fall through to
    the legacy behaviour. Kills false-positives on near-miss narrative
    queries (e.g. "depth/L ratio" must not fire restricted_service).

    Multi-parameter topics require at least one PARAM_TOKENS disambiguation
    token to match.  Ties return None.

    Returns LookupMatch(None) if no rule meets the threshold.
    """
    if not rules:
        return None

    search_text = _normalize(f"{query_id} {query_en}")

    candidates: list[tuple[LookupRule, tuple[str, ...], int, int]] = []
    # candidate = (rule, matched_terms, total_score, param_bonus)

    for rule in rules:
        # Anchor gate: skip rules whose topic requires an anchor but the
        # query does not carry any of the topic-distinctive phrases.
        topic_anchors = ANCHOR_TERMS.get(rule.topic)
        if topic_anchors is not None:
            anchor_hit = any(
                _term_matches(search_text, anchor) for anchor in topic_anchors
            )
            if not anchor_hit:
                continue

        matched: list[str] = []
        base_score = 0
        for term in rule.trigger_terms:
            if _term_matches(search_text, term):
                matched.append(term)
                base_score += 1

        param_bonus = 0
        is_multi = rule.topic in _MULTI_PARAM_TOPICS
        if is_multi and rule.parameter:
            param_list = PARAM_TOKENS.get(rule.topic, {}).get(rule.parameter, [])
            for pt in param_list:
                if _term_matches(search_text, pt):
                    param_bonus += _PARAM_BONUS

        total = base_score + param_bonus
        if total >= min_matches:
            candidates.append((rule, tuple(matched), total, param_bonus))

    if not candidates:
        return None

    candidates.sort(key=lambda c: c[2], reverse=True)
    best = candidates[0]

    # Tie at the top -> ambiguous
    if len(candidates) > 1 and candidates[1][2] == best[2]:
        # If all candidates share param_bonus=0 (no material token matched),
        # pick the first candidate by id as deterministic default (e.g.
        # steel for generic 'modulus elastisitas' query) instead of None.
        default_path = False
        if all(c[3] == 0 for c in candidates):
            # Default-path is ONLY for modulus_of_elasticity (no material
            # token in query -> pick steel as default). Other multi-param
            # topics must return None when param_token is missing.
            if best[0].topic == "modulus_of_elasticity":
                # Prefer 'steel' as default (BKI canonical); alphabetical tie-break.
                candidates.sort(key=lambda c: (0 if c[0].parameter == "steel" else 1, c[0].parameter or ""))
                best = candidates[0]
                default_path = True
            else:
                return None
        else:
            return None
        # Default-path: skip the strict param-token check below and return.
        if default_path:
            return LookupMatch(rule=best[0], matched_terms=best[1], score=best[2])
        return None

    # Multi-parameter topics: require at least one disambiguation token
    if best[0].topic in _MULTI_PARAM_TOPICS and best[3] == 0:
        # Default-path: if all candidates had param_bonus=0 (no material token
        # matched), we already picked the default (alphabetical first) above.
        # Skip the strict param-token requirement in that case.
        return None

    return LookupMatch(rule=best[0], matched_terms=best[1], score=best[2])
