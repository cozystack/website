"""Validation rules for blog content.

These rules are the point of the whole tool. Writing a markdown file into the
right directory is trivial; what is not trivial is keeping every post
consistent with rules that live in a mix of documentation, templates and
habit. Each rule here encodes one such rule, and each one exists because the
mistake it prevents has been made in this repository already.

The same checks back the MCP server and the CI job, so a hand-written post and
a generated one are held to identical standards.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

import frontmatter

# Raster formats acceptable as an Open Graph card. AVIF and WebP are excluded
# on purpose: Telegram, LinkedIn and several other parsers do not render them
# in og:image, and the Telegram preview is the main reason the card exists.
OG_FORMATS = {".png", ".jpg", ".jpeg"}

# Open Graph cards are expected to be close to this. Not enforced exactly —
# a slightly different crop is fine, a square avatar is not.
OG_TARGET = (1200, 630)
OG_TOLERANCE = 0.25

# Descriptions feed both the meta description and the JSON-LD BlogPosting.
# Search engines truncate well before 200 characters, and an empty value
# produces an empty field in structured data.
DESCRIPTION_MIN = 50
DESCRIPTION_MAX = 200

BUNDLE_DIR_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)$")

# Internal links we can resolve against the content tree.
INTERNAL_LINK_RE = re.compile(
    r"\[[^\]]*\]\(\s*(?:https?://cozystack\.io)?(/[^)\s]*)"
)

# Hugo strips the version segment from docs URLs at build time only for the
# configured versions; a link naming a version other than the current one goes
# stale at the next release.
DOCS_VERSION_RE = re.compile(r"^/docs/(v[\w.]+|next)/")


@dataclass
class Report:
    """Outcome of a validation run."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def merge(self, other: "Report") -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)


