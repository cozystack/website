# Cozystack website translation pipeline

Automated, in-tree localization for cozystack.io with a machine review gate.
Detects English pages that are new or changed and, for each one, runs a
translate → verify → review → revise loop before publishing. Runs daily on the
maintainer's Claude subscription until the usage limit is hit.

Lives in the website repo (vendor-neutral, community-inspectable) alongside the
existing `hack/check-i18n.sh` CI guard.

## Per-page pipeline (every page, all languages)

```
content/en/**  ──▶ worklist.py        (missing | stale, via source_digest)
                       │
                       ▼
                   translate           (Opus + glossary + style guide)
                       │
                       ▼
                back-translate ─▶ compare vs original   (meaning-drift check)
                       │
                       ▼
        review ×2 (native speakers of the target language)
          • technical editor    → fluency / register / terminology
          • Cozystack maintainer → technical correctness vs source
                       │
                 findings? ──yes──▶ revise ──▶ (re-check, ≤ max_rounds)
                       │ no
                       ▼
             write content/<lang>/**   (source_digest + translation_review stamp)
                       │
                   check-i18n.sh  →  daily PR  →  auto-merge (CODEOWNERS-exempt)
```

A page is written **only after it clears the gate**, so the published tree is
always post-review and an interrupted daily run never leaves a half-done page.
`translation_review: auto-reviewed` marks machine-gated pages; native human
owners flip it to `ratified` after their pass.

## Auth — Max subscription via the Claude Agent SDK

The pipeline runs on the maintainer's Claude subscription (Max), so there is no
per-token API billing. Note: the **base `anthropic` SDK cannot use a
subscription** (metered API only), so `translate.py` calls the **Claude Agent
SDK** (`claude-agent-sdk`), which reads `CLAUDE_CODE_OAUTH_TOKEN`. Set it up once
on the machine that runs the daily job:

```bash
npm install -g @anthropic-ai/claude-code   # if the `claude` CLI isn't installed
claude setup-token                          # prints sk-ant-oat01-...  (~1-year token)
export CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-...
unset ANTHROPIC_API_KEY                      # it would shadow the subscription and bill metered API
```

The run hard-fails if `ANTHROPIC_API_KEY` is set. Cost is not the constraint —
the daily subscription usage limit is; the run stops cleanly at the limit and
resumes the next day.

Verify the active credential before running:

```bash
[ -n "$ANTHROPIC_API_KEY" ] && echo "metered API (wrong)" || \
{ [ -n "$CLAUDE_CODE_OAUTH_TOKEN" ] && echo "subscription (ok)" || echo "no credential"; }
```

## Daily run

```bash
hack/i18n/run-daily.sh            # all languages, until the limit
hack/i18n/run-daily.sh --lang ru  # one language
```

Schedule it once a day (cron/launchd). Each run translates and review-gates as
many pages as the limit allows, stops cleanly on a 429, commits the day's
output to a dated branch, and opens/auto-merges one PR. Over time it clears the
backlog, then just keeps translations fresh against the English source.

Manual/dry inspection:

```bash
python3 hack/i18n/worklist.py            # what needs work
python3 hack/i18n/translate.py --dry-run # plan, no model calls
./hack/check-i18n.sh                      # freshness + i18n key parity
```

## Files

| Path | Purpose |
|------|---------|
| `config.yaml` | languages, scope, blog cutoff, auth mode, back-translation + review config, publish mode |
| `glossary.yaml` | do-not-translate terms + preferred per-language terms |
| `prompts/translate.md` | translation system prompt |
| `prompts/back-translate.md` / `back-translate-compare.md` | round-trip meaning-drift check |
| `prompts/review-editor.md` | native technical-editor reviewer (fluency) |
| `prompts/review-maintainer.md` | native Cozystack-maintainer reviewer (technical correctness) |
| `prompts/revise.md` | revise a translation against reviewer findings |
| `style-guides/<lang>.md` | per-language tone/register conventions |
| `keyword-maps/<lang>.yaml` | Ahrefs-derived SEO keyword targets (generated) |
| `lib.py` | shared helpers (config, discovery, digest, front matter, protect/restore) |
| `worklist.py` | diff detector |
| `translate.py` | translate + review-gate driver |
| `ahrefs_keywords.py` | regenerate SEO keyword maps from Ahrefs |
| `run-daily.sh` | daily runner (subscription, until limit, commit + PR) |

## Scope

- **Docs:** latest version only; older versions stay English (they are `noindex`).
- **Blog:** posts newer than `blog_since` in `config.yaml`.
- **Never:** `docs/next/**`, `**/_include/**`.
- Code, shortcodes, comments, inline code, URLs, CLI, YAML keys, and brand names are preserved structurally or via the glossary.

## Governance

`content/<lang>/` is exempt from `.github/CODEOWNERS`, so the daily PR
auto-merges. Code, layouts, config, English source, and this pipeline stay
maintainer-owned. Set `publish_mode: pr_only` in `config.yaml` to require a
human merge instead.

## Secrets

- Translation auth: `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`) — subscription, not metered. Local runner reads it from the env; the optional GitHub Action reads it from a repo secret of the same name.
- `AHREFS_API_KEY` — optional (SEO keyword localization).
- Never set `ANTHROPIC_API_KEY` for this pipeline — it shadows the subscription and bills metered API (the run hard-fails if it's present).
