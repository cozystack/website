#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: hack/init_version.sh --version VERSION [--from VERSION]

Initialize a new docs version directory by copying from an existing version.
If the target directory already exists, does nothing.

Options:
  --version VERSION   Target version to create (e.g., v1.3)
  --from VERSION      Source version to copy from (default: auto-detect latest)
  -h, --help          Show this help and exit

Examples:
  hack/init_version.sh --version v1.3
  hack/init_version.sh --version v1.3 --from v1.2
EOF
}

VERSION=""
FROM_VERSION=""
DOCS_BASE="content/en/docs"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version) VERSION="$2"; shift 2 ;;
    --from)    FROM_VERSION="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ -z "$VERSION" ]]; then
  echo "Error: --version is required." >&2
  usage; exit 1
fi

TARGET_DIR="${DOCS_BASE}/${VERSION}"

if [[ -d "$TARGET_DIR" ]] && [[ -n "$(ls -A "$TARGET_DIR" 2>/dev/null)" ]]; then
  echo "Directory $TARGET_DIR already exists and is not empty, skipping init."
  exit 0
fi

# Auto-detect source version: find the latest existing version directory
if [[ -z "$FROM_VERSION" ]]; then
  FROM_VERSION=$(ls -d ${DOCS_BASE}/v[0-9]* 2>/dev/null \
    | xargs -I{} basename {} \
    | grep -v "^${VERSION}$" \
    | sort -V \
    | tail -1)

  if [[ -z "$FROM_VERSION" ]]; then
    echo "Error: could not auto-detect source version. Use --from." >&2
    exit 1
  fi
fi

SOURCE_DIR="${DOCS_BASE}/${FROM_VERSION}"

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "Error: source directory $SOURCE_DIR does not exist." >&2
  exit 1
fi

echo "Initializing $VERSION from $FROM_VERSION..."

# Copy content (exclude api.json which is downloaded at build time)
mkdir -p "$TARGET_DIR"
cp -a "${SOURCE_DIR}/." "${TARGET_DIR}/"
find "$TARGET_DIR" -name 'api.json' -delete

# Update internal doc references (both /docs/vX.Y/ URLs and "docs/vX.Y/" Hugo refs)
find "$TARGET_DIR" -name '*.md' -exec sed -i.bak \
  -e "s|/docs/${FROM_VERSION}/|/docs/${VERSION}/|g" \
  -e "s|\"docs/${FROM_VERSION}/|\"docs/${VERSION}/|g" \
  {} +
find "$TARGET_DIR" -name '*.bak' -delete

# Update _index.md frontmatter
if [[ -f "$TARGET_DIR/_index.md" ]]; then
  # Remove aliases from previous version (they belong to that version only)
  sed -i.bak '/^aliases:/,/^[^ ]/{ /^aliases:/d; /^  - /d; }' "$TARGET_DIR/_index.md"

  if [[ "$VERSION" == "next" ]]; then
    # Rewrite title/linkTitle to the unreleased form and prepend a draft banner
    sed -i.bak \
      -e 's|^title: .*|title: "Cozystack Next (unreleased)"|' \
      -e 's|^linkTitle: .*|linkTitle: "Cozystack Next"|' \
      -e 's|^weight: .*|weight: 5|' \
      "$TARGET_DIR/_index.md"
    # Prepend a draft banner shortcode block right after the frontmatter, if missing
    if ! grep -q '^{{% warning %}}$' "$TARGET_DIR/_index.md"; then
      python3 - "$TARGET_DIR/_index.md" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1])
src = p.read_text()
head, sep, body = src.partition('\n---\n')
banner = (
    '\n\n{{% warning %}}\n'
    '**This is documentation for an unreleased version of Cozystack.** '
    'Content may change before release. For the current stable release, see '
    '[the latest documentation](/docs/).\n'
    '{{% /warning %}}\n'
)
p.write_text(head + sep + banner + body.lstrip('\n'))
PY
    fi
  else
    sed -i.bak "s|Cozystack ${FROM_VERSION}|Cozystack ${VERSION}|g" "$TARGET_DIR/_index.md"
  fi
  rm -f "$TARGET_DIR/_index.md.bak"
fi

echo "✓ Initialized $TARGET_DIR from $SOURCE_DIR"

# Also seed data/versions/$VERSION.yaml from the source version, so the
# {{< version-pin >}} shortcode resolves in the freshly-copied content.
VERSIONS_DIR="data/versions"
SOURCE_DATA="${VERSIONS_DIR}/${FROM_VERSION}.yaml"
TARGET_DATA="${VERSIONS_DIR}/${VERSION}.yaml"
if [[ -f "$SOURCE_DATA" ]]; then
  mkdir -p "$VERSIONS_DIR"
  if [[ -e "$TARGET_DATA" ]]; then
    echo "  $TARGET_DATA already exists; leaving it as-is."
  else
    cp "$SOURCE_DATA" "$TARGET_DATA"
    echo "✓ Seeded $TARGET_DATA from $SOURCE_DATA"
  fi
else
  echo "  Note: $SOURCE_DATA not found; skipped version pins. Create $TARGET_DATA manually if the docs use {{< version-pin >}}."
fi

if [[ "$VERSION" == "next" ]]; then
  echo "  Trunk directory ready. Edit content/en/docs/next/ for upcoming release work."
  echo "  Bump data/versions/next.yaml to the target release's pinned versions."
else
  echo "  Review _index.md frontmatter (title, weight, aliases) and $TARGET_DATA."
fi
