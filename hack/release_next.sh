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

# Derive DOC_VERSION from RELEASE_TAG (e.g., v1.3.0 → v1.3, v0.30.0 → v0)
if [[ ! "$RELEASE_TAG" =~ ^v([0-9]+)\.([0-9]+)\.([0-9]+).*$ ]]; then
  echo "Error: RELEASE_TAG must match v<major>.<minor>.<patch>[...] (got: $RELEASE_TAG)" >&2
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
  # Collapse any double blank lines left after the banner removal
  sed -i.bak '/./,/^$/!d' "$INDEX_FILE"
  # Reset weight to the released-version default (10 — latest stable)
  sed -i.bak 's|^weight: .*|weight: 10|' "$INDEX_FILE"
  rm -f "$INDEX_FILE.bak"
  echo "✓ Updated $INDEX_FILE (title, removed draft banner, weight=10)"
fi

# 4. Register version in hugo.yaml as the new latest
./hack/register_version.sh --release "$DOC_VERSION"

echo ""
echo "✓ Released $DOC_VERSION from next/."
echo "  next/ is unchanged — continue using it for future unreleased work."
echo "  Review: $TARGET_DIR/_index.md, hugo.yaml"
