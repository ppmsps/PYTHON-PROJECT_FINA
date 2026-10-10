import unicodedata


def _char_width(ch):
    """Approximate terminal cell width using only Python stdlib.

    Works well for Latin, Thai, Arabic, Devanagari, CJK and common emoji.
    Combining/format/control characters do not consume a terminal cell.
    """
    cat = unicodedata.category(ch)
    if unicodedata.combining(ch) or cat.startswith("M") or cat.startswith("C"):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def display_width(text):
    """Return the visible terminal width of Unicode text.

    The function intentionally measures terminal *cells*, not Python
    ``len()`` or UTF-8 bytes. This keeps borders aligned when Thai names,
    accented Latin text, Arabic, Devanagari, CJK or emoji are displayed.
    """
    text = unicodedata.normalize("NFC", str(text))
    width = 0
    i = 0
    while i < len(text):
        ch = text[i]
        # Zero-width joiner sequences are rendered as one emoji glyph by
        # modern terminals; count the sequence as one wide cell pair.
        if unicodedata.category(ch) == "Cf" and ch == "\u200d":
            i += 1
            continue
        width += _char_width(ch)
        i += 1
    return width


def fit_text(text, width, align="left"):
    """Fit Unicode text to exactly ``width`` terminal cells."""
    text = unicodedata.normalize("NFC", str(text))
    result = []
    current = 0
    for char in text:
        cw = _char_width(char)
        if current + cw > width:
            break
        result.append(char)
        current += cw
    result = "".join(result)
    padding = max(0, width - current)
    if align == "right":
        return " " * padding + result
    if align == "center":
        left = padding // 2
        return " " * left + result + " " * (padding - left)
    return result + " " * padding


def table_line(widths):
    return "+" + "+".join("-" * (w + 2) for w in widths) + "+"


def table_row(values, widths, aligns=None):
    if aligns is None:
        aligns = ["left"] * len(widths)
    cells = []
    for value, width, align in zip(values, widths, aligns):
        cells.append(" " + fit_text(value, width, align) + " ")
    return "|" + "|".join(cells) + "|"
