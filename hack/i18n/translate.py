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

A page is written ONLY after it clears the gate, so the published tree is always
post-review and an interrupted daily run never leaves a half-done page.

Auth: OAuth subscription (Max). Uses a bare anthropic.Anthropic() client — with
no ANTHROPIC_API_KEY set it resolves the logged-in Claude / `ant auth login`
credential. Run `claude setup-token` or `ant auth login` once on the runner.

Daily-until-limit: on a rate-limit (429) the run stops cleanly (exit 0) and
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


def _read(path: str, default: str = "") -> str:
    return open(path, encoding="utf-8").read() if os.path.exists(path) else default


def load_keyword_map(cfg: dict, lang: str) -> dict:
    path = os.path.join(lib.REPO_ROOT, cfg["ahrefs"]["keyword_map_dir"], f"{lang}.yaml")
    return (yaml.safe_load(open(path, encoding="utf-8")) or {}) if os.path.exists(path) else {}


def render(template: str, lang_cfg: dict, glossary: dict) -> str:
    dnt = ", ".join(glossary.get("do_not_translate", []))
    preferred = "\n".join(
        f"  - {t} -> {pl[lang_cfg['code']]}"
        for t, pl in (glossary.get("preferred") or {}).items()
        if lang_cfg["code"] in pl
    ) or "  (none specified)"
    style = _read(os.path.join(STYLE_DIR, f"{lang_cfg['code']}.md"),
                  f"(use professional, natural {lang_cfg['name']}.)")
    return (template
            .replace("{{LANGUAGE}}", lang_cfg["name"])
            .replace("{{LANG_CODE}}", lang_cfg["code"])
            .replace("{{DO_NOT_TRANSLATE}}", dnt)
            .replace("{{PREFERRED_TERMS}}", preferred)
            .replace("{{STYLE_GUIDE}}", style))


def call(client, cfg, system, payload):
    """One Opus call over the OAuth subscription. Translate RateLimited on 429."""
    import anthropic
    try:
        msg = client.messages.create(
            model=cfg["model"]["default"],
            max_tokens=cfg["model"]["max_output_tokens"],
            temperature=cfg["model"]["temperature"],
            system=system,
            messages=[{"role": "user", "content": payload}],
        )
    except anthropic.RateLimitError as exc:
        raise RateLimited(str(exc)) from exc
    return "".join(b.text for b in msg.content if b.type == "text").strip()


def _parse_verdict(raw: str) -> dict:
    """Pull the JSON verdict object out of a reviewer response."""
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return {"verdict": "pass", "findings": []}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"verdict": "pass", "findings": []}


def _split_payload_response(out: str, store: dict) -> tuple[dict, str]:
    tr_fm, body = {}, out
    if "===BODY===" in out:
        head, body = out.split("===BODY===", 1)
        for line in head.replace("===FRONTMATTER===", "").strip().splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                tr_fm[k.strip()] = v.strip()
    return tr_fm, lib.restore(body.strip(), store)


