#!/usr/bin/env bash
#
# run-daily.sh — translation run. Cadence: run this DAILY (cron/launchd).
#
# Daily run, weekly PR: each run uses that day's model quota, and the week's
# output accumulates on a single `i18n/week-<ISO week>` branch. One PR per week
# is opened and updated, and a MAINTAINER merges it — nothing reaches the
# production site automatically, and CODEOWNERS/branch protection are untouched.
#
# RUN THIS IN A DEDICATED CLONE, not your working checkout: it switches branches
# and commits. It refuses to start if the working tree is dirty, and always
# restores the branch you started on.
#
# Auth: see `auth` in hack/i18n/config.yaml.
#   oauth-subscription (default): a logged-in `claude` CLI on this machine, or
#     CLAUDE_CODE_OAUTH_TOKEN from `claude setup-token`. ANTHROPIC_API_KEY must
#     NOT be set — it would shadow the subscription and bill metered API.
#   api-key: ANTHROPIC_API_KEY must be set (prefer an org-owned key).
#
# Usage: hack/i18n/run-daily.sh [--lang ru] [--limit N]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# ---------------------------------------------------------------- environment
VENV="${I18N_VENV:-$REPO_ROOT/.venv-i18n}"
if [ ! -x "$VENV/bin/python" ]; then
  echo "bootstrapping venv at $VENV ..."
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --quiet --upgrade pip
fi
# Distro Pythons are PEP 668 "externally managed", so the pipeline runs from a venv.
# Versions are PINNED (requirements.txt): this install runs on every invocation on
# a machine that holds maintainer credentials — it must not upgrade in place.
"$VENV/bin/pip" install --quiet -r "$REPO_ROOT/hack/i18n/requirements.txt"
PY="$VENV/bin/python"

cfg() { "$PY" - "$1" <<'PY'
import sys; sys.path.insert(0, "hack/i18n"); import lib
cfg = lib.load_config()
key = sys.argv[1]
if key == "langs":
    print("\n".join(l["code"] for l in cfg["languages"]))
else:
    print(cfg.get(key, ""))
PY
}

AUTH_MODE="$(cfg auth)"
if [ "$AUTH_MODE" = "oauth-subscription" ]; then
  if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
    echo "error: auth=oauth-subscription but ANTHROPIC_API_KEY is set — it shadows the" >&2
    echo "       subscription and would bill metered API. Unset it, or set auth: api-key." >&2
    exit 1
  fi
  if [ -z "${CLAUDE_CODE_OAUTH_TOKEN:-}" ] && ! command -v claude >/dev/null 2>&1; then
    echo "error: no subscription credential — log in with the 'claude' CLI, or run" >&2
    echo "       'claude setup-token' and export CLAUDE_CODE_OAUTH_TOKEN." >&2
    exit 1
  fi
elif [ "$AUTH_MODE" = "api-key" ]; then
  if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    echo "error: auth=api-key but ANTHROPIC_API_KEY is not set." >&2
    exit 1
  fi
else
  echo "error: unknown auth mode '$AUTH_MODE' in config.yaml" >&2
  exit 1
fi

# --------------------------------------------------------------- git preflight
# A dirty tree means we cannot safely switch branches; and stashing the user's
# work has proven to be a footgun (conflicts write markers into translations,
# and an empty stash pops someone else's).
if [ -n "$(git status --porcelain)" ]; then
  echo "error: working tree is not clean. Run this in a dedicated clone." >&2
  git status --short >&2
  exit 1
fi
START_REF="$(git symbolic-ref --quiet --short HEAD || git rev-parse HEAD)"
restore_branch() { git checkout --quiet "$START_REF" 2>/dev/null || true; }
trap restore_branch EXIT

# ------------------------------------------------- sync to the publish branch
# The week branch is checked out BEFORE translating, not after. Translating on
# whatever branch the clone happened to be on and switching only to publish
# wedged the runner on its second run: the EXIT trap restored the start branch,
# which removed day 1's translations from the working tree, so day 2 re-translated
# them (the worklist reads the filesystem) and then collided with the very same
# files as untracked on checkout. Working on the branch the commits belong to
# keeps the worklist honest, kills the collision, and refreshes content/en in
# the same move.
#
# One branch per ISO week. --prune matters: without it a remote-tracking ref for
# a merged+deleted branch lingers, and we would resurrect it.
git fetch --quiet --prune origin
BRANCH="i18n/week-$(date -u +%G-W%V)"
if git rev-parse --verify --quiet "origin/$BRANCH" >/dev/null; then
  git checkout --quiet -B "$BRANCH" "origin/$BRANCH"   # continue this week's branch
else
  git checkout --quiet -B "$BRANCH" origin/main        # first run of the week
