"""Shared helpers for the Cozystack website translation pipeline.

Pure-stdlib except PyYAML. No Hugo/Node required. Everything keys off the same
`source_digest` (sha256 of the English source) convention that hack/check-i18n.sh
already enforces, so the automated pipeline and the CI lint agree by construction.
"""

from __future__ import annotations

import copy
import datetime
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

# Link DESTINATIONS. Only backticked code was structurally protected before, so a
# URL sitting in ordinary prose (`[text](https://…)`) was defended by a prompt rule
# alone — the model could silently mutate, localize or "fix" it and nothing would
# catch it. Masking the destination makes URL integrity a guarantee instead of a
# hope, while leaving the link TEXT exposed so it still gets translated.
#   inline:   [text](/docs/install "Optional title")  -> destination only
#   autolink: <https://example.com>
#   refdef:   [id]: https://example.com
_LINKDEST_RE = re.compile(r'(?<=\])\((?P<dest><[^>]*>|[^)\s]*)(?P<title>\s+"[^"]*")?\)')
_AUTOLINK_RE = re.compile(r'<(?:https?|mailto):[^>\s]+>')
_REFDEF_RE = re.compile(r'(?m)^(?P<label>\[[^\]]+\]:[ \t]*)(?P<dest>\S+)')


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
    """True for any docs page that is not in the latest version (incl. `next`).

    Pages that live directly under docs/ (the version-picker landing,
    docs/_index.md) are not version-specific and stay in scope: they are
    translated, indexed pages whose freshness hack/check-i18n.sh tracks, so the
    pipeline must keep them fresh. Only the versioned subtrees (docs/<ver>/...)
    are narrowed to the latest version.
    """
    parts = rel.split("/")
    if parts[0] != "docs":
        return False
    if len(parts) < 3:
        return False  # docs/<file> — version-agnostic, always in scope
    return parts[1] != latest


_BLOG_DATE_RE = re.compile(r"^blog/(\d{4}-\d{2}-\d{2})-")


def _blog_too_old(rel: str, blog_since: str) -> bool:
    """True if rel is a blog post dated before the blog_since cutoff.

    blog_since is either an ISO date ("2026-05-17") or a rolling window ("60d",
    meaning today minus 60 days, resolved at scope-computation time). A fixed
    date quietly rots into "no blog post is ever in scope" as the site ages;
    the rolling form is what the config should normally use.
    """
    if not blog_since:
        return False
    m = _BLOG_DATE_RE.match(rel)
    if not m:
        return False
    w = re.fullmatch(r"(\d+)d", blog_since.strip())
    if w:
        cutoff = (datetime.date.today() - datetime.timedelta(days=int(w.group(1)))).isoformat()
    else:
        cutoff = blog_since
    return m.group(1) < cutoff


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


def find_orphan_translations(cfg: dict, only_lang: str | None = None) -> list[str]:
    """Translated pages whose English source no longer exists.

    Deleting an English page used to leave its translations behind forever:
    the worklist iterates English sources, so nothing ever revisited the
    leftovers, and check-i18n.sh could only report them. The pipeline removes
    them instead (translate.py), so the weekly PR carries the deletion.

    Only files carrying a `source_digest` stamp are considered — the stamp is
    what marks a page as pipeline-managed. Hand-authored locale-only pages
    (no stamp) are never touched. A page that merely LEFT the translation
    scope (older docs version, aged-out blog post) is not an orphan: its
    English source still exists.
    """
    orphans: list[str] = []
    for lang in (l["code"] for l in cfg["languages"] if only_lang in (None, l["code"])):
        lang_root = os.path.join(REPO_ROOT, cfg["content_dir"], lang)
        for dirpath, _dirs, files in os.walk(lang_root):
            for name in files:
                if not name.endswith((".md", ".html")):
                    continue
                tp = os.path.join(dirpath, name)
                if recorded_digest(tp) is None:
                    continue
                rel = os.path.relpath(tp, lang_root).replace(os.sep, "/")
                if not os.path.exists(source_path(cfg, rel)):
                    orphans.append(tp)
    return sorted(orphans)


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

    # 4. Link destinations LAST, so URLs already inside code/shortcodes are
    #    covered by their own placeholders and are not double-masked. Link TEXT
    #    stays exposed and still gets translated; only the target is opaque.
    text = _AUTOLINK_RE.sub(_sub("URL"), text)
    text = _LINKDEST_RE.sub(
        lambda m: "(" + _stash(m.group("dest"), "URL") + (m.group("title") or "") + ")", text)
    text = _REFDEF_RE.sub(
        lambda m: m.group("label") + _stash(m.group("dest"), "URL"), text)
    return text, store


def restore(text: str, store: dict[str, str]) -> str:
    for token, original in store.items():
        text = text.replace(token, original)
    return text


