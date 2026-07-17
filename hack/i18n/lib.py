"""Shared helpers for the Cozystack website translation pipeline.

Pure-stdlib except PyYAML. No Hugo/Node required. Everything keys off the same
`source_digest` (sha256 of the English source) convention that hack/check-i18n.sh
already enforces, so the automated pipeline and the CI lint agree by construction.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import PurePosixPath

import yaml

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
GLOSSARY_PATH = os.path.join(os.path.dirname(__file__), "glossary.yaml")

# Front-matter values we translate. Everything else (slug, date, weight,
# aliases, images, source_digest, params, …) is preserved verbatim.
TRANSLATABLE_FRONTMATTER_KEYS = ("title", "linkTitle", "description", "summary")

# Protected spans: replaced with opaque placeholders before the model sees the
# text, restored afterwards. Order matters (fenced code before inline code).
_PROTECT_PATTERNS = [
    ("FENCE", re.compile(r"```.*?```", re.DOTALL)),
    ("SHORTCODE", re.compile(r"\{\{[<%].*?[%>]\}\}", re.DOTALL)),
    ("HTMLCOMMENT", re.compile(r"<!--.*?-->", re.DOTALL)),
    ("INLINECODE", re.compile(r"`[^`\n]+`")),
]


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_glossary() -> dict:
    with open(GLOSSARY_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def sha256_file(path: str) -> str:
    """sha256 hex of raw file bytes — matches hack/check-i18n.sh."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _matches_any(rel: str, globs: list[str]) -> bool:
    """Match rel against glob patterns with sane path semantics.

    `fnmatch` treats `*` as matching `/` too, so a bare `*.md` silently matches
    `docs/v9/deep/page.md`. PurePosixPath.match gives proper segment semantics:
    `*.md` matches the basename only, and `docs/**` matches the subtree.
    """
    p = PurePosixPath(rel)
    for g in globs:
        if p.match(g):
            return True
        # PurePosixPath.match has no `**` recursion; expand `a/**` to a prefix test.
        if g.endswith("/**") and (rel == g[:-3] or rel.startswith(g[:-2])):
            return True
        if g.startswith("**/") and p.match(g[3:]):
            return True
    return False


def latest_docs_version(cfg: dict) -> str | None:
    """Read `params.latest_version_id` from hugo.yaml — the single source of truth.

    Hardcoding the version in this pipeline's config guarantees it drifts on the
    next release and quietly translates a noindex'd version.
    """
    path = os.path.join(REPO_ROOT, "hugo.yaml")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        hugo = yaml.safe_load(fh) or {}
    return ((hugo.get("params") or {}).get("latest_version_id")) or None


def _docs_out_of_scope(rel: str, latest: str | None) -> bool:
    """True for any docs page that is not in the latest version (incl. `next`)."""
    if not rel.startswith("docs/"):
        return False
    if latest is None:
        return False
    return not rel.startswith(f"docs/{latest}/")


_BLOG_DATE_RE = re.compile(r"^blog/(\d{4}-\d{2}-\d{2})-")


def _blog_too_old(rel: str, blog_since: str) -> bool:
    """True if rel is a blog post dated before the blog_since cutoff."""
    if not blog_since:
        return False
    m = _BLOG_DATE_RE.match(rel)
    return bool(m) and m.group(1) < blog_since


def iter_source_files(cfg: dict) -> list[str]:
    """Relative paths (under content/en) in scope for translation."""
    src_root = os.path.join(REPO_ROOT, cfg["content_dir"], cfg["source_lang"])
    latest = latest_docs_version(cfg)
    out: list[str] = []
    for dirpath, _dirs, files in os.walk(src_root):
        for name in files:
            if not name.endswith((".md", ".html")):
                continue
            rel = os.path.relpath(os.path.join(dirpath, name), src_root)
            rel = rel.replace(os.sep, "/")
            if cfg.get("exclude_globs") and _matches_any(rel, cfg["exclude_globs"]):
                continue
            if _blog_too_old(rel, cfg.get("blog_since", "")):
                continue
            if _docs_out_of_scope(rel, latest):
                continue
            if _matches_any(rel, cfg["translate_globs"]):
                out.append(rel)
    return sorted(out)


def source_path(cfg: dict, rel: str) -> str:
    return os.path.join(REPO_ROOT, cfg["content_dir"], cfg["source_lang"], rel)


def target_path(cfg: dict, lang: str, rel: str) -> str:
    return os.path.join(REPO_ROOT, cfg["content_dir"], lang, rel)


@dataclass
class WorkItem:
    lang: str
    rel: str
    reason: str  # "missing" | "stale"


def recorded_digest(path: str) -> str | None:
    """Read source_digest from a translated file's front matter, if present."""
    if not os.path.exists(path):
        return None
    # Read the whole front matter, not a fixed prefix: a long front matter would
    # push source_digest past a 4096-byte cut, the page would look permanently
    # stale, and it would be re-translated every single day.
    with open(path, encoding="utf-8") as fh:
        head = fh.read()
    fm_end = head.find("\n---", 4)
    if fm_end != -1:
        head = head[:fm_end]
    m = re.search(r"^source_digest:\s*\"?sha256:([0-9a-fA-F]+)\"?", head, re.MULTILINE)
    return m.group(1) if m else None


def build_worklist(cfg: dict, only_lang: str | None = None) -> list[WorkItem]:
    items: list[WorkItem] = []
    langs = [l["code"] for l in cfg["languages"] if only_lang in (None, l["code"])]
    for rel in iter_source_files(cfg):
        cur = sha256_file(source_path(cfg, rel))
        for lang in langs:
            tp = target_path(cfg, lang, rel)
            if not os.path.exists(tp):
                items.append(WorkItem(lang, rel, "missing"))
            elif recorded_digest(tp) != cur:
                items.append(WorkItem(lang, rel, "stale"))
    return items


# ---- front matter -----------------------------------------------------------

_FM_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def split_frontmatter(text: str) -> tuple[dict | None, str, str]:
    """Return (frontmatter_dict, body, raw_frontmatter). dict is None if absent.

    Only YAML front matter (--- fences) is handled; Cozystack content uses YAML.
    """
    m = _FM_RE.match(text)
    if not m:
        return None, text, ""
    raw = m.group(1)
    try:
        fm = yaml.safe_load(raw) or {}
    except yaml.YAMLError:
        fm = None
    return fm, m.group(2), raw


# ---- protect / restore ------------------------------------------------------


def protect(text: str) -> tuple[str, dict[str, str]]:
    """Replace code/shortcodes/comments with placeholders. Returns (masked, map)."""
    store: dict[str, str] = {}
    counter = 0

    def _sub(kind):
        def repl(match):
            nonlocal counter
            token = f"§§{kind}_{counter}§§"
            store[token] = match.group(0)
            counter += 1
            return token
        return repl

    for kind, pat in _PROTECT_PATTERNS:
        text = pat.sub(_sub(kind), text)
    return text, store


def restore(text: str, store: dict[str, str]) -> str:
    for token, original in store.items():
        text = text.replace(token, original)
    return text


def set_source_digest(front_lines: list[str], digest_hex: str) -> list[str]:
    """Insert/replace source_digest line in a list of front-matter YAML lines."""
    line = f'source_digest: "sha256:{digest_hex}"'
    for i, l in enumerate(front_lines):
        if l.startswith("source_digest:"):
            front_lines[i] = line
            return front_lines
    front_lines.append(line)
    return front_lines
