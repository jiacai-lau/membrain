#!/usr/bin/env bash
# Workspace hook: run every brain's own sync hook. 'pull' = pull-if-stale.sh, 'push' = push-if-changed.sh.
# Each brain pushes only to its own remote (see brains/<name>/scripts/sync.sh). Never blocks: always exits 0.
cd "$(dirname "$0")/.." || exit 0
mode="${1:-pull}"
for b in brains/*/; do
  b="${b%/}"
  s="$b/scripts/pull-if-stale.sh"
  [ "$mode" = "push" ] && s="$b/scripts/push-if-changed.sh"
  [ -d "$b/.git" ] && [ -f "$s" ] && bash "$s"
done
exit 0
