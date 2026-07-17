# Cozystack website translation pipeline

Automated, in-tree localization for cozystack.io with a machine review gate.
Detects English pages that are new or changed and, for each one, runs a
translate → verify → review → revise loop. Runs daily on a Claude subscription
until the usage limit is hit; a maintainer merges one translation PR per week.

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
                   check-i18n.sh  →  weekly PR  →  merged by a maintainer
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

## Cadence — daily run, weekly PR

```bash
hack/i18n/run-daily.sh            # all languages, until the limit
hack/i18n/run-daily.sh --lang ru  # one language
```

Schedule it once a day (cron/launchd). Each run translates and review-gates as
many pages as the day's quota allows, stops cleanly at the limit, and commits
onto a single `i18n/week-<ISO week>` branch. One PR per week is opened and kept
updated; **a maintainer merges it**. Running daily uses each day's quota (a
weekly-only run would use ~1/7 of the available capacity), while the weekly PR
keeps review to one deliberate merge instead of a stream of them.

Over time this clears the backlog, then just keeps translations fresh against
the English source.

Manual/dry inspection:

```bash
python3 hack/i18n/worklist.py            # what needs work
python3 hack/i18n/translate.py --dry-run # plan, no model calls
./hack/check-i18n.sh                      # freshness + i18n key parity
```

### Throughput, measured

The backlog is **183 pages × 4 languages = 720 jobs**. Each job is 5–15 Opus
calls (translate, back-translate, compare, two reviewers, and a revise round per
finding), so the backlog is on the order of 4k–11k model calls.

Measured pilots on a subscription, both on the same ~2500-word release blog post:

| Language | Wall clock | Outcome |
|----------|-----------|---------|
| de | 2m54s | cleared the gate on the first round |
| ru | 11m24s | went through the revise loop, findings still open |

So per-page cost is dominated by **whether the revise loop runs**, not by the
page alone — a clean page is ~3 min, one that keeps failing review is ~4× that.
Taking the range against 720 jobs puts the backlog at roughly 35–140 hours of
wall clock, before daily usage limits enter the picture at all. That is weeks to
months on a personal subscription, which is why the plan is to bootstrap the
backlog with `auth: api-key` on an organization account and leave the
daily/weekly cadence to handle only steady-state drift afterwards.

Most docs pages are far shorter than a release blog post, so treat these as an
upper bound rather than an average.

### Placeholder-dense pages

Code, shortcodes, and inline code are swapped for opaque `§§…§§` placeholders
before translation and restored after (see `protect`/`restore` in `lib.py`). A
long, code-heavy page can carry 60+ of them, and a model occasionally drops one.
The gate refuses to write a page with a dropped or duplicated placeholder — a
silently deleted code block is worse than a retry — so `translate.py` retries
such a page a few times within the run (the loss is non-deterministic and
usually clears). A page that still fails every attempt is skipped and stays in
the worklist; it is not stalled on, but it also will not publish until an attempt
succeeds. A page that reproducibly fails is a signal to translate it by hand.

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
| `lib.py` | shared helpers (config, discovery, digest, front matter, protect/restore) |
| `worklist.py` | diff detector |
| `translate.py` | translate + review-gate driver |
| `run-daily.sh` | daily runner (subscription, until limit, commit + PR) |
| `test_i18n.py` | tests for the pure functions (no network) — `python3 hack/i18n/test_i18n.py` |
| `../../layouts/partials/translation-banner.html` | reader-facing machine-translation disclaimer |

## Scope

- **Docs:** latest version only; older versions stay English (they are `noindex`).
- **Blog:** posts newer than `blog_since` in `config.yaml`.
- **Never:** `docs/next/**`, `**/_include/**`.
- Code, shortcodes, comments, inline code, URLs, CLI, YAML keys, and brand names are preserved structurally or via the glossary.

## Front-matter fields

| Field | Meaning | Read by |
|-------|---------|---------|
| `source_digest` | sha256 of the English source the translation was made from — the freshness signal | `hack/check-i18n.sh`, `worklist.py` |
| `l10n` | *how* the page was localized: `mt` (machine) or `transcreate` | humans triaging review |
| `translation_review` | *ratification state*: `auto-reviewed`, `auto-reviewed-with-findings`, or `ratified` | `translation-banner.html` |

`translation_status: current` appears on pages from the i18n PoC. It is not
written or read by anything — `source_digest` computes freshness properly — so
this pipeline does not write it.

## Adding a language

Two lists, two different questions:

| | `languages:` in `hack/i18n/config.yaml` | `languages:` in `hugo.yaml` |
|---|---|---|
| Answers | what gets **translated** | what gets **built and served** |
| Add it | as soon as you want the language | only once its content exists |

