# Cozystack website translation pipeline

Automated, in-tree localization for cozystack.io. Detects English pages that are
new or changed, translates them into every configured language with Claude, and
publishes under a **publish-then-review** model — machine translations ship
immediately; native owners ratify asynchronously.

Lives in the website repo (vendor-neutral, community-inspectable) alongside the
existing `hack/check-i18n.sh` CI guard.

## How it works

```
content/en/**  ──▶  worklist.py     (diff via source_digest: missing | stale)
                        │
                        ▼
                    translate.py     (Claude Opus + glossary + style guide
                        │             + Ahrefs keyword map for SEO front matter)
                        ▼
                content/<lang>/**    (source_digest stamped)
                        │
                    check-i18n.sh    (freshness + i18n key parity)
                        │
                    i18n-translate.yml  (PR → auto-merge; content/<lang> is
                                         CODEOWNERS-exempt)
```

Freshness is a `source_digest: "sha256:<hex>"` front-matter field on every
translated page — the sha256 of its English source. When the English page
changes, the digest no longer matches and the page is re-translated. This is the
same convention `hack/check-i18n.sh` enforces, so the pipeline and the CI lint
agree by construction.

## Files

| Path | Purpose |
|------|---------|
| `config.yaml` | languages, model routing, scope globs, blog cutoff, publish mode, Ahrefs |
| `glossary.yaml` | do-not-translate terms (brands/CLI/APIs) + preferred per-language terms |
| `prompts/translate.md` | translation system prompt (glossary + style + output protocol) |
| `style-guides/<lang>.md` | per-language tone/register conventions |
| `keyword-maps/<lang>.yaml` | Ahrefs-derived SEO keyword targets (generated) |
| `lib.py` | shared helpers (config, file discovery, digest, front matter, protect/restore) |
| `worklist.py` | diff detector — what needs translation |
| `translate.py` | the translator (Claude API) |
| `ahrefs_keywords.py` | regenerate SEO keyword maps from Ahrefs |

## Running locally

```bash
pip install anthropic pyyaml
export ANTHROPIC_API_KEY=...        # required for translate.py
export AHREFS_API_KEY=...           # optional; without it, SEO is translated literally

python3 hack/i18n/worklist.py                 # what would change
python3 hack/i18n/translate.py --dry-run      # plan, no API calls
python3 hack/i18n/translate.py --lang ru --limit 5   # translate a few RU pages
./hack/check-i18n.sh                           # verify freshness + key parity
```

## Scope

- **Docs:** latest version only (`docs/v1.4/**`); older versions stay English (they are `noindex`).
- **Blog:** posts newer than `blog_since` in `config.yaml` (rolling window; the full archive is out of scope by default).
- **Never:** `docs/next/**`, `**/_include/**`.
- Code blocks, shortcodes, HTML comments, inline code, URLs, CLI, YAML keys, and brand names are preserved structurally or via the glossary.

## Governance

- `content/<lang>/` is exempt from `.github/CODEOWNERS`, so the pipeline auto-merges translations. Code, layouts, config, English source, and this pipeline stay maintainer-owned.
- If branch protection requires approvals beyond CODEOWNERS, auto-merge falls back to leaving the PR open for a maintainer (the workflow logs a warning). Set `publish_mode: pr_only` in `config.yaml` to always require a human merge.

## Secrets (GitHub Actions)

- `ANTHROPIC_API_KEY` — required.
- `AHREFS_API_KEY` — optional (SEO keyword localization + monitoring).
