#!/usr/bin/env python3
"""Tests for the publishing tools.

Run with: python3 hack/mcp/test_mcp.py

Each test builds a throwaway site in a temporary directory, so nothing here
touches the real content tree. No test framework, matching the rest of hack/.
"""

from __future__ import annotations

import json
import io
import shutil
import sys
import tempfile
import textwrap
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import core
import frontmatter
import server
import validate

TAXONOMY = """
article_types:
  - announcement
  - how-to
  - news
  - release
topics:
  - kubernetes
  - platform
  - storage
"""

COMMUNITY = """
heading: Join the community
links:
  - text: Cozystack on GitHub
    url: https://github.com/cozystack/cozystack
"""


def make_site(tmp: Path, built: bool = True) -> Path:
    """Build a minimal site: taxonomy, community links, one existing page.

    With built=True a public/ tree is created too, which puts link checking in
    its exact mode. Without it, unresolved links are warnings rather than
    errors, and that path is covered by its own test.
    """
    (tmp / "data").mkdir(parents=True)
    (tmp / "data" / "taxonomy.yaml").write_text(TAXONOMY, encoding="utf-8")
    (tmp / "data" / "community-links.yaml").write_text(COMMUNITY, encoding="utf-8")
    (tmp / "hugo.yaml").write_text('  latest_version_id: "v1.6"\n', encoding="utf-8")

    blog = tmp / "content" / "en" / "blog"
    blog.mkdir(parents=True)

    docs = tmp / "content" / "en" / "docs" / "v1.6" / "storage"
    docs.mkdir(parents=True)
    (docs / "_index.md").write_text(
        "---\ntitle: Storage\n---\n\nbody\n", encoding="utf-8"
    )

    if built:
        served = tmp / "public"
        (served).mkdir()
        (served / "index.html").write_text("<html></html>", encoding="utf-8")
        page = served / "docs" / "v1.6" / "storage"
        page.mkdir(parents=True)
        (page / "index.html").write_text("<html></html>", encoding="utf-8")
    return tmp


def write_post(root: Path, name: str, front: str, body: str = "Text.") -> Path:
    path = root / "content" / "en" / "blog" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{textwrap.dedent(front).strip()}\n---\n\n{body}\n", encoding="utf-8")
    return path


VALID_FRONT = """
title: A Post About Storage
slug: a-post
date: 2026-08-03
author: Someone
description: A description long enough to be a useful search snippet for readers.
article_types:
  - how-to
topics:
  - storage
"""


# --- frontmatter ------------------------------------------------------------


def test_frontmatter_roundtrip():
    text = "---\ntitle: Hi\ndate: 2026-01-01\n---\n\nBody here.\n"
    data, body = frontmatter.load(text)
    assert data["title"] == "Hi", data
    assert body.strip() == "Body here.", body


def test_frontmatter_missing_delimiter():
    try:
        frontmatter.load("no front matter here")
    except frontmatter.FrontMatterError:
        return
    raise AssertionError("expected FrontMatterError")


def test_frontmatter_key_order():
    out = frontmatter.dump({"topics": ["a"], "title": "T", "zzz": 1}, "body")
    lines = [l for l in out.splitlines() if l and not l.startswith("-")]
    assert lines[0].startswith("title:"), out
    assert "topics:" in out and "zzz:" in out, out


# --- validators -------------------------------------------------------------


def test_valid_post_passes():
    with tempfile.TemporaryDirectory() as tmp:
        root = make_site(Path(tmp))
        path = write_post(root, "2026-08-03-a-post.md", VALID_FRONT)
        report = validate.validate_post(path, validate.Site(root))
        assert report.ok, report.errors


def test_html_content_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        root = make_site(Path(tmp))
        path = root / "content" / "en" / "blog" / "post.html"
        path.write_text("---\ntitle: X\n---\n\nbody\n", encoding="utf-8")
        report = validate.validate_post(path, validate.Site(root))
        assert not report.ok, "html must be rejected"
        assert "markdown" in report.errors[0], report.errors