They are allowed to differ in exactly one direction. **Translated but not
declared** is the normal way a language starts — the pipeline fills
`content/<code>/` while the site stays quiet about it. **Declared but not
translated** is broken, and `test_i18n.py` fails on it.

Order matters, because declaring a language in `hugo.yaml` before
`content/<code>/` exists does not build nothing: Hugo emits `/<code>/`,
`/<code>/tags/`, `/<code>/categories/`, `/<code>/topics/`,
`/<code>/article_types/` and `/<code>/404.html` anyway, all `index, follow` and
self-canonical — roughly six empty but indexable pages per language.

So the sequence is: add to `config.yaml` → let the pipeline translate → add to
`hugo.yaml` in the PR that lands the content.

`es` and `pt-br` are at step one right now: they are translated, have their
`i18n/*.toml` ready, and are commented out in `hugo.yaml` until their content
lands.

## Reader-facing disclosure

`layouts/partials/translation-banner.html` puts a machine-translation notice on
every localized page and links to the English original. The rule is fail-safe:
the banner shows on any non-English page **unless** its front matter says
`translation_review: ratified`. Pages from the i18n PoC carry no
`translation_review` at all, and they are machine output too — keying off the
field's presence would silently exempt exactly the pages that need the notice.

Localized pages are deliberately indexed from day one (no `noindex`): readers
get the docs now rather than after a native review that may take months. The
banner is what makes that trade honest.

The banner is wired into **`docs/baseof.html` only** — documentation pages, by
product decision. It is deliberately absent from the blog, marketing/`page`
layouts, `resources`, and the homepage: the notice belongs where a wrong
technical detail is costly (an operator running a translated command), not
across a marketing hero. To change coverage, add or remove the
`{{ partial "translation-banner.html" . }}` call in the relevant layout; the
partial's own guard (non-English and not `ratified`) is layout-agnostic.

## Rollback / kill switch

Ordered from cheapest to most drastic.

**Stop translating** — remove the cron entry, or just stop running
`run-daily.sh`. Nothing else runs on its own; there is no GitHub Action.

**Stop a single language** — comment it out of `languages:` in `config.yaml`.
Existing pages stay served.

**Take a language out of the site without deleting it** — comment its block out
of `languages:` in `hugo.yaml`. Hugo stops building `/<code>/` entirely; the
`content/<code>/` tree stays in git and can be re-enabled with one edit. This is
the right move if a language's quality is disputed: it de-indexes without losing
the work.

**De-index one page but keep it served** — add `robots: "noindex, follow"` to its
front matter and have `layouts/partials/hooks/head-end.html` honour it, or delete
the page (its English source is untouched, and `worklist.py` will simply see it
as missing again).

**Undo a bad run** — every run lands on one `i18n/week-<ISO week>` branch and is
merged by a maintainer, so the revert is a normal `git revert` of the merge
commit. Nothing reaches production without that merge.

**Full stop** — revert the merge, comment the non-English languages out of
`hugo.yaml`, and the site is English-only again. The pipeline touches nothing but
`content/<lang>/`.

## Governance

Nothing here changes CODEOWNERS or branch protection. `publish_mode: pr_only`
means the pipeline only ever opens a PR touching `content/<lang>/`; a
maintainer reviews and merges it weekly. Code, layouts, config, the English
source, and this pipeline itself remain maintainer-owned as before.

Pages are stamped `translation_review: auto-reviewed` when they clear the
machine gate and `auto-reviewed-with-findings` when the revise loop ran out of
rounds with findings still open — the latter are the ones worth a human's
attention first. Native owners flip either to `ratified` after their pass.

**What the gate is and is not.** The two "native reviewers" are the same model as
the translator, given different system prompts. That measures self-consistency
and catches the obvious failures (meaning drift, mangled terminology, broken
register); it is **not** native-speaker ratification, and `auto-reviewed` must
not be read as "a human checked this". Only a human sets `ratified`, and only
`ratified` removes the reader-facing disclaimer banner. The gate's real job is to
make the machine output good enough to publish while native review happens
asynchronously — not to replace it.

## Ownership and continuity

The pipeline currently authenticates with a maintainer's Claude subscription
(`auth: oauth-subscription`) to bootstrap the backlog. The intent is to move to
an organization-owned API key (`auth: api-key` + `ANTHROPIC_API_KEY`) once it is
provisioned, so the pipeline does not depend on one individual's account. That
switch is a config change; no code changes.

## Secrets

- Translation auth: `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`) — subscription, not metered. Only needed headless; if the `claude` CLI is logged in on the runner, the Agent SDK picks that credential up.
- Under `auth: oauth-subscription`, never set `ANTHROPIC_API_KEY` — it shadows the subscription and silently bills metered API (the run hard-fails if it's present).
- There is no GitHub Action and no CI-held credential: the pipeline runs from a maintainer's clone, by hand or by cron. That is deliberate — it keeps a personal subscription token out of repo secrets.