class Site:
    """The repository under validation.

    Holds the things every rule needs to consult: the taxonomy vocabularies,
    the current docs version and the set of pages that exist.

    Link resolution has two modes. When a build output is present in public/ it
    is used as the source of truth, which is exact — those are the paths the
    site actually serves. Without it, resolution falls back to inferring URLs
    from the content tree, which is only approximate: Hugo derives URLs through
    permalinks, per-page aliases and version directories, and reproducing all of
    that faithfully is not worth it. In the approximate mode an unresolved link
    is reported as a warning rather than an error, so the checker never blocks
    on its own guesswork.
    """

    def __init__(self, root: Path):
        self.root = root
        self._pages: set[str] | None = None
        self._built: set[str] | None = None
        taxonomy = self._load_taxonomy()
        self.article_types: set[str] = set(taxonomy.get("article_types", []))
        self.topics: set[str] = set(taxonomy.get("topics", []))
        self.latest_version: str = self._load_latest_version()

    def _load_taxonomy(self) -> dict:
        path = self.root / "data" / "taxonomy.yaml"
        if not path.exists():
            return {}
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    def _load_latest_version(self) -> str:
        path = self.root / "hugo.yaml"
        if not path.exists():
            return ""
        # A targeted read rather than a full YAML parse: hugo.yaml is large and
        # only this one key matters here.
        for line in path.read_text(encoding="utf-8").splitlines():
            match = re.match(r"\s*latest_version_id:\s*\"?([\w.]+)\"?", line)
            if match:
                return match.group(1)
        return ""

    @property
    def pages(self) -> set[str]:
        """Everything a link may legitimately point at, without leading slash.

        Covers three kinds of target, because a link in a post can address any
        of them:

        - pages from the content tree, by file path;
        - the same blog posts by their permalink, which is dated rather than
          matching the directory name (``permalinks.blog`` in hugo.yaml);
        - files under static/, which are copied to the site root verbatim.
        """
        if self._pages is None:
            self._pages = self._collect_pages() | self._collect_static()
        return self._pages

    def _collect_pages(self) -> set[str]:
        found: set[str] = set()
        content = self.root / "content"
        if not content.exists():
            return found

        for path in content.rglob("*.md"):
            rel = path.relative_to(content)
            parts = list(rel.parts)
            if not parts:
                continue
            # content/<lang>/... — the language segment is not part of the URL
            # for the default language, and localized trees mirror the same
            # structure, so it is dropped for resolution purposes.
            parts = parts[1:]
            if not parts:
                continue
            name = parts[-1]
            if name in ("_index.md", "index.md"):
                parts = parts[:-1]
            else:
                parts[-1] = name[: -len(".md")]
            if not parts:
                continue
            found.add("/".join(parts))
            found.update(self._blog_permalinks(parts))
            found.update(self._aliases(path))
        return found

    @staticmethod
    def _aliases(path: Path) -> set[str]:
        """Alias URLs declared in a page's front matter.

        Sections have moved between docs versions — storage used to live under
        operations/ — and the old URLs keep working through aliases. Ignoring
        them makes live links look broken.
        """
        try:
            head = path.read_text(encoding="utf-8", errors="replace")[:4096]
        except OSError:
            return set()
        if "aliases:" not in head:
            return set()

        found: set[str] = set()
        in_block = False
        for line in head.splitlines():
            if re.match(r"^aliases:\s*$", line):
                in_block = True
                continue
            if in_block:
                item = re.match(r"^\s+-\s+(.+?)\s*$", line)
                if item:
                    found.add(item.group(1).strip().strip("\"'").strip("/"))
                    continue
                break
            inline = re.match(r"^aliases:\s*\[(.+)\]\s*$", line)
            if inline:
                for raw in inline.group(1).split(","):
                    found.add(raw.strip().strip("\"'").strip("/"))
        return found

    @staticmethod
    def _blog_permalinks(parts: list[str]) -> set[str]:
        """Map a blog path to the permalinks it is reachable at.

        permalinks.blog in hugo.yaml is /:section/:year/:month/:slug/ — there is
        no day segment, so content/en/blog/2024-04-05-some-slug/ is served from
        /blog/2024/04/some-slug/. Verified against the live site: the shape with
        a day in it returns 404, so it is not accepted here.
        """
        if len(parts) != 2 or parts[0] != "blog":
            return set()
        match = re.match(r"^(\d{4})-(\d{2})-(\d{2})-(.+)$", parts[1])
        if not match:
            return set()
        year, month, _day, slug = match.groups()
        return {f"blog/{year}/{month}/{slug}"}

    def _collect_static(self) -> set[str]:
        found: set[str] = set()
        static = self.root / "static"
        if not static.exists():
            return found
        for path in static.rglob("*"):
            if path.is_file():
                found.add(str(path.relative_to(static)))
        return found

    @property
    def built(self) -> set[str] | None:
        """Paths served by a build in public/, or None when there is no build."""
        if self._built is None:
            public = self.root / "public"
            if not (public / "index.html").exists():
                return None
            served: set[str] = set()
            for path in public.rglob("*"):
                if not path.is_file():
                    continue
                rel = path.relative_to(public)
                served.add(str(rel))
                if rel.name == "index.html":
                    served.add(str(rel.parent).strip("."))
            self._built = served
        return self._built

    @property
    def exact_links(self) -> bool:
        """Whether link resolution is exact, i.e. backed by a build."""
        return self.built is not None

    def resolves(self, url: str) -> bool:
        """Whether a site-relative URL addresses something that exists.

        Beyond exact matches this accepts version-agnostic docs links such as
        /docs/components/. Those serve the current version and return 200 on
        the live site, so treating them as broken would be wrong — even though
        no file sits at that literal path.
        """
        candidate = url.strip("/")
        if not candidate:
            return True

        built = self.built
        if built is not None:
            return candidate in built or f"{candidate}/index.html" in built

        if candidate in self.pages:
            return True

        if candidate.startswith("docs/") and not DOCS_VERSION_RE.match(url):
            tail = candidate[len("docs/") :]
            if self.latest_version:
                if f"docs/{self.latest_version}/{tail}" in self.pages:
                    return True
            # Fall back to any version providing the page: the unversioned URL
            # is served from whichever version is current, and that moves.
            suffix = f"/{tail}"
            return any(
                page.startswith("docs/") and page.endswith(suffix)
                for page in self.pages
            )

        return False


