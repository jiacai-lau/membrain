#!/usr/bin/env bash
# Membrain self-test. Generates a throwaway workspace from Membrain (BASE = raw URL or local folder),
# then checks lint (core + plugin), spin-off with a privacy block, routing, the pre-commit hook, the sync scripts
# (own-remote only, never force), the log format, the catalog (list/diff/install from a public and a private source,
# spin-off from a brain kind) and a no-op upgrade.
# usage: tests/run.sh [BASE]     (default BASE: 'source' in .membrain.yaml)      exit 0 = all passed
set -uo pipefail
# A pipe into grep -c (not grep -q) reads all input, so pipefail never sees SIGPIPE from the producer.
HERE="$(cd "$(dirname "$0")/.." && pwd)"
BASE="${1:-$(python3 -c "import json,re,sys;t=open('$HERE/.membrain.yaml').read();print(json.loads(re.search(r'^source: (.*)$',t,re.M).group(1)))" 2>/dev/null)}"
[[ -n "$BASE" ]] || { echo "usage: tests/run.sh BASE"; exit 2; }
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
export MB_TODAY=2026-10-08 GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t PYTHONDONTWRITEBYTECODE=1
pass=0; fail=0
check(){ if eval "$2"; then echo "PASS  $1"; pass=$((pass+1)); else echo "FAIL  $1"; fail=$((fail+1)); fi; }

MB="$HERE/scripts/membrain.py"; [ -f "$MB" ] || MB="$HERE/../scripts/membrain.py"   # workspace, or templates/ in the Membrain repo
python3 "$MB" setup --base "$BASE" --workspace "$TMP/ws" --owner alice --aliases "alpha-notes" \
   --date 2026-10-08 --no-selftest >"$TMP/setup.log" 2>&1
check "setup generates a workspace from templates" "[ -f '$TMP/ws/.membrain.yaml' ] && [ -f '$TMP/ws/AGENTS.md' ]"
cd "$TMP/ws" || exit 1
check "personal brain is a local git repo"     "[ -d brains/personal/.git ]"
check "no remote was added"                    "[ -z \"\$(git -C brains/personal remote)\" ]"
check "personal brain has hooks, CI, log, lint" "[ -f brains/personal/.claude/settings.json ] && [ -f brains/personal/.cursor/hooks.json ] && [ -f brains/personal/.github/workflows/lint.yml ] && [ -f brains/personal/log/README.md ] && [ -x brains/personal/scripts/sync.sh ] && [ -f brains/personal/scripts/lint.py ]"
check "hook configs are valid JSON"            "python3 -c 'import json,sys;[json.load(open(f)) for f in sys.argv[1:]]' brains/personal/.claude/settings.json brains/personal/.cursor/hooks.json .claude/settings.json .cursor/hooks.json"

out="$(python3 scripts/lint.py tests/fixtures --visibility shared --skip sitemap)"; rc=$?
check "lint is warn-only by default (exit 0)"  "[ $rc = 0 ]"
python3 scripts/lint.py tests/fixtures --visibility shared --skip sitemap --strict >/dev/null; rc=$?
check "lint --strict exits 1 on findings"      "[ $rc = 1 ]"
check "lint finds the triplicated line twice"  "[ \$(grep -c 'E010 duplicate ' <<<\"\$out\") = 2 ]"
check "lint finds the near-duplicate"          "grep -q 'W011 near-duplicate' <<<\"\$out\""
check "lint flags price, phone, missing date"  "grep -q E101 <<<\"\$out\" && grep -q E103 <<<\"\$out\" && grep -q E001 <<<\"\$out\""
check "lint flags a passed deadline"           "grep -q 'E060 stale-deadline' <<<\"\$out\""
check "lint flags grant amounts once per file" "[ \$(grep -c 'E108 grant-amounts' <<<\"\$out\") = 1 ]"

