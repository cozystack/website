"""The single write path.

Every write goes through publish(): assemble in memory, validate, write, and
roll back if anything fails. A tool that errors out or is interrupted leaves
the repository exactly as it was, so a failed publish never needs manual
cleanup.
"""

from __future__ import annotations

import datetime as dt
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import yaml

import frontmatter
import validate

BLOG_DIR = Path("content") / "en" / "blog"

# Community links live in one file so that changing one does not mean editing
# thirty published posts after the fact.
COMMUNITY_DATA = Path("data") / "community-links.yaml"

COMMUNITY_HEADING = "Join the community"

SLUG_RE = re.compile(r"[^a-z0-9]+")


class PublishError(Exception):
    """Raised when a publish cannot proceed. Nothing has been written."""


@dataclass
class PublishResult:
    path: Path
    slug: str
    branch: str | None = None
    commit: str | None = None
    warnings: list[str] = field(default_factory=list)
    copied_images: list[str] = field(default_factory=list)


def slugify(title: str) -> str:
    return SLUG_RE.sub("-", title.lower()).strip("-")


def community_block(root: Path) -> str:
    """Render the closing community section from data.

    Returns an empty string when the data file is absent, so that a repository
    without it still publishes rather than failing on a cosmetic section.
    """
    path = root / COMMUNITY_DATA
    if not path.exists():
        return ""

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    links = data.get("links") or []
    if not links:
        return ""

    lines = [f"## {data.get('heading', COMMUNITY_HEADING)}", ""]
    for item in links:
        text = item.get("text", "")
        url = item.get("url", "")
        note = item.get("note", "")
        entry = f"- [{text}]({url})" if url else f"- {text}"
        if note:
            entry += f" {note}"
        lines.append(entry)
    return "\n".join(lines) + "\n"


def documentation_block(links: list[dict]) -> str:
    """Render the optional documentation section."""
    if not links:
        return ""
    lines = ["## Documentation", ""]
    for item in links:
        lines.append(f"- [{item.get('text', '')}]({item.get('url', '')})")
    return "\n".join(lines) + "\n"


def assemble_body(
    root: Path, body: str, doc_links: list[dict] | None = None
) -> str:
    """Append the standard closing sections to an article body."""
    parts = [body.rstrip("\n")]

    docs = documentation_block(doc_links or [])
    if docs and "## Documentation" not in body:
        parts.append(docs.rstrip("\n"))

    community = community_block(root)
    if community and COMMUNITY_HEADING not in body:
        parts.append(community.rstrip("\n"))

    return "\n\n".join(parts) + "\n"


def publish(
    root: Path,
    title: str,
    description: str,
    author: str,
    body: str,
    article_types: list[str],
    topics: list[str],
    images: list[str] | None = None,
    slug: str | None = None,
    date: str | None = None,
    doc_links: list[dict] | None = None,
    branch: str | None = None,
    commit: bool = True,
) -> PublishResult:
    """Create a blog post. Validates before writing and rolls back on failure.

    images are paths on disk; the first one becomes the Open Graph card. They
    are copied into the bundle unchanged: resizing and format conversion are
    left to Hugo, which processes bundle resources natively and, since 0.162,
    encodes AVIF.
    """
    images = images or []
    slug = slug or slugify(title)
    date = date or dt.date.today().isoformat()

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        raise PublishError(f"date must be YYYY-MM-DD, got '{date}'")
    if not slug:
        raise PublishError("could not derive a slug; pass one explicitly")

    site = validate.Site(root)
    _reject_unknown_terms(site, article_types, topics)
    _reject_conflicting_image_names(images)

    is_bundle = bool(images)
    if is_bundle:
        target_dir = root / BLOG_DIR / f"{date}-{slug}"
        target = target_dir / "index.md"
    else:
        target_dir = None
        target = root / BLOG_DIR / f"{date}-{slug}.md"

    if target.exists():
        raise PublishError(f"{target.relative_to(root)} already exists")
    if target_dir is not None and target_dir.exists():
        raise PublishError(f"{target_dir.relative_to(root)} already exists")

    data = {
        "title": title,
        "slug": slug,
        "date": date,
        "author": author,
        "description": description,
        "article_types": list(article_types),
        "topics": list(topics),
    }
    if images:
        data["images"] = [Path(images[0]).name]

    content = frontmatter.dump(data, assemble_body(root, body, doc_links))

    created: list[Path] = []
    try:
        if target_dir is not None:
            target_dir.mkdir(parents=True)
            created.append(target_dir)
        target.write_text(content, encoding="utf-8")
        created.append(target)

        copied = []
        for src in images:
            source = Path(src).expanduser()
            if not source.exists():
                raise PublishError(f"image not found: {source}")
            dest = target.parent / source.name
            shutil.copy2(source, dest)
            created.append(dest)
            copied.append(source.name)

        report = validate.validate_post(target, validate.Site(root))
        if not report.ok:
            raise PublishError(
                "validation failed:\n" + "\n".join(f"  - {e}" for e in report.errors)
            )

        result = PublishResult(
            path=target.relative_to(root),
            slug=slug,
            warnings=report.warnings,
            copied_images=copied,
        )

        if commit:
            result.branch, result.commit = _commit(
                root, target_dir or target, branch or f"blog/{slug}", title
            )

        return result

    except Exception:
        _rollback(created)
        raise


