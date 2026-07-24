#!/usr/bin/env python3
"""Translate Cozystack website pages with a full machine review gate.

Per page, per language, the pipeline runs:
  1. translate            — Claude (Opus) with glossary + style guide
  2. back-translate        — literal EN round-trip of the translation
     + compare             — flag meaning drift vs the original English
  3. review (two natives)  — technical editor (fluency) + Cozystack maintainer
                             (technical correctness); both prompted as native
                             speakers of the target language
  4. revise-if-needed      — one revision addressing all findings, then re-check,
                             bounded by review.max_rounds / back_translation.max_retries

Nothing is written until the gate finishes, so an interrupted run never leaves a
half-done page. A page that clears the gate is stamped `auto-reviewed`; one that
runs out of revise rounds with findings still open is written but stamped
`auto-reviewed-with-findings`, so the two are always distinguishable. Reviewer
replies that cannot be parsed count as "revise", never as a silent pass.

Auth: see `auth` in config.yaml — either a Claude subscription via the Claude
Agent SDK (`claude-agent-sdk`; the base `anthropic` SDK cannot use a
subscription), or a metered org API key.

Daily-until-limit: on a usage-limit error the run stops cleanly (exit 0) and
resumes next day; already-written pages are skipped via source_digest.

Usage:
  translate.py [--lang ru] [--limit N] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

import yaml

import lib

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")
STYLE_DIR = os.path.join(os.path.dirname(__file__), "style-guides")
# Findings still open after the revise loop, for the weekly PR body. Gitignored:
# it is a per-run artifact, not content.
REPORT_PATH = os.path.join(os.path.dirname(__file__), "last-run-findings.md")
# Orphan mass-deletion floor: refuse to auto-delete translations of more than
# this many distinct English pages in one run (a large batch means the English
# tree moved, not that N pages died). Module-level so it is pinned by a test.
ORPHAN_PAGE_FLOOR = 5


def _format_report(report: list[dict]) -> str:
    """Render open findings as the markdown that goes in the PR body."""
    out = [f"### Pages with open findings ({len(report)})", "",
           "The revise loop ran out of rounds with these findings still raised by at",
           "least one reviewer, so the pages are stamped",
           "`translation_review: auto-reviewed-with-findings`. They are published anyway",
           "(publish-then-ratify) but are the ones worth a human's attention first.",
           "",
           "Findings come from the model reviewers, so some will be noise — that is",
           "expected; they are listed rather than acted on automatically.", ""]
    for entry in report:
        out.append(f"**`{entry['lang']}: {entry['rel']}`**")
        out.append("")
        for f in entry["findings"]:
            sev, who = f.get("severity", "?"), f.get("from", "?")
            out.append(f"- _{sev}_ ({who}): {f.get('issue', f)}")
        out.append("")
    return "\n".join(out)


class RateLimited(Exception):
    """Raised when the subscription hits its usage limit — stop the run cleanly."""


def _read(path: str) -> str:
    """Read a prompt/style file. A missing prompt is a hard failure — silently
    returning "" would send a reviewer out with no instructions, and its prose
    reply would then be read as a pass."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"required prompt/config file missing: {path}")
    return open(path, encoding="utf-8").read()


def _read_optional(path: str, default: str = "") -> str:
    return open(path, encoding="utf-8").read() if os.path.exists(path) else default


def render(template: str, lang_cfg: dict, glossary: dict) -> str:
    dnt = ", ".join(glossary.get("do_not_translate", []))
    preferred = "\n".join(
        f"  - {t} -> {pl[lang_cfg['code']]}"
        for t, pl in (glossary.get("preferred") or {}).items()
        if lang_cfg["code"] in pl
    ) or "  (none specified)"
    style = _read_optional(os.path.join(STYLE_DIR, f"{lang_cfg['code']}.md"),
                           f"(use professional, natural {lang_cfg['name']}.)")
    return (template
            .replace("{{LANGUAGE}}", lang_cfg["name"])
            .replace("{{LANG_CODE}}", lang_cfg["code"])
            .replace("{{DO_NOT_TRANSLATE}}", dnt)
            .replace("{{PREFERRED_TERMS}}", preferred)
            .replace("{{STYLE_GUIDE}}", style))