def test_unknown_taxonomy_term_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        root = make_site(Path(tmp))
        front = VALID_FRONT.replace("- storage", "- invented-topic")
        path = write_post(root, "2026-08-03-a-post.md", front)
        report = validate.validate_post(path, validate.Site(root))
        assert not report.ok, "unknown term must be rejected"
        assert any("invented-topic" in e for e in report.errors), report.errors


def test_term_on_wrong_axis_rejected():
    """A genre in topics, or a subject in article_types, must be caught."""
    with tempfile.TemporaryDirectory() as tmp:
        root = make_site(Path(tmp))
        front = VALID_FRONT.replace("- storage", "- release")
        path = write_post(root, "2026-08-03-a-post.md", front)
        report = validate.validate_post(path, validate.Site(root))
        assert not report.ok, "genre in topics must be rejected"
        assert any("genre" in e for e in report.errors), report.errors

        front2 = VALID_FRONT.replace("- how-to", "- storage")
        path2 = write_post(root, "2026-08-03-b-post.md", front2)
        report2 = validate.validate_post(path2, validate.Site(root))
        assert not report2.ok, "subject in article_types must be rejected"
        assert any("subject" in e for e in report2.errors), report2.errors


def test_image_filename_in_topics_rejected():
    """The mistake that motivated the closed vocabulary."""
    with tempfile.TemporaryDirectory() as tmp:
        root = make_site(Path(tmp))
        front = VALID_FRONT.replace("- storage", '- "cozystack-v1.3.0.png"')
        path = write_post(root, "2026-08-03-a-post.md", front)
        report = validate.validate_post(path, validate.Site(root))
        assert not report.ok, "image filename must not pass as a topic"


def test_missing_description_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        root = make_site(Path(tmp))
        front = "\n".join(
            l for l in VALID_FRONT.strip().splitlines() if not l.startswith("description")
        )
        path = write_post(root, "2026-08-03-a-post.md", front)
        report = validate.validate_post(path, validate.Site(root))
        assert not report.ok, "missing description must be rejected"


def test_slug_directory_mismatch_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        root = make_site(Path(tmp))
        bundle = root / "content" / "en" / "blog" / "2026-08-03-wrong-name"
        bundle.mkdir(parents=True)
        (bundle / "index.md").write_text(
            f"---\n{VALID_FRONT.strip()}\n---\n\nText.\n", encoding="utf-8"
        )
        (bundle / "card.png").write_bytes(b"x")
        report = validate.validate_post(bundle / "index.md", validate.Site(root))
        assert not report.ok, "slug/directory mismatch must be rejected"
        assert any("directory" in e for e in report.errors), report.errors


def test_broken_internal_link_rejected():
    """With a build present, an unserved link is an error."""
    with tempfile.TemporaryDirectory() as tmp:
        root = make_site(Path(tmp))
        body = "See [storage](https://cozystack.io/docs/v1/storage/) for details."
        path = write_post(root, "2026-08-03-a-post.md", VALID_FRONT, body)
        report = validate.validate_post(path, validate.Site(root))
        assert not report.ok, "link to a nonexistent page must be rejected"
        assert any("not served" in e for e in report.errors), report.errors


def test_broken_link_is_warning_without_build():
    """Without a build the checker must not fail on its own inference."""
    with tempfile.TemporaryDirectory() as tmp:
        root = make_site(Path(tmp), built=False)
        body = "See [storage](/docs/v1/storage/) for details."
        path = write_post(root, "2026-08-03-a-post.md", VALID_FRONT, body)
        site = validate.Site(root)
        assert not site.exact_links, "no build means approximate mode"
        report = validate.validate_post(path, site)
        assert report.ok, report.errors
        assert any("could not be resolved" in w for w in report.warnings), report.warnings


def test_good_internal_link_passes():
    with tempfile.TemporaryDirectory() as tmp:
        root = make_site(Path(tmp))
        body = "See [storage](/docs/v1.6/storage/) for details."
        path = write_post(root, "2026-08-03-a-post.md", VALID_FRONT, body)
        report = validate.validate_post(path, validate.Site(root))
        assert report.ok, report.errors


def test_link_to_next_trunk_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        root = make_site(Path(tmp))
        body = "See [storage](/docs/next/storage/)."
        path = write_post(root, "2026-08-03-a-post.md", VALID_FRONT, body)
        report = validate.validate_post(path, validate.Site(root))
        assert not report.ok, "link into the unreleased trunk must be rejected"


