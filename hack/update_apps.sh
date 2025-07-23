#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: hack/update_apps.sh [OPTIONS]

Options:
  --branch BRANCH   Git branch in cozystack/cozystack (default: main)
  --apps  LIST      Space- or comma-separated list of apps to update
  --dest  PATH      Destination directory to write the *.md files to
  -h, --help        Show this help and exit

Notes:
  * Template markdown files are expected in DEST_DIR/_include (derived automatically).
  * Each template file should be named <app>.md.

Examples:
  hack/update_apps.sh --apps "tenant redis" --dest content/en/docs/reference/applications
  hack/update_apps.sh --apps "tenant,redis" --dest content/en/docs/reference/applications --branch feature/foo
EOF
}

BRANCH="main"
DEST_DIR=""
APPS=()

# -------------------- Parse arguments --------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --branch)
      BRANCH="$2"; shift 2 ;;
    --apps)
      IFS=', ' read -r -a APPS <<< "$2"; shift 2 ;;
    --dest)
      DEST_DIR="$2"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      # allow trailing positional apps as well
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

# Derive templates location: DEST_DIR/_include
SRC_DIR="${DEST_DIR%/}/_include"

GITHUB_REPO="cozystack/cozystack"
RAW_BASE_URL="https://raw.githubusercontent.com/${GITHUB_REPO}/${BRANCH}/packages/apps"

mkdir -p "$DEST_DIR"

for app in "${APPS[@]}"; do
  src_file="${SRC_DIR%/}/${app}.md"
  dest_file="${DEST_DIR%/}/${app}.md"

  # Ensure template exists (touch if missing)
  [[ -f "$src_file" ]] || touch "$src_file"

  # Copy template to destination (overwrite)
  cp "$src_file" "$dest_file"

  readme_url="${RAW_BASE_URL}/${app}/README.md"
  echo "Processing $app..."

  if curl -fsSL "$readme_url" \
    | awk 'NR==1 && /^#{1,2} / { next } { print }' >> "$dest_file"; then
    echo "✓ Appended README for $app -> $dest_file"
  else
    echo "⚠️  Failed to fetch README for $app" >&2
  fi

done