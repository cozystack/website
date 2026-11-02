#!/usr/bin/env bash
set -euo pipefail

# Run after Hugo. Python handles URL escaping and keeps rewritten query strings
# and fragments unchanged. No third-party Python packages are needed.
exec python3 "$(dirname "$0")/mirror_latest.py" "${1:-public}"
