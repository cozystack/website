"""Shared helpers for the Cozystack website translation pipeline.

Pure-stdlib except PyYAML. No Hugo/Node required. Everything keys off the same
`source_digest` (sha256 of the English source) convention that hack/check-i18n.sh
already enforces, so the automated pipeline and the CI lint agree by construction.
"""

from __future__ import annotations

import copy
import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import PurePosixPath

import yaml

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
GLOSSARY_PATH = os.path.join(os.path.dirname(__file__), "glossary.yaml")

# Front-matter values we translate, AT ANY DEPTH. The landing page keeps
# user-visible copy in nested structures (taglines[], benefits[].title,
# features[].description, seo.title …) which Hugo renders into the hero and the
# cards — translating only top-level keys would copy the English hero verbatim
# into every locale and silently revert hand-translated pages.
# Everything else (slug, date, weight, aliases, images, icon, source_digest, …)
# is preserved verbatim.
TRANSLATABLE_FRONTMATTER_KEYS = ("title", "linkTitle", "description", "summary")
# Keys whose value is a list of user-visible strings, each translated.
TRANSLATABLE_LIST_KEYS = ("taglines", "keywords")

# Protected spans: replaced with opaque placeholders before the model sees the
# text, restored afterwards. Order matters (fenced code before inline code).
# SHORTCODE is handled specially (see protect) so that visible-text attributes
# inside it are still translated; the others are protected wholesale.
_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_SHORTCODE_RE = re.compile(r"\{\{[<%].*?[%>]\}\}", re.DOTALL)
_HTMLCOMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_INLINECODE_RE = re.compile(r"`[^`\n]+`")

