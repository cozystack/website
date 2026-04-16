#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: hack/register_version.sh [--release VERSION | --draft VERSION]

Manage version entries in hugo.yaml.

Actions:
  --release VERSION   Register (or unhide) VERSION, set it as latest_version_id
  --draft VERSION     Register VERSION as hidden (draft/unreleased)

Both actions auto-compute the 'order' field from existing entries.
If the version already exists, only the relevant fields are updated.

Requires: yq v4+ (https://github.com/mikefarah/yq/) for reading config.

Examples:
  hack/register_version.sh --release v1.3
  hack/register_version.sh --draft v1.4
EOF
}

ACTION=""
VERSION=""
HUGO_YAML="hugo.yaml"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --release) ACTION="release"; VERSION="$2"; shift 2 ;;
    --draft)   ACTION="draft";   VERSION="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Error: unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ -z "$ACTION" || -z "$VERSION" ]]; then
  echo "Error: action and version are required." >&2
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

# Find the max existing order value (yq for reads only)
max_order=$(yq '.params.versions[].order // 0' "$HUGO_YAML" | sort -n | tail -1)
max_order=${max_order:-0}

# Check if version already exists
exists=$(yq ".params.versions[] | select(.id == \"$VERSION\") | .id" "$HUGO_YAML")

if [[ -n "$exists" ]]; then
  # Version entry exists — update it
  if [[ "$ACTION" == "release" ]]; then
    echo "Updating $VERSION: unhiding, setting as latest..."
    # Remove "hidden: true" line within this version's block (between its id and the next entry)
    sed -i "/id: \"${V_ESC}\"/,/^    - version:\|^  [^ ]/{/^      hidden: true$/d;}" "$HUGO_YAML"
    # Update latest_version_id
    sed -i "s/latest_version_id: \".*\"/latest_version_id: \"${VERSION}\"/" "$HUGO_YAML"
  else
    echo "Updating $VERSION: marking as hidden draft..."
    # Add hidden: true after the order line of this version's block (if not already there)
    if ! sed -n "/id: \"${V_ESC}\"/,/^    - version:\|^  [^ ]/p" "$HUGO_YAML" | grep -q 'hidden: true'; then
      sed -i "/id: \"${V_ESC}\"/,/order:/{/order:/a\\      hidden: true
      }" "$HUGO_YAML"
    fi
  fi
else
  # Version entry doesn't exist — insert before the first existing version entry
  new_order=$((max_order + 1))

  if [[ "$ACTION" == "release" ]]; then
    echo "Registering $VERSION (order=$new_order), setting as latest..."
    BLOCK="    - version: \"${VERSION}\"\n      url: \"/docs/${VERSION}/\"\n      id: \"${VERSION}\"\n      order: ${new_order}"
    sed -i "s/latest_version_id: \".*\"/latest_version_id: \"${VERSION}\"/" "$HUGO_YAML"
  else
    echo "Registering $VERSION as hidden draft (order=$new_order)..."
    BLOCK="    - version: \"${VERSION}\"\n      url: \"/docs/${VERSION}/\"\n      id: \"${VERSION}\"\n      order: ${new_order}\n      hidden: true"
  fi
  # Insert new version block before the first existing version entry
  sed -i "/^  versions:$/a\\${BLOCK}" "$HUGO_YAML"
fi

# Manage content mount files exclusion for draft versions
EXCLUDE_LINE="        - '! docs/${VERSION}/**'"
if [[ "$ACTION" == "draft" ]]; then
  if ! grep -qF "docs/${VERSION}/**" "$HUGO_YAML"; then
    echo "Excluding docs/${VERSION}/** from content mount..."
    sed -i "/- '! \*\*\/_include\/\*'/a\\${EXCLUDE_LINE}" "$HUGO_YAML"
  fi
else
  if grep -qF "docs/${VERSION}/**" "$HUGO_YAML"; then
    echo "Including docs/${VERSION}/** in content mount..."
    sed -i "\|docs/${VERSION}/\*\*|d" "$HUGO_YAML"
  fi
fi

echo "✓ Done. Current versions in hugo.yaml:"
yq '.params.versions[] | [.id, "order=" + (.order | tostring), (.hidden // false | tostring)] | join(" ")' "$HUGO_YAML"