def test_svg_og_card_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        root = make_site(Path(tmp))
        bundle = root / "content" / "en" / "blog" / "2026-08-03-a-post"
        bundle.mkdir(parents=True)
        front = VALID_FRONT.strip() + '\nimages:\n  - "card.svg"'
        (bundle / "index.md").write_text(
            f"---\n{front}\n---\n\nText.\n", encoding="utf-8"
        )
        (bundle / "card.svg").write_text("<svg/>", encoding="utf-8")
        report = validate.validate_post(bundle / "index.md", validate.Site(root))
        assert not report.ok, "SVG must not be accepted as an OG card"
        assert any("SVG" in e for e in report.errors), report.errors


def test_missing_og_card_file_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        root = make_site(Path(tmp))
        bundle = root / "content" / "en" / "blog" / "2026-08-03-a-post"
        bundle.mkdir(parents=True)
        front = VALID_FRONT.strip() + '\nimages:\n  - "absent.png"'
        (bundle / "index.md").write_text(
            f"---\n{front}\n---\n\nText.\n", encoding="utf-8"
        )
        report = validate.validate_post(bundle / "index.md", validate.Site(root))
        assert not report.ok, "declared card that does not exist must be rejected"


def test_plain_file_with_images_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        root = make_site(Path(tmp))
        front = VALID_FRONT.strip() + '\nimages:\n  - "card.png"'
        path = write_post(root, "2026-08-03-a-post.md", front)
        report = validate.validate_post(path, validate.Site(root))
        assert not report.ok, "images on a plain file must be rejected"
        assert any("bundle" in e for e in report.errors), report.errors


# --- publishing -------------------------------------------------------------


def publish_args(**overrides):
    args = dict(
        title="A Post About Storage",
        description="A description long enough to be a useful search snippet.",
        author="Someone",
        body="Some text about storage.",
        article_types=["how-to"],
        topics=["storage"],
        date="2026-08-03",
        commit=False,
    )
    args.update(overrides)
    return args


def test_publish_plain_post():
    with tempfile.TemporaryDirectory() as tmp:
        root = make_site(Path(tmp))
        result = core.publish(root=root, **publish_args())
        path = root / result.path
        assert path.exists(), result.path
        text = path.read_text(encoding="utf-8")
        assert "Join the community" in text, "community section must be appended"
        assert "Cozystack on GitHub" in text, text


def test_publish_bundle_with_image():
    with tempfile.TemporaryDirectory() as tmp:
        root = make_site(Path(tmp))
        card = Path(tmp) / "card.png"
        _write_png(card, 1200, 630)
        result = core.publish(root=root, images=[str(card)], **publish_args())
        assert result.path.name == "index.md", result.path
        assert (root / result.path.parent / "card.png").exists()
        data, _ = frontmatter.load((root / result.path).read_text(encoding="utf-8"))
        assert data["images"] == ["card.png"], data


def test_publish_rejects_unknown_term_before_writing():
    with tempfile.TemporaryDirectory() as tmp:
        root = make_site(Path(tmp))
        try:
            core.publish(root=root, **publish_args(topics=["invented"]))
        except core.PublishError:
            blog = root / "content" / "en" / "blog"
            assert not any(blog.iterdir()), "nothing must be written on failure"
            return
        raise AssertionError("expected PublishError")


def test_publish_rolls_back_on_missing_image():
    with tempfile.TemporaryDirectory() as tmp:
        root = make_site(Path(tmp))
        try:
            core.publish(root=root, images=["/nonexistent/x.png"], **publish_args())
        except core.PublishError:
            blog = root / "content" / "en" / "blog"
            assert not any(blog.iterdir()), "bundle must be removed on failure"
            return
        raise AssertionError("expected PublishError")


def test_publish_rolls_back_on_validation_failure():
    """A body with a broken link must leave nothing behind."""
    with tempfile.TemporaryDirectory() as tmp:
        root = make_site(Path(tmp))
        try:
            core.publish(
                root=root,
                **publish_args(body="See [x](/docs/v1.6/absent/)."),
            )
        except core.PublishError:
            blog = root / "content" / "en" / "blog"
            assert not any(blog.iterdir()), "file must be removed on failure"
            return
        raise AssertionError("expected PublishError")


