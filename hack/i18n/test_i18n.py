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

    def test_figure_caption_and_alt_are_exposed_for_translation(self):
        # The bug a virtual reviewer caught: captions render under the image and
        # were staying English because the whole shortcode was masked.
        sc = '{{< figure src="a.webp" alt="Dashboard view" width="720" caption="The new dashboard." >}}'
        masked, store = lib.protect(sc)
        self.assertIn("Dashboard view", masked)      # alt exposed
        self.assertIn("The new dashboard.", masked)   # caption exposed
        self.assertNotIn("a.webp", masked)            # src protected
        self.assertNotIn("720", masked)               # width protected

    def test_figure_structure_survives_translated_caption(self):
        sc = '{{< figure src="a.webp" alt="A" width="720" caption="B" >}}'
        masked, store = lib.protect(sc)
        translated = masked.replace("A", "Я").replace("B", "Б")
        self.assertEqual(
            lib.restore(translated, store),
            '{{< figure src="a.webp" alt="Я" width="720" caption="Б" >}}')

    def test_shortcode_without_visible_attrs_is_masked_wholesale(self):
        masked, store = lib.protect('{{< youtube id="abc123" >}}')
        self.assertNotIn("abc123", masked)
        self.assertEqual(len(store), 1)


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

    def test_docs_version_picker_landing_in_scope(self):
        # docs/_index.md is the version-picker, not a versioned page — it must
        # stay in scope so the pipeline keeps its translations fresh.
        self.assertFalse(lib._docs_out_of_scope("docs/_index.md", "v1.5"))
        # A versioned landing still narrows to the latest version.
        self.assertFalse(lib._docs_out_of_scope("docs/v1.5/_index.md", "v1.5"))
        self.assertTrue(lib._docs_out_of_scope("docs/v1.4/_index.md", "v1.5"))

    def test_non_docs_paths_are_untouched(self):
        self.assertFalse(lib._docs_out_of_scope("blog/2026-06-01-post.md", "v1.5"))

    def test_blog_cutoff(self):
        self.assertTrue(lib._blog_too_old("blog/2026-01-01-old.md", "2026-05-17"))
        self.assertFalse(lib._blog_too_old("blog/2026-06-01-new.md", "2026-05-17"))

    def test_blog_cutoff_disabled_by_empty_string(self):
        self.assertFalse(lib._blog_too_old("blog/2020-01-01-ancient.md", ""))

    def test_undated_blog_paths_are_kept(self):
        self.assertFalse(lib._blog_too_old("blog/_index.md", "2026-05-17"))

    def test_blog_rolling_window(self):
        import datetime
        recent = (datetime.date.today() - datetime.timedelta(days=10)).isoformat()
        ancient = (datetime.date.today() - datetime.timedelta(days=90)).isoformat()
        self.assertFalse(lib._blog_too_old(f"blog/{recent}-post.md", "60d"))
        self.assertTrue(lib._blog_too_old(f"blog/{ancient}-post.md", "60d"))
        # An undated path is kept regardless of the window form.
        self.assertFalse(lib._blog_too_old("blog/_index.md", "60d"))


