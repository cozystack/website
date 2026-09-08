#!/usr/bin/env bash
# Builds the mocked Cozystack console demo into ../static/demo.
#
# The demo is a thin overlay on cozystack/cozystack-ui: a few new files
# (demo/ mock layer, MSW worker, smoke test) plus small patches to main.tsx,
# vite.config and the manifests. This fetches upstream fresh, lays the overlay
# on top, smoke-checks a root build, then produces the /demo/ bundle.
#
#   demo-src/build.sh [cozystack-ui-ref]     # ref defaults to "main"
#   SKIP_SMOKE=1 demo-src/build.sh           # regenerate the bundle only
#
set -euo pipefail

REF="${1:-main}"
HERE="$(cd "$(dirname "$0")" && pwd)"
SITE="$(cd "$HERE/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
UI="$WORK/ui"

echo "==> cloning cozystack-ui @ $REF"
git clone --depth 1 --branch "$REF" https://github.com/cozystack/cozystack-ui.git "$UI"

echo "==> applying demo overlay"
cp -R "$HERE/overlay/." "$UI/"

echo "==> applying patches"
( cd "$UI"
  for p in "$HERE"/patches/*.patch; do
    echo "    $(basename "$p")"
    git apply --3way "$p" || { echo "PATCH FAILED: $(basename "$p") — upstream drifted, needs a human"; exit 3; }
  done )

echo "==> installing deps"
corepack enable >/dev/null 2>&1 || true
( cd "$UI" && pnpm install --frozen-lockfile=false )

if [ "${SKIP_SMOKE:-0}" != "1" ]; then
  echo "==> smoke: root build + walk every screen"
  ( cd "$UI"
    VITE_DEMO=1 DEMO_BASE_PATH=/ pnpm --filter @cozystack/console build
    cp apps/console/dist/index.html apps/console/dist/404.html
    PW_FLAGS=""; [ "${CI:-}" = "true" ] && PW_FLAGS="--with-deps"
    pnpm --filter @cozystack/console exec playwright install $PW_FLAGS chromium
    SMOKE_DIST="$UI/apps/console/dist" node apps/console/demo-smoke.mjs )
fi

echo "==> building demo (base /demo/)"
( cd "$UI"
  VITE_DEMO=1 DEMO_BASE_PATH=/demo-app/ pnpm --filter @cozystack/console build
  cp apps/console/dist/index.html apps/console/dist/404.html )

echo "==> publishing to static/demo-app"
rm -rf "$SITE/static/demo" "$SITE/static/demo-app"
mkdir -p "$SITE/static/demo-app"
cp -R "$UI/apps/console/dist/." "$SITE/static/demo-app/"
echo "==> done: $(find "$SITE/static/demo-app" -type f | wc -l) files in static/demo-app"
