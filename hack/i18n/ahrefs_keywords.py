#!/usr/bin/env python3
"""Generate per-language SEO keyword maps from Ahrefs, for SEO transcreation.

For a curated set of seed topics (derived from the English pages), query the
Ahrefs Keywords Explorer for the target country/language and record the highest-
value localized keywords. translate.py injects these into the front-matter
transcreation prompt so localized title/description target real search demand
instead of a literal translation.

Requires AHREFS_API_KEY. Writes hack/i18n/keyword-maps/<lang>.yaml, keyed by the
page's relative path. Degrades gracefully: without a key it writes/keeps empty
maps and the pipeline falls back to literal SEO translation.

Usage:
  ahrefs_keywords.py [--lang es] [--dry-run]

NOTE: Ahrefs API v3 endpoint/field names should be confirmed against the current
docs when the subscription is active; the request shape is isolated in
`_ahrefs_keywords()` for easy adjustment.
"""

from __future__ import annotations

import argparse
import os
import sys

import yaml

import lib

AHREFS_API = "https://api.ahrefs.com/v3/keywords-explorer/overview"

# Seed topics per page (relative path -> English seed phrases). Kept small and
# explicit rather than auto-derived, so keyword targeting is deliberate. Extend
# as more pages are prioritized for SEO.
SEED_TOPICS: dict[str, list[str]] = {
    "_index.html": ["kubernetes platform", "private cloud", "bare metal kubernetes"],
    "docs/v1.4/getting-started/_index.md": ["install kubernetes", "kubernetes getting started"],
    "support.md": ["kubernetes support", "enterprise kubernetes support"],
}


def _ahrefs_keywords(seeds: list[str], country: str, api_key: str) -> list[str]:
    """Return localized keyword suggestions for seeds in a target country."""
    import urllib.parse
    import urllib.request

    found: list[str] = []
    for seed in seeds:
        params = urllib.parse.urlencode({
            "keywords": seed,
            "country": country,
            "select": "keyword,volume,difficulty",
        })
        req = urllib.request.Request(
            f"{AHREFS_API}?{params}",
            headers={"Authorization": f"Bearer {api_key}",
                     "Accept": "application/json"},
        )
        try:
            import json
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.load(resp)
            for row in data.get("keywords", data.get("data", [])):
                kw = row.get("keyword")
                if kw:
                    found.append(kw)
        except Exception as exc:  # never hard-fail keyword research
            print(f"::warning::ahrefs lookup failed for '{seed}' ({country}): {exc}",
                  file=sys.stderr)
    # de-dup, keep order, cap
    seen, out = set(), []
    for kw in found:
        if kw not in seen:
            seen.add(kw)
            out.append(kw)
    return out[:10]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = lib.load_config()
    if not cfg["ahrefs"].get("enabled"):
        print("ahrefs disabled in config; nothing to do")
        return 0

    api_key = os.environ.get("AHREFS_API_KEY")
    country_by_lang = cfg["ahrefs"]["country_by_lang"]
    out_dir = os.path.join(lib.REPO_ROOT, cfg["ahrefs"]["keyword_map_dir"])
    os.makedirs(out_dir, exist_ok=True)

    langs = [l for l in cfg["languages"] if args.lang in (None, l["code"])]
    for lang_cfg in langs:
        code = lang_cfg["code"]
        country = country_by_lang.get(code, "us")
        kmap: dict[str, list[str]] = {}
        for rel, seeds in SEED_TOPICS.items():
            if args.dry_run or not api_key:
                kmap[rel] = []  # placeholder; literal SEO fallback in translate.py
            else:
                kmap[rel] = _ahrefs_keywords(seeds, country, api_key)
        dest = os.path.join(out_dir, f"{code}.yaml")
        with open(dest, "w", encoding="utf-8") as fh:
            yaml.safe_dump(kmap, fh, allow_unicode=True, sort_keys=True)
        note = "placeholder" if (args.dry_run or not api_key) else "from Ahrefs"
        print(f"  wrote {dest} ({note})")

    if not api_key and not args.dry_run:
        print("::warning::AHREFS_API_KEY not set — wrote empty maps; "
              "SEO front matter will be translated literally", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
