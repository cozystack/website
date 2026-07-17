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


def _split_payload_response(out: str, store: dict) -> tuple[dict, str]:
    """Parse a translate/revise reply. Raises rather than treating a preamble
    ("Here's the translation:") as the page body, and verifies every protected
    placeholder survived — a dropped §§FENCE_n§§ would silently delete a code
    block from the page."""
    if "===BODY===" not in out:
        raise ProtocolError(f"no ===BODY=== marker in reply: {out.strip()[:200]}")
    head, body = out.split("===BODY===", 1)
    tr_fm = {}
    for line in head.replace("===FRONTMATTER===", "").strip().splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            tr_fm[k.strip()] = v.strip()
    body = body.strip()
    missing = [tok for tok in store if tok not in body]
    if missing:
        raise ProtocolError(f"{len(missing)} protected placeholder(s) lost by the model "
                            f"(e.g. {missing[0]}) — refusing to write a page with dropped code")
    return tr_fm, lib.restore(body, store)


def translate_page(cfg, glossary, lang_cfg, rel) -> tuple[str, bool]:
    """Run the full gate for one page.

    Returns (file_text, gate_passed). gate_passed is False when the revise loop
    ran out of rounds with findings still open — the page is still written
    (publish-then-review), but stamped honestly so it is distinguishable from a
    page that actually cleared the gate.
    """
    src = lib.source_path(cfg, rel)
    text = open(src, encoding="utf-8").read()
    fm, body, _ = lib.split_frontmatter(text)
    if fm is None:
        # Unparseable / absent YAML front matter: writing the page would silently
        # drop slug/date/aliases/images. Refuse instead.
        raise ProtocolError(f"{rel}: could not parse YAML front matter in the English source")
    masked_body, store = lib.protect(body)

    fm_values = {}
    for k in lib.TRANSLATABLE_FRONTMATTER_KEYS:
        if isinstance(fm.get(k), str):
            fm_values[k] = fm[k]

    # --- Stage 1: translate ---
    sys_translate = render(_read(os.path.join(PROMPT_DIR, "translate.md")), lang_cfg, glossary)
    payload = (
        "Translate the FRONTMATTER values and the BODY below.\n"
        "Return EXACTLY:\n===FRONTMATTER===\n<key: value per line>\n===BODY===\n<translated body>"
        + "\n\n===FRONTMATTER===\n" + "\n".join(f"{k}: {v}" for k, v in fm_values.items())
        + "\n===BODY===\n" + masked_body
    )
    tr_fm, tr_body = _split_payload_response(call(cfg, sys_translate, payload), store)

    # --- Stages 2-4: gate with revise loop ---
    max_rounds = max(cfg["review"]["max_rounds"], cfg["back_translation"]["max_retries"])
    gate_passed = False
    for _ in range(max_rounds + 1):
        findings: list[dict] = []

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
                findings += [{**f, "from": "back-translation"} for f in cmp["findings"]]

        # 3. two native reviewers
        for reviewer in cfg["review"]["reviewers"]:
            sys_r = render(_read(os.path.join(PROMPT_DIR, os.path.basename(reviewer["prompt"]))),
                           lang_cfg, glossary)
            verdict = _parse_verdict(call(cfg, sys_r,
                f"ENGLISH SOURCE:\n{body}\n\n{lang_cfg['name'].upper()} TRANSLATION:\n{tr_body}"),
                reviewer["id"])
            if verdict["verdict"] == "revise":
                findings += [{**f, "from": reviewer["id"]} for f in verdict["findings"]]

        if not findings:
            gate_passed = True
            break

        # 4. revise addressing all findings, then re-check
        masked_body2, store = lib.protect(tr_body)
        sys_rev = render(_read(os.path.join(PROMPT_DIR, "revise.md")), lang_cfg, glossary)
        rev_payload = (
            "ENGLISH SOURCE:\n" + body
            + "\n\nCURRENT TRANSLATION:\n===FRONTMATTER===\n"
            + "\n".join(f"{k}: {v}" for k, v in tr_fm.items())
            + "\n===BODY===\n" + masked_body2
            + "\n\nFINDINGS:\n" + json.dumps(findings, ensure_ascii=False, indent=2)
        )
        tr_fm, tr_body = _split_payload_response(call(cfg, sys_rev, rev_payload), store)

    # --- assemble ---
    out_fm = dict(fm)
    for k in fm_values:
        if tr_fm.get(k):
            out_fm[k] = tr_fm[k]
    out_fm["source_digest"] = f"sha256:{lib.sha256_file(src)}"
    # Stamp honestly: a page that ran out of revise rounds with findings still
    # open is NOT the same as one that cleared the gate.
    out_fm[cfg["review_status_field"]] = (
        cfg["review_status_value"] if gate_passed else f"{cfg['review_status_value']}-with-findings")
    fm_yaml = yaml.safe_dump(out_fm, allow_unicode=True, sort_keys=False,
                             default_flow_style=False, width=10 ** 9).strip()
    return f"---\n{fm_yaml}\n---\n{tr_body}\n", gate_passed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = lib.load_config()
    glossary = lib.load_glossary()
    lang_by_code = {l["code"]: l for l in cfg["languages"]}
    if args.lang and args.lang not in lang_by_code:
        print(f"::error::unknown --lang '{args.lang}'; configured: "
              f"{', '.join(lang_by_code)}", file=sys.stderr)
        return 1
    items = lib.build_worklist(cfg, only_lang=args.lang)
    if args.limit:
        items = items[: args.limit]

    print(f"{len(items)} page(s) to process{' (dry run)' if args.dry_run else ''}")
    if args.dry_run:
        for it in items:
            print(f"  [{it.reason:7}] {it.lang}: {it.rel}")
        return 0
    if not items:
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

    clean = with_findings = failed = 0
    for it in items:
        try:
            result, gate_passed = translate_page(cfg, glossary, lang_by_code[it.lang], it.rel)
        except RateLimited as exc:
            print(f"\nsubscription usage limit reached after "
                  f"{clean + with_findings} page(s) — stopping cleanly, resume tomorrow. ({exc})")
            break
        except (ProtocolError, FileNotFoundError) as exc:
            # One bad page must not stall the run; it stays in the worklist and is
            # retried tomorrow (nothing was written, so no digest was stamped).
            failed += 1
            print(f"::warning::skipped {it.lang}: {it.rel} — {exc}", file=sys.stderr)
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

    print(f"\nthis run: {clean} clean, {with_findings} written with open findings, "
          f"{failed} skipped on error")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
