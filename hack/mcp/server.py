#!/usr/bin/env python3
"""MCP server for publishing to cozystack.io.

Speaks MCP over stdio as line-delimited JSON-RPC 2.0. The protocol is small
enough to implement directly, which keeps this in line with the rest of hack/:
no dependency beyond PyYAML, and Pillow only for reading image dimensions.

Two tools:

    publish_post  create a blog post from markdown plus images, validate it,
                  and commit it to a branch
    validate      run the same checks without writing anything, over one post
                  or the whole blog

Run it directly to talk MCP on stdin/stdout, or with --check to run the
validator as a CI job.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import core  # noqa: E402
import validate  # noqa: E402

PROTOCOL_VERSION = "2025-06-18"
SERVER_NAME = "cozystack-website-publish"
SERVER_VERSION = "0.1.0"


def repo_root() -> Path:
    """The repository this server operates on: two levels up from hack/mcp."""
    return Path(__file__).resolve().parent.parent.parent


TOOLS = [
    {
        "name": "publish_post",
        "description": (
            "Create a blog post on cozystack.io from markdown. Writes the file "
            "(a page bundle when images are given, a plain file otherwise), "
            "copies the images beside it, appends the standard community "
            "section, validates the result and commits it to a branch. "
            "Refuses to write anything if validation fails. Images are copied "
            "unchanged: resizing and AVIF/WebP conversion are Hugo's job. The "
            "first image becomes the Open Graph card and must be PNG or JPEG "
            "near 1200x630, because social parsers do not render SVG, AVIF or "
            "WebP as previews."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Post title"},
                "description": {
                    "type": "string",
                    "description": (
                        "Meta description, also used in JSON-LD BlogPosting. "
                        "Aim for 50-200 characters."
                    ),
                },
                "author": {"type": "string", "description": "Author name"},
                "body": {
                    "type": "string",
                    "description": (
                        "Article body in markdown, without front matter and "
                        "without the community section"
                    ),
                },
                "article_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Genre terms from data/taxonomy.yaml: announcement, "
                        "case, how-to, news, release, tech-article"
                    ),
                },
                "topics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Subject terms from data/taxonomy.yaml, e.g. platform, "
                        "kubernetes, storage, security"
                    ),
                },
                "images": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Paths to images on disk. The first is the Open Graph "
                        "card. Omit for a post without illustrations."
                    ),
                },
                "doc_links": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "url": {"type": "string"},
                        },
                    },
                    "description": (
                        "Optional links for a Documentation section. Each URL "
                        "is checked against the content tree."
                    ),
                },
                "slug": {
                    "type": "string",
                    "description": "Override the slug derived from the title",
                },
                "date": {
                    "type": "string",
                    "description": "Publication date as YYYY-MM-DD, defaults to today",
                },
                "branch": {
                    "type": "string",
                    "description": "Branch name, defaults to blog/<slug>",
                },
                "commit": {
                    "type": "boolean",
                    "description": "Commit the post. Default true.",
                },
            },
            "required": [
                "title",
                "description",
                "author",
                "body",
                "article_types",
                "topics",
            ],
        },
    },
    {
        "name": "validate",
        "description": (
            "Run the publishing checks without writing anything. Given a path, "
            "checks that one post; given nothing, checks every post in the "
            "blog. Verifies front matter, that taxonomy terms come from the "
            "vocabularies and stay on their own axis, that internal links "
            "resolve to real pages, that the description is present and the "
            "Open Graph card is a raster image of roughly the right shape."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "Repository-relative path to one post. Omit to check "
                        "the whole blog."
                    ),
                }
            },
        },
    },
]


def tool_publish_post(root: Path, args: dict) -> str:
    result = core.publish(
        root=root,
        title=args["title"],
        description=args["description"],
        author=args["author"],
        body=args["body"],
        article_types=args["article_types"],
        topics=args["topics"],
        images=args.get("images"),
        slug=args.get("slug"),
        date=args.get("date"),
        doc_links=args.get("doc_links"),
        branch=args.get("branch"),
        commit=args.get("commit", True),
    )

    lines = [f"Published {result.path}"]
    if result.copied_images:
        lines.append(f"Images: {', '.join(result.copied_images)}")
    if result.branch:
        lines.append(f"Branch: {result.branch} ({result.commit})")
    if result.warnings:
        lines.append("")
        lines.append("Warnings:")
        lines.extend(f"  - {w}" for w in result.warnings)
    return "\n".join(lines)


def tool_validate(root: Path, args: dict) -> str:
    site = validate.Site(root)
    rel = args.get("path")

    if rel:
        path = (root / rel).resolve()
        if not path.exists():
            return f"{rel}: no such file"
        reports = {rel: validate.validate_post(path, site)}
    else:
        reports = validate.validate_tree(site)

    if not reports:
        return "No posts found."

    errors = {p: r for p, r in reports.items() if r.errors}
    warned = {p: r for p, r in reports.items() if r.warnings and not r.errors}

    lines = []
    for path, report in errors.items():
        lines.append(f"FAIL {path}")
        lines.extend(f"  error: {e}" for e in report.errors)
        lines.extend(f"  warn:  {w}" for w in report.warnings)
    for path, report in warned.items():
        lines.append(f"WARN {path}")
        lines.extend(f"  warn:  {w}" for w in report.warnings)

    summary = (
        f"{len(reports)} post(s): {len(errors)} with errors, "
        f"{len(warned)} with warnings only"
    )
    if lines:
        return summary + "\n\n" + "\n".join(lines)
    return summary + "\nAll checks passed."


HANDLERS = {
    "publish_post": tool_publish_post,
    "validate": tool_validate,
}


def handle(request: dict, root: Path) -> dict | None:
    """Handle one JSON-RPC request. Returns None for notifications."""
    method = request.get("method")
    request_id = request.get("id")

    if method == "initialize":
        return _result(
            request_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        )

    if method in ("notifications/initialized", "initialized"):
        return None

    if method == "ping":
        return _result(request_id, {})

    if method == "tools/list":
        return _result(request_id, {"tools": TOOLS})

    if method == "tools/call":
        params = request.get("params") or {}
        name = params.get("name")
        handler = HANDLERS.get(name)
        if handler is None:
            return _error(request_id, -32602, f"unknown tool: {name}")
        try:
            text = handler(root, params.get("arguments") or {})
            return _result(
                request_id, {"content": [{"type": "text", "text": text}]}
            )
        except Exception as exc:
            # Tool failures are reported in-band so the caller can react,
            # rather than as protocol errors.
            return _result(
                request_id,
                {
                    "content": [{"type": "text", "text": f"{type(exc).__name__}: {exc}"}],
                    "isError": True,
                },
            )

    if request_id is None:
        return None
    return _error(request_id, -32601, f"unknown method: {method}")


def _result(request_id, payload: dict) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": payload}


def _error(request_id, code: int, message: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def serve(root: Path, stdin=sys.stdin, stdout=sys.stdout) -> None:
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = handle(request, root)
        if response is not None:
            stdout.write(json.dumps(response) + "\n")
            stdout.flush()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="run the validator over the whole blog and exit non-zero on errors",
    )
    parser.add_argument(
        "--path", help="with --check, validate a single post instead"
    )
    args = parser.parse_args()

    root = repo_root()

    if args.check:
        output = tool_validate(root, {"path": args.path} if args.path else {})
        print(output)
        return 1 if "FAIL" in output else 0

    serve(root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