def _reject_unknown_terms(
    site: validate.Site, article_types: list[str], topics: list[str]
) -> None:
    """Fail before touching disk when taxonomy terms are wrong."""
    if not site.article_types and not site.topics:
        return

    problems = []
    for term in article_types:
        if term in site.topics:
            problems.append(f"'{term}' is a subject; it belongs in topics")
        elif term not in site.article_types:
            problems.append(
                f"'{term}' is not a known article type "
                f"({', '.join(sorted(site.article_types))})"
            )
    for term in topics:
        if term in site.article_types:
            problems.append(f"'{term}' is a genre; it belongs in article_types")
        elif term not in site.topics:
            problems.append(
                f"'{term}' is not a known topic; add it to data/taxonomy.yaml "
                "if the subject genuinely recurs"
            )
    if problems:
        raise PublishError("\n".join(f"  - {p}" for p in problems))


def _reject_conflicting_image_names(images: list[str]) -> None:
    """Fail before touching disk when two images would land on one path.

    Images are copied into the bundle by basename, so /a/card.png and
    /b/card.png would overwrite each other, and an image named index.md
    would overwrite the post itself.
    """
    seen: set[str] = set()
    for src in images:
        name = Path(src).expanduser().name
        if name == "index.md":
            raise PublishError(f"image name conflicts with the post: {src}")
        if name in seen:
            raise PublishError(f"two images share the file name '{name}'")
        seen.add(name)


def _rollback(created: list[Path]) -> None:
    """Undo whatever the failed publish managed to create."""
    for path in reversed(created):
        try:
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
        except OSError:
            # Nothing useful to do here; the exception being handled upstream
            # is the one worth reporting.
            pass


def _git(root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise PublishError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def _commit(root: Path, path: Path, branch: str, title: str) -> tuple[str, str]:
    """Put the new post on its own branch and commit it.

    Never commits onto the default branch: blog posts arrive through pull
    requests. If any git step fails, the index and the checked-out branch are
    restored before the error propagates, so together with the file rollback
    in publish() a failed commit leaves the repository as it was.
    """
    original = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    created_branch = None
    if original in ("main", "master"):
        _git(root, "checkout", "-b", branch)
        created_branch = branch
    else:
        branch = original

    rel = str(path.relative_to(root))
    try:
        _git(root, "add", "--", rel)
        _git(root, "commit", "--signoff", "-m", f"feat(blog): {title}")
        return branch, _git(root, "rev-parse", "--short", "HEAD")
    except PublishError:
        _restore_git(root, rel, original, created_branch)
        raise


def _restore_git(
    root: Path, rel: str, original: str, created_branch: str | None
) -> None:
    """Best-effort undo of what _commit did before it failed."""
    steps = [("reset", "--quiet", "--", rel)]
    if created_branch is not None:
        steps += [("checkout", "--quiet", original), ("branch", "-D", created_branch)]
    for step in steps:
        try:
            _git(root, *step)
        except PublishError:
            # The failure being handled upstream is the one worth reporting.
            pass
