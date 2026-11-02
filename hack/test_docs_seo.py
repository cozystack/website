#!/usr/bin/env python3
"""Check the built site's docs canonical URLs, robots tags and sitemaps.

Usage: python3 hack/test_docs_seo.py PUBLIC_DIR --latest v1.6
Run after Hugo and mirror_latest.sh. Uses only the Python standard library.
"""

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET


class Head(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.canonical = []
        self.robots = []
        self.refresh = []
        self.links = []
        self.languages = {}
        self.og_urls = []
        self.formats = {}
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonical.append(attrs.get("href"))
        if tag == "meta" and attrs.get("name", "").lower() == "robots":
            self.robots.append(attrs.get("content"))
        if tag == "meta" and attrs.get("http-equiv", "").lower() == "refresh":
            self.refresh.append(attrs.get("content"))
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        if tag == "link" and attrs.get("hreflang"):
            self.languages[attrs["hreflang"]] = attrs.get("href")
        if tag == "meta" and attrs.get("property") == "og:url":
            self.og_urls.append(attrs.get("content"))
        if tag == "link" and attrs.get("rel") == "alternate" and attrs.get("type"):
            self.formats[attrs["type"]] = attrs.get("href")


class BuiltSiteTests(unittest.TestCase):
    public = None
    latest = None

    def head(self, path):
        return Head((self.public / path).read_text())

    def test_current_docs_canonical(self):
        count = 0
        for source in (self.public / "docs" / self.latest).rglob("*.html"):
            relative = source.relative_to(self.public / "docs" / self.latest)
            original = Head(source.read_text())
            if original.refresh:
                continue
            count += 1
            for version in (self.latest, "", self.latest.split(".")[0]):
                with self.subTest(page=str(relative), version=version):
                    page = self.head(Path("docs") / version / relative)
                    self.assertEqual(len(page.canonical), 1)
                    self.assertEqual(urlsplit(page.canonical[0]).path, "/docs/" + str(relative).removesuffix("index.html"))
                    self.assertEqual(page.canonical, original.canonical)
                    self.assertEqual(page.robots, ["index, follow"])
                    if version != self.latest:
                        self.assertEqual(page.og_urls, page.canonical)
                        for url in page.formats.values():
                            self.assertNotIn(f"/docs/{self.latest}/", urlsplit(url).path)
        self.assertGreater(count, 0)

    def test_archive_robots(self):
        count = 0
        for version in (self.public / "docs").iterdir():
            if not re.fullmatch(r"v[0-9]+(?:\.[0-9]+)?", version.name) or version.name in (self.latest, self.latest.split(".")[0]):
                continue
            for source in version.rglob("*.html"):
                page = Head(source.read_text())
                if page.refresh:
                    continue
                count += 1
                with self.subTest(page=str(source.relative_to(self.public))):
                    self.assertEqual(page.robots, ["noindex, follow"])
                    self.assertEqual(page.canonical, [])
        self.assertGreater(count, 0)

    def test_sitemap_matches_canonical(self):
        count = 0
        latest_count = 0
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        for sitemap in self.public.rglob("sitemap.xml"):
            root = ET.parse(sitemap).getroot()
            urls = [loc.text for loc in root.findall("s:url/s:loc", ns)]
            self.assertEqual(len(urls), len(set(urls)))
            for url in urls:
                count += 1
                latest_count += "/docs/" in url and not re.search(r"/docs/(?:v[0-9]+|versions|next)(?:[./])", url)
                path = unquote(urlsplit(url).path).lstrip("/")
                with self.subTest(url=url):
                    page = self.head(Path(path) / "index.html")
                    self.assertEqual(page.canonical, [url])
                    self.assertEqual(page.robots, ["index, follow"])
        self.assertGreater(count, 0)
        self.assertGreater(latest_count, 0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("public", type=Path)
    parser.add_argument("--latest", required=True)
    args, remaining = parser.parse_known_args()
    BuiltSiteTests.public = args.public.resolve()
    BuiltSiteTests.latest = args.latest
    unittest.main(argv=[__file__, *remaining])
