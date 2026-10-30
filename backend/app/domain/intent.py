"""Finds "in category X" / "categorize as X" in a transcript. Pure: no I/O."""
import re

MAX_NAME_WORDS = 3
STOP_WORDS = {"and", "then", "also"}

_TRIGGER = re.compile(
    r"(?:\bin\s+(?:the\s+)?category|\bcategori[sz]e\s+(?:this\s+)?as)\s+",
    re.IGNORECASE,
)
_WORD = re.compile(r"[\w'-]+")


def parse_intent(text: str) -> tuple[str, str | None]:
    """Returns (clean_text, category_or_none). Without a clear phrase the text is unchanged."""
    text = text.strip()
    match = _TRIGGER.search(text)
    if match is None:
        return text, None

    words: list[str] = []
    end = match.end()
    for word in _WORD.finditer(text, match.end()):
        between = text[end : word.start()]
        if words and re.search(r"[.,;:!?]", between):
            break
        if not words and re.search(r"[.,;:!?]", between):
            return text, None
        if word.group().lower() in STOP_WORDS or len(words) == MAX_NAME_WORDS:
            break
        words.append(word.group())
        end = word.end()
    if not words:
        return text, None

    before = text[: match.start()].rstrip(" ,;:.")
    after = text[end:].lstrip(" ,;:.")
    if before and after.startswith(("and ", "then ", "also ")):
        clean = f"{before} {after}"
    elif before:
        clean = f"{before} {after}".strip() if after else before
    else:
        clean = after
    return clean.strip(), " ".join(words)
