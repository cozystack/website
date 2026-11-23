#!/usr/bin/env python3
"""Serve current docs at stable paths after the Hugo build."""

from html.parser import HTMLParser
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit


class PageURL(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.url = None
        self.version_landing = False
        self.redirect = False
        self.legacy_url = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        # Numbered source pages retain og:url even when previews omit canonical.
        if tag == "meta" and attrs.get("property") == "og:url":
            self.url = attrs.get("content")
        if "data-docs-version-landing" in attrs:
            self.version_landing = True
        if tag == "meta" and attrs.get("http-equiv", "").lower() == "refresh":
            self.redirect = True
        if "data-docs-legacy-url" in attrs:
            self.legacy_url = attrs["data-docs-legacy-url"]


def rewrite_og_url(text, source_url, target_url):
    return re.sub(r'''(<meta\b(?=[^>]*\bproperty=["']?og:url(?:["'\s>]))[^>]*\bcontent=["']?)''' + re.escape(source_url),
                  lambda m: m[1] + target_url, text)


def rewrite(text, source_url, alias):
    source_path = urlsplit(source_url).path
    base_url = source_url.rsplit("/docs/", 1)[0]
    destination_url = f"{base_url}/docs/{alias}"
    destination_path = urlsplit(destination_url).path
    canonical_url = f"{base_url}/docs/"
    # Keep the original formatting (Hugo's minified attributes may be unquoted).
    text = re.sub(r'''(["'(=])''' + re.escape(source_path),
                  lambda m: m[1] + destination_path, text)
    # Hugo alias stubs do not use the regular head template.
    text = re.sub(r'''(<link\b(?=[^>]*\brel=["']?canonical(?:["'\s>]))[^>]*\bhref=["']?)''' + re.escape(source_url),
                  lambda m: m[1] + canonical_url, text)
    text = rewrite_og_url(text, source_url, canonical_url)
    text = re.sub(r'''(\b(?:href|src)=["']?)''' + re.escape(source_url),
                  lambda m: m[1] + destination_url, text)
    text = re.sub(r'''(http-equiv="?refresh"? content="?[0-9]+;\s*url=)''' + re.escape(source_url),
                  lambda m: m[1] + destination_url, text)
    return text


def reserved(name):
    return re.fullmatch(r"v[0-9]+(?:\.[0-9]+)?|next|versions|latest", name)


def root_target(public, name, *, allow_major=False):
    """Keep managed copies outside numbered archives, including symlinks."""
    path = Path(name)
    parts = path.parts
    offset = 1 if parts and parts[0] == "docs" else 2
    if (path.is_absolute() or ".." in parts or len(parts) <= offset
            or parts[offset - 1] != "docs"
            or (reserved(parts[offset]) and not (allow_major and re.fullmatch(r"v[1-9][0-9]*", parts[offset])))):
        raise ValueError(f"invalid root mirror path: {name}")
    target = public / path
    if target.resolve() != target or target.is_dir():
        raise ValueError(f"refusing a symlink or directory target: {target}")
    return target


def legacy_page(public, url):
    if (not isinstance(url, str) or not re.fullmatch(r"/(?:[A-Za-z0-9_.-]+/)+", url)
            or any(part in (".", "..") for part in url.split("/"))):
        raise ValueError(f"invalid legacy URL: {url}")
    path = public / url.lstrip("/") / "index.html"
    if (path.resolve() != path or path.is_dir()
            or any(p.is_file() for p in path.parents if p == public or public in p.parents)):
        raise ValueError(f"invalid legacy page path: {path}")
    return path


def legacy_copies(public, latest, copies, previous):
    mappings = json.loads(Path("data/docs-legacy-urls.json").read_text())
    if not isinstance(mappings, dict):
        raise ValueError("data/docs-legacy-urls.json must be a URL-to-URL object")
    result = {}
    major = latest.split(".")[0]
    for old, new in mappings.items():
        legacy_page(public, old)
        source = legacy_page(public, new)
        parts = old.strip("/").split("/")
        if old != "/roadmap/" and (len(parts) < 2 or parts[0] != "docs" or reserved(parts[1])):
            raise ValueError(f"legacy destination must be an unversioned docs path: {old}")
        if old == new or not new.startswith("/docs/"):
            raise ValueError(f"invalid legacy target: {old} -> {new}")
        if source in copies:
            content = copies[source]
        elif re.match(r"^/docs/v[0-9]+(?:\.[0-9]+)?/", new) and source.is_file():
            content = source.read_bytes()
        else:
            raise ValueError(f"legacy target is not built: {old} -> {new}")
        if PageURL(content.decode()).redirect:
            raise ValueError(f"legacy target must be a content page: {new}")
        urls = [old]
        if source in copies and old.startswith("/docs/") and major != latest:
            urls.append(f"/docs/{major}/" + old[len("/docs/"):])
        for url in urls:
            target = legacy_page(public, url)
            if target in copies and not PageURL(copies[target].decode()).redirect:
                raise ValueError(f"legacy URL collides with current content: {url}")
            if target.is_file():
                existing = target.read_bytes()
                page = PageURL(existing.decode())
                owned = previous.get(str(target.relative_to(public))) == sha256(existing).hexdigest()
                if not (page.redirect or page.legacy_url == url or owned):
                    raise ValueError(f"legacy URL collides with existing content: {url}")
            text, count = re.subn(r"<html\b", f'<html data-docs-legacy-url="{url}"', content.decode(), count=1)
            if not count:
                raise ValueError(f"legacy target has no HTML document: {new}")
            result[target] = text.encode()
    return result


def mirror(public):
    config = Path("hugo.yaml").read_text()
    match = re.search(r'^  latest_version_id:\s*"(v[0-9]+(?:\.[0-9]+)?)"\s*$', config, re.M)
    if not match:
        raise ValueError("params.latest_version_id must name a released version in hugo.yaml")
    latest = match[1]
    sources = [public / "docs" / latest]
    sources.extend(sorted(public.glob(f"*/docs/{latest}")))
    major = latest.split(".")[0]
    manifest = public / ".docs-mirror.json"
    if manifest.resolve() != manifest:
        raise ValueError(f"refusing a symlink manifest: {manifest}")
    previous = json.loads(manifest.read_text()) if manifest.exists() else {}
    if not isinstance(previous, dict):
        raise ValueError(f"invalid root mirror manifest: {manifest}")
    for name, digest in previous.items():
        if name == "roadmap/index.html":
            legacy_page(public, "/roadmap/")
        else:
            root_target(public, name, allow_major=True)
        if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValueError(f"invalid root mirror digest: {name}")

    # Validate every source before replacing any previous mirror.
    plans = []
    landings = []
    for landing in [public / "docs/index.html", *sorted(public.glob("*/docs/index.html"))]:
        versions = landing.parent / "versions/index.html"
        if versions.resolve() != versions or versions.is_dir():
            raise ValueError(f"invalid versions landing path: {versions}")
        html = landing.read_text()
        page_url = PageURL(html)
        if page_url.version_landing:
            if not page_url.url:
                raise ValueError(f"missing og:url in {landing}")
            landings.append((versions, rewrite_og_url(html, page_url.url, page_url.url + "versions/").encode()))
        elif not versions.is_file():
            raise ValueError(f"missing version-selection landing: {landing}")
    for source in sources:
        if source.is_symlink() or not (source / "index.html").is_file():
            raise ValueError(f"missing docs source: {source} (run Hugo first)")
        source_url = PageURL((source / "index.html").read_text()).url
        if not source_url or not urlsplit(source_url).path.endswith(f"/docs/{latest}/"):
            raise ValueError(f"invalid og:url in {source / 'index.html'}")
        destination = source.parent / major
        if major != latest and (destination.resolve() != destination or destination.is_file()):
            raise ValueError(f"invalid major mirror destination: {destination}")
        for file in source.rglob("*"):
            if file.is_symlink() or reserved(file.relative_to(source).parts[0]):
                raise ValueError(f"reserved or symlink source path: {file}")
            if file.is_file():
                aliases = [""] if major == latest else ["", major + "/"]
                for alias in aliases:
                    target = source.parent / alias / file.relative_to(source)
                    root_target(public, target.relative_to(public), allow_major=bool(alias))
                    plans.append((file, source_url, target, alias))

    copies = {}
    for file, source_url, target, alias in plans:
        content = file.read_bytes()
        if file.suffix in (".html", ".xml"):
            content = rewrite(content.decode(), source_url, alias).encode()
        copies[target] = content
    legacy = legacy_copies(public, latest, copies, previous)
    copies.update(legacy)

    for versions, content in landings:
        versions.parent.mkdir(parents=True, exist_ok=True)
        versions.write_bytes(content)
    current = {}
    for target, content in copies.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        current[str(target.relative_to(public))] = sha256(content).hexdigest()
    for name, digest in previous.items():
        target = public / name
        # Hugo may have replaced a removed page with a historical alias. Keep it.
        if name not in current and target.is_file() and sha256(target.read_bytes()).hexdigest() == digest:
            target.unlink()
    manifest.write_text(json.dumps(current, indent=2) + "\n")
    print(f"mirrored {latest} to /docs/ and /docs/{major}/; version selection at /docs/versions/")


if __name__ == "__main__":
    try:
        mirror(Path(sys.argv[1] if len(sys.argv) > 1 else "public").resolve())
    except (OSError, ValueError) as exc:
        sys.exit(f"error: {exc}")
