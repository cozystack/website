#!/usr/bin/env bash
#
# check-i18n.sh — fast CI guards for the multi-language website.
#
# Subcommands:
#   check           (default) Run every guard; exit non-zero on any gap.
#   update-digests  Recompute and rewrite `source_digest` in every translated
#                   page from its English source. Run this after editing an
#                   English source or after adding/refreshing a translation.
#
# Guards run by `check`:
#   1. i18n key parity  — every i18n/<lang>.toml must define exactly the same
#      top-level keys as the reference i18n/en.toml. A missing key would render
#      as a visible `[i18n] <key>` placeholder on translated pages because
#      hugo.yaml sets `enableMissingTranslationPlaceholders: true`; an extra key
#      is almost always a typo. Both fail the build.
#   2. translation freshness — every translated page carrying a `source_digest`
#      front-matter field must match the current sha256 of its English source
#      (content/en/<same-relative-path>). A mismatch means the English page
#      changed after the translation was made, so the translation is stale.
#
# No Hugo/Node/toolchain required — pure shell, safe as a quick pull-request lint.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

I18N_DIR="i18n"
CONTENT_DIR="content"
DEFAULT_LANG="en"

sha256() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum --algorithm 256 "$1" | awk '{print $1}'
  fi
}

# Fully-qualified translation keys (`table.subkey`, e.g. `note.other`),
# sorted and de-duplicated. Emitting the plural sub-key (`other`, `one`, …)
# rather than just the `[table]` header means parity also catches a missing
# plural form, not only a missing table. The table regex accepts any character
# so hyphen/dot key names are not silently dropped.
toml_keys() {
  awk '
    /^[[:space:]]*#/ { next }
    /^[[:space:]]*\[.+\][[:space:]]*$/ {
      tbl = $0
      sub(/^[[:space:]]*\[/, "", tbl)
      sub(/\][[:space:]]*$/, "", tbl)
      next
    }
    /=/ && tbl != "" {
      sub(/[[:space:]]*=.*$/, "")
      gsub(/[[:space:]]/, "")
      if ($0 != "") print tbl "." $0
    }
  ' "$1" | sort -u
}

# Enumerate translated files (any content/<lang>/... except content/en/...)
# that declare a `source_digest` front-matter field.
translated_digest_files() {
  grep -rlE '^source_digest:' "$CONTENT_DIR" \
    | grep -vE "^$CONTENT_DIR/$DEFAULT_LANG/" \
    | sort
}

# Map content/<lang>/<rel> -> content/en/<rel>
en_source_for() {
  local f="$1"
  local stripped="${f#"$CONTENT_DIR"/}"      # <lang>/<rel>
  local rel="${stripped#*/}"                   # <rel>
  echo "$CONTENT_DIR/$DEFAULT_LANG/$rel"
}

check_key_parity() {
  local ref="$I18N_DIR/$DEFAULT_LANG.toml"
  local rc=0
  if [ ! -f "$ref" ]; then
    echo "::error::reference i18n file not found: $ref"
    return 1
  fi
  local ref_keys
  ref_keys="$(toml_keys "$ref")"
  if [ -z "$ref_keys" ]; then
    echo "::error::reference $ref produced 0 keys — parser or file is broken; refusing to report a false pass"
    return 1
  fi
  local f
  for f in "$I18N_DIR"/*.toml; do
    [ "$f" = "$ref" ] && continue
    local lang_keys missing extra
    lang_keys="$(toml_keys "$f")"
    missing="$(comm -23 <(printf '%s\n' "$ref_keys") <(printf '%s\n' "$lang_keys") || true)"
    extra="$(comm -13 <(printf '%s\n' "$ref_keys") <(printf '%s\n' "$lang_keys") || true)"
    if [ -n "$missing" ] || [ -n "$extra" ]; then
      rc=1
      echo "::error::i18n key mismatch in $f (reference: $ref)"
      if [ -n "$missing" ]; then
        echo "  missing keys (would render as [i18n] placeholders):"
        printf '%s\n' "$missing" | sed 's/^/    - /'
      fi
      if [ -n "$extra" ]; then
        echo "  extra keys (not present in $DEFAULT_LANG, likely a typo):"
        printf '%s\n' "$extra" | sed 's/^/    - /'
      fi
    fi
  done
  [ "$rc" -eq 0 ] && echo "i18n key parity: OK ($(printf '%s\n' "$ref_keys" | grep -c . ) keys across all languages)"
  return "$rc"
}

check_digest_freshness() {
  local rc=0
  local checked=0
  local f
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    local src expected actual
    src="$(en_source_for "$f")"
    if [ ! -f "$src" ]; then
      rc=1
      echo "::error::$f references English source that does not exist: $src"
      continue
    fi
    expected="$(sha256 "$src")"
    actual="$(grep -m1 -E '^source_digest:' "$f" | sed -E 's/.*sha256:([0-9a-fA-F]+).*/\1/')"
    checked=$((checked + 1))
    if [ "$actual" != "$expected" ]; then
      rc=1
      echo "::error::stale translation: $f"
      echo "    English source: $src"
      echo "    recorded digest: sha256:${actual}"
      echo "    current  digest: sha256:${expected}"
      echo "    fix: refresh the translation, then run 'hack/check-i18n.sh update-digests'"
    fi
  done < <(translated_digest_files)
  [ "$rc" -eq 0 ] && echo "translation freshness: OK ($checked translated pages match their English source)"
  return "$rc"
}

update_digests() {
  local f
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    local src expected tmp
    src="$(en_source_for "$f")"
    if [ ! -f "$src" ]; then
      echo "::warning::skip $f — English source missing: $src"
      continue
    fi
    expected="$(sha256 "$src")"
    tmp="$(mktemp)"
    awk -v d="sha256:${expected}" '
      /^source_digest:/ && !done { print "source_digest: \"" d "\""; done=1; next }
      { print }
    ' "$f" > "$tmp"
    mv "$tmp" "$f"
    echo "updated $f -> sha256:${expected}"
  done < <(translated_digest_files)
}

cmd="${1:-check}"
case "$cmd" in
  check)
    rc=0
    check_key_parity || rc=1
    check_digest_freshness || rc=1
    exit "$rc"
    ;;
  update-digests)
    update_digests
    ;;
  *)
    echo "usage: $0 [check|update-digests]" >&2
    exit 2
    ;;
esac
