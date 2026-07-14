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
    "anchor_holding_power": {
        # HHP and VHHP are acronyms. _term_matches detects all-uppercase
        # tokens and applies word-boundary matching, so "HHP" will NOT
        # match inside "VHHP" (and vice versa). The full phrase
        # "very high holding power" is a vhhp token; "high holding power"
        # is intentionally NOT an hhp token because it is a substring of
        # the vhhp phrase and would cause a false hhp param_bonus on vhhp
        # queries that happen to include the full phrase.
        "hhp": ["HHP"],
        "vhhp": ["VHHP"],
    },
    # Build 7D: hatch corrosion addition (Sec 17 B Table 17.1). Discriminator
    # tokens for nonbulk vs bulk application columns of Table 17.1. Phrases
    # are kept long enough to avoid incidental match on general queries.
    "hatch_corrosion_addition": {
        "nonbulk": [
            "non-bulk", "non bulk",
            "other ship types", "all other ship types",
            "selain tipe kapal curah", "selain kapal curah",
            "passenger",
            "container ship", "container ships",
            "car carrier", "car carriers",
            "paper carrier", "paper carriers",
        ],
        "bulk": [
            "bulk carrier", "bulk carriers",
            "self-unloading", "self unloading",
            "ore carrier", "ore carriers",
            "combination carrier", "combination carriers",
        ],
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
    # cargo hatch coaming minimum height (Sec 17 A.2.2). Two positions.
    # Generics banned: bare "coaming" (overlaps with ventilator), bare "hatch",
    # bare "tutup palka" / "hatch cover" (overlaps with hose test queries).
    "cargo_hatch_coaming_height": (
        "hatch coaming",
        "cargo hatch",
        "hatchway coaming",
        "coaming palka",
        "palka kargo",
    ),
    # ventilator coaming minimum height (Sec 21 G.1.1). Two positions.
    # Generics banned: bare "coaming" (overlaps with cargo hatch).
    "ventilator_coaming_height": (
        "ventilator coaming",
        "coaming ventilator",
    ),
    # Poisson's ratio for aluminium alloys (Sec 2 D.1.7). Only for aluminium.
    # Generics banned: bare "poisson" alone is acceptable (distinctive enough).
    "poisson_ratio_aluminium": (
        "poisson",
        "poisson's ratio",
        "poisson ratio",
        "rasio poisson",
    ),
    # collision bulkhead position from forward perpendicular (Sec 11 A.2.1.1).
    # Position-specific anchors. Bare "collision bulkhead" / "sekat tubrukan"
    # excluded so thickness/other-aspect queries do not false-fire.
    "collision_bulkhead_position": (
        "forward perpendicular",
        "garis tegak haluan",
        "0,05Lc",
        "0,08Lc",
        "0.05Lc",
        "0.08Lc",
        "located from",
        "posisi sekat tubrukan",
        "sekat tubrukan dari",
        "sekat tabrakan dari",
        "posisi sekat tabrakan",
    ),
    # anchor holding power (Sec 18 C.4/C.5). HHP vs VHHP discriminated by
    # PARAM_TOKENS (acronyms, word-boundary matched). Anchor is RESTRICTIVE:
    # only "holding power" / "daya cengkeram" — generic "anchor", "stockless",
    # and the acronyms are excluded to prevent over-match on mass / other
    # aspect queries (e.g. "VHHP max mass", "HHP mass reduction %"). If
    # query carries neither holding-power phrase, the anchor gate rejects
    # the rule. If HHP/VHHP acronym absent, param_bonus is 0 and the
    # multi-param check returns None — no silent default.
    "anchor_holding_power": (
        "holding power",
        "daya cengkeram",
    ),
    # accommodation / superstructure deck min thickness (Sec 29 E.2).
    # Distinct from Sec 7 general deck plating (rules_deck_min_id).
    "accommodation_deck_min_thickness": (
        "accommodation deck",
        "accommodation decks",
        "superstructure deck",
        "superstructure decks",
        "geladak akomodasi",
        "geladak bangunan atas",
    ),
    # Build 7D: hatch corrosion addition (Sec 17 B Table 17.1). Distinct
    # from hatch_cover_deflection (Sec 17 B.2.2) and from
    # cargo_hatch_coaming_height / ventilator_coaming_height. Anchor requires
    # corrosion-specific phrases so the rule only fires on tK / corrosion
    # addition queries for hatch covers, not on coaming / deflection queries
    # or general 'corrosion' queries unrelated to hatches.
    "hatch_corrosion_addition": (
        "corrosion addition",
        "tambahan korosi",
        "corrosion addition tK",
        "corrosion addition hatch",
        "corrosion addition tk",
        "tk hatch",
        "tk palka",
        "hatch corrosion",
    ),
    # Build 7D: restrict hatch_cover_deflection to deflection-specific
    # queries. Trigger set includes generic phrases ('hatch cover',
    # 'penutup palka') that incidentally match hatch corrosion queries; the
    # anchor gate now requires a deflection-specific phrase before trigger
    # matching is allowed. hatch_deflection_en (golden) carries 'deflection'
    # and remains eligible. Hatch corrosion queries (carry 'corrosion'
    # /'tambahan korosi' but not 'defleksi'/'deflection'/'0,0056'/'lg')
    # are blocked here and routed to hatch_corrosion_addition.
    "hatch_cover_deflection": (
        "defleksi",
        "deflection",
        "0,0056",
        "lg",
    ),
    # Build 10 (Bagian A): supply_deck_thickness requires thickness language,
    # not just "kapal suplai" alone. Prevents misfire on location / position /
    # ventilation / engine-room queries that mention "kapal suplai" incidentally.
    "supply_deck_thickness": (
        "tebal", "thickness", "ketebalan",
        "pelat geladak", "deck plating",
    ),
    # Build 10 (Bagian A): tanker_strake_width requires strake / longitudinal
    # bulkhead context, not just "tanker" / "kapal tanker" alone. Prevents
    # misfire on dimension / STL / room queries that mention "tanker" incidentally.
    "tanker_strake_width": (
        "strake", "lebar strake", "0,1H", "1H",
        "longitudinal bulkhead", "sekat memanjang",
    ),
    # Build 10 (Bagian A): aluminium_steel_galvanic_insulation requires
    # galvanic/insulation context, not just "aluminium" / "paduan aluminium"
    # alone. Prevents misfire on temperature / fire / core queries that mention
    # aluminium incidentally.
    "aluminium_steel_galvanic_insulation": (
        "insulasi", "insulation", "isolasi",
        "galvanik", "korosi galvanik", "galvanic corrosion",
    ),
    # Build 10 (Bagian A): bulwark_guardrail_min_height requires minimum
    # height language. Prevents misfire on sill / door / compartment queries.
    # Build 10 (Bagian A): bulwark_guardrail_min_height anchor kept
    # equipment-specific ("bulwark"/"guard rail"/"railing"/"pagar pelindung")
    # after regression on neg_deckhouse_height_id where generic "tinggi
    # minimum"/"minimum" combined with en_query "height" + ID "tinggi" would
    # have met MIN_TRIGGER_MATCHES=2. Anchor must stay minimal.
    "bulwark_guardrail_min_height": (
        "bulwark", "guard rail", "guardrail", "railing", "pagar pelindung",
    ),
    # Build 13: anchor_vhhp_max_mass requires mass-specific language.
    # Prevents misfire on holding power / daya cengkeram queries that
    # also mention VHHP. Bare "VHHP" is NOT an anchor — both mass and
    # holding-power queries share the acronym.
    "anchor_vhhp_max_mass": (
        "maximum mass", "massa maksimum",
        "vhhp anchor mass", "massa jangkar vhhp",
        "exceed 1500", "1500 kg",
    ),
    # Build 13: anchor_hhp_mass_reduction requires reduction / percentage
    # language. Prevents misfire on stockless head mass (60%) queries and
    # on holding power queries. Bare "HHP" is NOT an anchor — multiple
    # aspect queries share the acronym.
    "anchor_hhp_mass_reduction": (
        "reduced", "reduksi",
        "percentage", "persen",
        "bower", "bower anchor",
        "75%",
        "massa jangkar stockless",
    ),
}

