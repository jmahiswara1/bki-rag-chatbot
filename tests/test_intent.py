"""Unit tests for intent classification heuristic (Fase 5).

Tests the classify() function from src.llm.intent to ensure:
- Calculation (high): has_num AND (has_imper OR topical)
- Calculation (low/ambiguous): has_imper AND NOT is_quest AND NOT has_num
- Rules_qa: all other cases (fall through to LLM)

These tests are deterministic (no Ollama/Supabase calls).
"""
import sys
sys.path.insert(0, r"E:\Project\bki-rag-chatbot")

from src.llm.intent import classify


def test_calc_high_with_numbers_and_imperative():
    """Calculation (high): has_num AND has_imper"""
    query = "Calculate section modulus with a=0.6, pL=10, k=1, tK=1"
    intent = classify(query)
    assert intent.kind == "calculation"
    assert intent.confidence == "high"
    assert intent.source == "heuristic"
    print("PASS: test_calc_high_with_numbers_and_imperative")


def test_calc_high_with_numbers_and_topical():
    """Calculation (high): has_num AND topical hit"""
    query = "Hitung tebal web penumpu tengah dengan L=100"
    intent = classify(query)
    assert intent.kind == "calculation"
    assert intent.confidence == "high"
    assert intent.source == "heuristic"
    print("PASS: test_calc_high_with_numbers_and_topical")


def test_calc_low_ambiguous_imperative_no_numbers():
    """Calculation (low/ambiguous): has_imper AND NOT is_quest AND NOT has_num"""
    query = "Tolong hitung tebal pelat"
    intent = classify(query)
    assert intent.kind == "calculation"
    assert intent.confidence == "low"
    assert intent.source == "heuristic"
    print("PASS: test_calc_low_ambiguous_imperative_no_numbers")


def test_calc_low_ambiguous_english():
    """Calculation (low/ambiguous): has_imper AND NOT is_quest AND NOT has_num"""
    query = "Calculate the thickness for me"
    intent = classify(query)
    assert intent.kind == "calculation"
    assert intent.confidence == "low"
    assert intent.source == "heuristic"
    print("PASS: test_calc_low_ambiguous_english")


def test_rules_qa_how_calculated():
    """Rules_qa: question about how something is calculated (not a calculation request)"""
    query = "How is the section modulus of tween deck frames calculated?"
    intent = classify(query)
    # Should be rules_qa with HIGH confidence (branch 3: is_quest AND NOT has_num AND NOT has_imper)
    assert intent.kind == "rules_qa"
    assert intent.confidence == "high"
    assert intent.source == "heuristic"
    print("PASS: test_rules_qa_how_calculated")


def test_rules_qa_how_defined():
    """Rules_qa: question about how something is defined (not a calculation request)"""
    query = "How is frame spacing 'a' defined in the framing rules?"
    intent = classify(query)
    # Should be rules_qa with HIGH confidence (branch 3: is_quest AND NOT has_num AND NOT has_imper)
    assert intent.kind == "rules_qa"
    assert intent.confidence == "high"
    assert intent.source == "heuristic"
    print("PASS: test_rules_qa_how_defined")


def test_rules_qa_kapan():
    """Rules_qa: question about when (not a calculation request)"""
    query = "Kapan gading forecastle perlu diperkuat terhadap kecepatan kapal?"
    intent = classify(query)
    # Should be rules_qa with HIGH confidence (kapan is a question cue)
    assert intent.kind == "rules_qa"
    assert intent.confidence == "high"
    assert intent.source == "heuristic"
    print("PASS: test_rules_qa_kapan")


def test_rules_qa_bagaimana_menentukan():
    """Rules_qa: question about how to determine (not a calculation request)"""
    query = "Bagaimana menentukan beban dek pL untuk perhitungan pelat?"
    intent = classify(query)
    # Should be rules_qa with HIGH confidence (bagaimana is a question cue)
    assert intent.kind == "rules_qa"
    assert intent.confidence == "high"
    assert intent.source == "heuristic"
    print("PASS: test_rules_qa_bagaimana_menentukan")


def test_rules_qa_berapa_menurut_aturan():
    """Rules_qa: question about what the rule says (not a calculation request)"""
    query = "Berapa tebal minimum pelat dek kedua menurut aturan?"
    intent = classify(query)
    # Should be rules_qa with HIGH confidence (berapa is a question cue)
    assert intent.kind == "rules_qa"
    assert intent.confidence == "high"
    assert intent.source == "heuristic"
    print("PASS: test_rules_qa_berapa_menurut_aturan")


def test_table_routing_gate_t271():
    """Build 32a: T27.1 table value request must bypass LLM fallback and go to rules_qa."""
    query = "test force for design force 800 kN"
    intent = classify(query)
    assert intent.kind == "rules_qa"
    assert intent.confidence == "high"
    assert intent.source == "heuristic"


def test_table_routing_gate_t391():
    """Build 32a: T39.1 table value request must bypass LLM fallback."""
    query = "brittle crack arrest steel for thickness 60 mm"
    intent = classify(query)
    assert intent.kind == "rules_qa"
    assert intent.confidence == "high"
    assert intent.source == "heuristic"


def test_table_routing_gate_explicit_table():
    """Build 32a: Explicit table mention must bypass LLM fallback."""
    query = "table 19.1 bending radius"
    intent = classify(query)
    assert intent.kind == "rules_qa"
    assert intent.confidence == "high"
    assert intent.source == "heuristic"


def test_word_boundary_perhitungan():
    """Regression: 'perhitungan' should NOT trigger calculation (word boundary test)"""
    query = "Apa itu perhitungan tebal pelat?"
    intent = classify(query)
    # Should be rules_qa (perhitungan contains hitung but word boundary prevents match)
    assert intent.kind == "rules_qa"
    assert intent.confidence == "high"
    assert intent.source == "heuristic"
    print("PASS: test_word_boundary_perhitungan")


def test_gate_33a_not_overroute_calc_imperative_en():
    """Build 33a: Query with compute imperative must stay calculation, not rules_qa."""
    query = "calculate section modulus for L=150"
    intent = classify(query)
    assert intent.kind == "calculation", f"expected calculation, got {intent.kind}"


def test_gate_33a_not_overroute_calc_assignment_en():
    """Build 33a: Query with explicit assignment must stay calculation."""
    query = "moment of inertia for L=100"
    intent = classify(query)
    assert intent.kind == "calculation", f"expected calculation, got {intent.kind}"


def test_gate_33a_not_overroute_calc_imperative_id():
    """Build 33a: Indonesian compute imperative must stay calculation."""
    query = "Hitung tebal web penumpu tengah untuk L=100"
    intent = classify(query)
    assert intent.kind == "calculation", f"expected calculation, got {intent.kind}"


def test_gate_33a_not_overroute_calc_topical_id():
    """Build 33a: Indonesian topical term with assignment must stay calculation."""
    query = "Kalkulasi modulus penampang untuk jarak gading 0.5"
    intent = classify(query)
    assert intent.kind == "calculation", f"expected calculation, got {intent.kind}"


if __name__ == "__main__":
    test_calc_high_with_numbers_and_imperative()
    test_calc_high_with_numbers_and_topical()
    test_calc_low_ambiguous_imperative_no_numbers()
    test_calc_low_ambiguous_english()
    test_rules_qa_how_calculated()
    test_rules_qa_how_defined()
    test_rules_qa_kapan()
    test_rules_qa_bagaimana_menentukan()
    test_rules_qa_berapa_menurut_aturan()
    test_word_boundary_perhitungan()
    print("\nAll 10 tests passed!")
