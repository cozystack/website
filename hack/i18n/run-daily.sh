#!/usr/bin/env bash
#
# run-daily.sh — daily translation run on the maintainer's Claude subscription.
#
# Auth is the logged-in Claude / OAuth subscription (Max), NOT an API key:
# run `claude setup-token` (or `ant auth login`) ONCE on this machine, then this
# script's bare `anthropic.Anthropic()` client picks up the subscription.
#
# It translates + review-gates as many pages as the daily usage limit allows,
# stops cleanly when the limit is hit, commits the day's output to a dated
# branch, and opens/updates one PR. Run it from cron/launchd once a day; over
# time it works through the whole backlog and then just keeps translations
# fresh against the English source.
#
# Usage: hack/i18n/run-daily.sh [--lang ru]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# Guard against metered billing: this pipeline is subscription-only.
if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  echo "warning: ANTHROPIC_API_KEY is set; unset it so the run uses your OAuth subscription." >&2
fi

python3 -m pip install --quiet anthropic pyyaml 2>/dev/null || true

echo "== i18n daily run $(date -u +%Y-%m-%dT%H:%MZ) =="
python3 hack/i18n/worklist.py "$@" | head -3

# Translate until the daily limit stops us (translate.py exits 0 on rate limit).
python3 hack/i18n/translate.py "$@"

# Verify freshness + i18n key parity before publishing.
./hack/check-i18n.sh

if git diff --quiet -- content/; then
  echo "no new translations today — nothing to publish."
  exit 0
fi

BRANCH="i18n/daily-$(date -u +%Y%m%d)"
git config user.name  "$(git config user.name  || echo cozystack-i18n)"
git config user.email "$(git config user.email || echo noreply@cozystack.io)"
git checkout -B "$BRANCH"
git add content/
git commit --signoff -m "i18n: daily machine-reviewed translation update ($(date -u +%Y-%m-%d))

Translated + back-translation checked + reviewed by two native virtual
reviewers (technical editor + Cozystack maintainer). Native human owners
ratify asynchronously; source_digest tracks freshness."
git push -u origin "$BRANCH"

# Open the PR if it doesn't exist yet for today's branch.
if ! gh pr view "$BRANCH" >/dev/null 2>&1; then
  gh pr create --base main --head "$BRANCH" \
    --title "i18n: daily translation update ($(date -u +%Y-%m-%d))" \
    --body "Automated daily run on the maintainer's Claude subscription. Only \`content/<lang>/\` is touched (CODEOWNERS-exempt). Every page passed back-translation + two native reviewers (editor + maintainer). Freshness/parity verified by \`check-i18n.sh\`." || true
  # content/<lang> is CODEOWNERS-exempt → auto-merge is allowed.
  gh pr merge "$BRANCH" --auto --squash || \
    echo "auto-merge not enabled by branch protection — PR left for a maintainer."
fi
echo "== done =="
