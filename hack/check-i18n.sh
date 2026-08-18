#!/usr/bin/env bash
#
# check-i18n.sh — fast CI guards for the multi-language website.
#
# Subcommands:
#   check           (default) Run every guard; exit non-zero on any gap.
#                   Hand-localized pages (l10n: transcreate) get a ::warning::
#                   instead of an error when they drift: the pipeline never
#                   regenerates them, so drift is a report for a human, not a
#                   build failure.
#   update-digests [file...]
#                   Recompute and rewrite `source_digest` in translated pages
#                   from their English source. Run after editing an English
#                   source or after adding/refreshing a translation. Without
#                   arguments, hand-localized pages are SKIPPED (a wholesale
#                   re-stamp would silence their drift report); pass the file
#                   explicitly to re-stamp one you refreshed by hand.
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

# A page a human localized by hand (l10n: transcreate). The pipeline never
# regenerates these, so a stale digest here is a drift REPORT, not a build
# failure — and re-stamping it wholesale would silence the report while the
# drift persists.
is_transcreate() {
  grep -m1 -E '^l10n:' "$1" 2>/dev/null | grep -qE '^l10n:[[:space:]]*"?transcreate"?[[:space:]]*$'
}

# Map content/<lang>/<rel> -> content/en/<rel>
en_source_for() {
  local f="$1"
  local stripped="${f#"$CONTENT_DIR"/}"      # <lang>/<rel>
  local rel="${stripped#*/}"                   # <rel>
  echo "$CONTENT_DIR/$DEFAULT_LANG/$rel"
}

# The latest docs version (params.latest_version_id in hugo.yaml). The pipeline
# only ever refreshes the latest version, so a stale digest on an older,
# noindex'd version is not something a PR can fix by rerunning. Read once and
# cached. lib.py fails closed on a missing key; here we degrade to an empty
# value, which turns is_superseded_docs into a no-op (nothing is treated as
# superseded) rather than silencing a genuine error.
LATEST_DOCS=""
latest_docs_version() {
  local hugo; hugo="$(dirname "$CONTENT_DIR")/hugo.yaml"
  [ -f "$hugo" ] || return 0
  grep -m1 -E '^[[:space:]]*latest_version_id:' "$hugo" \
    | sed -E 's/.*latest_version_id:[[:space:]]*"?([^"[:space:]]+)"?.*/\1/'
}

# True when f is a translated docs page of a NON-latest version
# (content/<lang>/docs/<ver>/... with ver != latest). Such a page is out of the
# pipeline's scope: it is never refreshed and is removed by the next pipeline
# run (find_orphan_translations), so a drifted digest on it must be advisory,
# not a CI blocker for every unrelated PR in the repo.
is_superseded_docs() {
  [ -n "$LATEST_DOCS" ] || return 1
  local rel="${1#"$CONTENT_DIR"/}"; rel="${rel#*/}"   # <rel> under the lang
  case "$rel" in
    docs/*/*)
      local ver="${rel#docs/}"; ver="${ver%%/*}"
      [ "$ver" != "$LATEST_DOCS" ]
      ;;
    *) return 1 ;;
  esac
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
  LATEST_DOCS="$(latest_docs_version)"
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
      if is_transcreate "$f"; then
        # Advisory by design: a drifted transcreation is refreshed when a
        # human decides to, and must not block unrelated PRs meanwhile.
        echo "::warning::hand-localized page drifted from its English source: $f"
        echo "    refresh the transcreation by hand, then re-stamp it with:"
        echo "    hack/check-i18n.sh update-digests $f"
      elif is_superseded_docs "$f"; then
        # Out of the pipeline's scope: the latest version is $LATEST_DOCS, the
        # pipeline never refreshes older versions, and its next run removes this
        # page as a superseded orphan. Failing the lint here would block every
        # unrelated PR on a page no PR can fix by rerunning the pipeline.
        echo "::warning::stale translation of a superseded docs version (latest is $LATEST_DOCS): $f"
        echo "    the pipeline removes superseded translations on its next run; not a blocker."
      else
        rc=1
        echo "::error::stale translation: $f"
        echo "    English source: $src"
        echo "    recorded digest: sha256:${actual}"
        echo "    current  digest: sha256:${expected}"
        echo "    fix: refresh the translation, then run 'hack/check-i18n.sh update-digests'"
      fi
    fi
  done < <(translated_digest_files)
  [ "$rc" -eq 0 ] && echo "translation freshness: OK ($checked translated pages match their English source)"
  return "$rc"
}

update_digests() {
  # With explicit files, re-stamp exactly those — the escape hatch for a
  # transcreation a human just refreshed. With no arguments, re-stamp every
  # machine-translated page but SKIP hand-localized ones: their stale digest
  # is the only signal that the transcreation drifted, and a wholesale
  # re-stamp would silence it while the drift persists.
  local f
  {
    # `|| true`: with zero stamped translations the underlying grep exits 1,
    # which under `set -euo pipefail` would silently kill the whole script.
    if [ "$#" -gt 0 ]; then printf '%s\n' "$@"; else translated_digest_files || true; fi
  } | while IFS= read -r f; do
    [ -z "$f" ] && continue
    if [ "$#" -eq 0 ] && is_transcreate "$f"; then
      echo "skip $f — hand-localized (l10n: transcreate); refresh it by hand, then: hack/check-i18n.sh update-digests $f"
      continue
    fi
    local src expected tmp
    src="$(en_source_for "$f")"
    if [ ! -f "$src" ]; then
      echo "::warning::skip $f — English source missing: $src"
      continue
    fi
    # The awk below only REWRITES an existing line; without this check a page
    # missing the field would pass through untouched yet be reported "updated".
    if ! grep -qE '^source_digest:' "$f"; then
      echo "::warning::skip $f — no source_digest line in the front matter; add one, then re-run"
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
  done
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
    shift
    update_digests "$@"
    ;;
  *)
    echo "usage: $0 [check|update-digests [file...]]" >&2
    exit 2
    ;;
esac