def validate_post(path: Path, site: Site) -> Report:
    """Validate a single blog post, given the path to its markdown file."""
    report = Report()

    if path.suffix != ".md":
        report.error(
            f"{path.name}: content must be markdown. Hugo denies text/html "
            "content by default since it fixed the XSS in html content files, "
            "and this repository carries no .html content any more"
        )
        return report

    try:
        data, body = frontmatter.load(path.read_text(encoding="utf-8"))
    except frontmatter.FrontMatterError as exc:
        report.error(f"{path.name}: {exc}")
        return report

    report.merge(_check_structure(path, data))
    report.merge(_check_taxonomy(path, data, site))
    report.merge(_check_description(path, data))
    report.merge(_check_og_image(path, data))
    report.merge(_check_links(path, body, site))
    return report


def _check_structure(path: Path, data: dict) -> Report:
    report = Report()
    name = path.name

    for key in ("title", "date", "author"):
        if not data.get(key):
            report.error(f"{name}: '{key}' is required")

    slug = data.get("slug")
    is_bundle = path.name == "index.md"

    if is_bundle:
        match = BUNDLE_DIR_RE.match(path.parent.name)
        if not match:
            report.error(
                f"{path.parent.name}: bundle directory must be named "
                "YYYY-MM-DD-<slug>"
            )
        else:
            dir_date, dir_slug = match.groups()
            if slug and slug != dir_slug:
                report.error(
                    f"{path.parent.name}: 'slug' is '{slug}' but the directory "
                    f"says '{dir_slug}'"
                )
            fm_date = data.get("date")
            if isinstance(fm_date, dt.date):
                fm_date = fm_date.isoformat()
            if fm_date and str(fm_date)[:10] != dir_date:
                report.error(
                    f"{path.parent.name}: 'date' is {fm_date} but the "
                    f"directory says {dir_date}"
                )
        # A bundle exists to hold assets; one without any is a plain file
        # wearing a costume.
        assets = [
            p
            for p in path.parent.iterdir()
            if p.is_file() and p.name != "index.md"
        ]
        if not assets:
            report.warn(
                f"{path.parent.name}: page bundle holds no assets — a plain "
                "markdown file would do"
            )
    else:
        # Only locally-hosted images require a bundle. Older posts point at a
        # remote CDN, and there is nothing to sit beside the markdown then.
        local = [
            str(i)
            for i in (data.get("images") or [])
            if not str(i).startswith(("http://", "https://"))
        ]
        if local:
            report.error(
                f"{name}: post declares local images but is a plain file; posts "
                "with images belong in a page bundle so the assets sit beside "
                "them"
            )

    return report


def _check_taxonomy(path: Path, data: dict, site: Site) -> Report:
    report = Report()
    name = path.name

    if not site.article_types and not site.topics:
        report.warn(
            "data/taxonomy.yaml not found — taxonomy terms cannot be checked"
        )
        return report

    types = data.get("article_types") or []
    topics = data.get("topics") or []

    if not types:
        report.error(f"{name}: 'article_types' is required")
    if not topics:
        report.error(f"{name}: 'topics' is required")

    for term in types:
        if term in site.topics:
            report.error(
                f"{name}: '{term}' is a subject, not a genre — it belongs in "
                "'topics'"
            )
        elif term not in site.article_types:
            report.error(
                f"{name}: '{term}' is not in the article_types vocabulary. "
                f"Known: {', '.join(sorted(site.article_types))}"
            )

    for term in topics:
        if term in site.article_types:
            report.error(
                f"{name}: '{term}' is a genre, not a subject — it belongs in "
                "'article_types'"
            )
        elif term not in site.topics:
            report.error(
                f"{name}: '{term}' is not in the topics vocabulary. Add it to "
                "data/taxonomy.yaml if the subject genuinely recurs"
            )

    return report