# The Agent SDK's rate-limit exception type is version-dependent / undocumented,
# so we match on the message text. Broaden this list if a limit slips through.
# Only markers that mean "the subscription/account is out of budget". Deliberately
# NOT "overloaded" (transient 529) or a bare "429" (can appear in unrelated text):
# treating those as the daily limit would silently end the run with exit 0 and an
# skipped day would look identical to a successful one.
_RATE_LIMIT_MARKERS = ("rate_limit_error", "usage limit", "quota exceeded",
                       "out of credit", "credit balance")


async def _aquery(cfg, system, payload):
    """One single-turn, tool-less completion via the Claude Agent SDK (subscription)."""
    from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock
    opts = ClaudeAgentOptions(
        model=cfg["model"]["default"],
        system_prompt=system,
        allowed_tools=[],   # pure text: no tools, no filesystem, no MCP, no approval prompts
        max_turns=1,
    )
    out = []
    async for message in query(prompt=payload, options=opts):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    out.append(block.text)
    return "".join(out).strip()


def call(cfg, system, payload):
    """One Opus call over the Max subscription (Claude Agent SDK / CLAUDE_CODE_OAUTH_TOKEN).

    Raises RateLimited when the subscription's usage limit is hit, so the daily
    run stops cleanly and resumes tomorrow.
    """
    import asyncio
    try:
        return asyncio.run(_aquery(cfg, system, payload))
    except RateLimited:
        raise
    except Exception as exc:
        if any(m in str(exc).lower() for m in _RATE_LIMIT_MARKERS):
            raise RateLimited(str(exc)) from exc
        raise


def _parse_verdict(raw: str, who: str) -> dict:
    """Pull the JSON verdict out of a reviewer response.

    FAILS CLOSED: anything we cannot parse as a verdict (model refusal, prose,
    truncated JSON) counts as "revise", never a silent pass — otherwise a broken
    prompt or SDK would wave every page through and the gate would be
    unfalsifiable. Tries the non-greedy match first so prose containing braces
    before the JSON doesn't swallow the whole response.
    """
    for pat in (r"\{.*?\}\s*$", r"\{.*\}"):
        m = re.search(pat, raw.strip(), re.DOTALL)
        if not m:
            continue
        try:
            v = json.loads(m.group(0))
        except json.JSONDecodeError:
            continue
        if isinstance(v, dict) and v.get("verdict") in ("pass", "revise"):
            v.setdefault("findings", [])
            return v
    return {"verdict": "revise", "parse_failed": True,
            "findings": [{"severity": "major", "from": who,
                          "issue": f"unparseable reviewer response from {who} "
                                   f"(treated as revise): {raw.strip()[:200]}"}]}


class ProtocolError(Exception):
    """The model did not answer in the ===FRONTMATTER===/===BODY=== protocol."""


