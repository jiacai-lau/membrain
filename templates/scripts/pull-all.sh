#!/usr/bin/env bash
# Pull every registered brain that has a git remote (fast-forward only). Run from the workspace root.
set -euo pipefail
python3 "$(dirname "$0")/route.py" paths --registry brains/personal/brains.yaml | while IFS=$'\t' read -r name path vis remote; do
  if [[ -d "$path/.git" ]] && git -C "$path" remote get-url origin >/dev/null 2>&1; then
    echo "== $name"; git -C "$path" pull --ff-only -q && echo "  up to date"
  else
    echo "== $name: no git remote yet, skipped"
  fi
done
