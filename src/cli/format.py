import re

_SYMBOL_MAP: dict[str, str] = {
    r"\times": "\u00d7",
    r"\div": "\u00f7",
    r"\cdot": "\u00b7",
    r"\pm": "\u00b1",
    r"\geq": "\u2265",
    r"\leq": "\u2264",
    r"\le": "\u2264",
    r"\ge": "\u2265",
    r"\neq": "\u2260",
    r"\approx": "\u2248",
}

_DELIM_MAP: list[tuple[str, str]] = [
    (r"\left", ""),
    (r"\right", ""),
    (r"\;", " "),
    (r"\:", " "),
    (r"\,", " "),
    (r"\!", " "),
    (r"\quad", " "),
    (r"\qquad", " "),
]

_DISPLAY_OPEN = re.compile(r"(?<!\\)\\\[")
_DISPLAY_CLOSE = re.compile(r"(?<!\\)\\\]")
_INLINE_OPEN = re.compile(r"(?<!\\)\\\(")
_INLINE_CLOSE = re.compile(r"(?<!\\)\\\)")
_DOLLAR_DISPLAY = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)
_DOLLAR_INLINE = re.compile(r"(?<!\\)\$([^$]+?)(?<!\\)\$")


def _match_brace_content(text: str, start: int) -> tuple[str, int] | None:
    """Parse balanced-brace content starting at text[start] (the '{')."""
    if start >= len(text) or text[start] != "{":
        return None
    depth = 0
    i = start
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1 : i], i + 1
        i += 1
    return None


def _replace_frac(text: str) -> str:
    """Replace \\frac{a}{b} with a/b, adding parens when a or b need them."""
    result: list[str] = []
    i = 0
    while i < len(text):
        if text[i : i + 5] == r"\frac" and i + 5 < len(text) and text[i + 5] == "{":
            num_res = _match_brace_content(text, i + 5)
            if num_res is None:
                result.append(text[i])
                i += 1
                continue
            num, pos2 = num_res
            if pos2 < len(text) and text[pos2] == "{":
                den_res = _match_brace_content(text, pos2)
                if den_res is None:
                    result.append(text[i])
                    i += 1
                    continue
                den, pos3 = den_res
                num_str = num.strip()
                den_str = den.strip()
                if any(c in num_str for c in "+-"):
                    num_str = f"({num_str})"
                if any(c in den_str for c in "+-"):
                    den_str = f"({den_str})"
                result.append(f"{num_str}/{den_str}")
                i = pos3
                continue
        result.append(text[i])
        i += 1
    return "".join(result)


def _replace_text_macros(text: str) -> str:
    """Replace \\text{...} and \\mathrm{...} with their content."""
    def _repl(m):
        content = m.group(1) or m.group(2)
        return content
    text = re.sub(r"\\text\s*\{(.+?)\}", _repl, text)
    text = re.sub(r"\\mathrm\s*\{(.+?)\}", _repl, text)
    return text


def _replace_sqrt(text: str) -> str:
    """Replace \\sqrt{x} with sqrt(x)."""
    result: list[str] = []
    i = 0
    while i < len(text):
        if text[i : i + 5] == r"\sqrt" and i + 5 < len(text) and text[i + 5] == "{":
            content_res = _match_brace_content(text, i + 5)
            if content_res is None:
                result.append(text[i])
                i += 1
                continue
            content, pos2 = content_res
            result.append(f"sqrt({content.strip()})")
            i = pos2
            continue
        result.append(text[i])
        i += 1
    return "".join(result)


def _replace_super_sub_script(text: str) -> str:
    """Replace _{...} -> _... and ^{...} -> ^... (plain, no braces)."""
    result: list[str] = []
    i = 0
    while i < len(text):
        if text[i] in "_{" and i + 1 < len(text) and text[i + 1] == "{":
            prefix = text[i]
            content_res = _match_brace_content(text, i + 1)
            if content_res is None:
                result.append(text[i])
                i += 1
                continue
            content, pos2 = content_res
            result.append(f"{prefix}{content.strip()}")
            i = pos2
            continue
        if text[i] in "^" and i + 1 < len(text) and text[i + 1] == "{":
            content_res = _match_brace_content(text, i + 1)
            if content_res is None:
                result.append(text[i])
                i += 1
                continue
            content, pos2 = content_res
            result.append(f"^{content.strip()}")
            i = pos2
            continue
        result.append(text[i])
        i += 1
    return "".join(result)


def _remove_unknown_commands(text: str) -> str:
    """Remove backslash from orphan LaTeX command tokens like \\word.

    Only matches \\[a-zA-Z]+ when the backslash is NOT part of a Windows
    path (i.e. not preceded by a letter or colon). The backslash-letter
    sequence must be a standalone token, not embedded in a path segment.
    """
    def _repl(m):
        return m.group(1)
    text = re.sub(r"(?<![a-zA-Z:])\\([a-zA-Z]+)", _repl, text)
    return text


def _clean_spaces(text: str) -> str:
    """Collapse multiple spaces and remove padding around parentheses."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)
    text = text.strip(" ")
    return text


def format_for_cli(text: str) -> str:
    """Convert LaTeX math to plain text for terminal display.

    Deterministic, idempotent, no LLM calls. Only changes formatting,
    never numeric values.
    """
    if not text:
        return text
    s = text

    for left, right in _DELIM_MAP:
        s = s.replace(left, right)

    s = _DISPLAY_OPEN.sub("", s)
    s = _DISPLAY_CLOSE.sub("", s)
    s = _INLINE_OPEN.sub("", s)
    s = _INLINE_CLOSE.sub("", s)
    s = _DOLLAR_DISPLAY.sub(r"\1", s)
    s = _DOLLAR_INLINE.sub(r"\1", s)

    s = _replace_frac(s)
    s = _replace_sqrt(s)
    s = _replace_text_macros(s)

    for cmd, repl in _SYMBOL_MAP.items():
        s = s.replace(cmd, repl)

    s = _replace_super_sub_script(s)
    s = _remove_unknown_commands(s)
    s = _clean_spaces(s)

    return s