def _split_payload_response(out: str, store: dict, expect: set[str]) -> tuple[dict, str]:
    """Parse a translate/revise reply. Raises rather than treating a preamble
    ("Here's the translation:") as the page body, and verifies every protected
    placeholder survived — a dropped §§FENCE_n§§ would silently delete a code
    block from the page.

    The front-matter half is JSON ({path: translated_text}), not `key: value`
    lines: values are addressed by path so nested copy (taglines[0],
    benefits[1].description) round-trips, and a multi-line description no longer
    gets shredded by a line-oriented parser.
    """
    if "===BODY===" not in out:
        raise ProtocolError(f"no ===BODY=== marker in reply: {out.strip()[:200]}")
    head, body = out.split("===BODY===", 1)
    head = head.replace("===FRONTMATTER===", "").strip()
    if expect:
        m = re.search(r"\{.*\}", head, re.DOTALL)
        if not m:
            raise ProtocolError(f"front-matter half is not JSON: {head[:200]}")
        try:
            tr_fm = json.loads(m.group(0))
        except json.JSONDecodeError as exc:
            raise ProtocolError(f"front-matter JSON did not parse: {exc}") from exc
        if not isinstance(tr_fm, dict):
            raise ProtocolError("front-matter JSON is not an object")
        # Missing keys mean the hero/cards would silently stay English on a page
        # whose body IS translated — a half-translated page is worse than a retry.
        missing = expect - set(tr_fm)
        if missing:
            raise ProtocolError(f"front-matter keys not returned: {sorted(missing)}")
        tr_fm = {k: v for k, v in tr_fm.items() if k in expect and isinstance(v, str)}
    else:
        tr_fm = {}
    body = body.strip()
    bad = {tok: body.count(tok) for tok in store if body.count(tok) != 1}
    if bad:
        tok, n = next(iter(bad.items()))
        what = "lost" if n == 0 else "duplicated"
        raise ProtocolError(f"{len(bad)} protected placeholder(s) {what} by the model "
                            f"(e.g. {tok} appears {n}×, expected 1) — refusing to write a page "
                            f"with dropped or duplicated code")
    return tr_fm, lib.restore(body, store)


