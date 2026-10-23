#!/usr/bin/env python3
"""Exercise docs routing with small Hugo sites. Set HUGO to the CI-pinned binary."""

import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from urllib.request import urlopen
import xml.etree.ElementTree as ET

from test_docs_seo import Head

REPO = Path(__file__).resolve().parents[1]
HUGO = os.environ.get("HUGO", "hugo")


class DocsFixtureTests(unittest.TestCase):
    def setUp(self):
        (REPO / "tmp").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=REPO / "tmp")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.public = self.root / "public"
        for path in ("layouts/partials/head.html", "layouts/partials/docs-seo.html", "layouts/partials/navbar-lang-selector.html",
                     "layouts/partials/version-switcher.html",
                     "layouts/partials/hooks/head-end.html", "layouts/sitemap.xml"):
            self.write(path, (REPO / path).read_text())
        for name in ("favicons", "page-description", "schema", "twitter_cards", "head-css", "google_analytics"):
            self.write(f"layouts/partials/{name}.html", "")
        self.write("layouts/partials/opengraph.html", '<meta property="og:url" content="{{ .Permalink }}">')
        # Same output-format selection used by Docsy v0.12.0.
        self.write("layouts/partials/outputformat.html", '''{{ $alts := newScratch }}{{ $format := "unknown" }}
{{ range .AlternativeOutputFormats }}{{ $alts.Set .Name true }}{{ end }}
{{ range .OutputFormats }}{{ if not ($alts.Get .Name) }}{{ $format = .Name }}{{ end }}{{ end }}
{{ return $format }}''')
        page = '{{ define "_internal/google_analytics.html" }}{{ end }}<!doctype html><html><head>{{ partial "head.html" . }}</head><body>{{ .Content }}{{ partial "navbar-lang-selector.html" . }}{{ partial "version-switcher.html" . }}</body></html>'
        for path in ("layouts/_default/single.html", "layouts/_default/list.html", "layouts/_default/single.print.html"):
            self.write(path, page)
        for lang in ("en", "ru"):
            self.write(f"content/{lang}/_index.md", '---\ntitle: Home\n---\nHome')
            self.write(f"content/{lang}/docs/_index.md", '---\ntitle: Choose Documentation Version\nlayout: docs-landing\n---\nChoose a version')
            self.write(f"content/{lang}/about.md", '---\ntitle: About\n---\nAbout')
            for version in ("v0", "v1.5", "v1.6", "v1.7", "next"):
                self.write(f"content/{lang}/docs/{version}/_index.md", f'---\ntitle: {version}\n---\n{version}')
                self.write(f"content/{lang}/docs/{version}/guide.md", f'---\ntitle: Guide\n---\n{version}')
        self.write("content/en/docs/v1.6/removed.md", '---\ntitle: Removed\n---\nOld page')
        self.write("content/en/private.md", '---\ntitle: Private\nparams:\n  noindex: true\n---\nPrivate')
        self.write("content/en/print.md", '---\ntitle: Print\noutputs: [HTML, PRINT]\n---\nPrint')
        self.configure()

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def configure(self, version="v1.6", base="https://example.org/"):
        self.write("hugo.yaml", f'''baseURL: {base}
title: Test
defaultContentLanguage: en
languages:
  en:
    contentDir: content/en
    locale: en
    languageCode: en
  ru:
    contentDir: content/ru
    locale: ru
    languageCode: ru
params:
  latest_version_id: "{version}"
  versions:
    - id: "{version}"
      version: "{version}"
      url: "/docs/{version}/"
    - id: v0
      version: v0
      url: /docs/v0/
  images: [image.png]
mediaTypes:
  text/html:
    suffixes: [html]
outputFormats:
  PRINT:
    mediaType: text/html
    baseName: print
    isHTML: true
    permalinkable: true
markup:
  goldmark:
    renderer:
      unsafe: true
''')

    def build(self, environment="production"):
        result = subprocess.run([HUGO, "--environment", environment, "--minify"], cwd=self.root,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.mirror()

    def mirror(self, success=True):
        result = subprocess.run(["bash", str(REPO / "hack/mirror_latest.sh"), str(self.public)],
                                cwd=self.root, capture_output=True, text=True)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def head(self, path):
        return Head((self.public / path).read_text())

    def locations(self):
        return [e.text for path in self.public.rglob("sitemap.xml")
                for e in ET.parse(path).findall("{*}url/{*}loc")]

    def test_root_landing_archives_and_legacy_aliases(self):
        self.write("content/en/docs/v0/legacy.md", '---\ntitle: Legacy\naliases: [/docs/legacy/]\n---\nLegacy')
        self.write("content/en/docs/v0/guide.md", '---\ntitle: Legacy guide\naliases: [/docs/guide/]\n---\nLegacy guide')
        self.build()
        for prefix in ("", "ru/"):
            self.assertEqual(self.head(f"{prefix}docs/index.html").canonical,
                             [f"https://example.org/{prefix}docs/"])
            versions = f"{prefix}docs/versions/index.html"
            self.assertIn("Choose a version", (self.public / versions).read_text())
            self.assertEqual(self.head(versions).canonical,
                             [f"https://example.org/{prefix}docs/versions/"])
            self.assertIn(f"https://example.org/{prefix}docs/versions/", self.locations())
            other_prefix = "ru/" if not prefix else ""
            self.assertIn(f"/{other_prefix}docs/versions/", self.head(versions).links)
            self.assertIn(f"/{prefix}docs/versions/", self.head(f"{prefix}docs/guide/index.html").links)
        self.assertFalse(self.head("docs/guide/index.html").refresh)
        self.assertIn("v1.6", (self.public / "docs/guide/index.html").read_text())
        self.assertIn("/docs/v0/legacy/", self.head("docs/legacy/index.html").refresh[0])
        archive = (self.public / "docs/v0/guide/index.html").read_bytes()
        versions = (self.public / "docs/versions/index.html").read_bytes()
        self.mirror()
        self.assertEqual((self.public / "docs/v0/guide/index.html").read_bytes(), archive)
        self.assertEqual((self.public / "docs/versions/index.html").read_bytes(), versions)
        self.configure("v1.7")
        self.build()
        self.assertIn("/docs/v0/legacy/", self.head("docs/legacy/index.html").refresh[0])
        self.assertIn("v1.7", (self.public / "docs/guide/index.html").read_text())

    def test_removed_asset_and_hugo_replaced_legacy_alias(self):
        self.write("content/en/docs/v0/removed.md", '---\ntitle: Old page\naliases: [/docs/removed/]\n---\nLegacy page')
        self.write("content/en/docs/v1.6/guide/asset.txt", "Old asset")
        self.build()
        self.assertTrue((self.public / "docs/guide/asset.txt").is_file())
        self.assertFalse(self.head("docs/removed/index.html").refresh)
        self.configure("v1.7")
        self.build()
        self.assertFalse((self.public / "docs/guide/asset.txt").exists())
        self.assertIn("/docs/v0/removed/", self.head("docs/removed/index.html").refresh[0])
        self.assertIn("Old page", (self.public / "docs/v1.6/removed/index.html").read_text())

    def test_reserved_source_path_preserves_output(self):
        self.build()
        original = (self.public / "docs/guide/index.html").read_bytes()
        for name in ("v0", "next", "versions"):
            self.write(f"public/docs/v1.6/{name}/index.html", "Reserved")
            self.mirror(success=False)
            self.assertEqual((self.public / "docs/guide/index.html").read_bytes(), original)
            (self.public / "docs/v1.6" / name / "index.html").unlink()
            (self.public / "docs/v1.6" / name).rmdir()

    def test_version_landing_without_translated_current_docs(self):
        self.write("content/ru-landing/_index.md", '---\ntitle: Home\n---\nHome')
        self.write("content/ru-landing/docs/_index.md", '---\ntitle: Versions\n---\nTranslated chooser')
        config = self.root / "hugo.yaml"
        config.write_text(config.read_text().replace("contentDir: content/ru", "contentDir: content/ru-landing"))
        self.build()
        self.assertIn("Translated chooser", (self.public / "ru/docs/versions/index.html").read_text())
        self.assertEqual(self.head("ru/docs/versions/index.html").canonical,
                         ["https://example.org/ru/docs/versions/"])
        self.assertFalse((self.public / "ru/docs/guide/index.html").exists())

    def test_invalid_manifest_and_symlink_preserve_archives(self):
        self.build()
        manifest = self.public / ".docs-mirror.json"
        original = manifest.read_bytes()
        archive = self.public / "docs/v0/guide/index.html"
        archive_content = archive.read_bytes()
        for name in ("docs/v0/guide/index.html", "../outside", "/outside"):
            manifest.write_text(json.dumps({name: "0" * 64}))
            self.mirror(success=False)
            self.assertEqual(archive.read_bytes(), archive_content)
        manifest.write_bytes(original)
        target = self.public / "docs/guide/index.html"
        target.unlink()
        target.symlink_to(archive)
        self.mirror(success=False)
        self.assertEqual(archive.read_bytes(), archive_content)

    def test_minor_rollover_and_removed_page(self):
        self.build()
        before = self.head("docs/guide/index.html").canonical
        self.assertTrue((self.public / "docs/removed/index.html").exists())
        self.configure("v1.7")
        self.build()
        self.assertEqual(before, self.head("docs/guide/index.html").canonical)
        self.assertIn("v1.7", (self.public / "docs/guide/index.html").read_text())
        self.assertFalse((self.public / "docs/removed/index.html").exists())
        self.assertEqual(self.head("docs/v1.6/guide/index.html").robots, ["noindex, follow"])
        self.assertFalse(any("/docs/v1.6/" in url for url in self.locations()))

    def test_subpath_language_queries_fragments_and_aliases(self):
        self.configure(base="https://example.org/project/")
        for lang, prefix in (("en", ""), ("ru", "ru/")):
            path = f"/project/{prefix}docs/v1.6/guide/?q=one&sort=asc#section"
            self.write(f"content/{lang}/docs/v1.6/links.md", f'''---
title: Links
aliases: [/docs/v1.6/old-links/]
---
<a href="{path}">Relative</a>
<a href="https://example.org{path}">Absolute</a>
<a href="https://other.example{path}">External</a>
''')
        self.build()
        for prefix in ("", "ru/"):
            for alias in ("", "v1/"):
                page = self.head(f"{prefix}docs/{alias}links/index.html")
                self.assertEqual(page.canonical, [f"https://example.org/project/{prefix}docs/links/"])
                self.assertEqual(page.languages, {
                    "en": "https://example.org/project/docs/links/",
                    "x-default": "https://example.org/project/docs/links/",
                    "ru": "https://example.org/project/ru/docs/links/",
                })
                target = f"/project/{prefix}docs/{alias}guide/?q=one&sort=asc#section"
                self.assertEqual(page.links[:2], [target, "https://example.org" + target])
                self.assertIn("https://other.example/project/", page.links[2])
                stub = self.head(f"{prefix}docs/{alias}old-links/index.html")
                self.assertEqual(stub.canonical, page.canonical)
                self.assertIn(f"/docs/{alias}links/", stub.refresh[0])
        self.assertIn("https://example.org/project/ru/docs/guide/", self.locations())
        self.assertIn("https://example.org/project/about/", self.locations())
        self.assertFalse(any("/private/" in url or "/docs/next/" in url for url in self.locations()))
        alternates = [e.attrib["href"] for p in self.public.rglob("sitemap.xml")
                      for e in ET.parse(p).findall("{*}url/{*}link")]
        self.assertIn("https://example.org/project/ru/docs/guide/", alternates)

    def test_preview_and_print_are_noindex(self):
        self.build()
        self.assertEqual(self.head("print.html").robots, ["noindex, nofollow"])
        self.assertEqual(self.head("print.html").canonical, [])
        self.build("preview")
        self.assertEqual(self.head("docs/guide/index.html").robots, ["noindex, nofollow"])
        self.assertEqual(self.head("docs/guide/index.html").canonical, [])
        self.assertEqual(self.locations(), [])

    def test_invalid_configuration_preserves_existing_mirror(self):
        self.build()
        original = (self.public / "docs/guide/index.html").read_bytes()
        for version in ("../../docs", "latest", "", "v9.9"):
            self.configure(version)
            self.mirror(success=False)
            self.assertEqual((self.public / "docs/guide/index.html").read_bytes(), original)

    def test_missing_latest_version_fails_build(self):
        config = self.root / "hugo.yaml"
        config.write_text(config.read_text().replace('  latest_version_id: "v1.6"\n', ''))
        result = subprocess.run([HUGO], cwd=self.root, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("latest_version_id is required", result.stdout + result.stderr)

    def test_static_http_without_javascript(self):
        self.build()
        class QuietHandler(SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=self.public))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            for alias in ("", "v1/", "v1.6/"):
                with urlopen(f"http://127.0.0.1:{server.server_port}/docs/{alias}guide/?source=test") as response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(Head(response.read().decode()).canonical,
                                     ["https://example.org/docs/guide/"])
        finally:
            server.shutdown()
            thread.join()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