# Hugo `ref`/`relref` shortcodes. Both argument shapes Hugo accepts:
#   positional: {{% ref "/docs/v1.5/getting-started/install-talos" %}}
#               {{< relref "install-cozystack#section" >}}
#   named:      {{% ref path="/docs/v1.5/x" lang="de" %}}
# The whole call is captured (args blob between `ref` and the closing delimiter),
# then `_ref_target` pulls the target out of either shape.
_REF_SHORTCODE = re.compile(r'\{\{[%<]\s*(?:rel)?ref\s+([^%>]*?)\s*[%>]\}\}')
_REF_PATH_NAMED = re.compile(r'\bpath\s*=\s*"([^"]+)"')
# Any residual ref/relref shortcode at all — used for the fail-closed check.
_ANY_REF_SHORTCODE = re.compile(r'\{\{[%<]\s*(?:rel)?ref\b')


def _ref_target(args: str) -> str | None:
    """Extract the link target from a ref/relref args blob, or None if it cannot
    be determined (an unsupported shape — the caller then fails closed)."""
    named = _REF_PATH_NAMED.search(args)
    if named:
        return named.group(1)
    args = args.strip()
    if not args:
        return None
    first = args.split()[0].strip('"').strip("'").strip("`")
    # If a quote/backtick/`=`/space survived stripping, this is a shape we do not
    # understand (unbalanced quoting, an unhandled named param): return None so
    # has_ref_shortcode fires and translate_page fails closed rather than ship a
    # silently-broken link.
    if not first or any(c in first for c in '"\'`= '):
        return None
    return first


def has_ref_shortcode(text: str) -> bool:
    """True if any ref/relref shortcode remains — a build-breaking hazard."""
    return bool(_ANY_REF_SHORTCODE.search(text))


# ---- deterministic integrity & typography checks ----------------------------
#
# The masking in protect() guarantees that code, shortcodes and URLs survive
# byte-for-byte. What it CANNOT guarantee is the material that legitimately sits
# in ordinary prose: a bare `--flag`, a `kind: Tenant` written without backticks,
# a version number, a brand from do_not_translate. Those are defended only by
# prompt rules, which is to say softly. These checks turn "the model was told
# not to" into "we looked". They return FINDINGS (fed to the same revise loop as
# the reviewers) rather than raising: a false positive should cost one revise
# round, never a hard-failed page.

_CODEISH_RE = re.compile(
    r"```.*?```"                 # fenced code
    r"|`[^`\n]+`"                # inline code
    r"|§§[A-Z]+_\d+§§"           # pipeline placeholders
    r"|\{\{[<%].*?[%>]\}\}"      # Hugo shortcodes (params are not prose)
    r"|<!--.*?-->"               # HTML comments
    r"|<[^>\n]+>"                # HTML tags with their attributes
    r"|\]\([^)\s]*\)"            # markdown link/image destinations
    r"|^\[[^\]]+\]:[ \t]*\S+",   # reference-link definitions
    re.DOTALL | re.MULTILINE)


def _prose_only(text: str) -> str:
    """Drop everything that is markup or code, so the checks see prose alone.

    Without this the typography rules fire on things that are *correctly* written
    with ASCII punctuation — an HTML attribute (`class="hero"`), a shortcode
    param, a file path — and a check that cries wolf is a check reviewers learn
    to ignore.
    """
    return _CODEISH_RE.sub(" ", text)


# Version-ish tokens: v1.5, 1.2.3, v1.2.5. Localizing the separator (1,2,3) or
# bumping a digit changes documented behaviour, so counts must match the source.
_VERSION_RE = re.compile(r"\bv?\d+\.\d+(?:\.\d+)?\b")
# Bare long CLI flags in prose.
_FLAG_RE = re.compile(r"(?<![\w-])--[a-z][a-z0-9-]{2,}\b")


def integrity_findings(src_body: str, tr_body: str, dnt_terms: list[str] | None = None,
                       who: str = "integrity-check") -> list[dict]:
    """Compare source and translation for material that must survive verbatim.

    Checks, all on prose only (masked spans are already guaranteed):
      * version tokens      — same multiset
      * bare CLI flags      — same multiset
      * do_not_translate    — a term present in the source must not vanish
    """
    out: list[dict] = []
    src, tr = _prose_only(src_body), _prose_only(tr_body)

    def _counts(rx, s):
        d: dict[str, int] = {}
        for m in rx.finditer(s):
            d[m.group(0)] = d.get(m.group(0), 0) + 1
        return d

    for label, rx in (("version", _VERSION_RE), ("CLI flag", _FLAG_RE)):
        a, b = _counts(rx, src), _counts(rx, tr)
        for tok, n in a.items():
            got = b.get(tok, 0)
            if got < n:
                out.append({"severity": "major", "from": who,
                            "issue": f"{label} '{tok}' appears {n}× in the English source but "
                                     f"{got}× in the translation — it must be carried over "
                                     f"unchanged"})
        for tok in b:
            if tok not in a:
                out.append({"severity": "minor", "from": who,
                            "issue": f"{label} '{tok}' appears in the translation but not in "
                                     f"the source — do not invent versions or flags"})

    for term in (dnt_terms or []):
        n = src.count(term)
        if n and tr.count(term) < n:
            out.append({"severity": "major", "from": who,
                        "issue": f"do-not-translate term '{term}' appears {n}× in the source "
                                 f"but only {tr.count(term)}× in the translation — it must be "
                                 f"kept verbatim, not translated or transliterated"})
    return out