def translate_page(cfg, glossary, lang_cfg, rel) -> tuple[str, bool, list[dict]]:
    """Run the full gate for one page.

    Returns (file_text, gate_passed, findings). gate_passed is False when the
    revise loop ran out of rounds with findings still open — the page is still
    written (publish-then-review), but stamped honestly so it is distinguishable
    from a page that actually cleared the gate.

    `findings` are the ones still open on the final round. They are returned, not
    swallowed: a page stamped `-with-findings` with no record of WHAT was found
    tells a maintainer only that something is wrong, which is not reviewable.
    """
    src = lib.source_path(cfg, rel)
    text = open(src, encoding="utf-8").read()
    fm, body, _ = lib.split_frontmatter(text)
    if fm is None:
        # Unparseable / absent YAML front matter: writing the page would silently
        # drop slug/date/aliases/images. Refuse instead.
        raise ProtocolError(f"{rel}: could not parse YAML front matter in the English source")
    masked_body, store = lib.protect(body)

    # Every user-visible string in the front matter, at any depth, addressed by
    # path. The landing page renders its hero and cards from taglines[]/
    # benefits[]/features[]; a top-level-only walk would leave them English.
    fm_values = lib.extract_translatable(fm)
    expect = set(fm_values)

    _FM_PROTOCOL = (
        "Translate the FRONTMATTER values and the BODY below.\n"
        "FRONTMATTER is a JSON object mapping an opaque path to the English text.\n"
        "Return a JSON object with the SAME keys and translated values — do not add,\n"
        "drop, or rename keys, and do not interpret the keys themselves.\n"
        "Return EXACTLY:\n===FRONTMATTER===\n<json object>\n===BODY===\n<translated body>"
    )

    # --- Stage 1: translate ---
    sys_translate = render(_read(os.path.join(PROMPT_DIR, "translate.md")), lang_cfg, glossary)
    payload = (
        _FM_PROTOCOL
        + "\n\n===FRONTMATTER===\n" + json.dumps(fm_values, ensure_ascii=False, indent=2)
        + "\n===BODY===\n" + masked_body
    )
    tr_fm, tr_body = _split_payload_response(call(cfg, sys_translate, payload), store, expect)

    # --- Stages 2-4: gate with revise loop ---
    max_rounds = max(cfg["review"]["max_rounds"], cfg["back_translation"]["max_retries"])
    gate_passed = False
    findings: list[dict] = []
    for round_no in range(max_rounds + 1):
        findings = []

        # 2. back-translation round-trip
        if cfg["back_translation"]["enabled"]:
            masked_tr, tr_store = lib.protect(tr_body)
            back_en = call(cfg,
                           render(_read(os.path.join(PROMPT_DIR, "back-translate.md")), lang_cfg, glossary),
                           masked_tr)
            cmp = _parse_verdict(call(cfg,
                render(_read(os.path.join(PROMPT_DIR, "back-translate-compare.md")), lang_cfg, glossary),
                f"ORIGINAL:\n{body}\n\nBACK-TRANSLATION:\n{lib.restore(back_en, tr_store)}"),
                "back-translation")
            if cmp["verdict"] == "revise":
                # A "revise" with an empty findings list must still block the gate:
                # deriving pass/fail from len(findings) would let an explicit
                # "redo this" verdict through as auto-reviewed.
                findings += ([{**f, "from": "back-translation"} for f in cmp["findings"]]
                             or [{"severity": "major", "from": "back-translation",
                                  "issue": "revise verdict with no findings listed"}])

        # 2b. deterministic checks — cheap, objective, and not subject to the
        # reviewers' mood. Masking already guarantees code/shortcodes/URLs; these
        # cover what legitimately lives in prose (versions, bare flags, brands)
        # and the per-language typography the style guides mandate but nothing
        # previously verified. They feed the same revise loop as the reviewers.
        findings += lib.integrity_findings(body, tr_body, glossary.get("do_not_translate"))
        findings += lib.check_typography(tr_body, lang_cfg["code"])

        # 3. two native reviewers
        for reviewer in cfg["review"]["reviewers"]:
            sys_r = render(_read(os.path.join(PROMPT_DIR, os.path.basename(reviewer["prompt"]))),
                           lang_cfg, glossary)
            verdict = _parse_verdict(call(cfg, sys_r,
                f"ENGLISH SOURCE:\n{body}\n\n{lang_cfg['name'].upper()} TRANSLATION:\n{tr_body}"),
                reviewer["id"])
            if verdict["verdict"] == "revise":
                findings += ([{**f, "from": reviewer["id"]} for f in verdict["findings"]]
                             or [{"severity": "major", "from": reviewer["id"],
                                  "issue": "revise verdict with no findings listed"}])

        if not findings:
            gate_passed = True
            break

        # Out of rounds: publish what the reviewers last SAW, stamped
        # `-with-findings`. Revising here instead would ship text that nothing
        # re-checked, and the findings posted to the weekly PR would describe a
        # version of the page that no longer exists — the stamp and the report
        # must always refer to the text actually written.
        if round_no == max_rounds:
            break

        # 4. revise addressing all findings, then re-check
        masked_body2, store = lib.protect(tr_body)
        sys_rev = render(_read(os.path.join(PROMPT_DIR, "revise.md")), lang_cfg, glossary)
        rev_payload = (
            _FM_PROTOCOL
            + "\n\nENGLISH SOURCE:\n" + body
            + "\n\nCURRENT TRANSLATION:\n===FRONTMATTER===\n"
            + json.dumps(tr_fm, ensure_ascii=False, indent=2)
            + "\n===BODY===\n" + masked_body2
            + "\n\nFINDINGS:\n" + json.dumps(findings, ensure_ascii=False, indent=2)
        )
        tr_fm, tr_body = _split_payload_response(call(cfg, sys_rev, rev_payload), store, expect)

    # --- assemble ---
    # Apply by path onto a copy of the English front matter: structural keys
    # (slug, date, weight, icon, aliases, images) are carried over untouched.
    out_fm = lib.apply_translations(fm, tr_fm)
    # Then re-attach keys a human added to the localized page that do not exist
    # upstream (a locale-specific `seo:` block, `l10n:` notes). Deriving the page
    # purely from the English front matter would delete native reviewers' work
    # every time the source changed.
    dest = lib.target_path(cfg, lang_cfg["code"], rel)
    if os.path.exists(dest):
        existing_fm, _, _ = lib.split_frontmatter(open(dest, encoding="utf-8").read())
        out_fm = lib.merge_target_only_keys(out_fm, existing_fm)
    out_fm["source_digest"] = f"sha256:{lib.sha256_file(src)}"
    # `l10n` is the site's existing convention for HOW a page was localized
    # (mt | transcreate). Whatever the page was before, this pipeline just
    # machine-translated it, so say so — the disclaimer banner and any future
    # native-review triage read this.
    out_fm["l10n"] = "mt"
    # Stamp honestly: a page that ran out of revise rounds with findings still
    # open is NOT the same as one that cleared the gate. Neither is "ratified" —
    # only a human sets that, and only that value drops the disclaimer banner.
    out_fm[cfg["review_status_field"]] = (
        cfg["review_status_value"] if gate_passed else f"{cfg['review_status_value']}-with-findings")
    fm_yaml = yaml.safe_dump(out_fm, allow_unicode=True, sort_keys=False,
                             default_flow_style=False, width=10 ** 9).strip()
    # Rewrite ref/relref cross-links to plain links: a link to a sibling page not
    # yet translated into this language would otherwise hard-fail the Hugo build
    # (REF_NOT_FOUND). See lib.deref_shortcodes.
    tr_body = lib.deref_shortcodes(tr_body, rel)
    # Fail closed: if any ref/relref survived (an unsupported shortcode shape),
    # refuse to write the page rather than ship one that can break the build.
    if lib.has_ref_shortcode(tr_body):
        raise ProtocolError(
            f"{rel}: a ref/relref shortcode survived deref (unsupported shape) — "
            f"refusing to write a page that could break the Hugo build")
    return f"---\n{fm_yaml}\n---\n{tr_body}\n", gate_passed, findings


