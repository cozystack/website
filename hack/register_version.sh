#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: hack/register_version.sh --release VERSION

Manage version entries in hugo.yaml.

Actions:
  --release VERSION   Register (or unhide) VERSION, set it as latest_version_id

The 'order' field is auto-computed from existing entries.
If the version already exists, only the relevant fields are updated.

The permanent 'next' entry is never modified by this script.

Requires: yq v4+ (https://github.com/mikefarah/yq/) for reading config.

Examples:
  hack/register_version.sh --release v1.3
EOF
}

ACTION=""
VERSION=""
HUGO_YAML="hugo.yaml"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --release) ACTION="release"; VERSION="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Error: unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ -z "$ACTION" || -z "$VERSION" ]]; then
  echo "Error: --release VERSION is required." >&2
  usage; exit 1
fi

if ! command -v yq &>/dev/null; then
  echo "Error: yq v4+ is required. Install from https://github.com/mikefarah/yq/" >&2
  exit 1
fi

# Check that the version entry format looks right (vN or vN.M)
if [[ ! "$VERSION" =~ ^v[0-9]+(\.[0-9]+)?$ ]]; then
  echo "Error: version must match vN or vN.M (got: $VERSION)" >&2
  exit 1
fi

# Escape dots for use in sed patterns
V_ESC="${VERSION//./\\.}"

# Find the max existing order among non-hidden entries (skip 'next' with order=999)
max_order=$(yq '[.params.versions[] | select(.hidden != true) | .order // 0] | max' "$HUGO_YAML")
max_order=${max_order:-0}

# Check if version already exists
exists=$(yq ".params.versions[] | select(.id == \"$VERSION\") | .id" "$HUGO_YAML")

if [[ -n "$exists" ]]; then
  # Version entry exists — update it (unhide, set as latest)
  echo "Updating $VERSION: unhiding, setting as latest..."
  # Remove "hidden: true" and "label:" lines within this version's block
  sed -i "/id: \"${V_ESC}\"/,/^    - version:\|^  [^ ]/{
    /^      hidden: true$/d
    /^      label: /d
  }" "$HUGO_YAML"
  # Update latest_version_id
  sed -i "s/latest_version_id: \".*\"/latest_version_id: \"${VERSION}\"/" "$HUGO_YAML"
else
  # Version entry doesn't exist — insert as first released entry
  new_order=$((max_order + 1))
  echo "Registering $VERSION (order=$new_order), setting as latest..."
  BLOCK="    - version: \"${VERSION}\"\n      url: \"/docs/${VERSION}/\"\n      id: \"${VERSION}\"\n      order: ${new_order}"
  sed -i "s/latest_version_id: \".*\"/latest_version_id: \"${VERSION}\"/" "$HUGO_YAML"
  # Insert new version block before the first existing version entry
  sed -i "/^  versions:$/a\\${BLOCK}" "$HUGO_YAML"
fi

# Normalize _index.md weights across non-hidden versions so sidebar ordering
# stays deterministic. Latest (highest order) = 10, then 20, 30, 40, ….
# The permanent `next` trunk keeps weight 5 (set by init_version.sh) and is
# not touched here.
echo "Normalizing _index.md weights..."
mapfile -t sorted_ids < <(yq '[.params.versions[] | select(.hidden != true)] | sort_by(.order) | reverse | .[].id' "$HUGO_YAML")
w=10
for vid in "${sorted_ids[@]}"; do
  idx="content/en/docs/${vid}/_index.md"
  if [[ -f "$idx" ]]; then
    sed -i.bak "s|^weight: .*|weight: ${w}|" "$idx"
    rm -f "${idx}.bak"
    echo "  ${vid}/_index.md → weight ${w}"
  else
    echo "  ${vid}: no _index.md on disk, skipping"
  fi
  w=$((w + 10))
done

echo "✓ Done. Current versions in hugo.yaml:"
yq '.params.versions[] | [.id, "order=" + (.order | tostring), "hidden=" + (.hidden // false | tostring)] | join(" ")' "$HUGO_YAML"
