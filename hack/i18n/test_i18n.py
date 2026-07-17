#!/usr/bin/env python3
"""Tests for the pure functions behind the translation pipeline.

No network, no model calls, no Hugo: everything here is deterministic. Run with
`python3 -m pytest hack/i18n/test_i18n.py` (or plain `python3 hack/i18n/test_i18n.py`).

These cover the failure modes that are silent in production — a dropped code
fence, a reverted hero, a page that looks permanently stale, a reviewer verdict
read as a pass. Each one shipped a real bug during development.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import lib
import translate


class TestProtectRestore(unittest.TestCase):
    def test_roundtrip_is_lossless(self):
        text = (
            "Intro `inline` text.\n\n"
            "```yaml\nkey: value\n```\n\n"
            "{{< figure src=\"a.png\" >}}\n\n"
            "<!-- a comment -->\n"
        )
        masked, store = lib.protect(text)
        self.assertEqual(lib.restore(masked, store), text)

    def test_code_is_hidden_from_the_model(self):
        masked, store = lib.protect("before\n```bash\nkubectl get pods\n```\nafter")
        self.assertNotIn("kubectl", masked)
        self.assertEqual(len(store), 1)

    def test_fence_wins_over_inline_code(self):
        # A fence contains backticks; if INLINECODE ran first it would shred it.
        masked, store = lib.protect("```\na `b` c\n```")
        self.assertEqual(len(store), 1)
        self.assertTrue(next(iter(store)).startswith("§§FENCE_"))


class TestGlobMatching(unittest.TestCase):
    def test_star_md_matches_basename_at_any_depth(self):
        # Intended breadth: config.yaml's `*.md` means "a markdown page anywhere".
        # Scope is narrowed afterwards by _docs_out_of_scope / _blog_too_old.
        self.assertTrue(lib._matches_any("page.md", ["*.md"]))
        self.assertTrue(lib._matches_any("docs/v1.5/deep/page.md", ["*.md"]))

    def test_star_md_does_not_match_other_extensions(self):
        self.assertFalse(lib._matches_any("page.html", ["*.md"]))

    def test_single_star_does_not_swallow_a_subtree(self):
        # The fnmatch trap: its `*` matches `/` too, so `docs/*` would match at
        # any depth. Path semantics keep it to one level.
        self.assertTrue(lib._matches_any("docs/x.md", ["docs/*"]))
        self.assertFalse(lib._matches_any("docs/v1.5/x.md", ["docs/*"]))

    def test_subtree_glob(self):
        self.assertTrue(lib._matches_any("docs/v1.5/x.md", ["docs/**"]))
        self.assertFalse(lib._matches_any("blog/x.md", ["docs/**"]))

    def test_leading_doublestar(self):
        self.assertTrue(lib._matches_any("docs/_include/x.md", ["**/_include/**"]))


class TestScope(unittest.TestCase):
    def test_only_latest_docs_version(self):
        self.assertFalse(lib._docs_out_of_scope("docs/v1.5/intro.md", "v1.5"))
        self.assertTrue(lib._docs_out_of_scope("docs/v1.4/intro.md", "v1.5"))
        self.assertTrue(lib._docs_out_of_scope("docs/next/intro.md", "v1.5"))

    def test_non_docs_paths_are_untouched(self):
        self.assertFalse(lib._docs_out_of_scope("blog/2026-06-01-post.md", "v1.5"))

    def test_blog_cutoff(self):
        self.assertTrue(lib._blog_too_old("blog/2026-01-01-old.md", "2026-05-17"))
        self.assertFalse(lib._blog_too_old("blog/2026-06-01-new.md", "2026-05-17"))

    def test_blog_cutoff_disabled_by_empty_string(self):
        self.assertFalse(lib._blog_too_old("blog/2020-01-01-ancient.md", ""))

    def test_undated_blog_paths_are_kept(self):
        self.assertFalse(lib._blog_too_old("blog/_index.md", "2026-05-17"))


class TestRecordedDigest(unittest.TestCase):
    def _write(self, text):
        fh = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
        fh.write(text)
        fh.close()
        self.addCleanup(os.unlink, fh.name)
        return fh.name

    def test_reads_digest(self):
        p = self._write('---\ntitle: x\nsource_digest: "sha256:abc123"\n---\nbody\n')
        self.assertEqual(lib.recorded_digest(p), "abc123")

    def test_digest_after_a_long_front_matter(self):
        # A fixed-size read would miss this, the page would look permanently
        # stale, and it would be re-translated (and re-billed) every single day.
        filler = "\n".join(f"k{i}: {'v' * 80}" for i in range(200))
        p = self._write(f'---\n{filler}\nsource_digest: "sha256:deadbeef"\n---\nbody\n')
        self.assertEqual(lib.recorded_digest(p), "deadbeef")

    def test_missing_file_and_missing_digest(self):
        self.assertIsNone(lib.recorded_digest("/nonexistent/page.md"))
        self.assertIsNone(lib.recorded_digest(self._write("---\ntitle: x\n---\nbody\n")))

    def test_body_mentioning_source_digest_is_not_read(self):
        p = self._write('---\ntitle: x\n---\nsource_digest: "sha256:fake"\n')
        self.assertIsNone(lib.recorded_digest(p))


class TestNestedFrontMatter(unittest.TestCase):
    FM = {
        "title": "T",
        "slug": "keep-me",
        "taglines": ["A", "B"],
        "benefits": [{"title": "BT", "icon": "fas fa-code", "description": "BD"}],
        "seo": {"title": "ST", "keywords": ["K1"]},
    }

    def test_extracts_nested_user_visible_copy(self):
        got = lib.extract_translatable(self.FM)
        self.assertEqual(
            set(got),
            {"title", "taglines[0]", "taglines[1]", "benefits[0].title",
             "benefits[0].description", "seo.title", "seo.keywords[0]"},
        )

    def test_structural_keys_are_never_extracted(self):
        got = lib.extract_translatable(self.FM)
        self.assertNotIn("slug", got)
        self.assertNotIn("benefits[0].icon", got)

    def test_apply_translates_in_place_by_path(self):
        out = lib.apply_translations(self.FM, {
            "taglines[1]": "Б", "benefits[0].description": "БД", "seo.keywords[0]": "К1"})
        self.assertEqual(out["taglines"], ["A", "Б"])
        self.assertEqual(out["benefits"][0]["description"], "БД")
        self.assertEqual(out["benefits"][0]["icon"], "fas fa-code")  # untouched
        self.assertEqual(out["seo"]["keywords"], ["К1"])
        self.assertEqual(out["slug"], "keep-me")

    def test_apply_does_not_mutate_the_source(self):
        lib.apply_translations(self.FM, {"taglines[0]": "MUT"})
        self.assertEqual(self.FM["taglines"][0], "A")

    def test_stale_path_is_skipped_not_fatal(self):
        out = lib.apply_translations(self.FM, {"benefits[9].title": "ghost"})
        self.assertEqual(len(out["benefits"]), 1)

    def test_target_only_keys_survive(self):
        # A human added `seo:` and `l10n:` to the localized page; regenerating
        # from the English front matter must not delete their work.
        out = lib.merge_target_only_keys(
            {"title": "T"}, {"title": "old", "l10n": "transcreate", "seo": {"title": "S"}})
        self.assertEqual(out["title"], "T")          # translation wins
        self.assertEqual(out["l10n"], "transcreate")  # human addition kept
        self.assertEqual(out["seo"], {"title": "S"})

    def test_merge_tolerates_no_existing_page(self):
        self.assertEqual(lib.merge_target_only_keys({"title": "T"}, None), {"title": "T"})


class TestGlossary(unittest.TestCase):
    def setUp(self):
        self.g = lib.load_glossary()
        self.cfg = lib.load_config()

    def test_every_enabled_language_has_every_preferred_term(self):
        # zh-cn and hi shipped with zero preferred terms while being live, so
        # their translations had nothing keeping terminology consistent.
        pref = self.g["preferred"]
        for lang in (l["code"] for l in self.cfg["languages"]):
            missing = sorted(t for t, p in pref.items() if lang not in p)
            self.assertEqual(missing, [], f"{lang} has no preferred rendering for: {missing}")

    def test_terms_in_both_lists_differ_only_by_case(self):
        # `Tenant` (API kind, verbatim) vs `tenant` (ordinary noun, translated)
        # is deliberate. Any OTHER overlap is a genuine contradiction: the
        # translator would be told both to keep and to translate the same term.
        dnt = {t.lower(): t for t in self.g["do_not_translate"]}
        for term in self.g["preferred"]:
            clash = dnt.get(term.lower())
            if clash is not None:
                self.assertNotEqual(
                    clash, term,
                    f"{term!r} is in do_not_translate AND preferred with identical case")

    def test_do_not_translate_has_no_duplicates(self):
        dnt = self.g["do_not_translate"]
        self.assertEqual(len(dnt), len(set(dnt)))


class TestRealContentScope(unittest.TestCase):
    """Runs against the actual content tree, so drift in the site shows up here."""

    def setUp(self):
        self.cfg = lib.load_config()
        self.files = lib.iter_source_files(self.cfg)

    def test_scope_is_not_empty(self):
        self.assertGreater(len(self.files), 50)

    def test_no_out_of_scope_paths_leak_in(self):
        latest = lib.latest_docs_version(self.cfg)
        for rel in self.files:
            self.assertFalse(rel.startswith("oss-health/"), rel)
            self.assertNotIn("/_include/", f"/{rel}")
            if rel.startswith("docs/"):
                self.assertTrue(rel.startswith(f"docs/{latest}/"), f"stale docs version: {rel}")

    def test_pipeline_languages_match_hugo(self):
        # A language translated but not declared in hugo.yaml produces a
        # content tree Hugo never builds; declared but not translated produces
        # empty indexable pages. Both are silent.
        import yaml as _yaml
        hugo = _yaml.safe_load(open(os.path.join(lib.REPO_ROOT, "hugo.yaml"), encoding="utf-8"))
        declared = set(hugo["languages"]) - {self.cfg["source_lang"]}
        configured = {l["code"] for l in self.cfg["languages"]}
        self.assertEqual(configured, declared,
                         "hack/i18n/config.yaml and hugo.yaml disagree on which "
                         "languages are enabled")

    def test_no_unknown_user_visible_frontmatter_keys(self):
        # Guards against a new user-visible field (like `lede` was) being added
        # to content and silently shipping in English on every localized page.
        known_visible = set(lib.TRANSLATABLE_FRONTMATTER_KEYS) | set(lib.TRANSLATABLE_LIST_KEYS)
        # Structural or deliberately-untranslated keys.
        allowed = {
            "weight", "aliases", "date", "slug", "images", "author", "draft", "type",
            "layout", "menu", "cascade", "taxonomyCloud", "source_digest",
            "translation_status", "translation_review", "l10n",
            # taxonomy terms: translating them would fork the taxonomy
            "article_types", "topics",
            # containers whose translatable children are reached by recursion
            "benefits", "features",
        }
        seen = set()
        for rel in self.files:
            fm, _, _ = lib.split_frontmatter(
                open(lib.source_path(self.cfg, rel), encoding="utf-8").read())
            if isinstance(fm, dict):
                seen |= set(fm)
        unknown = seen - known_visible - allowed
        self.assertEqual(unknown, set(),
                         f"unrecognized front-matter key(s) {sorted(unknown)}: decide whether "
                         f"they are user-visible (add to lib.TRANSLATABLE_* ) or structural "
                         f"(add to `allowed` here)")


class TestVerdictParsing(unittest.TestCase):
    def test_pass_and_revise(self):
        self.assertEqual(translate._parse_verdict('{"verdict": "pass"}', "r")["verdict"], "pass")
        self.assertEqual(
            translate._parse_verdict('{"verdict": "revise", "findings": []}', "r")["verdict"],
            "revise")

    def test_json_after_prose(self):
        raw = 'Sure! Here is my review.\n\n{"verdict": "pass", "findings": []}'
        self.assertEqual(translate._parse_verdict(raw, "r")["verdict"], "pass")

    def test_unparseable_fails_closed(self):
        # The critical one: a refusal or prose reply must never read as a pass,
        # or a broken prompt waves every page through and the gate is a no-op.
        for raw in ("I cannot help with that.", "", "{truncated", '{"verdict": "maybe"}'):
            v = translate._parse_verdict(raw, "editor")
            self.assertEqual(v["verdict"], "revise", f"failed open on: {raw!r}")
            self.assertTrue(v["findings"])


class TestPayloadProtocol(unittest.TestCase):
    def test_parses_json_frontmatter_and_body(self):
        _, store = lib.protect("x")
        fm, body = translate._split_payload_response(
            '===FRONTMATTER===\n{"title": "Заголовок"}\n===BODY===\nтело', {}, {"title"})
        self.assertEqual(fm, {"title": "Заголовок"})
        self.assertEqual(body, "тело")

    def test_preamble_without_marker_is_rejected(self):
        # Otherwise "Here's the translation:" gets written into the page.
        with self.assertRaises(translate.ProtocolError):
            translate._split_payload_response("Here's the translation!", {}, set())

    def test_missing_frontmatter_key_is_rejected(self):
        # A page whose body is translated but whose hero silently stayed English
        # is worse than a retry tomorrow.
        with self.assertRaises(translate.ProtocolError):
            translate._split_payload_response(
                '===FRONTMATTER===\n{"title": "T"}\n===BODY===\nb', {}, {"title", "taglines[0]"})

    def test_dropped_placeholder_is_rejected(self):
        masked, store = lib.protect("a\n```\ncode\n```\nb")
        with self.assertRaises(translate.ProtocolError) as cm:
            translate._split_payload_response(
                '===FRONTMATTER===\n{}\n===BODY===\ntranslated, fence gone', store, set())
        self.assertIn("lost", str(cm.exception))

    def test_duplicated_placeholder_is_rejected(self):
        masked, store = lib.protect("a\n```\ncode\n```\nb")
        tok = next(iter(store))
        with self.assertRaises(translate.ProtocolError) as cm:
            translate._split_payload_response(
                f'===FRONTMATTER===\n{{}}\n===BODY===\n{tok}\n{tok}', store, set())
        self.assertIn("duplicated", str(cm.exception))

    def test_placeholders_are_restored(self):
        masked, store = lib.protect("a\n```\ncode\n```\nb")
        tok = next(iter(store))
        _, body = translate._split_payload_response(
            f'===FRONTMATTER===\n{{}}\n===BODY===\nпереведено\n{tok}', store, set())
        self.assertIn("```\ncode\n```", body)


class TestRateLimitMarkers(unittest.TestCase):
    def test_real_limits_are_recognized(self):
        for msg in ("rate_limit_error: too many", "You have hit your usage limit",
                    "credit balance is too low"):
            self.assertTrue(any(m in msg.lower() for m in translate._RATE_LIMIT_MARKERS), msg)

    def test_transient_errors_are_not_treated_as_the_daily_limit(self):
        # "overloaded" is a transient 529: swallowing it as the daily limit would
        # end the run with exit 0, and a skipped day would look like a good one.
        for msg in ("Error: overloaded_error", "connection reset", "500 internal"):
            self.assertFalse(any(m in msg.lower() for m in translate._RATE_LIMIT_MARKERS), msg)


if __name__ == "__main__":
    unittest.main(verbosity=2)
