#!/usr/bin/env bash
# Offline self-check for the data/versions/*.yaml pin pipeline
# (hack/update_versions.sh).
# Run from the repo root: hack/test_version_pins.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
fail=0
check() {  # check <description> <expected> <actual>
  if [[ "$2" == "$3" ]]; then
    echo "ok   $1"
  else
    echo "FAIL $1: expected '$2', got '$3'"; fail=1
  fi
}

# shellcheck source=hack/update_versions.sh
source hack/update_versions.sh

# GitHub lists releases newest-created first.
check "resolver skips a draft and a prerelease" "v1.6.3" "$(latest_published_tag <<'EOF'
[
  {"tag_name": "v1.6.4", "draft": true, "prerelease": false},
  {"tag_name": "v1.7.0-rc.1", "draft": false, "prerelease": true},
  {"tag_name": "v1.6.3", "draft": false, "prerelease": false},
  {"tag_name": "v1.6.2", "draft": false, "prerelease": false}
]
EOF
)"

check "resolver picks the highest version, not the newest release" "v1.6.3" "$(latest_published_tag <<'EOF'
[
  {"tag_name": "v1.5.9", "draft": false, "prerelease": false},
  {"tag_name": "v1.6.3", "draft": false, "prerelease": false},
  {"tag_name": "v1.5.8", "draft": false, "prerelease": false}
]
EOF
)"

check "resolver prints nothing when no release is published" "" "$(latest_published_tag <<<'[{"tag_name": "v1.6.4", "draft": true, "prerelease": false}]')"

sandbox="$(mktemp -d)"
trap 'rm -rf "$sandbox"' EXIT

# update_versions.sh must send GITHUB_TOKEN on curl's stdin, never in argv
# where any process listing shows it. A PATH stub stands in for curl.
mkdir -p "$sandbox/bin"
cat > "$sandbox/bin/curl" <<'EOF'
#!/usr/bin/env bash
echo "argv: $*" >> "$CURL_LOG"
case "$*" in
  *api.github.com*)
    if [[ "$*" == *"--header @-"* ]]; then sed 's/^/stdin: /' >> "$CURL_LOG"; fi
    echo '[{"tag_name": "v1.6.3", "draft": false, "prerelease": false}]' ;;
  *) echo 'version: v1.13.6' ;;
esac
EOF
chmod +x "$sandbox/bin/curl"
run_update() {
  CURL_LOG="$sandbox/curl.log" PATH="$sandbox/bin:$PATH" \
    hack/update_versions.sh --dest "$sandbox/pin.yaml" >/dev/null
}
GITHUB_TOKEN=s3cr3t run_update
check "token stays out of curl argv" "0" "$(grep --count '^argv: .*s3cr3t' "$sandbox/curl.log" || true)"
check "token is sent as a header on stdin" "1" "$(grep --count '^stdin: Authorization: token s3cr3t$' "$sandbox/curl.log" || true)"
check "pin file takes the resolved release" '"v1.6.3"' "$(awk '/^cozystack_tag:/{print $2}' "$sandbox/pin.yaml")"
rm "$sandbox/curl.log"
(unset GITHUB_TOKEN GH_TOKEN; run_update)
check "no token, plain request" "argv: -fsSL https://api.github.com/repos/cozystack/cozystack/releases?per_page=100" "$(grep 'api.github.com' "$sandbox/curl.log")"

# Without jq the default tag cannot be resolved: the error must say so rather
# than claim upstream has no published release. An explicit tag needs no jq.
mkdir -p "$sandbox/nojq"
for tool in bash awk sed grep sort tail mkdir dirname cat; do
  ln -s "$(type -P "$tool")" "$sandbox/nojq/$tool"
done
ln -s "$sandbox/bin/curl" "$sandbox/nojq/curl"
run_nojq() {
  CURL_LOG="$sandbox/curl.log" PATH="$sandbox/nojq" \
    hack/update_versions.sh --dest "$sandbox/pin.yaml" "$@" 2>&1
}
echo keep > "$sandbox/pin.yaml"
rc=0; out="$(run_nojq)" || rc=$?
check "no jq, no tag: exits non-zero" "1" "$rc"
check "no jq, no tag: error names jq" "1" "$(grep --count 'jq is required' <<<"$out" || true)"
check "no jq, no tag: pin file untouched" "keep" "$(cat "$sandbox/pin.yaml")"
run_nojq --cozystack-tag v1.6.2 >/dev/null
check "no jq, explicit tag: pins it" '"v1.6.2"' "$(awk '/^cozystack_tag:/{print $2}' "$sandbox/pin.yaml")"

exit "$fail"
