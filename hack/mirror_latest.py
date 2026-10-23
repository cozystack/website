#!/usr/bin/env python3
"""Serve current docs at stable paths after the Hugo build."""

from html.parser import HTMLParser
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import sys
from urllib.parse import urlsplit


class PageURL(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.url = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        # Open Graph retains the original page URL, including on previews where
        # no canonical is emitted. This also supplies the baseURL subpath.
        if tag == "meta" and attrs.get("property") == "og:url":
            self.url = attrs.get("content")


def rewrite(text, source_url, alias):
    source_path = urlsplit(source_url).path
    base_url = source_url.rsplit("/docs/", 1)[0]
    destination_url = f"{base_url}/docs/{alias}"
    destination_path = urlsplit(destination_url).path
    canonical_url = f"{base_url}/docs/"
    # Keep the original formatting (Hugo's minified attributes may be unquoted).
    text = re.sub(r'''(["'(=])''' + re.escape(source_path),
                  lambda m: m[1] + destination_path, text)
    text = re.sub(r'''(<a\b[^>]*\bhref=["']?)''' + re.escape(source_url),
                  lambda m: m[1] + destination_url, text)
    text = re.sub(r'''(http-equiv="?refresh"? content="?[0-9]+;\s*url=)''' + re.escape(source_url),
                  lambda m: m[1] + destination_url, text)
    # Hugo alias stubs do not use the regular head template.
    text = re.sub(r'''(<link\b[^>]*\brel="?canonical"?\s+href=["']?)''' + re.escape(source_url),
                  lambda m: m[1] + canonical_url, text)
    return text


def reserved(name):
    return re.fullmatch(r"v[0-9]+(?:\.[0-9]+)?|next|versions|latest", name)


def root_target(public, name):
    """Keep cleanup and root copies outside version trees, including symlinks."""
    path = Path(name)
    parts = path.parts
    offset = 1 if parts and parts[0] == "docs" else 2
    if (path.is_absolute() or ".." in parts or len(parts) <= offset
            or parts[offset - 1] != "docs" or reserved(parts[offset])):
        raise ValueError(f"invalid root mirror path: {name}")
    target = public / path
    if target.resolve() != target or target.is_dir():
        raise ValueError(f"refusing a symlink or directory target: {target}")
    return target


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
        root_target(public, name)
        if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValueError(f"invalid root mirror digest: {name}")

    # Validate every source before replacing any previous mirror.
    plans = []
    landings = []
    for landing in [public / "docs/index.html", *sorted(public.glob("*/docs/index.html"))]:
        versions = landing.parent / "versions/index.html"
        if versions.resolve() != versions or versions.is_dir():
            raise ValueError(f"invalid versions landing path: {versions}")
        landing_url = PageURL(landing.read_text()).url
        if landing_url and urlsplit(landing_url).path.endswith("/docs/"):
            landings.append((versions, landing.read_bytes()))
        elif not versions.is_file():
            raise ValueError(f"missing version-selection landing: {landing}")
    for source in sources:
        if source.is_symlink() or not (source / "index.html").is_file():
            raise ValueError(f"missing docs source: {source} (run Hugo first)")
        source_url = PageURL((source / "index.html").read_text()).url
        if not source_url or not urlsplit(source_url).path.endswith(f"/docs/{latest}/"):
            raise ValueError(f"invalid og:url in {source / 'index.html'}")
        for file in source.rglob("*"):
            if file.is_symlink() or reserved(file.relative_to(source).parts[0]):
                raise ValueError(f"reserved or symlink source path: {file}")
            if file.is_file():
                target = source.parent / file.relative_to(source)
                root_target(public, target.relative_to(public))
                plans.append((file, source_url, target))
        destination = source.parent / major
        if major != latest and (destination.resolve() != destination or destination.is_file()):
            raise ValueError(f"invalid major mirror destination: {destination}")

    for versions, content in landings:
        versions.parent.mkdir(parents=True, exist_ok=True)
        versions.write_bytes(content)
    current = {}
    for file, source_url, target in plans:
        content = file.read_bytes()
        if file.suffix in (".html", ".xml"):
            content = rewrite(content.decode(), source_url, "").encode()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        current[str(target.relative_to(public))] = sha256(content).hexdigest()
    for name, digest in previous.items():
        target = public / name
        # Hugo may have replaced a removed page with a historical alias. Keep it.
        if name not in current and target.is_file() and sha256(target.read_bytes()).hexdigest() == digest:
            target.unlink()
    manifest.write_text(json.dumps(current, indent=2) + "\n")
    if major != latest:
        for source in sources:
            destination = source.parent / major
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(source, destination)
            source_url = PageURL((source / "index.html").read_text()).url
            for file in destination.rglob("*"):
                if file.suffix in (".html", ".xml"):
                    file.write_text(rewrite(file.read_text(), source_url, major + "/"))
    print(f"mirrored {latest} to /docs/ and /docs/{major}/; version selection at /docs/versions/")


if __name__ == "__main__":
    try:
        mirror(Path(sys.argv[1] if len(sys.argv) > 1 else "public").resolve())
    except (OSError, ValueError) as exc:
        sys.exit(f"error: {exc}")
