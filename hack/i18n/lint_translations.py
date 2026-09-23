#!/usr/bin/env python3
"""Lint already-published translations for per-language typography.

WHY: `check-i18n.sh` guards i18n key parity and translation freshness, and the
pipeline's gate checks a page at the moment it is generated. Neither looks at a
page again afterwards — so a hand edit (or a page translated before a style rule
existed) can sit in the tree indefinitely with English quotation marks in Russian
prose or half-width punctuation in Chinese. The style guides state these rules;
this makes them enforceable on every PR.

Findings are advisory by default (exit 0) because typography rules are heuristic
and the tree has history. Pass --strict to fail the build instead, once a
language's backlog is clean.

Usage:
    python3 hack/i18n/lint_translations.py                 # all configured languages
    python3 hack/i18n/lint_translations.py --lang ru       # one language
    python3 hack/i18n/lint_translations.py --strict        # exit 1 on any finding
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import lib


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", help="only this language code")
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero when findings exist (default: advisory)")
    args = ap.parse_args()

    cfg = lib.load_config()
    langs = [l["code"] for l in cfg["languages"] if args.lang in (None, l["code"])]
    if args.lang and not langs:
        print(f"::error::unknown --lang '{args.lang}'", file=sys.stderr)
        return 2

    total = 0
    for lang in langs:
        root = os.path.join(lib.REPO_ROOT, cfg["content_dir"], lang)
        if not os.path.isdir(root):
            continue
        for dirpath, _dirs, files in os.walk(root):
            for name in sorted(files):
                if not name.endswith((".md", ".html")):
                    continue
                path = os.path.join(dirpath, name)
                with open(path, encoding="utf-8") as fh:
                    _fm, body, _raw = lib.split_frontmatter(fh.read())
                findings = lib.check_typography(body, lang)
                if findings:
                    rel = os.path.relpath(path, lib.REPO_ROOT)
                    print(f"{rel}")
                    for f in findings:
                        print(f"  - {f['issue']}")
                    total += len(findings)

    if total:
        print(f"\n{total} typography finding(s). These are the rules the per-language "
              f"style guides state; fix them or refine the rule in lib._TYPO_RULES.")
    else:
        print("no typography findings")
    return 1 if (total and args.strict) else 0


if __name__ == "__main__":
    raise SystemExit(main())