mkdir -p brains/personal/projects/a
printf '# Q&A\n\n- Label printer prints blank labels → reload the roll glossy side down · Client A · 2026-10-01 · @alice · verified\n' > brains/personal/projects/a/clean.md
printf '# Deal\n\n- Proposal quoted SGD 1,200 and the grant covers half · Client B · 2026-10-01 · @alice · unverified\n' > brains/personal/projects/a/deal.md
git -C brains/personal add -A >/dev/null; git -C brains/personal commit -qm notes >/dev/null 2>&1
scripts/spinoff.sh team --topics "client issue,known fix" --keywords "printer,label" --org acme --base "$BASE" \
   --move projects/a/clean.md:playbook/clean.md --move projects/a/deal.md >"$TMP/spin.log" 2>&1; rc=$?
check "spinoff exits 3 when a move is blocked" "[ $rc = 3 ]"
check "shared brain generated + own git repo"  "[ -d brains/team/.git ] && [ -f brains/team/scripts/lint.py ] && [ -f brains/team/README.md ] && [ -f brains/team/.cursor/rules/team.mdc ]"
check "shared CLAUDE.md has real objectives"   "grep -q '^1\. Anyone on the team finds' brains/team/CLAUDE.md && grep -q 'SUPERSEDED YYYY-MM-DD' brains/team/CLAUDE.md"
check "clean file moved, stub left"            "[ -f brains/team/playbook/clean.md ] && grep -q '→ team:playbook/clean.md' brains/personal/projects/a/clean.md"
check "private file NOT moved"                 "[ ! -e brains/team/projects/a/deal.md ] && grep -q SGD brains/personal/projects/a/deal.md"
check "route registered + ROUTES refreshed"    "grep -q 'name: team' brains/personal/brains.yaml && grep -q '| team | shared |' brains/personal/ROUTES.md"
check "shared brain never names personal"      "! grep -rqi 'alpha-notes' brains/team --exclude-dir=.git && ! grep -rqi 'brains/personal' brains/team --exclude-dir=.git --exclude-dir=scripts"
check "workspace lints clean (--strict)"       "python3 scripts/lint.py . --strict >/dev/null"
check "clean fix routes to shared brain"       "scripts/route.py classify 'label printer prints blank, reload the roll fix' | grep >/dev/null -c 'WRITE -> team'"
check "money routes to personal"               "scripts/route.py classify 'quotation of SGD 500' | grep >/dev/null -c 'WRITE -> personal'"

printf -- '- Scanner beeps twice and stops\n' >> brains/team/playbook/fixes.md
sed -i 's/^plugins: \[\]/plugins: [cs_playbook]/' brains/team/.membrain/lint.yaml
out="$(python3 brains/team/scripts/lint.py)"
check "cs_playbook plugin (enabled by config) flags format" "grep -q 'P201 playbook-format' <<<\"\$out\""
git -C brains/team checkout -q -- . 
check "plugin is off by default"               "! python3 brains/team/scripts/lint.py | grep >/dev/null -c P201"
mkdir -p brains/team/log && printf '## [2026-10-08 10:00] fix | Client A | added printer fix\nwho/tool: t · files: playbook/clean.md\n\n## 2026-10-08 bad heading\n' > brains/team/log/2026-10.md
check "log format checked (L070)"              "[ \$(python3 brains/team/scripts/lint.py | grep -c L070) = 1 ]"
rm -f brains/team/log/2026-10.md

echo '- See alpha-notes for the price → n/a · Client A · 2026-10-08 · @alice' >> brains/team/playbook/fixes.md
git -C brains/team add -A >/dev/null; git -C brains/team commit -qm leak >/dev/null 2>&1; rc=$?
check "pre-commit hook blocks private reference" "[ $rc != 0 ]"
git -C brains/team reset -q --hard