fi

# ------------------------------------------------------------------- translate
echo "== i18n run $(date -u +%Y-%m-%dT%H:%MZ) (auth=$AUTH_MODE) =="
# `| head` closes the pipe and makes Python raise BrokenPipeError, which under
# `set -o pipefail` would kill the run before a single page is translated.
"$PY" hack/i18n/worklist.py ${1:+"$@"} 2>/dev/null | head -3 || true

# Translates until the daily quota stops it; exits 0 on a usage limit.
"$PY" hack/i18n/translate.py "$@"

# --------------------------------------------------------------- collect output
LANG_PATHS=()
while IFS= read -r code; do
  # Only existing dirs: `git stash`/`git add` fail hard on a pathspec that
  # matches nothing (a language with no content yet), whereas `git status` does not.
  [ -d "content/$code" ] && LANG_PATHS+=("content/$code")
done < <(cfg langs)

if [ ${#LANG_PATHS[@]} -eq 0 ] || [ -z "$(git status --porcelain -- "${LANG_PATHS[@]}")" ]; then
  echo "no new translations this run — nothing to publish."
  exit 0
fi

# Freshness/parity is informational here: "some pages are still stale" is the
# normal steady state of a quota-limited backlog, so it must not block
# publishing the work this run DID finish.
if ! ./hack/check-i18n.sh; then
  echo "::warning::check-i18n.sh reported gaps (expected while the backlog drains)."
fi

# ------------------------------------------------------------------- publish
# Already on $BRANCH (checked out before translating) — commit in place.
git config user.name  "$(git config user.name  || echo cozystack-i18n)"
git config user.email "$(git config user.email || echo noreply@cozystack.io)"

git add -- "${LANG_PATHS[@]}"
if git diff --cached --quiet; then
  echo "nothing staged — nothing to publish."
  exit 0
fi
git commit --quiet --signoff -m "i18n: machine-reviewed translation update ($(date -u +%Y-%m-%d))

Machine review gate: translation, back-translation meaning check, and two
native virtual reviewers (technical editor + Cozystack maintainer). Pages that
did not clear the gate are stamped auto-reviewed-with-findings. Native owners
ratify asynchronously; source_digest tracks freshness."
git push --quiet -u origin "$BRANCH"

# Open a PR only if this week's branch has no OPEN one. `gh pr view` resolves the
# branch's most recent PR regardless of state, so a merged PR would otherwise
# look like "a PR exists" and the week's later work would sit on an orphan branch.
PR_BODY="Automated translation run. Touches \`content/<lang>/\` only — no changes to code, layouts, config, or the English source.

This PR collects **this week's** translations; the pipeline runs daily and pushes onto this branch, so please review and merge it at the end of the week.

Each page went through the machine review gate: translation, a back-translation meaning check, and two virtual reviewers prompted as native speakers (technical editor + Cozystack maintainer). Pages that cleared it are stamped \`translation_review: auto-reviewed\`; pages where findings stayed open are stamped \`auto-reviewed-with-findings\` — review those first. The reviewers are the same model as the translator, so this gate measures self-consistency, not human ratification.

Every localized page carries a machine-translation banner linking to the English original until a native speaker sets \`translation_review: ratified\`."

PR_STATE="$(gh pr view "$BRANCH" --json state -q .state 2>/dev/null || echo NONE)"
if [ "$PR_STATE" != "OPEN" ]; then
  # No `|| true` here (or on the comment below): commits are already pushed, so a
  # failed `gh` call must fail the run — a cron exit 0 with pushed commits and no
  # PR would be indistinguishable from a good run.
  gh pr create --base main --head "$BRANCH" \
    --title "i18n: translation update, week $(date -u +%G-W%V)" \
    --body "$PR_BODY"
fi

# Surface what the reviewers actually found. A "-with-findings" stamp with no
# record of the finding is not something a maintainer can act on.
#
# This goes in a COMMENT, not the PR body: the body would have to be rewritten
# every day, and each rewrite would drop the previous days' findings — the PR
# accumulates a week of runs, but the report file only ever holds the last one.
# Comments accumulate on their own, so the thread ends up being the week's log.
FINDINGS="hack/i18n/last-run-findings.md"
if [ -f "$FINDINGS" ]; then
  { printf '#### Run %s\n\n' "$(date -u +%Y-%m-%d\ %H:%MZ)"; cat "$FINDINGS"; } \
    | gh pr comment "$BRANCH" --body-file -
fi

# There is deliberately no auto-merge code path: "nothing reaches the production
# site without a maintainer merging it" is a property of this script, not a
# default that one config word away stops being true.
echo "PR left open for a maintainer to review and merge (weekly)."
echo "== done =="
