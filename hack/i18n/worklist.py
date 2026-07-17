#!/usr/bin/env python3
"""Print the translation worklist: pages that are missing or stale per language.

Usage:
  worklist.py                 # all languages, human-readable summary
  worklist.py --json          # machine-readable (for the CI matrix)
  worklist.py --lang ru       # restrict to one language

"Missing" = no translated file exists. "Stale" = the translated file's
source_digest no longer matches the current sha256 of its English source.
Exit code is always 0; an empty list simply means everything is up to date.
"""

from __future__ import annotations

import argparse
import json
import sys

import lib


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="emit JSON")
    ap.add_argument("--lang", help="restrict to one language code")
    args = ap.parse_args()

    cfg = lib.load_config()
    items = lib.build_worklist(cfg, only_lang=args.lang)

    if args.json:
        json.dump(
            [{"lang": i.lang, "rel": i.rel, "reason": i.reason} for i in items],
            sys.stdout,
        )
        sys.stdout.write("\n")
        return 0

    if not items:
        print("translation worklist: empty — all languages up to date")
        return 0

    by_lang: dict[str, list[lib.WorkItem]] = {}
    for i in items:
        by_lang.setdefault(i.lang, []).append(i)
    total = len(items)
    print(f"translation worklist: {total} page(s) need work\n")
    for lang in sorted(by_lang):
        rows = by_lang[lang]
        missing = sum(1 for r in rows if r.reason == "missing")
        stale = sum(1 for r in rows if r.reason == "stale")
        print(f"  {lang}: {len(rows)} ({missing} missing, {stale} stale)")
        for r in rows:
            print(f"    [{r.reason:7}] {r.rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