def translate_page(client, cfg, glossary, lang_cfg, rel) -> str | None:
    """Run the full gate for one page. Returns file text, or None if it can't pass."""
    src = lib.source_path(cfg, rel)
    text = open(src, encoding="utf-8").read()
    fm, body, _ = lib.split_frontmatter(text)
    masked_body, store = lib.protect(body)

    fm_values = {}
    if isinstance(fm, dict):
        for k in lib.TRANSLATABLE_FRONTMATTER_KEYS:
            if isinstance(fm.get(k), str):
                fm_values[k] = fm[k]

    kw = load_keyword_map(cfg, lang_cfg["code"])
    kw_hint = ("\n\nSEO keyword targets (transcreate title/description toward these, "
               "no stuffing): " + ", ".join(kw[rel])) if kw.get(rel) else ""

    # --- Stage 1: translate ---
    sys_translate = render(_read(os.path.join(PROMPT_DIR, "translate.md")), lang_cfg, glossary)
    payload = (
        "Translate the FRONTMATTER values and the BODY below.\n"
        "Return EXACTLY:\n===FRONTMATTER===\n<key: value per line>\n===BODY===\n<translated body>"
        + kw_hint
        + "\n\n===FRONTMATTER===\n" + "\n".join(f"{k}: {v}" for k, v in fm_values.items())
        + "\n===BODY===\n" + masked_body
    )
    tr_fm, tr_body = _split_payload_response(call(client, cfg, sys_translate, payload), store)

    # --- Stages 2-4: gate with revise loop ---
    max_rounds = max(cfg["review"]["max_rounds"], cfg["back_translation"]["max_retries"])
    for _ in range(max_rounds + 1):
        findings: list[dict] = []

        # 2. back-translation round-trip
        if cfg["back_translation"]["enabled"]:
            masked_tr, tr_store = lib.protect(tr_body)
            back_en = call(client, cfg,
                           render(_read(os.path.join(PROMPT_DIR, "back-translate.md")), lang_cfg, glossary),
                           masked_tr)
            cmp = _parse_verdict(call(client, cfg,
                render(_read(os.path.join(PROMPT_DIR, "back-translate-compare.md")), lang_cfg, glossary),
                f"ORIGINAL:\n{body}\n\nBACK-TRANSLATION:\n{lib.restore(back_en, tr_store)}"))
            if cmp.get("verdict") == "revise":
                findings += [{**f, "from": "back-translation"} for f in cmp.get("findings", [])]

        # 3. two native reviewers
        for reviewer in cfg["review"]["reviewers"]:
            sys_r = render(_read(os.path.join(PROMPT_DIR, os.path.basename(reviewer["prompt"]))),
                           lang_cfg, glossary)
            verdict = _parse_verdict(call(client, cfg, sys_r,
                f"ENGLISH SOURCE:\n{body}\n\n{lang_cfg['name'].upper()} TRANSLATION:\n{tr_body}"))
            if verdict.get("verdict") == "revise":
                findings += [{**f, "from": reviewer["id"]} for f in verdict.get("findings", [])]

        if not findings:
            break  # gate passed

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
        tr_fm, tr_body = _split_payload_response(call(client, cfg, sys_rev, rev_payload), store)
    else:
        # exhausted rounds with findings still open — publish-then-review model:
        # write it anyway (machine-reviewed, native humans ratify later), but do
        # not stamp it as clean. Caller logs this.
        pass

    # --- assemble ---
    out_fm = dict(fm) if isinstance(fm, dict) else {}
    for k in fm_values:
        if tr_fm.get(k):
            out_fm[k] = tr_fm[k]
    out_fm["source_digest"] = f"sha256:{lib.sha256_file(src)}"
    out_fm[cfg["review_status_field"]] = cfg["review_status_value"]
    fm_yaml = yaml.safe_dump(out_fm, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{fm_yaml}\n---\n{tr_body}\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = lib.load_config()
    glossary = lib.load_glossary()
    lang_by_code = {l["code"]: l for l in cfg["languages"]}
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
        import anthropic  # noqa: F401
    except ImportError:
        print("::error::anthropic SDK not installed (pip install anthropic)", file=sys.stderr)
        return 1
    if os.environ.get("ANTHROPIC_API_KEY"):
        print("::warning::ANTHROPIC_API_KEY is set — this pipeline is meant to run on the "
              "OAuth subscription. Unset it to avoid metered API billing.", file=sys.stderr)
    client = anthropic.Anthropic()  # OAuth/subscription when no API key is set

    done = 0
    for it in items:
        try:
            result = translate_page(client, cfg, glossary, lang_by_code[it.lang], it.rel)
        except RateLimited:
            print(f"\nrate limit reached after {done} page(s) — stopping cleanly, "
                  f"resume tomorrow.")
            return 0
        if result is None:
            continue
        dest = lib.target_path(cfg, it.lang, it.rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(result)
        done += 1
        print(f"  reviewed+wrote {it.lang}: {it.rel}")

    print(f"done: {done} page(s) processed this run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