git init -q --bare "$TMP/wrong.git"; git -C brains/team remote add origin "$TMP/wrong.git"
echo '- Label jams at the cutter → clean the blade · Client A · 2026-10-08 · @alice · unverified' >> brains/team/playbook/fixes.md
(cd brains/team && bash scripts/sync.sh "test" >/dev/null 2>&1); rc=$?
check "sync refuses a remote that is not the brain's own" "[ $rc = 1 ] && [ -z \"\$(git --git-dir=$TMP/wrong.git branch)\" ]"
git init -q --bare "$TMP/team.git"; git -C brains/team remote set-url origin "$TMP/team.git"
sed -i "s#^remote: .*#remote: $TMP/team.git#" brains/team/.membrain.yaml
(cd brains/team && bash scripts/sync.sh "playbook: cutter fix" >/dev/null 2>&1); rc=$?
check "sync commits and pushes to its own remote" "[ $rc = 0 ] && git --git-dir=$TMP/team.git log main --oneline | grep >/dev/null -c 'cutter fix'"
echo '- Label curls → store rolls flat · Client A · 2026-10-08 · @alice · unverified' >> brains/team/playbook/fixes.md
bash brains/team/scripts/push-if-changed.sh; rc=$?
check "push-if-changed syncs and exits 0"      "[ $rc = 0 ] && [ -z \"\$(git -C brains/team status --porcelain)\" ] && git --git-dir=$TMP/team.git log main --oneline | grep >/dev/null -c 'agent update'"
bash brains/team/scripts/pull-if-stale.sh; rc=$?
check "pull-if-stale exits 0"                  "[ $rc = 0 ]"
echo '- private note · 2026-10-08 · @alice' >> brains/personal/inbox.md
(cd brains/personal && bash scripts/sync.sh "inbox" 2>&1 | grep >/dev/null -c 'Committed locally only'); rc=$?
check "personal brain without a remote commits locally only" "[ $rc = 0 ] && [ -z \"\$(git -C brains/personal remote)\" ]"
git -C brains/personal remote add origin "$TMP/wrong.git"
echo '- another note · 2026-10-08 · @alice' >> brains/personal/inbox.md
(cd brains/personal && bash scripts/sync.sh "inbox" >/dev/null 2>&1); rc=$?
check "personal brain never pushes to a foreign remote" "[ $rc = 1 ] && [ -z \"\$(git --git-dir=$TMP/wrong.git branch)\" ]"
git -C brains/personal remote remove origin; git -C brains/personal checkout -q -- .
check "workspace sync hook never fails"        "bash scripts/sync-brains.sh pull && bash scripts/sync-brains.sh push"

