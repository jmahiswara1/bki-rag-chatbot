import pytest
from src.cli.format import format_for_cli


class TestFormatForCli:
    def test_display_math_with_symbols(self):
        given = r"\[ tp \geq 600 \times 100 = 60000 \text{ mm} \]"
        expected = "tp \u2265 600 \u00d7 100 = 60000 mm"
        assert format_for_cli(given) == expected

    def test_inline_dollar_math(self):
        assert format_for_cli("$x = 5$") == "x = 5"

    def test_frac_simple(self):
        assert format_for_cli(r"\frac{600}{100}") == "600/100"

    def test_frac_with_addition_parens(self):
        assert format_for_cli(r"\frac{a + b}{c}") == "(a + b)/c"

    def test_plain_text_unchanged(self):
        assert format_for_cli("Tebal pelat minimum adalah 6 mm.") == "Tebal pelat minimum adalah 6 mm."

    def test_idempotent(self):
        x = r"\[ tp \geq 600 \times 100 = 60000 \text{ mm} \]"
        once = format_for_cli(x)
        twice = format_for_cli(once)
        assert once == twice

    def test_no_leftover_known_commands(self):
        outputs = [
            format_for_cli(r"\times"),
            format_for_cli(r"\frac{x}{y}"),
            format_for_cli(r"\text{hello}"),
            format_for_cli(r"\sqrt{x}"),
            format_for_cli(r"\geq"),
            format_for_cli(r"\leq"),
            format_for_cli(r"\cdot"),
            format_for_cli(r"\mathrm{x}"),
        ]
        for o in outputs:
            assert r"\times" not in o
            assert r"\frac" not in o
            assert r"\text" not in o
            assert r"\sqrt" not in o
            assert r"\geq" not in o
            assert r"\leq" not in o
            assert r"\cdot" not in o
            assert r"\mathrm" not in o

    def test_inline_paren_math(self):
        assert format_for_cli(r"\(\alpha + \beta\)") == "alpha + beta"

    def test_double_dollar_display(self):
        assert "a" == format_for_cli("$$a$$")

    def test_sqrt_with_content(self):
        assert format_for_cli(r"\sqrt{25}") == "sqrt(25)"

    def test_superscript(self):
        assert format_for_cli("x^{2}") == "x^2"

    def test_subscript(self):
        assert format_for_cli("x_{max}") == "x_max"

    def test_windows_path_preserved(self):
        path = "E:\\Project\\bki-rag-chatbot"
        assert format_for_cli(path) == path

    def test_empty_string(self):
        assert format_for_cli("") == ""

    def test_left_right_parens(self):
        assert format_for_cli(r"\left( \frac{1}{2} \right)") == "(1/2)"

    def test_unknown_command_stripped(self):
        assert format_for_cli(r"\alpha test") == "alpha test"

    def test_combined_super_sub(self):
        assert format_for_cli("a_b^{c}") == "a_b^c"
