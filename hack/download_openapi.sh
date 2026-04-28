#!/usr/bin/env bash
set -euo pipefail

# Download openapi.json from GitHub releases for each docs version that needs it.
# Versions with api.json already in content/ (v0, v1.0) are skipped.
# For other versions, finds the latest matching release and downloads openapi.json.
#
# Works without gh CLI — uses GitHub API via curl.

REPO="cozystack/cozystack"
API_BASE="https://api.github.com/repos/${REPO}"
DOCS_BASE="content/en/docs"
STATIC_BASE="static/docs"

# Optional: set GITHUB_TOKEN for higher rate limits
AUTH_HEADER=""
if [[ -n "${GITHUB_TOKEN:-}" ]]; then
  AUTH_HEADER="Authorization: token ${GITHUB_TOKEN}"
fi

curl_gh() {
  if [[ -n "$AUTH_HEADER" ]]; then
    curl -fsSL -H "$AUTH_HEADER" "$@"
  else
    curl -fsSL "$@"
  fi
}

# Fetch all releases once (up to 100)
RELEASES_JSON=$(curl_gh "${API_BASE}/releases?per_page=100")

for version_dir in ${DOCS_BASE}/v*/; do
  version=$(basename "$version_dir")

  # Skip if no cozystack-api section exists
  [[ -d "${version_dir}cozystack-api" ]] || continue

  # Skip if api.json already exists in content (committed to git, e.g., v0, v1.0)
  if [[ -f "${version_dir}cozystack-api/api.json" ]]; then
    echo "Skipping $version — api.json exists in content/"
    continue
  fi

  # Determine release tag pattern
  if [[ "$version" == "v0" ]]; then
    tag_pattern="^v0\\."
  else
    tag_pattern="^${version}\\."
  fi

  echo "Finding latest release for $version (pattern: ${tag_pattern})..."

  # Find the latest stable release matching this version. Prereleases must be
  # excluded explicitly: GNU `sort -V` orders e.g. v1.3.0-rc.1 AFTER v1.3.0
  # (opposite of semver), so without this filter `tail -1` would pick the rc.
  latest_tag=$(echo "$RELEASES_JSON" \
    | jq -r '.[] | select(.draft == false and .prerelease == false) | .tag_name' \
    | grep -E "$tag_pattern" \
    | sort -V \
    | tail -1 || true)

  if [[ -z "$latest_tag" ]]; then
    echo "⚠️  No release found for $version, skipping"
    continue
  fi

  download_url="https://github.com/${REPO}/releases/download/${latest_tag}/openapi.json"
  echo "Downloading openapi.json from $latest_tag for $version..."
  mkdir -p "${STATIC_BASE}/${version}/cozystack-api"

  if curl -fsSL -o "${STATIC_BASE}/${version}/cozystack-api/api.json" "$download_url"; then
    echo "✓ Downloaded openapi.json for $version ($latest_tag)"
  else
    echo "⚠️  Failed to download openapi.json for $version ($latest_tag), skipping"
  fi
done