def _format_run_status(stopped_early: bool, rate_limit_reason: str,
                       done: int, skipped: list[dict], attempts: int) -> str:
    """Render an early-stop / skipped-page summary for the weekly PR comment.

    Open findings already have a durable home (the PR comment via last-run-findings.md),
    but a run that stopped on the usage limit or skipped a page after repeated
    protocol errors did not — it was only ever visible in the run's stdout/stderr,
    which a cron/launchd job discards unless the operator captured it. Surfacing it
    here gives a maintainer the same durable, actionable record in-band."""
    if not stopped_early and not skipped:
        return ""
    out = ["### Run status", ""]
    if stopped_early:
        reason = f" ({rate_limit_reason})" if rate_limit_reason else ""
        out.append(f"- Stopped early on the subscription usage limit after {done} "
                   f"page(s){reason}. Remaining pages stay in the worklist and resume "
                   f"next run.")
    if skipped:
        out.append(f"- {len(skipped)} page(s) skipped after {attempts} protocol "
                   f"attempts (left in the worklist, retried next run):")
        for s in skipped:
            out.append(f"  - `{s['lang']}: {s['rel']}` — {s.get('error', '?')}")
    out.append("")
    return "\n".join(out)


def _distinct_orphan_pages(orphans: list[str], content_root: str) -> set[str]:
    """Collapse orphan translation FILES to distinct English PAGE paths.

    One deleted English page fans out to one orphan per language, so the
    mass-deletion floor must count pages, not files (`content/<lang>/<page>` →
    `<page>`). Pulled out of main() so the gating comparison is unit-testable."""
    return {os.path.relpath(p, content_root).split(os.sep, 1)[1] for p in orphans}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--path", help="translate only this exact source rel "
                                   "(e.g. docs/v1.5/getting-started/install-kubernetes.md)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = lib.load_config()
    glossary = lib.load_glossary()
    lang_by_code = {l["code"]: l for l in cfg["languages"]}
    if args.lang and args.lang not in lang_by_code:
        print(f"::error::unknown --lang '{args.lang}'; configured: "
              f"{', '.join(lang_by_code)}", file=sys.stderr)
        return 1
    # The English tree is the reference for BOTH the worklist and orphan
    # detection. If it is missing (broken checkout, sparse clone, renamed dir),
    # os.walk would silently yield nothing: the worklist would look "done" and
    # every stamped translation would look orphaned. Refuse instead.
    en_root = os.path.join(lib.REPO_ROOT, cfg["content_dir"], cfg["source_lang"])
    if not os.path.isdir(en_root) or not os.listdir(en_root):
        print(f"::error::English content root missing or empty: {en_root} — "
              f"refusing to run against a broken checkout", file=sys.stderr)
        return 1

    # Orphans first: a deleted English page must take its translations with it,
    # or they outlive the source forever (the worklist only iterates English
    # sources). Only `source_digest`-stamped (pipeline-managed) files qualify.
    orphans = [] if args.path else lib.find_orphan_translations(cfg, only_lang=args.lang)
    # Mass-deletion floor: English pages normally disappear one or two at a
    # time. A large batch means the English tree moved out from under us
    # (restructure, bad checkout), and deleting on that signal would commit a
    # massacre. The floor counts distinct English PAGES, not files — one
    # deleted page fans out to one orphan per language, and a floor on files
    # would trip on two legitimately deleted pages × six languages. Threshold
    # rather than never: a deliberate cleanup can delete the survivors by hand.
    content_root = os.path.join(lib.REPO_ROOT, cfg["content_dir"])
    orphan_pages = _distinct_orphan_pages(orphans, content_root)
    if len(orphan_pages) > ORPHAN_PAGE_FLOOR:
        print(f"::warning::{len(orphans)} orphaned translations of {len(orphan_pages)} "
              f"English pages found (> {ORPHAN_PAGE_FLOOR} pages) — refusing to "
              f"mass-delete. If this is a deliberate restructure, remove them "
              f"manually; first few: "
              + ", ".join(os.path.relpath(p, lib.REPO_ROOT) for p in orphans[:3]),
              file=sys.stderr)
        orphans = []
    for path in orphans:
        if args.dry_run:
            print(f"  [orphan ] would remove {os.path.relpath(path, lib.REPO_ROOT)}")
        else:
            os.unlink(path)
            print(f"  ✗ removed orphan {os.path.relpath(path, lib.REPO_ROOT)} "
                  f"(English source deleted)")

    items = lib.build_worklist(cfg, only_lang=args.lang)
    if args.path:
        items = [it for it in items if it.rel == args.path]
        if not items:
            print(f"::error::--path '{args.path}' matched nothing in the worklist "
                  f"(already translated, out of scope, or misspelled)", file=sys.stderr)
            return 1
    if args.limit:
        items = items[: args.limit]

    print(f"{len(items)} page(s) to process{' (dry run)' if args.dry_run else ''}")
    if args.dry_run:
        for it in items:
            print(f"  [{it.reason:7}] {it.lang}: {it.rel}")
        return 0
    if not items:
        # An empty worklist still has to clear any report a prior run left behind,
        # or run-daily.sh reposts stale findings stamped with today's date. This
        # is the pipeline's normal steady state once the backlog drains.
        if os.path.exists(REPORT_PATH):
            os.unlink(REPORT_PATH)
        return 0

    try:
        import claude_agent_sdk  # noqa: F401
    except ImportError:
        print("::error::claude-agent-sdk not installed (pip install claude-agent-sdk)", file=sys.stderr)
        return 1
    # Auth mode is a config decision, not a code one (see config.yaml `auth`).
    auth_mode = cfg.get("auth", "oauth-subscription")
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    if auth_mode == "oauth-subscription" and has_key:
        print("::error::auth=oauth-subscription but ANTHROPIC_API_KEY is set — it shadows the "
              "subscription and would bill metered API. `unset ANTHROPIC_API_KEY`, or set "
              "auth: api-key in config.yaml if metered billing is intended.", file=sys.stderr)
        return 1
    if auth_mode == "api-key" and not has_key:
        print("::error::auth=api-key but ANTHROPIC_API_KEY is not set.", file=sys.stderr)
        return 1
    # Under oauth-subscription, a missing CLAUDE_CODE_OAUTH_TOKEN is fine when the
    # `claude` CLI is logged in on this machine — the Agent SDK picks that up. The
    # token is only needed headless/CI; if neither exists the SDK raises.

    # A protocol error is usually the model non-deterministically dropping a
    # placeholder on a placeholder-dense page (a long docs page can have 60+
    # opaque §§ tokens). It tends to succeed on a fresh attempt, so retry within
    # the run rather than only next day — otherwise such a page can fail every
    # daily run forever, never publishing while re-spending quota each time.
    PROTOCOL_ATTEMPTS = 3

    clean = with_findings = failed = 0
    stopped_early = False
    rate_limit_reason = ""
    report: list[dict] = []
    skipped: list[dict] = []
    for it in items:
        try:
            for attempt in range(1, PROTOCOL_ATTEMPTS + 1):
                try:
                    result, gate_passed, findings = translate_page(
                        cfg, glossary, lang_by_code[it.lang], it.rel)
                    break
                except ProtocolError as exc:
                    if attempt == PROTOCOL_ATTEMPTS:
                        raise
                    print(f"  … retry {attempt}/{PROTOCOL_ATTEMPTS - 1} "
                          f"{it.lang}: {it.rel} — {exc}", file=sys.stderr)
        except RateLimited as exc:
            stopped_early = True
            rate_limit_reason = str(exc)
            print(f"\nsubscription usage limit reached after "
                  f"{clean + with_findings} page(s) — stopping cleanly, resume tomorrow. ({exc})")
            break
        except ProtocolError as exc:
            # Still malformed after every attempt: skip it. It stays in the
            # worklist (nothing written, no digest stamped) and is retried next
            # run — but the daily run is not stalled on it.
            failed += 1
            skipped.append({"lang": it.lang, "rel": it.rel, "error": str(exc)})
            print(f"::warning::skipped {it.lang}: {it.rel} after {PROTOCOL_ATTEMPTS} "
                  f"attempts — {exc}", file=sys.stderr)
            continue
        dest = lib.target_path(cfg, it.lang, it.rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(result)
        if gate_passed:
            clean += 1
            print(f"  ✓ gate passed  {it.lang}: {it.rel}")
        else:
            with_findings += 1
            print(f"  ! findings open {it.lang}: {it.rel} (stamped -with-findings)")
            for f in findings:
                print(f"      [{f.get('severity', '?')}/{f.get('from', '?')}] "
                      f"{f.get('issue', f)}")
            report.append({"lang": it.lang, "rel": it.rel, "findings": findings})

    # The report is the pipeline's only durable, maintainer-facing channel
    # (run-daily.sh posts it as a PR comment). It carries open findings AND an
    # early-stop / skipped-page summary — dropping either on the floor leaves a
    # `-with-findings` stamp or a stalled page unactionable.
    status_md = _format_run_status(stopped_early, rate_limit_reason,
                                   clean + with_findings, skipped, PROTOCOL_ATTEMPTS)
    sections = [s for s in (status_md, _format_report(report) if report else "") if s]
    if sections:
        with open(REPORT_PATH, "w", encoding="utf-8") as fh:
            fh.write("\n".join(sections))
        print(f"\nrun report written to {REPORT_PATH}")
    elif os.path.exists(REPORT_PATH):
        os.unlink(REPORT_PATH)  # don't let a previous run's report go stale

    print(f"\nthis run: {clean} clean, {with_findings} written with open findings, "
          f"{failed} skipped on error")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