# Per-topic EXCLUDE_TERMS: if the query carries any of these phrases,
# the rule is skipped regardless of anchor/trigger match. Used to prevent
# over-match when the anchor name appears incidentally in a question
# about a different aspect (e.g. "HHP mass reduction" must not fire the
# anchor_holding_power lookup, even though "holding power" / "HHP" are
# present as part of the anchor type name).
EXCLUDE_TERMS: dict[str, tuple[str, ...]] = {
    "anchor_holding_power": (
        "mass", "massa",
        "reduction", "reduksi", "reduced",
        "percentage", "persen", "percent",
        "reduce", "kurangi",
    ),
    # reh_normal_steel: prevent over-fire on questions about specific
    # higher-strength steel grades (315, 355, 390, 460 N/mm2) which
    # are covered by material_factor_k rule.
    "reh_normal_steel": (
        "315", "355", "390", "460",
    ),
    # collision_bulkhead_barge: prevent over-fire on ship collision
    # bulkhead position queries (handled by collision_bulkhead_position).
    # Barge queries mention "barge" or "pontoon" or "Lcon".
    "collision_bulkhead_barge": (
        "forward perpendicular", "garis tegak haluan", "from FP", "0,05L",
        "thickness", "tebal", "plating",
    ),
    # stockless_anchor_head_mass: prevent over-fire on holding capacity
    # queries (handled by anchor_holding_power). Head mass vs holding
    # capacity are different aspects.
    "stockless_anchor_head_mass": (
        "holding", "hold",
        "daya cengkeram", "cengkeram",
        "two times", "four times", "dua kali", "empat kali",
    ),
    # towing_hook_force: prevent over-fire on drum/winch diameter queries
    # (handled by tug_winch_drum_diameter). Hook force vs drum diameter
    # are different aspects of the same equipment.
    "towing_hook_force": (
        "drum", "diameter", "14 times", "derek",
    ),
    # hatch_cover_deflection: prevent over-fire on coaming height queries
    # (handled by cargo_hatch_coaming_height). Deflection vs coaming
    # height are different aspects of hatch covers.
    "hatch_cover_deflection": (
        "coaming", "600 mm", "450 mm", "coaming height",
    ),
    # tug_winch_drum_diameter: prevent over-fire on questions about
    # towing winch HOLDING CAPACITY or BRAKE HOLDING (a different aspect
    # of the same equipment). Without this gate the winch/drum/tug anchors
    # and triggers match any winch query, and the rule returns the drum
    # diameter answer for a holding-capacity question. The correct
    # behaviour when no holding-capacity lookup rule exists is to fall
    # back to RAG, not to answer with the wrong aspect.
    "tug_winch_drum_diameter": (
        "holding", "hold",
        "brake",
        "capacity", "kapasitas",
    ),
    # poisson_ratio_aluminium: prevent over-fire on questions about
    # Poisson's ratio for steel / baja. The document does not state
    # Poisson's ratio for steel explicitly (context_note on the rule),
    # so the correct behaviour for steel queries is to fall back to RAG
    # rather than return the aluminium value (0.33).
    "poisson_ratio_aluminium": (
        "baja",
        "steel",
    ),
    # Build 10 (Bagian A): safety EXCLUDE for the ship-type numeric rules.
    "supply_deck_thickness": (
        "lokasi", "posisi", "di mana", "pintu", "lubang", "cut-out",
        "pipa udara", "ventilasi", "ruang mesin", "mesin", "compartment",
        "hatch", "hatchway",
    ),
    "tanker_strake_width": (
        "lokasi", "passageway", "STL", "submerged turret",
        "under-deck", "under deck", "ruang",
    ),
    "aluminium_steel_galvanic_insulation": (
        "suhu", "temperature", "kenaikan suhu", "tes api", "fire",
        "api", "core temperature",
    ),
    "bulwark_guardrail_min_height": (
        "sill", "ambang", "pintu", "door", "cut-out", "compartment",
        "pintu akses", "opening",
    ),
    # Build 13: anchor mass rules must not fire on holding power queries
    # that mention the same anchor type acronym (VHHP or HHP). The holding
    # power aspect is handled by anchor_holding_power.
    # Note: "holding power" and "daya cengkeram" are NOT excluded here
    # because the anchor type name "High/Very High Holding Power" itself
    # contains those phrases. Instead, holding-power-query discriminators
    # are used: comparison language (times/kali), kN units, etc.
    "anchor_vhhp_max_mass": (
        "kali", "times", "two", "four", "dua", "empat",
        "kN",
    ),
    "anchor_hhp_mass_reduction": (
        "kali", "times", "two", "four", "dua", "empat",
        "head", "kepala", "pins", "fittings",
        "60%", "60",
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

    Short tokens (≤2 chars) and all-uppercase acronyms (e.g. HHP, VHHP)
    must match as whole words (word boundary). This prevents substring
    collisions like "hhp" inside "vhhp" and "high holding power" inside
    "very high holding power".
    """
    is_acronym = term.isupper() and term.isalpha()
    term = _normalize(term)
    if " " not in term and (len(term) <= 2 or is_acronym):
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

        # Exclude gate: skip rules whose topic has exclude terms and the
        # query carries any of them. Prevents over-match on incidental
        # mentions of the topic (e.g. anchor name in a mass/aspect query).
        topic_excludes = EXCLUDE_TERMS.get(rule.topic)
        if topic_excludes is not None:
            if any(_term_matches(search_text, ex) for ex in topic_excludes):
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
