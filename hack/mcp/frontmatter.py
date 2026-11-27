"""Reading and writing YAML front matter of Hugo content files.

Kept deliberately small: the publishing tools need to inspect a handful of
keys and to emit front matter in the shape the existing blog posts use, not
to model everything Hugo accepts.
"""

from __future__ import annotations

import re

import yaml

DELIMITER = "---"

# Key order used when writing front matter, mirroring the existing blog posts.
# Keys not listed here follow, alphabetically.
KEY_ORDER = [
    "title",
    "slug",
    "date",
    "author",
    "description",
    "images",
    "article_types",
    "topics",
]


_OPENING_RE = re.compile(rf"{DELIMITER}[ \t]*\r?\n")
_CLOSING_RE = re.compile(rf"^{DELIMITER}[ \t]*\r?$", re.MULTILINE)


class FrontMatterError(Exception):
    """Raised when a content file has no parseable front matter."""


def split(text: str) -> tuple[str, str]:
    """Split a content file into its raw front matter and body.

    Returns (front_matter_text, body). Raises FrontMatterError when the file
    does not open with a delimiter or the closing delimiter is missing.
    """
    # Both delimiters must stand alone on their line: "---title: x" is not an
    # opening, and a "---" inside a block scalar line is not a closing.
    opening = _OPENING_RE.match(text)
    if opening is None:
        raise FrontMatterError("file does not start with '---'")

    rest = text[opening.end() :]
    closing = _CLOSING_RE.search(rest)
    if closing is None:
        raise FrontMatterError("closing '---' not found")

    fm = rest[: closing.start()]
    body = rest[closing.end() :]
    return fm.lstrip("\n"), body.lstrip("\n")


def load(text: str) -> tuple[dict, str]:
    """Parse a content file into (front matter mapping, body)."""
    fm_text, body = split(text)
    try:
        data = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError as exc:
        raise FrontMatterError(f"front matter is not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise FrontMatterError("front matter is not a mapping")
    return data, body


class _Dumper(yaml.SafeDumper):
    """Indents sequences, so lists match the style of the existing posts."""

    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


# Written unquoted so Hugo parses them as dates rather than strings.
_UNQUOTED_KEYS = {"date"}


def dump(data: dict, body: str) -> str:
    """Render front matter and body back into a content file.

    The output is shaped to match the hand-written posts: keys in the usual
    order, double-quoted scalars, indented lists, and no line wrapping. That
    last one matters beyond aesthetics — a wrapped title reaches the templates
    with the fold in it, which then shows up in og:title and in the JSON-LD
    headline.
    """
    ordered = {}
    for key in KEY_ORDER:
        if key in data:
            ordered[key] = data[key]
    for key in sorted(data):
        if key not in ordered:
            ordered[key] = data[key]

    lines = []
    for key, value in ordered.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {_scalar(item)}")
        elif key in _UNQUOTED_KEYS:
            lines.append(f"{key}: {value}")
        else:
            lines.append(f"{key}: {_scalar(value)}")

    fm = "\n".join(lines)
    body = body.rstrip("\n")
    return f"{DELIMITER}\n{fm}\n{DELIMITER}\n\n{body}\n"


# Characters YAML does not allow raw inside a double-quoted scalar, or that
# would break the value across lines, mapped to their escape sequences.
_NAMED_ESCAPES = {
    "\\": "\\\\",
    '"': '\\"',
    "\0": "\\0",
    "\a": "\\a",
    "\b": "\\b",
    "\t": "\\t",
    "\n": "\\n",
    "\v": "\\v",
    "\f": "\\f",
    "\r": "\\r",
    "\x1b": "\\e",
    "\x85": "\\N",
    "\u2028": "\\L",
    "\u2029": "\\P",
}


def _escape_char(char: str) -> str:
    if char in _NAMED_ESCAPES:
        return _NAMED_ESCAPES[char]
    code = ord(char)
    if code < 0x20 or 0x7F <= code <= 0x9F:
        return f"\\x{code:02x}"
    if 0xD800 <= code <= 0xDFFF or code in (0xFFFE, 0xFFFF):
        return f"\\u{code:04x}"
    return char


def _scalar(value) -> str:
    """Render one scalar as a YAML value on a single line.

    Strings are always double-quoted, with control characters escaped, so a
    value containing a newline still occupies exactly one line and reads back
    unchanged.
    """
    if isinstance(value, bool) or value is None or isinstance(value, (int, float)):
        rendered = yaml.safe_dump(value, default_flow_style=True).strip()
        # safe_dump terminates a bare scalar document with an explicit "..."
        # end marker; drop that suffix, not every trailing dot.
        if rendered.endswith("..."):
            rendered = rendered[: -len("...")].rstrip()
        return rendered
    escaped = "".join(_escape_char(char) for char in str(value))
    return f'"{escaped}"'
