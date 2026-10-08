#!/usr/bin/env bash
# Membrain self-test. Generates a throwaway workspace from Membrain (BASE = raw URL or local folder),
# then checks lint, spin-off with a privacy block, routing, the pre-commit hook and a no-op upgrade.
# usage: tests/run.sh [BASE]     (default BASE: 'source' in .membrain.yaml)      exit 0 = all passed
set -uo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
BASE="${1:-$(python3 -c "import json,re,sys;t=open('$HERE/.membrain.yaml').read();print(json.loads(re.search(r'^source: (.*)$',t,re.M).group(1)))" 2>/dev/null)}"
[[ -n "$BASE" ]] || { echo "usage: tests/run.sh BASE"; exit 2; }
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
export MB_TODAY=2026-10-08 GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t
pass=0; fail=0
check(){ if eval "$2"; then echo "PASS  $1"; pass=$((pass+1)); else echo "FAIL  $1"; fail=$((fail+1)); fi; }

MB="$HERE/scripts/membrain.py"; [ -f "$MB" ] || MB="$HERE/../scripts/membrain.py"   # workspace, or templates/ in the Membrain repo
python3 "$MB" setup --base "$BASE" --workspace "$TMP/ws" --owner alice --aliases "alpha-notes" \
   --date 2026-10-08 --no-selftest >"$TMP/setup.log" 2>&1
check "setup generates a workspace from templates" "[ -f '$TMP/ws/.membrain.yaml' ] && [ -f '$TMP/ws/AGENTS.md' ]"
cd "$TMP/ws" || exit 1
check "personal brain is a local git repo"     "[ -d brains/personal/.git ]"
check "no remote was added"                    "[ -z \"\$(git -C brains/personal remote)\" ]"

out="$(python3 scripts/lint.py tests/fixtures --visibility shared --skip sitemap)"; rc=$?
check "lint exits 1 on errors"                 "[ $rc = 1 ]"
check "lint finds the triplicated line twice"  "[ \$(grep -c 'E010 duplicate-line' <<<\"\$out\") = 2 ]"
check "lint flags money, phone, missing date"  "grep -q E101 <<<\"\$out\" && grep -q E103 <<<\"\$out\" && grep -q E001 <<<\"\$out\""

mkdir -p brains/personal/projects/a
printf '# Q&A\n\n- Label printer prints blank labels → reload the roll glossy side down · Client A · 2026-10-01 · @alice · verified\n' > brains/personal/projects/a/clean.md
printf '# Deal\n\n- Proposal quoted SGD 1,200 and the grant covers half · Client B · 2026-10-01 · @alice · unverified\n' > brains/personal/projects/a/deal.md
git -C brains/personal add -A >/dev/null; git -C brains/personal commit -qm notes >/dev/null 2>&1
scripts/spinoff.sh team --topics "client issue,known fix" --keywords "printer,label" --base "$BASE" \
   --move projects/a/clean.md:playbook/clean.md --move projects/a/deal.md >"$TMP/spin.log" 2>&1; rc=$?
check "spinoff exits 3 when a move is blocked" "[ $rc = 3 ]"
check "shared brain generated + own git repo"  "[ -d brains/team/.git ] && [ -f brains/team/.membrain/lint.py ]"
check "clean file moved, stub left"            "[ -f brains/team/playbook/clean.md ] && grep -q '→ team:playbook/clean.md' brains/personal/projects/a/clean.md"
check "private file NOT moved"                 "[ ! -e brains/team/projects/a/deal.md ] && grep -q SGD brains/personal/projects/a/deal.md"
check "route registered + ROUTES refreshed"    "grep -q 'name: team' brains/personal/brains.yaml && grep -q '| team | shared |' brains/personal/ROUTES.md"
check "shared brain never names personal"      "! grep -rqi 'alpha-notes\|brains/personal' brains/team --exclude-dir=.git --exclude-dir=.membrain"
check "workspace lints clean"                  "python3 scripts/lint.py . >/dev/null"
check "clean fix routes to shared brain"       "scripts/route.py classify 'label printer prints blank, reload the roll fix' | grep -q 'WRITE -> team'"
check "money routes to personal"               "scripts/route.py classify 'quotation of SGD 500' | grep -q 'WRITE -> personal'"
echo '- See alpha-notes for the price → n/a · Client A · 2026-10-08 · @alice' >> brains/team/playbook/fixes.md
git -C brains/team add -A >/dev/null; git -C brains/team commit -qm leak >/dev/null 2>&1; rc=$?
check "pre-commit hook blocks private reference" "[ $rc != 0 ]"
git -C brains/team checkout -q -- . 2>/dev/null; git -C brains/team reset -q --hard
up="$(scripts/upgrade.sh --base "$BASE")"
check "upgrade dry-run on a fresh workspace proposes nothing" "grep -q 'none: every framework file is current' <<<\"\$up\""

echo "--- $pass passed, $fail failed"
[ $fail = 0 ]
