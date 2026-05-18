#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: hack/release_next.sh --release-tag TAG

Promote content/en/docs/next/ to a released version.

Given a release tag like v1.3.0, derives DOC_VERSION (v1.3) and:
  1. Validates next/ is non-empty and $DOC_VERSION/ does not already exist
  2. Copies next/ → $DOC_VERSION/
  3. Rewrites /docs/next/ links in $DOC_VERSION/ to /docs/$DOC_VERSION/
  4. Updates $DOC_VERSION/_index.md: title → "Cozystack $DOC_VERSION Documentation",
     strips the draft banner shortcode block
  5. Registers $DOC_VERSION in hugo.yaml as the new latest version

The /docs/v<major>/ short path is handled dynamically by layouts/404.html,
which reads Site.Params.latest_version_id and redirects. No Hugo alias is
emitted for that path, so no release-time alias shuffling is needed.

Only accepts final release tags (vX.Y.Z); pre-release tags like vX.Y.Z-rc1
are rejected — those should accumulate in next/ via update-all.

next/ is never modified.

Options:
  --release-tag TAG   Release tag (e.g., v1.3.0)
  -h, --help          Show this help and exit

Examples:
  hack/release_next.sh --release-tag v1.3.0
EOF
}

RELEASE_TAG=""
DOCS_BASE="content/en/docs"
NEXT_DIR="${DOCS_BASE}/next"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --release-tag) RELEASE_TAG="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Error: unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ -z "$RELEASE_TAG" ]]; then
  echo "Error: --release-tag is required." >&2
  usage; exit 1
fi

# Derive DOC_VERSION from RELEASE_TAG (e.g., v1.3.0 → v1.3, v0.30.0 → v0).
# Pre-release tags (v1.3.0-rc1, v1.3.0-beta, …) are rejected: release-next is
# only invoked for final minor/major releases; pre-releases still accumulate
# in next/ via update-all.
if [[ ! "$RELEASE_TAG" =~ ^v([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
  echo "Error: RELEASE_TAG must match v<major>.<minor>.<patch> with no suffix (got: $RELEASE_TAG)" >&2
  exit 1
fi
MAJOR="${BASH_REMATCH[1]}"
MINOR="${BASH_REMATCH[2]}"
if [[ "$MAJOR" == "0" ]]; then
  DOC_VERSION="v0"
else
  DOC_VERSION="v${MAJOR}.${MINOR}"
fi
TARGET_DIR="${DOCS_BASE}/${DOC_VERSION}"

# Validate next/ exists and is non-empty
if [[ ! -d "$NEXT_DIR" ]] || [[ -z "$(ls -A "$NEXT_DIR" 2>/dev/null)" ]]; then
  echo "Error: $NEXT_DIR does not exist or is empty. Run 'make init-next' first." >&2
  exit 1
fi

# Validate target directory does not already exist
if [[ -e "$TARGET_DIR" ]]; then
  echo "Error: $TARGET_DIR already exists. release-next refuses to overwrite an existing released version." >&2
  echo "       Use 'make update-all RELEASE_TAG=$RELEASE_TAG' for patch releases of an existing version." >&2
  exit 1
fi

echo "Releasing next/ as $DOC_VERSION (from $RELEASE_TAG)..."

# 1. Copy next/ → $DOC_VERSION/
cp -a "$NEXT_DIR" "$TARGET_DIR"
echo "✓ Copied $NEXT_DIR → $TARGET_DIR"

# 2. Rewrite /docs/next/ → /docs/$DOC_VERSION/ in all markdown files
find "$TARGET_DIR" -name '*.md' -exec sed -i.bak \
  -e "s|/docs/next/|/docs/${DOC_VERSION}/|g" \
  -e "s|\"docs/next/|\"docs/${DOC_VERSION}/|g" \
  {} +
find "$TARGET_DIR" -name '*.bak' -delete
echo "✓ Rewrote internal links /docs/next/ → /docs/${DOC_VERSION}/"

# 3. Update _index.md: title + strip draft banner
INDEX_FILE="$TARGET_DIR/_index.md"
if [[ -f "$INDEX_FILE" ]]; then
  # Update title and linkTitle
  sed -i.bak \
    -e "s|^title: .*|title: \"Cozystack ${DOC_VERSION} Documentation\"|" \
    -e "s|^linkTitle: .*|linkTitle: \"Cozystack ${DOC_VERSION}\"|" \
    "$INDEX_FILE"
  # Strip the draft banner block — lines from `{{% warning %}}` through `{{% /warning %}}`
  # including any immediately following blank line
  sed -i.bak '/^{{% warning %}}$/,/^{{% \/warning %}}$/d' "$INDEX_FILE"
  # Trim leading/trailing blank lines and collapse runs of blanks left by the
  # banner removal. `/./,/^$/!d` keeps every range from a non-empty line up to
  # the next blank, inclusive of one blank, which drops leading/trailing blanks
  # and collapses consecutive blanks to a single separator.
  sed -i.bak '/./,/^$/!d' "$INDEX_FILE"
  rm -f "$INDEX_FILE.bak"
  echo "✓ Updated $INDEX_FILE (title, removed draft banner)"
fi

# 4. Register version in hugo.yaml as the new latest. register_version.sh also
#    normalizes _index.md weights across all non-hidden versions so sidebar
#    ordering stays deterministic (new latest → 10, older → 20, 30, …).
./hack/register_version.sh --release "$DOC_VERSION"

# 5. Snapshot data/versions/next.yaml → data/versions/$DOC_VERSION.yaml so the
#    {{< version-pin >}} shortcode in the released docs keeps resolving to the
#    values that were true at the cut. next.yaml is unchanged; update it
#    separately for the next development cycle.
VERSIONS_DIR="data/versions"
NEXT_DATA="${VERSIONS_DIR}/next.yaml"
TARGET_DATA="${VERSIONS_DIR}/${DOC_VERSION}.yaml"
if [[ -f "$NEXT_DATA" ]]; then
  if [[ -e "$TARGET_DATA" ]]; then
    echo "! $TARGET_DATA already exists; leaving it as-is." >&2
  else
    cp "$NEXT_DATA" "$TARGET_DATA"
    echo "✓ Snapshotted $NEXT_DATA → $TARGET_DATA"
  fi
else
  echo "! $NEXT_DATA missing; skipped data/versions snapshot. Create $TARGET_DATA manually if the docs use {{< version-pin >}}." >&2
fi

echo ""
echo "✓ Released $DOC_VERSION from next/."
echo "  next/ is unchanged — continue using it for future unreleased work."
echo "  Review: $TARGET_DIR/_index.md, hugo.yaml, $TARGET_DATA"
