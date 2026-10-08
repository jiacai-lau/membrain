#!/usr/bin/env bash
# Membrain brain sync: pull everyone's latest notes, commit your changes, push to THIS brain's own remote.
# Stops on a conflict (never overwrites anyone's work). Never force-pushes.
# Pushes only to the remote recorded in .membrain.yaml ('remote:'); a personal brain never pushes without one.
set -euo pipefail
cd "$(dirname "$0")/.."
msg="${1:-update notes}"
[ -d .githooks ] && [ -z "$(git config core.hooksPath)" ] && git config core.hooksPath .githooks   # lint hook in fresh clones
slug() { printf '%s' "$1" | sed -E 's#^(git@[^:]+:|ssh://git@[^/]+/|https?://[^/]+/)##; s#\.git$##; s#/$##'; }
field() { sed -nE "s/^$1:[[:space:]]*\"?([^\"#[:space:]]*)\"?.*/\1/p" .membrain.yaml 2>/dev/null | head -1; }
expected="$(field remote)"
visibility="$(field visibility)"
actual="$(git remote get-url origin 2>/dev/null || true)"
branch="$(git branch --show-current)"
push_ok=1
if [ -z "$actual" ]; then
  push_ok=0; why="no remote yet"
elif [ -n "$expected" ] && [ "$(slug "$actual")" != "$(slug "$expected")" ]; then
  echo "sync: origin ($actual) is not this brain's remote ($expected). Not syncing. Fix the remote or 'remote:' in .membrain.yaml." >&2
  exit 1
elif [ -z "$expected" ] && [ "$visibility" = "personal" ]; then
  push_ok=0; why="personal brain has no 'remote:' in .membrain.yaml, so it never pushes"
fi
if [ "$push_ok" = 1 ] && git ls-remote --exit-code --heads origin "$branch" >/dev/null 2>&1; then
  git pull --rebase --autostash origin "$branch" || {
    echo "Conflict on pull. Keep both people's lines, delete the conflict markers, then: git add -A && git rebase --continue && ./scripts/sync.sh. Never force-push." >&2
    exit 1; }
fi
if [ -n "$(git status --porcelain)" ]; then
  git add -A
  git commit -q -m "$msg" || { echo "Commit blocked (the lint pre-commit hook found a leak?). Fix the findings above, then sync again." >&2; exit 1; }
fi
if [ "$push_ok" = 0 ]; then
  echo "Committed locally only: $why."
  exit 0
fi
git push origin "HEAD:$branch" || { echo "Push failed. Run ./scripts/sync.sh again; if git reports a conflict, fix it by hand. Never force-push." >&2; exit 1; }
echo "Brain synced."
