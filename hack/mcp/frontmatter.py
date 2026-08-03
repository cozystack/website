"""Reading and writing YAML front matter of Hugo content files.

Kept deliberately small: the publishing tools need to inspect a handful of
keys and to emit front matter in the shape the existing blog posts use, not
to model everything Hugo accepts.
"""

from __future__ import annotations

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


class FrontMatterError(Exception):
    """Raised when a content file has no parseable front matter."""


def split(text: str) -> tuple[str, str]:
    """Split a content file into its raw front matter and body.

    Returns (front_matter_text, body). Raises FrontMatterError when the file
    does not open with a delimiter or the closing delimiter is missing.
    """
    if not text.startswith(DELIMITER):
        raise FrontMatterError("file does not start with '---'")

    # Search for the closing delimiter on its own line.
    rest = text[len(DELIMITER) :]
    marker = f"\n{DELIMITER}"
    end = rest.find(marker)
    if end == -1:
        raise FrontMatterError("closing '---' not found")

    fm = rest[:end]
    body = rest[end + len(marker) :]
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


def dump(data: dict, body: str) -> str:
    """Render front matter and body back into a content file.

    Ordering follows KEY_ORDER so that generated posts stay diff-friendly
    against the hand-written ones.
    """
    ordered = {}
    for key in KEY_ORDER:
        if key in data:
            ordered[key] = data[key]
    for key in sorted(data):
        if key not in ordered:
            ordered[key] = data[key]

    fm = yaml.safe_dump(
        ordered,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    body = body.rstrip("\n")
    return f"{DELIMITER}\n{fm}{DELIMITER}\n\n{body}\n"
