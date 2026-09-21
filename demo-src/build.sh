#!/usr/bin/env bash
# Builds the mocked Cozystack console demo into ../static/demo-app.
#
# The console lives in the cozystack monorepo under
# packages/system/dashboard/images/console. It used to be its own repository,
# cozystack/cozystack-ui, which was archived in June 2026 — building from there
# now pins the demo to a June snapshot, so this script follows the monorepo.
#
# The demo is a thin overlay on that tree: a few new files (demo/ mock layer,
# MSW worker, smoke test) plus small patches to main.tsx, vite.config and the
# manifests. This fetches upstream fresh, lays the overlay on top, smoke-checks
# a root build, then produces the /demo-app/ bundle.
#
#   demo-src/build.sh [cozystack-ref]        # branch or tag, defaults to "main"
#   SKIP_SMOKE=1 demo-src/build.sh           # regenerate the bundle only
#   DEMO_VERSION=v1.7.0 demo-src/build.sh    # label the header explicitly
#
set -euo pipefail

REF="${1:-main}"
REPO="${DEMO_UI_REPO:-https://github.com/cozystack/cozystack.git}"
SUBDIR="${DEMO_UI_SUBDIR:-packages/system/dashboard/images/console}"
HERE="$(cd "$(dirname "$0")" && pwd)"
SITE="$(cd "$HERE/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
SRC="$WORK/src"
UI="$WORK/ui"

echo "==> cloning $REPO @ $REF ($SUBDIR)"
# Blobless + sparse: the monorepo is large and only the console tree is wanted.
git clone --filter=blob:none --no-checkout --depth 1 --branch "$REF" "$REPO" "$SRC"
git -C "$SRC" sparse-checkout set --no-cone "$SUBDIR"
git -C "$SRC" checkout
# Shown in the header where a release build shows its version, so a visitor (and
# a reviewer of the refresh PR) can tell which upstream commit the demo is. A
# release tag reads as itself, a branch as branch@sha; DEMO_VERSION overrides.
if [ -n "${DEMO_VERSION:-}" ]; then
  VERSION="$DEMO_VERSION"
elif git -C "$SRC" rev-parse -q --verify "refs/tags/$REF" >/dev/null; then
  VERSION="$REF"
else
  VERSION="$REF@$(git -C "$SRC" rev-parse --short HEAD)"
fi
export VITE_APP_VERSION="$VERSION"

# The patches are rooted at the console directory, so lift that subtree into a
# repository of its own — `git apply --3way` then resolves their preimages, and
# the overlay paths stay the same as when the console had its own repo.
mkdir -p "$UI"
cp -R "$SRC/$SUBDIR/." "$UI/"
git -C "$UI" init -q
git -C "$UI" add -A
git -C "$UI" -c user.email=demo@localhost -c user.name=demo commit -qm "upstream $REF"

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

echo "==> building demo (base /demo-app/, version $VERSION)"
( cd "$UI"
  VITE_DEMO=1 DEMO_BASE_PATH=/demo-app/ pnpm --filter @cozystack/console build
  cp apps/console/dist/index.html apps/console/dist/404.html )

echo "==> publishing to static/demo-app"
rm -rf "$SITE/static/demo" "$SITE/static/demo-app"
mkdir -p "$SITE/static/demo-app"
cp -R "$UI/apps/console/dist/." "$SITE/static/demo-app/"
echo "==> done: $(find "$SITE/static/demo-app" -type f | wc -l) files in static/demo-app"