def _check_description(path: Path, data: dict) -> Report:
    report = Report()
    name = path.name
    description = (data.get("description") or "").strip()

    if not description:
        report.error(
            f"{name}: 'description' is required — it feeds both the meta "
            "description and the JSON-LD BlogPosting"
        )
        return report

    if len(description) < DESCRIPTION_MIN:
        report.warn(
            f"{name}: description is {len(description)} characters; under "
            f"{DESCRIPTION_MIN} rarely earns a useful snippet"
        )
    elif len(description) > DESCRIPTION_MAX:
        report.warn(
            f"{name}: description is {len(description)} characters; search "
            f"results truncate well before {DESCRIPTION_MAX}"
        )

    return report


def _check_og_image(path: Path, data: dict) -> Report:
    report = Report()
    name = path.name
    images = data.get("images") or []

    if not images:
        # Legitimate: the site default card is used instead. Worth saying out
        # loud, because a post with a good illustration and no card gets a
        # generic preview in Telegram and Slack.
        report.warn(
            f"{name}: no 'images' — social previews fall back to the site "
            "default card"
        )
        return report

    card = str(images[0])
    if card.startswith("http://") or card.startswith("https://"):
        report.warn(f"{name}: Open Graph card is remote, not checked: {card}")
        return report

    card_path = path.parent / card
    if not card_path.exists():
        report.error(f"{name}: Open Graph card '{card}' does not exist")
        return report

    suffix = card_path.suffix.lower()
    if suffix == ".svg":
        report.error(
            f"{name}: '{card}' is SVG. Social parsers do not render SVG in "
            "og:image — leave 'images' unset to fall back to the site default, "
            "or add a raster card"
        )
        return report
    if suffix not in OG_FORMATS:
        report.error(
            f"{name}: '{card}' is {suffix}; an Open Graph card must be one of "
            f"{', '.join(sorted(OG_FORMATS))}. AVIF and WebP are fine in the "
            "article body but are not rendered as previews"
        )
        return report

    report.merge(_check_og_dimensions(name, card, card_path))
    return report


def _check_og_dimensions(name: str, card: str, card_path: Path) -> Report:
    report = Report()
    try:
        from PIL import Image
    except ImportError:
        report.warn(f"{name}: Pillow unavailable, '{card}' dimensions unchecked")
        return report

    try:
        with Image.open(card_path) as img:
            width, height = img.size
    except Exception as exc:  # pragma: no cover - depends on broken files
        report.error(f"{name}: cannot read '{card}': {exc}")
        return report

    target_ratio = OG_TARGET[0] / OG_TARGET[1]
    ratio = width / height if height else 0
    if abs(ratio - target_ratio) / target_ratio > OG_TOLERANCE:
        report.warn(
            f"{name}: '{card}' is {width}×{height}; Open Graph cards are "
            f"expected near {OG_TARGET[0]}×{OG_TARGET[1]} and other shapes get "
            "cropped unpredictably"
        )
    return report


def _check_links(path: Path, body: str, site: Site) -> Report:
    report = Report()
    name = path.name

    for target in INTERNAL_LINK_RE.findall(body):
        url = target.split("#")[0].split("?")[0]
        if not url or url == "/":
            continue

        version_match = DOCS_VERSION_RE.match(url)
        if version_match:
            version = version_match.group(1)
            if version == "next":
                report.error(
                    f"{name}: link to '{url}' points at the unreleased docs "
                    "trunk, which is excluded from production builds"
                )
                continue
            if site.latest_version and version != site.latest_version:
                report.warn(
                    f"{name}: link to '{url}' pins docs version {version} "
                    f"while the current one is {site.latest_version}; it will "
                    "age out"
                )

        if not site.resolves(url):
            if site.exact_links:
                report.error(f"{name}: link to '{url}' is not served by the build")
            else:
                report.warn(
                    f"{name}: link to '{url}' could not be resolved from the "
                    "content tree. Build the site and re-run for an exact check"
                )

    return report


def validate_tree(site: Site, section: str = "blog") -> dict[str, Report]:
    """Validate every post in a section. Returns path -> report."""
    results: dict[str, Report] = {}
    base = site.root / "content" / "en" / section
    if not base.exists():
        return results

    for path in sorted(base.rglob("*.md")):
        if path.name.startswith("_"):
            continue
        rel = str(path.relative_to(site.root))
        results[rel] = validate_post(path, site)
    return results
