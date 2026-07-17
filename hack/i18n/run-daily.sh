#!/usr/bin/env bash
#
# run-daily.sh — translation run. Cadence: run this DAILY (cron/launchd).
#
# Daily run, weekly PR: each run uses that day's subscription quota, and the
# week's output accumulates on a single `i18n/week-<ISO week>` branch. One PR
# per week is opened and updated, and a MAINTAINER merges it — nothing reaches
# the production site automatically, and CODEOWNERS/branch protection are
# untouched.
#
# Auth is the maintainer's Claude subscription (Max) via the Claude Agent SDK,
# NOT an API key. Two ways the SDK finds the subscription — either works:
#   (a) you are already logged in with the `claude` CLI on this machine
#       (`claude` / `/login`) — nothing else to do; or
#   (b) headless/CI: `claude setup-token` -> export CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-...
# The only hard requirement is that ANTHROPIC_API_KEY is NOT set: it shadows the
# subscription and silently bills metered API.
#
# It translates + review-gates as many pages as the daily usage limit allows,
# stops cleanly when the limit is hit, and commits the day's output onto this
# week's branch. Over time it works through the backlog and then just keeps
# translations fresh against the English source.
#
# Usage: hack/i18n/run-daily.sh [--lang ru]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# Subscription-only. An API key would shadow the subscription and bill metered API.
if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  echo "error: ANTHROPIC_API_KEY is set — unset it so the run uses your Max subscription." >&2
  exit 1
fi
if [ -z "${CLAUDE_CODE_OAUTH_TOKEN:-}" ] && ! command -v claude >/dev/null 2>&1; then
  echo "error: no subscription credential — either log in with the \`claude\` CLI on this" >&2
  echo "       machine, or run 'claude setup-token' and export CLAUDE_CODE_OAUTH_TOKEN." >&2
  exit 1
fi

# Self-contained venv: distro Pythons are PEP 668 "externally managed", so a
# plain `pip install` fails. Bootstrap once, reuse on later runs.
VENV="${I18N_VENV:-$REPO_ROOT/.venv-i18n}"
if [ ! -x "$VENV/bin/python" ]; then
  echo "bootstrapping venv at $VENV ..."
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --quiet --upgrade pip
fi
"$VENV/bin/pip" install --quiet claude-agent-sdk pyyaml
PY="$VENV/bin/python"

echo "== i18n daily run $(date -u +%Y-%m-%dT%H:%MZ) =="
"$PY" hack/i18n/worklist.py "$@" | head -3

# Translate until the daily limit stops us (translate.py exits 0 on rate limit).
"$PY" hack/i18n/translate.py "$@"

# Verify freshness + i18n key parity before publishing.
./hack/check-i18n.sh

# `git diff --quiet` only sees TRACKED files — every brand-new translation is
# untracked, so it would report "nothing to publish" forever. Use porcelain,
# which covers untracked too, and scope it to the localized trees only so an
# unrelated edit in content/en never rides along in the bot's PR.
LANG_PATHS=()
while IFS= read -r code; do LANG_PATHS+=("content/$code"); done < <(
  "$PY" - <<'PY'
import sys; sys.path.insert(0, "hack/i18n"); import lib
print("\n".join(l["code"] for l in lib.load_config()["languages"]))
PY
)
if [ -z "$(git status --porcelain -- "${LANG_PATHS[@]}")" ]; then
  echo "no new translations today — nothing to publish."
  exit 0
fi

# One branch per ISO week: the run happens daily (to use each day's quota), but
# the week's translations accumulate onto a single branch so maintainers get ONE
# PR to review and merge per week, not seven.
#
# Days 2..7 continue the existing week branch; a new week starts fresh from
# origin/main so it never carries the previous week's (possibly already merged)
# commits.
git fetch --quiet origin main
BRANCH="i18n/week-$(date -u +%G-W%V)"
git config user.name  "$(git config user.name  || echo cozystack-i18n)"
git config user.email "$(git config user.email || echo noreply@cozystack.io)"
git stash push --include-untracked --quiet -- "${LANG_PATHS[@]}"
if git rev-parse --verify --quiet "origin/$BRANCH" >/dev/null; then
  git checkout -B "$BRANCH" "origin/$BRANCH"   # continue this week's branch
else
  git checkout -B "$BRANCH" origin/main        # first run of the week
fi
git stash pop --quiet

git add -- "${LANG_PATHS[@]}"
if git diff --cached --quiet; then
  echo "nothing staged after all — aborting publish."
  exit 0
fi
git commit --signoff -m "i18n: machine-reviewed translation update ($(date -u +%Y-%m-%d))

Machine review gate: translation, back-translation meaning check, and two
native virtual reviewers (technical editor + Cozystack maintainer). Pages that
did not clear the gate are stamped auto-reviewed-with-findings. Native human
owners ratify asynchronously; source_digest tracks freshness."
git push -u origin "$BRANCH"

PUBLISH_MODE="$("$PY" - <<'PY'
import sys; sys.path.insert(0, "hack/i18n"); import lib
print(lib.load_config().get("publish_mode", "pr_only"))
PY
)"

if ! gh pr view "$BRANCH" >/dev/null 2>&1; then
  gh pr create --base main --head "$BRANCH" \
    --title "i18n: translation update, week $(date -u +%G-W%V)" \
    --body "Automated translation run. Touches \`content/<lang>/\` only — no changes to code, layouts, config, or the English source.

This PR collects **this week's** translations; the pipeline runs daily and pushes onto this branch, so please review/merge it at the end of the week.

Each page went through the machine review gate: translation, a back-translation meaning check, and two native virtual reviewers (technical editor + Cozystack maintainer). Pages that cleared it are stamped \`translation_review: auto-reviewed\`; pages where findings remained open are stamped \`auto-reviewed-with-findings\` — those are worth a closer look. Freshness and i18n key parity are verified by \`check-i18n.sh\`." || true
fi
if [ "$PUBLISH_MODE" = "auto_merge" ]; then
  gh pr merge "$BRANCH" --auto --squash || \
    echo "auto-merge not enabled by branch protection — PR left for a maintainer."
else
  echo "publish_mode=$PUBLISH_MODE — PR left open for a maintainer to merge (weekly)."
fi
echo "== done =="
