#!/usr/bin/env bash
# Session start / before each prompt: pull this brain if the last fetch was more than 10 minutes ago.
# Never blocks the agent: always exits 0.
cd "$(dirname "$0")/.." || exit 0
# Turn on the lint pre-commit hook in fresh clones (git does not carry this setting).
[ -d .githooks ] && [ -z "$(git config core.hooksPath)" ] && git config core.hooksPath .githooks
git remote get-url origin >/dev/null 2>&1 || exit 0
if [ -z "$(find .git/FETCH_HEAD -mmin -10 2>/dev/null)" ]; then
  git pull --rebase --autostash -q origin "$(git branch --show-current)" >/dev/null 2>&1 || {
    touch .git/FETCH_HEAD 2>/dev/null
    echo "$(basename "$PWD"): pull failed or conflict; run ./scripts/sync.sh to see why and fix it by hand" >&2; }
fi
exit 0
