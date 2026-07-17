#!/usr/bin/env python3
"""Translate Cozystack website pages into the configured languages.

For each page that is missing or stale (see worklist.py) this:
  1. splits YAML front matter from the body;
  2. protects code fences, shortcodes, HTML comments and inline code;
  3. asks Claude (Opus) to translate the body and a whitelist of front-matter
     values, guided by the glossary, the per-language style guide, and — when
     available — the Ahrefs keyword map for SEO front matter;
  4. restores protected spans, stamps `source_digest`, and writes the file.

Requires ANTHROPIC_API_KEY. Idempotent: rerunning only touches missing/stale
pages. `--dry-run` prints the plan without calling the API or writing files.

Usage:
  translate.py [--lang ru] [--limit N] [--dry-run]
"""

from __future__ import annotations

import argparse
import os
import sys

import yaml

import lib

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")
STYLE_DIR = os.path.join(os.path.dirname(__file__), "style-guides")


def _read(path: str, default: str = "") -> str:
    return open(path, encoding="utf-8").read() if os.path.exists(path) else default


def load_keyword_map(cfg: dict, lang: str) -> dict:
    path = os.path.join(lib.REPO_ROOT, cfg["ahrefs"]["keyword_map_dir"], f"{lang}.yaml")
    if os.path.exists(path):
        return yaml.safe_load(open(path, encoding="utf-8")) or {}
    return {}


def build_system_prompt(cfg: dict, lang_cfg: dict, glossary: dict) -> str:
    base = _read(os.path.join(PROMPT_DIR, "translate.md"))
    style = _read(os.path.join(STYLE_DIR, f"{lang_cfg['code']}.md"),
                  f"(no style guide for {lang_cfg['code']} yet — use professional, natural {lang_cfg['name']}.)")
    dnt = ", ".join(glossary.get("do_not_translate", []))
    preferred_lines = []
    for term, per_lang in (glossary.get("preferred") or {}).items():
        if lang_cfg["code"] in per_lang:
            preferred_lines.append(f"  - {term} → {per_lang[lang_cfg['code']]}")
    preferred = "\n".join(preferred_lines) or "  (none specified)"
    return (
        base
        .replace("{{LANGUAGE}}", lang_cfg["name"])
        .replace("{{LANG_CODE}}", lang_cfg["code"])
        .replace("{{DO_NOT_TRANSLATE}}", dnt)
        .replace("{{PREFERRED_TERMS}}", preferred)
        .replace("{{STYLE_GUIDE}}", style)
    )


def translate_text(client, model: str, cfg: dict, system: str, payload: str) -> str:
    msg = client.messages.create(
        model=model,
        max_tokens=cfg["model"]["max_output_tokens"],
        temperature=cfg["model"]["temperature"],
        system=system,
        messages=[{"role": "user", "content": payload}],
    )
    return "".join(block.text for block in msg.content if block.type == "text").strip()


def translate_page(client, cfg, glossary, lang_cfg, rel) -> str:
    src = lib.source_path(cfg, rel)
    text = open(src, encoding="utf-8").read()
    fm, body, raw_fm = lib.split_frontmatter(text)

    masked_body, store = lib.protect(body)
    model = cfg["model"]["hero"] if lib.is_hero(cfg, rel) else cfg["model"]["default"]
    system = build_system_prompt(cfg, lang_cfg, glossary)

    # Front-matter values to transcreate (SEO-aware), plus the body, in one call
    # using a simple delimiter protocol the prompt describes.
    fm_values = {}
    if isinstance(fm, dict):
        for k in lib.TRANSLATABLE_FRONTMATTER_KEYS:
            if k in fm and isinstance(fm[k], str):
                fm_values[k] = fm[k]

    kw = load_keyword_map(cfg, lang_cfg["code"])
    kw_hint = ""
    if kw.get(rel):
        kw_hint = ("\n\nSEO keyword targets for this page (transcreate title/"
                   "description toward these, do not stuff): "
                   + ", ".join(kw[rel]))

    payload = (
        "Translate the FRONTMATTER values and the BODY below.\n"
        "Return EXACTLY this structure:\n"
        "===FRONTMATTER===\n<one `key: value` per line for the given keys>\n"
        "===BODY===\n<translated body>\n"
        + kw_hint
        + "\n\n===FRONTMATTER===\n"
        + "\n".join(f"{k}: {v}" for k, v in fm_values.items())
        + "\n===BODY===\n"
        + masked_body
    )

    out = translate_text(client, model, cfg, system, payload)

    # Parse the model's response back into front matter + body.
    tr_fm, tr_body = {}, out
    if "===BODY===" in out:
        head, tr_body = out.split("===BODY===", 1)
        for line in head.replace("===FRONTMATTER===", "").strip().splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                tr_fm[k.strip()] = v.strip()
    tr_body = lib.restore(tr_body.strip(), store)

    # Reassemble front matter: preserve everything, override translated keys,
    # stamp source_digest.
    out_fm = dict(fm) if isinstance(fm, dict) else {}
    for k in fm_values:
        if tr_fm.get(k):
            out_fm[k] = tr_fm[k]
    out_fm["source_digest"] = f"sha256:{lib.sha256_file(src)}"

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

    print(f"{len(items)} page(s) to translate"
          f"{' (dry run)' if args.dry_run else ''}")
    if args.dry_run:
        for it in items:
            print(f"  [{it.reason:7}] {it.lang}: {it.rel}")
        return 0

    if not items:
        return 0

    try:
        import anthropic
    except ImportError:
        print("::error::anthropic SDK not installed (pip install anthropic)", file=sys.stderr)
        return 1
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("::error::ANTHROPIC_API_KEY not set", file=sys.stderr)
        return 1
    client = anthropic.Anthropic()

    failures = 0
    for it in items:
        try:
            result = translate_page(client, cfg, glossary, lang_by_code[it.lang], it.rel)
            dest = lib.target_path(cfg, it.lang, it.rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "w", encoding="utf-8") as fh:
                fh.write(result)
            print(f"  translated {it.lang}: {it.rel}")
        except Exception as exc:  # keep going; one bad page must not stall the run
            failures += 1
            print(f"::warning::failed {it.lang}: {it.rel} — {exc}", file=sys.stderr)

    if failures:
        print(f"::warning::{failures} page(s) failed", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