# Per-language typography. The style guides state these rules; nothing checked
# them, so a page could read fine and still be typeset like English. Findings are
# advisory-but-real: they are the cheapest quality signal we have per language.
_TYPO_RULES: dict[str, list[tuple[str, str]]] = {
    "ru": [
        (r'"[^"\n]{1,80}"', 'ASCII double quotes in Russian prose — use «ёлочки»'),
        (r'[“”][^\n]{0,80}[“”]', 'English curly quotes in Russian prose — use «ёлочки»'),
        # A hyphen doing a dash's job — but NOT a list marker ("\n- item"), which
        # is why a non-space character is required immediately before it.
        (r'(?<=[^\s])[ ]-[ ](?=\S)', 'hyphen used as a dash — use the em dash «—»'),
    ],
    "de": [
        (r'"[^"\n]{1,80}"', 'ASCII double quotes in German prose — use „…“'),
        (r'[“][^\n]{0,80}[”]', 'English curly quotes in German prose — use „…“'),
    ],
    "es": [
        (r'(?<![¿])\b[A-ZÁÉÍÓÚÑ][^.!?\n]{5,120}\?', 'question without an opening ¿'),
        (r'(?<![¡])\b[A-ZÁÉÍÓÚÑ][^.!?\n]{5,120}!', 'exclamation without an opening ¡'),
    ],
    "pt-br": [
        (r'\b(ficheiro|utilizador|ecrã|rato|autocarro|telemóvel|casa de banho)\b',
         'European Portuguese vocabulary leaked into pt-BR'),
        (r'\bestá a [a-zçãéêó]+r\b', 'European Portuguese "está a fazer" — pt-BR uses the gerund'),
    ],
    "zh-cn": [
        (r'[一-鿿]\s*[,;:!?]', 'half-width punctuation after a Chinese character — use ，；：！？'),
        (r'[,;:!?]\s*[一-鿿]', 'half-width punctuation before a Chinese character — use ，；：！？'),
        (r'[一-鿿]\.(?=\s|$)', 'half-width period ending a Chinese sentence — use 。'),
        (r'[Ａ-Ｚａ-ｚ０-９]', 'full-width Latin letters or digits — use half-width'),
    ],
    "hi": [
        (r'[०-९]', 'Devanagari digits — use Western Arabic numerals in technical content'),
    ],
}


def check_typography(text: str, lang: str, who: str = "typography-check") -> list[dict]:
    """Per-language typography findings (prose only; code spans are exempt)."""
    prose = _prose_only(text)
    out: list[dict] = []
    for pattern, message in _TYPO_RULES.get(lang, []):
        hits = re.findall(pattern, prose)
        if hits:
            sample = hits[0] if isinstance(hits[0], str) else str(hits[0])
            out.append({"severity": "minor", "from": who,
                        "issue": f"{message} ({len(hits)}×, e.g. {sample.strip()[:60]!r})"})
    return out


def deref_shortcodes(text: str, page_rel: str) -> str:
    """Rewrite Hugo ref/relref shortcodes to plain absolute links.

    `ref`/`relref` are resolved at build time WITHIN the current language and
    hard-fail (REF_NOT_FOUND) when the target page has not been translated into
    that language yet — the normal state of a partially-translated site, which
    would break the entire Hugo build. Plain links do not: the render-link hook
    (`layouts/_default/_markup/render-link.html`) resolves them to the in-language
    page when it exists and otherwise falls back to the unprefixed English page.
    This mirrors the convention established in commit 5ca8e55.

    A shortcode whose target cannot be extracted is left untouched on purpose, so
    `has_ref_shortcode` can catch it and the caller can fail closed rather than
    ship a page that may break the build."""
    def _sub(m: "re.Match[str]") -> str:
        target = _ref_target(m.group(1))
        if target is None:
            return m.group(0)
        path, _, frag = target.partition("#")
        if not path:
            # Anchor-only ref (`#section`) means "the current page".
            path = "/" + page_rel
        elif not path.startswith("/"):
            # Relative target: resolve against the current page's directory.
            path = os.path.normpath(os.path.join("/" + os.path.dirname(page_rel), path))
        path = path.rstrip("/")
        if path.endswith(".md"):
            path = path[:-3]
        # A section index (`.../_index` or `.../index`) is served at the parent
        # URL, not at `.../_index/`.
        for suffix in ("/_index", "/index"):
            if path.endswith(suffix):
                path = path[: -len(suffix)]
                break
        return path + "/" + (f"#{frag}" if frag else "")
    return _REF_SHORTCODE.sub(_sub, text)


