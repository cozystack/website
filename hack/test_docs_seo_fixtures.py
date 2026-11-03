#!/usr/bin/env python3
"""Exercise docs routing with small Hugo sites. Set HUGO to the CI-pinned binary."""

import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from urllib.error import URLError
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
        page = '{{ define "_internal/google_analytics.html" }}{{ end }}<!doctype html><html><head>{{ partial "head.html" . }}</head><body{{ if eq .Params.layout "docs-landing" }} data-docs-version-landing{{ end }}>{{ .Content }}{{ partial "navbar-lang-selector.html" . }}{{ partial "version-switcher.html" . }}</body></html>'
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
        self.write("data/docs-legacy-urls.json", "{}")
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
            self.assertEqual(self.head(versions).og_urls, self.head(versions).canonical)
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
        self.write("content/ru-landing/docs/_index.md", '---\ntitle: Versions\nlayout: docs-landing\n---\nTranslated chooser')
        config = self.root / "hugo.yaml"
        config.write_text(config.read_text().replace("contentDir: content/ru", "contentDir: content/ru-landing"))
        self.build()
        self.assertIn("Translated chooser", (self.public / "ru/docs/versions/index.html").read_text())
        self.assertEqual(self.head("ru/docs/versions/index.html").canonical,
                         ["https://example.org/ru/docs/versions/"])
        self.assertEqual(self.head("ru/docs/versions/index.html").og_urls,
                         ["https://example.org/ru/docs/versions/"])
        self.assertFalse((self.public / "ru/docs/guide/index.html").exists())

    def test_invalid_manifest_and_symlink_preserve_archives(self):
        self.build()
        manifest = self.public / ".docs-mirror.json"
        original = manifest.read_bytes()
        archive = self.public / "docs/v0/guide/index.html"
        archive_content = archive.read_bytes()
        for name in ("docs/v0/guide/index.html", "docs/v1.6/guide/index.html", "../outside", "/outside"):
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

    def test_metadata_uses_stable_copy_urls(self):
        self.configure(base="https://example.org/project/")
        config = self.root / "hugo.yaml"
        config.write_text(config.read_text().replace("    baseName: print", "    rel: alternate\n    baseName: print"))
        for lang in ("en", "ru"):
            self.write(f"content/{lang}/docs/v1.6/guide.md", '---\ntitle: Guide\noutputs: [HTML, RSS, PRINT]\n---\nGuide')
        self.build()
        for prefix in ("", "ru/"):
            for alias in ("", "v1/"):
                head = self.head(f"{prefix}docs/{alias}guide/index.html")
                self.assertEqual(head.og_urls, [f"https://example.org/project/{prefix}docs/guide/"])
                base = f"https://example.org/project/{prefix}docs/{alias}guide/"
                self.assertEqual(head.formats["application/rss+xml"], base + "index.xml")
                self.assertEqual(head.formats["text/html"], base + "print.html")

    def test_major_rollover_cleans_owned_files(self):
        self.build()
        manifest = json.loads((self.public / ".docs-mirror.json").read_text())
        self.assertIn("docs/v1/guide/index.html", manifest)
        for lang in ("en", "ru"):
            self.write(f"content/{lang}/docs/v2.0/_index.md", '---\ntitle: v2.0\n---\nv2.0')
            self.write(f"content/{lang}/docs/v2.0/guide.md", '---\ntitle: Guide\n---\nv2.0')
        self.configure("v2.0")
        self.build()
        for prefix in ("", "ru/"):
            self.assertFalse((self.public / f"{prefix}docs/v1/guide/index.html").exists())
            self.assertFalse((self.public / f"{prefix}docs/v1/index.html").exists())
            self.assertTrue((self.public / f"{prefix}docs/v1.6/guide/index.html").is_file())
            self.assertEqual(self.head(f"{prefix}docs/v2/guide/index.html").canonical,
                             [f"https://example.org/{prefix}docs/guide/"])

    def test_major_copy_preserves_hugo_aliases(self):
        self.write("content/en/docs/v1.6/guide.md", '---\ntitle: Guide\naliases: [/docs/v1/legacy-guide/]\n---\nGuide')
        self.build()
        self.assertTrue(self.head("docs/v1/legacy-guide/index.html").refresh)
        self.write("content/en/docs/v0/removed.md", '---\ntitle: Legacy\naliases: [/docs/v1/removed/]\n---\nLegacy')
        self.configure("v1.7")
        self.build()
        self.assertIn("/docs/v0/removed/", self.head("docs/v1/removed/index.html").refresh[0])
        self.assertTrue((self.public / "docs/v1.6/removed/index.html").is_file())

    def test_invalid_major_destination_preserves_landings(self):
        result = subprocess.run([HUGO, "--minify"], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.write("public/docs/v1", "existing file")
        before = (self.public / "docs/index.html").read_bytes()
        self.mirror(success=False)
        self.assertEqual((self.public / "docs/index.html").read_bytes(), before)
        self.assertFalse((self.public / "docs/versions/index.html").exists())

    def test_dev_server_links_to_existing_version_chooser(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        process = subprocess.Popen([HUGO, "server", "--bind", "127.0.0.1", "--port", str(port),
                                    "--disableLiveReload"], cwd=self.root,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            deadline = time.monotonic() + 15
            while True:
                try:
                    with urlopen(f"http://127.0.0.1:{port}/docs/v1.6/guide/", timeout=1) as response:
                        guide = Head(response.read().decode())
                    break
                except URLError:
                    if time.monotonic() >= deadline or process.poll() is not None:
                        self.fail("Hugo server did not start")
                    time.sleep(0.05)
            self.assertIn("/docs/", guide.links)
            self.assertNotIn("/docs/versions/", guide.links)
            with urlopen(f"http://127.0.0.1:{port}/docs/") as response:
                chooser = Head(response.read().decode())
            self.assertIn("/ru/docs/", chooser.links)
            self.assertNotIn("/ru/docs/versions/", chooser.links)
        finally:
            process.terminate()
            process.communicate(timeout=5)

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

    def legacy_site(self):
        self.write("data/docs-legacy-urls.json", (REPO / "data/docs-legacy-urls.json").read_text())
        for version in ("v1.6", "v1.7"):
            for path, name in (("applications/_index.md", "Applications"),
                               ("applications/mariadb.md", "MariaDB"),
                               ("install/talos/boot-to-talos.md", "Boot to Talos"),
                               ("roadmap.md", "Roadmap"), ("storage/_index.md", "Storage")):
                self.write(f"content/en/docs/{version}/{path}", f'---\ntitle: {name}\n---\n{name} {version}\n\n## Backups\n')
        self.write("content/en/docs/v0/operations/configuration/bundles.md",
                   '---\ntitle: Archived bundles\n---\nArchived bundles\n\n## distro-hosted\n')
        return {
            "/docs/reference/applications/": "/docs/applications/",
            "/docs/reference/applications/mysql/": "/docs/applications/mariadb/",
            "/docs/install/talos/kexec/": "/docs/install/talos/boot-to-talos/",
            "/roadmap/": "/docs/roadmap/",
            "/docs/bundles/distro-hosted/": None,
            "/docs/operations/storage/linstor/": "/docs/storage/",
            "/docs/v1/reference/applications/": "/docs/applications/",
            "/docs/v1/reference/applications/mysql/": "/docs/applications/mariadb/",
            "/docs/v1/install/talos/kexec/": "/docs/install/talos/boot-to-talos/",
            "/docs/v1/operations/storage/linstor/": "/docs/storage/",
        }

    def test_legacy_urls_serve_current_and_archived_content(self):
        expected = self.legacy_site()
        self.build()
        for old, target in expected.items():
            with self.subTest(url=old):
                page = self.head(old.lstrip("/") + "index.html")
                self.assertFalse(page.refresh)
                if target:
                    self.assertEqual(page.canonical, ["https://example.org" + target])
                    self.assertEqual(page.og_urls, page.canonical)
                    self.assertEqual(page.robots, ["index, follow"])
                    self.assertIn("backups", page.ids)
                else:
                    self.assertEqual(page.canonical, [])
                    self.assertEqual(page.robots, ["noindex, follow"])
                    self.assertIn("distro-hosted", page.ids)
        self.configure("v1.7")
        self.build()
        for old, target in expected.items():
            html = (self.public / old.lstrip("/") / "index.html").read_text()
            self.assertIn("v1.7" if target else "Archived bundles", html)
        archive = (self.public / "docs/v1.6/applications/mariadb/index.html").read_bytes()
        self.mirror()
        self.assertEqual((self.public / "docs/v1.6/applications/mariadb/index.html").read_bytes(), archive)

    def test_legacy_urls_preserve_queries_and_fragments_without_javascript(self):
        expected = self.legacy_site()
        self.configure(base="https://example.org/project/")
        self.build()
        class QuietHandler(SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=self.public))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            for old, target in expected.items():
                fragment = "backups" if target else "distro-hosted"
                url = f"http://127.0.0.1:{server.server_port}{old}?source=test#{fragment}"
                with urlopen(url) as response:
                    page = Head(response.read().decode())
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.geturl(), url)
                    self.assertFalse(page.refresh)
                    self.assertIn(fragment, page.ids)
                    if target:
                        self.assertEqual(page.canonical, ["https://example.org/project" + target])
        finally:
            server.shutdown()
            thread.join()
            server.server_close()

    def test_invalid_legacy_map_preserves_previous_output(self):
        expected = self.legacy_site()
        self.build()
        before = {old: (self.public / old.lstrip("/") / "index.html").read_bytes() for old in expected}
        source = self.public / "docs/v1.6/applications/index.html"
        source.write_text(source.read_text().replace("Applications v1.6", "Changed applications"))
        self.write("public/docs/blocked", "existing file")
        for old, target in (("/docs/unknown/", "/docs/missing/"),
                            ("/docs/v0/overwrite/", "/docs/storage/"),
                            ("/docs/../outside/", "/docs/storage/"),
                            ("/docs/unknown/", "https://other.example/"),
                            ("/docs/blocked/guide/", "/docs/storage/"),
                            ("/docs/applications/", "/docs/storage/")):
            with self.subTest(old=old, target=target):
                mapping = {"/docs/reference/applications/": "/docs/applications/", old: target}
                self.write("data/docs-legacy-urls.json", json.dumps(mapping))
                self.mirror(success=False)
                for path, content in before.items():
                    self.assertEqual((self.public / path.lstrip("/") / "index.html").read_bytes(), content)
        for mapping in ([], None, {"/docs/unknown/": None},
                        {"/docs/unknown/": "/docs/storage/?x=one"},
                        {"/docs/%2e%2e/outside/": "/docs/storage/"}):
            self.write("data/docs-legacy-urls.json", json.dumps(mapping))
            self.mirror(success=False)
            for path, content in before.items():
                self.assertEqual((self.public / path.lstrip("/") / "index.html").read_bytes(), content)

    def test_legacy_map_refuses_symlinks(self):
        self.legacy_site()
        self.build()
        archive = self.public / "docs/v0/guide/index.html"
        original = archive.read_bytes()
        old = self.public / "docs/reference/applications/mysql/index.html"
        old.unlink()
        old.symlink_to(archive)
        self.mirror(success=False)
        self.assertTrue(old.is_symlink())
        self.assertEqual(archive.read_bytes(), original)

    def test_legacy_map_refuses_archive_source_symlink_and_alias_target(self):
        self.legacy_site()
        self.write("content/en/docs/v1.6/guide.md", '---\ntitle: Guide\naliases: [/docs/v1.6/alias-guide/]\n---\nGuide')
        self.build()
        self.write("data/docs-legacy-urls.json", json.dumps({"/docs/old-guide/": "/docs/alias-guide/"}))
        self.mirror(success=False)
        self.write("data/docs-legacy-urls.json", (REPO / "data/docs-legacy-urls.json").read_text())
        source = self.public / "docs/v0/operations/configuration/bundles/index.html"
        source.unlink()
        source.symlink_to(self.public / "docs/v0/guide/index.html")
        self.mirror(success=False)
        self.assertTrue(source.is_symlink())

    def test_legacy_map_preserves_real_roadmap_page(self):
        self.legacy_site()
        self.write("content/en/roadmap.md", '---\ntitle: Standalone roadmap\n---\nStandalone roadmap')
        result = subprocess.run([HUGO, "--minify"], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        before = (self.public / "roadmap/index.html").read_bytes()
        self.mirror(success=False)
        self.assertEqual((self.public / "roadmap/index.html").read_bytes(), before)

    def test_legacy_preview_has_no_indexable_copies(self):
        expected = self.legacy_site()
        self.build("preview")
        for old in expected:
            page = self.head(old.lstrip("/") + "index.html")
            self.assertEqual(page.robots, ["noindex, nofollow"])
            self.assertEqual(page.canonical, [])
        self.assertEqual(self.locations(), [])

    def test_legacy_major_aliases_are_cleaned_on_major_rollover(self):
        self.legacy_site()
        self.build()
        source = self.root / "content/en/docs/v1.7"
        for file in source.rglob("*.md"):
            self.write("content/en/docs/v2.0/" + str(file.relative_to(source)),
                       file.read_text().replace("v1.7", "v2.0"))
        self.configure("v2.0")
        self.build()
        self.assertFalse((self.public / "docs/v1/reference/applications/mysql/index.html").exists())
        self.assertIn("v2.0", (self.public / "docs/v2/reference/applications/mysql/index.html").read_text())
        self.assertTrue((self.public / "docs/v1.6/applications/mariadb/index.html").is_file())

    def check_output(self, environment, success=True):
        result = subprocess.run(
            [sys.executable, str(REPO / "hack/test_docs_seo.py"), str(self.public),
             "--latest", "v1.6", "--environment", environment,
             "--base-url", "https://example.org/project/"],
            capture_output=True, text=True)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, "corrupted output passed checks")
        return result.stdout + result.stderr

    def test_production_output_checker_rejects_corruption(self):
        self.legacy_site()
        self.configure(base="https://example.org/project/")
        self.write("config/production/hugo.yaml", '''module:
  mounts:
    - source: content/en
      target: content
      lang: en
      files: ['! docs/next/**']
    - source: content/ru
      target: content
      lang: ru
      files: ['! docs/next/**']
''')
        self.build()
        self.check_output("production")
        guide = self.public / "docs/guide/index.html"
        original = guide.read_text()
        guide.write_text(original.replace("https://example.org/project/docs/guide/", "https://wrong.example/docs/guide/"))
        self.assertIn("test_current_docs_canonical", self.check_output("production", success=False))
        guide.write_text(original)
        old = self.public / "docs/reference/applications/mysql/index.html"
        original = old.read_bytes()
        old.unlink()
        self.assertIn("test_legacy_urls", self.check_output("production", success=False))
        old.write_bytes(original)
        sitemap = next(path for path in self.public.rglob("sitemap.xml")
                       if ET.parse(path).getroot().tag.endswith("urlset"))
        original = sitemap.read_bytes()
        tree = ET.parse(sitemap)
        item = ET.SubElement(tree.getroot(), "{http://www.sitemaps.org/schemas/sitemap/0.9}url")
        ET.SubElement(item, "{http://www.sitemaps.org/schemas/sitemap/0.9}loc").text = "https://example.org/project/private/"
        tree.write(sitemap)
        self.assertIn("test_sitemap_matches_canonical", self.check_output("production", success=False))
        sitemap.write_bytes(original)

    def test_preview_output_checker_requires_next_and_noindex(self):
        self.legacy_site()
        self.configure(base="https://example.org/project/")
        self.build("preview")
        self.check_output("preview")
        guide = self.public / "ru/docs/guide/index.html"
        original = guide.read_text()
        guide.write_text(original.replace("noindex, nofollow", "index, follow"))
        self.assertIn("test_preview_docs_are_noindex", self.check_output("preview", success=False))
        guide.write_text(original)
        next_page = self.public / "docs/next/index.html"
        next_page.unlink()
        self.assertIn("preview must build next/", self.check_output("preview", success=False))


if __name__ == "__main__":
    unittest.main()