# Shortcode attributes whose VALUE renders as visible text and must be
# translated: figure captions (shown under the image), alt text (screen readers
# + SEO), and titles. Everything else in a shortcode (src, width, id, class,
# link, the delimiters, the param names) is structure and stays verbatim.
_VISIBLE_ATTR_RE = re.compile(r'\b(?:caption|alt|title)="([^"]*)"')


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
    """Match rel against glob patterns with path (not string) semantics.

    PurePosixPath.match is right-anchored and segment-aware: `*.md` matches the
    BASENAME, so it matches a .md page at any depth (this is intended — see
    `translate_globs` in config.yaml), while `docs/*` matches one level only
    rather than silently swallowing the whole subtree the way fnmatch's `*`
    does by matching `/` too.

    Breadth here is deliberate: `*.md` casts wide and scope is then narrowed by
    exclude_globs, _docs_out_of_scope, and _blog_too_old. Those are the checks
    that bound the work, not this one.
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


def latest_docs_version(cfg: dict) -> str:
    """Read `params.latest_version_id` from hugo.yaml — the single source of truth.

    FAILS CLOSED: if hugo.yaml or the key is missing/renamed we raise rather than
    return None. Returning None would make _docs_out_of_scope a no-op and quietly
    pull every old, noindex'd docs version (and `next`) into scope — 7× the work,
    burning quota on pages search engines ignore, and nobody would notice for
    weeks. Hardcoding the version here would drift for the same reason.
    """
    path = os.path.join(REPO_ROOT, "hugo.yaml")
    if not os.path.exists(path):
        raise RuntimeError(f"hugo.yaml not found at {path}: cannot determine the latest "
                           f"docs version, refusing to guess the translation scope")
    with open(path, encoding="utf-8") as fh:
        hugo = yaml.safe_load(fh) or {}
    latest = (hugo.get("params") or {}).get("latest_version_id")
    if not latest:
        raise RuntimeError("hugo.yaml has no params.latest_version_id: cannot determine the "
                           "latest docs version, refusing to guess the translation scope")
    return str(latest)


def _docs_out_of_scope(rel: str, latest: str) -> bool:
    """True for any docs page that is not in the latest version (incl. `next`)."""
    if not rel.startswith("docs/"):
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


# ---- nested front-matter extraction ----------------------------------------


def extract_translatable(fm: dict) -> dict[str, str]:
    """Walk front matter and return {path: text} for every translatable string.

    Paths look like "title", "taglines[0]", "benefits[1].description", "seo.title"
    — stable addresses we can send to the model and apply back without touching
    anything structural (icons, dates, slugs, weights).
    """
    out: dict[str, str] = {}

    def walk(node, path: str, key: str | None):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else k, k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                if isinstance(v, str):
                    if key in TRANSLATABLE_LIST_KEYS and v.strip():
                        out[f"{path}[{i}]"] = v
                else:
                    walk(v, f"{path}[{i}]", key)
        elif isinstance(node, str):
            if key in TRANSLATABLE_FRONTMATTER_KEYS and node.strip():
                out[path] = node

    walk(fm, "", None)
    return out


_PATH_RE = re.compile(r"([^.\[\]]+)|\[(\d+)\]")


def apply_translations(fm: dict, values: dict[str, str]) -> dict:
    """Return a deep copy of fm with `values` ({path: text}) applied by path."""
    out = copy.deepcopy(fm)
    for path, text in values.items():
        tokens = [(m.group(1), m.group(2)) for m in _PATH_RE.finditer(path)]
        node = out
        for i, (name, idx) in enumerate(tokens):
            last = i == len(tokens) - 1
            key = name if name is not None else int(idx)
            try:
                if last:
                    node[key] = text
                else:
                    node = node[key]
            except (KeyError, IndexError, TypeError):
                break  # path no longer exists (source changed) — skip it
    return out


def merge_target_only_keys(out_fm: dict, existing_fm: dict | None) -> dict:
    """Preserve keys a human added to the translated page but that do not exist
    in the English source (e.g. a locale-specific `seo:` block, `l10n:` notes).

    Without this, regenerating a page from the English front matter silently
    deletes work native reviewers did by hand.
    """
    if not existing_fm:
        return out_fm
    for k, v in existing_fm.items():
        if k not in out_fm:
            out_fm[k] = v
    return out_fm


# ---- protect / restore ------------------------------------------------------


def protect(text: str) -> tuple[str, dict[str, str]]:
    """Replace code/shortcodes/comments with placeholders. Returns (masked, map).

    Shortcodes are NOT protected wholesale: a `{{< figure >}}` carries a visible
    `caption` (rendered under the image) and `alt` (screen readers, SEO). Masking
    the whole shortcode left those in English on every localized page. Instead the
    shortcode's structure is protected and its visible-text attribute values are
    exposed between placeholders, so they translate like ordinary prose while
    src/width/delimiters stay byte-for-byte.
    """
    store: dict[str, str] = {}
    counter = 0

    def _stash(s: str, kind: str) -> str:
        nonlocal counter
        token = f"§§{kind}_{counter}§§"
        store[token] = s
        counter += 1
        return token

    def _sub(kind):
        return lambda m: _stash(m.group(0), kind)

    # 1. Fenced code first (it may contain backticks/shortcode-like text).
    text = _FENCE_RE.sub(_sub("FENCE"), text)

    # 2. Shortcodes: protect structure, expose caption/alt/title values.
    def _shortcode(m: "re.Match") -> str:
        sc = m.group(0)
        out, pos = [], 0
        for a in _VISIBLE_ATTR_RE.finditer(sc):
            out.append(_stash(sc[pos:a.start(1)], "SC"))  # structure up to the value
            out.append(a.group(1))                        # visible text, left to translate
            pos = a.end(1)
        out.append(_stash(sc[pos:], "SC"))                # trailing structure
        return "".join(out)
    text = _SHORTCODE_RE.sub(_shortcode, text)

    # 3. Comments, then inline code.
    text = _HTMLCOMMENT_RE.sub(_sub("HTMLCOMMENT"), text)
    text = _INLINECODE_RE.sub(_sub("INLINECODE"), text)
    return text, store


def restore(text: str, store: dict[str, str]) -> str:
    for token, original in store.items():
        text = text.replace(token, original)
    return text


