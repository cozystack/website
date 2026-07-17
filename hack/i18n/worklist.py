#!/usr/bin/env python3
"""Print the translation worklist: pages that are missing or stale per language.

Usage:
  worklist.py                 # all languages, human-readable summary
  worklist.py --json          # machine-readable
  worklist.py --lang ru       # restrict to one language
  worklist.py --limit 3       # only the first N items (mirrors translate.py)

"Missing" = no translated file exists. "Stale" = the translated file's
source_digest no longer matches the current sha256 of its English source.
Exits 0 with work to do or none (an empty list means everything is up to date);
exits 1 only on a bad argument.

The flags mirror translate.py's on purpose: run-daily.sh forwards the same "$@"
to both, so this script previews exactly what that run will translate.
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
    ap.add_argument("--limit", type=int, help="only the first N items")
    ap.add_argument("--dry-run", action="store_true",
                    help="accepted for parity with translate.py; this script never writes")
    args = ap.parse_args()

    cfg = lib.load_config()
    codes = [l["code"] for l in cfg["languages"]]
    if args.lang and args.lang not in codes:
        # Without this, a typo filters everything out and prints "all languages
        # up to date" — the same reassuring lie as an empty worklist.
        print(f"::error::unknown --lang '{args.lang}'; enabled: {', '.join(codes)}",
              file=sys.stderr)
        return 1
    items = lib.build_worklist(cfg, only_lang=args.lang)
    if args.limit:
        items = items[: args.limit]

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