class TestOrphanTranslations(unittest.TestCase):
    """A deleted English page must take its pipeline-managed translations with
    it — and ONLY those: a hand-authored locale-only page has no source_digest
    and must never be swept up."""

    CFG = {"content_dir": "content", "source_lang": "en",
           "languages": [{"code": "ru"}, {"code": "de"}]}

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._old_root = lib.REPO_ROOT
        lib.REPO_ROOT = self._tmp.name
        self.addCleanup(lambda: setattr(lib, "REPO_ROOT", self._old_root))

    def _write(self, rel, text):
        path = os.path.join(self._tmp.name, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    STAMPED = '---\ntitle: x\nsource_digest: "sha256:abc"\n---\nbody\n'
    UNSTAMPED = "---\ntitle: x\n---\nbody\n"

    def test_translation_of_deleted_source_is_an_orphan(self):
        orphan = self._write("content/ru/docs/gone.md", self.STAMPED)
        self.assertEqual(lib.find_orphan_translations(self.CFG), [orphan])

    def test_translation_with_live_source_is_kept(self):
        self._write("content/en/docs/page.md", "---\ntitle: x\n---\nhello\n")
        self._write("content/ru/docs/page.md", self.STAMPED)
        self.assertEqual(lib.find_orphan_translations(self.CFG), [])

    def test_hand_authored_page_without_stamp_is_never_touched(self):
        self._write("content/ru/docs/handmade.md", self.UNSTAMPED)
        self.assertEqual(lib.find_orphan_translations(self.CFG), [])

    def test_only_lang_filter(self):
        ru = self._write("content/ru/docs/gone.md", self.STAMPED)
        de = self._write("content/de/docs/gone.md", self.STAMPED)
        self.assertEqual(lib.find_orphan_translations(self.CFG, only_lang="ru"), [ru])
        self.assertEqual(sorted(lib.find_orphan_translations(self.CFG)), sorted([ru, de]))


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
            # Versioned docs pages (docs/<ver>/...) must be the latest version;
            # the version-picker landing (docs/_index.md) sits directly under
            # docs/ and is version-agnostic, so it is allowed.
            if rel.startswith("docs/") and rel.count("/") >= 2:
                self.assertTrue(rel.startswith(f"docs/{latest}/"), f"stale docs version: {rel}")

    def _declared(self):
        import yaml as _yaml
        hugo = _yaml.safe_load(open(os.path.join(lib.REPO_ROOT, "hugo.yaml"), encoding="utf-8"))
        return set(hugo["languages"]) - {self.cfg["source_lang"]}

    def test_every_served_language_is_translated(self):
        # The invariant is one-directional. Translated-but-not-declared is the
        # normal way a language starts; declared-but-not-translated means the
        # site serves a language nothing keeps up to date.
        configured = {l["code"] for l in self.cfg["languages"]}
        orphaned = self._declared() - configured
        self.assertEqual(orphaned, set(),
                         f"hugo.yaml serves {sorted(orphaned)} but hack/i18n/config.yaml "
                         f"does not translate them — they will never be created or refreshed")

    def test_every_served_language_has_content(self):
        # Declaring a language with an empty content tree does not build
        # nothing: Hugo still emits /<code>/, /<code>/tags/, /<code>/categories/,
        # /<code>/topics/ and /<code>/404.html, all `index, follow`.
        for code in self._declared():
            d = os.path.join(lib.REPO_ROOT, self.cfg["content_dir"], code)
            self.assertTrue(
                os.path.isdir(d) and os.listdir(d),
                f"hugo.yaml declares '{code}' but content/{code}/ is empty or missing — "
                f"that publishes empty indexable pages. Land the content first.")

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


class TestFindingsReport(unittest.TestCase):
    def test_report_names_the_page_and_every_finding(self):
        md = translate._format_report([{
            "lang": "ru", "rel": "docs/v1.5/intro.md",
            "findings": [
                {"severity": "major", "from": "cozystack-maintainer",
                 "issue": "'node pool' rendered as 'пул узлов' but glossary says 'узел'"},
                {"severity": "minor", "from": "technical-editor", "issue": "register drifts formal"},
            ]}])
        self.assertIn("ru: docs/v1.5/intro.md", md)
        self.assertIn("cozystack-maintainer", md)
        self.assertIn("пул узлов", md)
        self.assertIn("register drifts formal", md)

    def test_report_survives_a_malformed_finding(self):
        # Findings come from a model; a finding missing `issue`/`severity` must
        # still reach the maintainer rather than crash the run after the work.
        md = translate._format_report([{"lang": "de", "rel": "x.md", "findings": [{}]}])
        self.assertIn("de: x.md", md)


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


class TestDerefShortcodes(unittest.TestCase):
    def test_absolute_ref_becomes_plain_link(self):
        # The exact break shipped in the sample pages: a ref to a sibling not yet
        # translated into this language hard-fails the Hugo build.
        t = '[x]({{% ref "/docs/v1.5/getting-started/install-talos" %}})'
        self.assertEqual(
            lib.deref_shortcodes(t, "docs/v1.5/getting-started/install-kubernetes.md"),
            "[x](/docs/v1.5/getting-started/install-talos/)")

    def test_angle_relref_and_fragment_are_preserved(self):
        t = '{{< relref "/docs/v1.5/x#section" >}}'
        self.assertEqual(lib.deref_shortcodes(t, "docs/v1.5/p.md"), "/docs/v1.5/x/#section")

    def test_relative_ref_resolves_against_page_dir(self):
        t = '[y]({{% ref "install-cozystack" %}})'
        self.assertEqual(
            lib.deref_shortcodes(t, "docs/v1.5/getting-started/install-kubernetes.md"),
            "[y](/docs/v1.5/getting-started/install-cozystack/)")

    def test_md_suffix_is_stripped(self):
        self.assertEqual(
            lib.deref_shortcodes('{{% ref "/docs/v1.5/x.md" %}}', "docs/v1.5/p.md"),
            "/docs/v1.5/x/")

    def test_named_parameter_ref_is_rewritten(self):
        t = '[a]({{% ref path="/docs/v1.5/x" %}})'
        self.assertEqual(lib.deref_shortcodes(t, "docs/p.md"), "[a](/docs/v1.5/x/)")
        t2 = '{{< relref path="/docs/v1.5/y#s" lang="de" >}}'
        self.assertEqual(lib.deref_shortcodes(t2, "docs/p.md"), "/docs/v1.5/y/#s")

    def test_anchor_only_ref_targets_the_current_page(self):
        t = 'See [this]({{% ref "#tenant-system" %}}).'
        self.assertEqual(
            lib.deref_shortcodes(t, "docs/v1.5/guides/concepts.md"),
            "See [this](/docs/v1.5/guides/concepts/#tenant-system).")

    def test_text_without_shortcodes_is_untouched(self):
        t = "no shortcodes here, just [a link](/docs/x/) and `code`."
        self.assertEqual(lib.deref_shortcodes(t, "docs/p.md"), t)

    def test_has_ref_shortcode_detects_every_form(self):
        self.assertTrue(lib.has_ref_shortcode('x {{% ref "/a" %}} y'))
        self.assertTrue(lib.has_ref_shortcode('{{< relref path="/a" >}}'))
        self.assertFalse(lib.has_ref_shortcode("plain [a](/a/) and `code`"))

    def test_unsupported_ref_shape_survives_and_is_detectable(self):
        # No positional target, no path= — left intact so the fail-closed guard fires.
        t = '{{% ref foo="bar" %}}'
        self.assertTrue(lib.has_ref_shortcode(lib.deref_shortcodes(t, "docs/p.md")))

    def test_backtick_raw_string_target_is_rewritten(self):
        # Hugo accepts backtick raw-string args; strip them, don't leave a broken link.
        t = "{{< ref `/docs/v1.5/x` >}}"
        self.assertEqual(lib.deref_shortcodes(t, "docs/p.md"), "/docs/v1.5/x/")

    def test_section_index_target_maps_to_parent(self):
        # `_index.md`/`index.md` are served at the parent URL, not `.../_index/`.
        self.assertEqual(
            lib.deref_shortcodes('{{% ref "/docs/v1.5/section/_index.md" %}}', "docs/p.md"),
            "/docs/v1.5/section/")
        self.assertEqual(
            lib.deref_shortcodes('{{% ref "/docs/v1.5/section/index" %}}', "docs/p.md"),
            "/docs/v1.5/section/")

    def test_malformed_target_fails_closed(self):
        # A shape whose target can't be cleanly extracted must survive detection.
        self.assertTrue(lib.has_ref_shortcode(
            lib.deref_shortcodes('{{% ref bogus="x" other=1 %}}', "docs/p.md")))


class TestRunStatus(unittest.TestCase):
    def test_clean_run_produces_no_status(self):
        self.assertEqual(translate._format_run_status(False, "", 5, [], 3), "")

    def test_early_stop_is_recorded(self):
        md = translate._format_run_status(True, "usage limit", 7, [], 3)
        self.assertIn("Run status", md)
        self.assertIn("usage limit", md)
        self.assertIn("7 page(s)", md)

    def test_skipped_pages_are_named(self):
        md = translate._format_run_status(
            False, "", 4,
            [{"lang": "ru", "rel": "docs/v1.5/intro.md", "error": "no ===BODY==="}], 3)
        self.assertIn("ru: docs/v1.5/intro.md", md)
        self.assertIn("no ===BODY===", md)

    def test_skipped_survives_a_missing_error_field(self):
        md = translate._format_run_status(False, "", 0, [{"lang": "de", "rel": "x.md"}], 3)
        self.assertIn("de: x.md", md)


class TestOrphanFloor(unittest.TestCase):
    def test_floor_value_is_pinned(self):
        self.assertEqual(translate.ORPHAN_PAGE_FLOOR, 5)

    def test_distinct_pages_dedup_across_languages(self):
        root = "/repo/content"
        orphans = ["/repo/content/de/docs/x.md", "/repo/content/ru/docs/x.md",
                   "/repo/content/de/docs/y.md"]
        self.assertEqual(translate._distinct_orphan_pages(orphans, root),
                         {"docs/x.md", "docs/y.md"})

    def test_floor_gates_on_distinct_pages_not_files(self):
        root = "/repo/content"
        one_page = [f"/repo/content/{lc}/docs/x.md"
                    for lc in ("de", "ru", "hi", "zh-cn", "es", "pt-br")]
        self.assertLessEqual(
            len(translate._distinct_orphan_pages(one_page, root)),
            translate.ORPHAN_PAGE_FLOOR)
        six_pages = [f"/repo/content/de/docs/p{i}.md" for i in range(6)]
        self.assertGreater(
            len(translate._distinct_orphan_pages(six_pages, root)),
            translate.ORPHAN_PAGE_FLOOR)


class TestStaleReportCleanup(unittest.TestCase):
    def test_empty_worklist_clears_a_prior_run_report(self):
        # Once the backlog drains, build_worklist() is empty and main() returns
        # early. A report left by an earlier run must still be cleared, or
        # run-daily.sh reposts stale findings stamped with today's date.
        orig_wl, orig_orph, orig_argv = (
            lib.build_worklist, lib.find_orphan_translations, sys.argv)
        existed = os.path.exists(translate.REPORT_PATH)
        backup = open(translate.REPORT_PATH).read() if existed else None
        try:
            lib.build_worklist = lambda *a, **k: []
            lib.find_orphan_translations = lambda *a, **k: []
            sys.argv = ["translate.py"]
            with open(translate.REPORT_PATH, "w", encoding="utf-8") as fh:
                fh.write("### stale findings from a previous run\n- something\n")
            rc = translate.main()
            self.assertEqual(rc, 0)
            self.assertFalse(os.path.exists(translate.REPORT_PATH),
                             "stale report was not cleared on an empty worklist")
        finally:
            lib.build_worklist, lib.find_orphan_translations, sys.argv = (
                orig_wl, orig_orph, orig_argv)
            if backup is not None:
                with open(translate.REPORT_PATH, "w", encoding="utf-8") as fh:
                    fh.write(backup)
            elif os.path.exists(translate.REPORT_PATH):
                os.unlink(translate.REPORT_PATH)


if __name__ == "__main__":
    unittest.main(verbosity=2)