def test_publish_refuses_duplicate():
    with tempfile.TemporaryDirectory() as tmp:
        root = make_site(Path(tmp))
        core.publish(root=root, **publish_args())
        try:
            core.publish(root=root, **publish_args())
        except core.PublishError:
            return
        raise AssertionError("expected PublishError on duplicate")


def test_community_section_not_duplicated():
    with tempfile.TemporaryDirectory() as tmp:
        root = make_site(Path(tmp))
        body = "Text.\n\n## Join the community\n\n- already here\n"
        result = core.publish(root=root, **publish_args(body=body))
        text = (root / result.path).read_text(encoding="utf-8")
        assert text.count("Join the community") == 1, text


def test_doc_links_validated():
    with tempfile.TemporaryDirectory() as tmp:
        root = make_site(Path(tmp))
        try:
            core.publish(
                root=root,
                **publish_args(
                    doc_links=[{"text": "Absent", "url": "/docs/v1.6/absent/"}]
                ),
            )
        except core.PublishError:
            return
        raise AssertionError("expected PublishError for an unresolvable doc link")


def test_slugify():
    assert core.slugify("Hello, World!") == "hello-world"
    assert core.slugify("Cozystack 1.6: What's New") == "cozystack-1-6-what-s-new"


# --- server protocol --------------------------------------------------------


def test_initialize_and_tools_list():
    with tempfile.TemporaryDirectory() as tmp:
        root = make_site(Path(tmp))
        init = server.handle(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize"}, root
        )
        assert init["result"]["serverInfo"]["name"] == server.SERVER_NAME, init

        listing = server.handle(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, root
        )
        names = {t["name"] for t in listing["result"]["tools"]}
        assert names == {"publish_post", "validate"}, names


def test_notification_returns_nothing():
    with tempfile.TemporaryDirectory() as tmp:
        root = make_site(Path(tmp))
        out = server.handle(
            {"jsonrpc": "2.0", "method": "notifications/initialized"}, root
        )
        assert out is None, out


def test_tool_error_reported_in_band():
    with tempfile.TemporaryDirectory() as tmp:
        root = make_site(Path(tmp))
        response = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "publish_post",
                    "arguments": publish_args(topics=["invented"]),
                },
            },
            root,
        )
        assert response["result"].get("isError"), response
        assert "invented" in response["result"]["content"][0]["text"]


def test_unknown_tool():
    with tempfile.TemporaryDirectory() as tmp:
        root = make_site(Path(tmp))
        response = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": "nope", "arguments": {}},
            },
            root,
        )
        assert "error" in response, response


def test_serve_loop_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        root = make_site(Path(tmp))
        stdin = io.StringIO(
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}) + "\n"
        )
        stdout = io.StringIO()
        server.serve(root, stdin=stdin, stdout=stdout)
        response = json.loads(stdout.getvalue().strip())
        assert response["id"] == 1, response
        assert "tools" in response["result"], response


def test_validate_tool_over_tree():
    with tempfile.TemporaryDirectory() as tmp:
        root = make_site(Path(tmp))
        write_post(root, "2026-08-03-good.md", VALID_FRONT)
        write_post(
            root,
            "2026-08-03-bad.md",
            VALID_FRONT.replace("- storage", "- invented"),
        )
        out = server.tool_validate(root, {})
        assert "FAIL" in out, out
        assert "2 post(s)" in out, out


# --- helpers ----------------------------------------------------------------


def _write_png(path: Path, width: int, height: int) -> None:
    from PIL import Image

    Image.new("RGB", (width, height), "white").save(path)


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = []
    for test in tests:
        try:
            test()
            print(f"  ok   {test.__name__}")
        except Exception:
            failed.append(test.__name__)
            print(f"  FAIL {test.__name__}")
            traceback.print_exc()

    print(f"\n{len(tests) - len(failed)}/{len(tests)} passed")
    if failed:
        print("failed: " + ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
