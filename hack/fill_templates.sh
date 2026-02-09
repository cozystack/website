#!/usr/bin/env bash
set -euo pipefail

# Set UTF-8 locale to ensure proper character encoding
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

usage() {
  cat <<'EOF'
Usage: hack/fill_templates.sh [OPTIONS]

Options:
  --branch BRANCH   Git branch in cozystack/cozystack (default: main)
  --apps  LIST      Space- or comma-separated list of apps to update
  --dest  PATH      Destination directory where final docs live (templates go to DEST/_include)
  --pkgdir DIR      Subdirectory under packages/ to fetch from (default: apps). Examples: apps, extra
  -h, --help        Show this help and exit

Notes:
  * Template markdown files are written to DEST/_include.
  * Each template file is named <app>.md and only contains the front matter.

Examples:
  hack/fill_templates.sh --apps "tenant redis" --dest content/en/docs/reference/applications
  hack/fill_templates.sh --apps "tenant,redis" --dest content/en/docs/reference/applications --branch feature/foo
EOF
}

BRANCH="main"
DEST_DIR=""
APPS=()
PKG_DIR="apps"

# -------------------- Parse arguments --------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --branch)
      BRANCH="$2"; shift 2 ;;
    --apps)
      IFS=', ' read -r -a APPS <<< "$2"; shift 2 ;;
    --dest)
      DEST_DIR="$2"; shift 2 ;;
    --pkgdir)
      PKG_DIR="$2"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      if [[ "$1" == --* ]]; then
        echo "Unknown option: $1" >&2
        usage; exit 1
      else
        APPS+=("$1"); shift
      fi
      ;;
  esac
done

if [[ ${#APPS[@]} -eq 0 ]]; then
  echo "Error: no apps specified. Use --apps." >&2
  usage; exit 1
fi

if [[ -z "$DEST_DIR" ]]; then
  echo "Error: --dest is required." >&2
  usage; exit 1
fi

# Derive where templates live
SRC_DIR="${DEST_DIR%/}/_include"
mkdir -p "$SRC_DIR"

GITHUB_REPO="cozystack/cozystack"
RAW_BASE_URL="https://raw.githubusercontent.com/${GITHUB_REPO}/${BRANCH}/packages/${PKG_DIR}"

for app in "${APPS[@]}"; do
  readme_url="${RAW_BASE_URL}/${app}/README.md"
  echo "Processing $app..."

  # Try to fetch the first line (title) of the README
  if ! first_line=$(curl -fsSL "$readme_url" | head -n 1); then
    echo "⚠️  Failed to fetch README for $app" >&2
    continue
  fi

  if [[ -z "$first_line" ]]; then
    echo "⚠️  README for $app has no content" >&2
    continue
  fi

  # Strip leading hashes and trim whitespace
  title=$(echo "$first_line" | sed 's/^#*\s*//' | xargs)
  # Remove words like Managed or Service from linkTitle (case-insensitive)
  link_title=$(echo "$title" | sed -E 's/\b(Managed|Service)\b//Ig' | xargs)

  template_file="${SRC_DIR%/}/${app}.md"
  cat > "$template_file" <<EOF
---
title: "$title"
linkTitle: "$link_title"
---

EOF
  echo "✓ Wrote template for $app -> $template_file"

done