# ---- catalog: public (BASE/catalog) + a private source (synthetic fixture copy registered in brains.yaml)
CAT="python3 scripts/catalog.py --base $BASE"
[ ! -d "$BASE/catalog" ] || { $CAT check "$BASE/catalog" >"$TMP/cat-check.log" 2>&1; rc=$?; }
check "public catalog validates (INDEX, ITEM.md, files)" "[ ! -d '$BASE/catalog' ] || [ \${rc:-1} = 0 ]"
cp -r tests/catalog-fixture "$TMP/acme-cat"
python3 - "$TMP/acme-cat" <<'PY'
import re, sys
p = "brains/personal/brains.yaml"; t = open(p).read()
t = t.replace("    visibility: public\n", f"    visibility: public\n  - name: acme-private\n    url: {sys.argv[1]}\n    visibility: private\n", 1)
open(p, "w").write(t)
PY
out="$($CAT list)"
check "catalog list merges public and private sources" "grep -q 'cs-brain .* membrain' <<<\"\$out\" && grep -q 'label-check .* acme-private' <<<\"\$out\""
check "catalog diff shows new items"           "$CAT diff | grep >/dev/null -c 'NEW .*label-check@acme-private'"
$CAT install label-check >/dev/null 2>&1; rc=$?
check "install refuses missing config"         "[ $rc = 1 ] && [ ! -e brains/personal/installed/skill/label-check ]"
$CAT install label-check --set PRINTER=front-desk >"$TMP/inst.log" 2>&1; rc=$?
check "install writes, fills config, records, commits" "[ $rc = 0 ] && grep -q 'Label check on front-desk' brains/personal/installed/skill/label-check/SKILL.md && grep -q 'id: \"label-check\"' .membrain.yaml && git -C brains/personal log --oneline | grep >/dev/null -c 'catalog: install label-check'"
$CAT install tiny-dash >/dev/null 2>&1; rc1=$?; $CAT install proposal-claim-review >/dev/null 2>&1; rc2=$?
check "spec/idea items refused without --docs (both sources)" "[ $rc1 = 1 ] && [ $rc2 = 1 ]"
$CAT install tiny-dash --docs --with-deps >/dev/null 2>&1; rc=$?
check "--docs --with-deps installs the spec and its dependency" "[ $rc = 0 ] && [ -f brains/personal/installed/app/tiny-dash/DESIGN.md ]"
$CAT install cs-brain >/dev/null 2>&1; rc=$?
check "brain kinds are not installed, only spun off" "[ $rc = 1 ]"
sed -i 's/version: "1.0.0"/version: "1.1.0"/' "$TMP/acme-cat/INDEX.yaml"; sed -i 's/Version:\*\* 1.0.0/Version:** 1.1.0/' "$TMP/acme-cat/skill/label-check/ITEM.md"
echo '3. Note the result.' >> "$TMP/acme-cat/skill/label-check/SKILL.md"
check "catalog diff shows an UPDATED item"     "$CAT diff | grep >/dev/null -c 'UPDATED  label-check@acme-private  1.0.0 -> 1.1.0'"
echo 'my own step' >> brains/personal/installed/skill/label-check/SKILL.md
$CAT install label-check --set PRINTER=front-desk >/dev/null 2>&1; rc=$?
check "update refuses to overwrite local edits (CONFLICT)" "[ $rc = 1 ] && grep -q 'my own step' brains/personal/installed/skill/label-check/SKILL.md"
$CAT install label-check --set PRINTER=front-desk --force-local >/dev/null 2>&1; rc=$?
check "--force-local updates after OK"         "[ $rc = 0 ] && grep -q 'Note the result' brains/personal/installed/skill/label-check/SKILL.md && grep -q 'version: \"1.1.0\"' .membrain.yaml"
check "personal brain lints clean with installs" "python3 brains/personal/scripts/lint.py brains/personal --strict --fail-on med >/dev/null"
scripts/spinoff.sh onb --from catalog:onboarding-brain --base "$BASE" >/dev/null 2>&1; rc=$?
check "spin-off refuses an idea brain kind"    "[ $rc = 1 ] && [ ! -e brains/onb ]"
scripts/spinoff.sh help --from catalog:cs-brain --set 'TICKET_PREFIX=T-\d+' --topics "client issue,known fix" --org acme --base "$BASE" >"$TMP/spin2.log" 2>&1; rc=$?
check "spin-off from catalog:cs-brain"         "[ $rc = 0 ] && [ -f brains/help/tickets/log.md ] && [ -f brains/help/clients/index.md ] && grep -q '## Folders' brains/help/CLAUDE.md && grep -q 'plugins: \[cs_playbook\]' brains/help/.membrain/lint.yaml && grep -q 'path: \"brains/help\"' .membrain.yaml"
check "brain registered under brains:, catalogs intact" "python3 scripts/route.py table | grep >/dev/null -c '| help | shared |' && $CAT list | grep >/dev/null -c acme-private"
printf -- '- Report arrives empty → set the filter to this week · Client A · 2026-10-08 · @alice · verified · src:T-12\n' >> brains/help/playbook/fixes.md
check "cs-brain plugin flags a ticket id missing from tickets/log.md" "python3 brains/help/scripts/lint.py | grep >/dev/null -c 'P202 missing-ticket'"
git -C brains/help checkout -q -- .

up="$(scripts/upgrade.sh --base "$BASE")"
check "upgrade dry-run on a fresh workspace proposes nothing" "grep -q 'none: every framework file is current' <<<\"\$up\""
check "upgrade also reports the catalog"       "grep -q '^Catalog' <<<\"\$up\" && grep -q 'NEW .*client-health-dashboard@membrain' <<<\"\$up\""

echo "--- $pass passed, $fail failed"
[ $fail = 0 ]
