#!/usr/bin/env bash
# End of each agent response: if this brain changed, run sync.sh (pull, commit, push). Fast no-op when nothing changed.
# Never blocks the agent: always exits 0.
cd "$(dirname "$0")/.." || exit 0
[ -z "$(git status --porcelain 2>/dev/null)" ] && exit 0
bash ./scripts/sync.sh "${1:-agent update $(date '+%Y-%m-%d %H:%M')}" >/dev/null 2>&1 || \
  echo "$(basename "$PWD"): sync failed (conflict, lint block or push error); run ./scripts/sync.sh to see why" >&2
exit 0
