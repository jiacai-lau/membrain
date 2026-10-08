# MEMBRAIN.md: instructions for an AI agent

You were pointed here to **set up** (A), **spin off** (B) or **upgrade** (C) a Membrain workspace for the person you work for.

**Nobody clones or forks Membrain.** You READ this repo: fetch raw files and GENERATE the person's workspace from the templates listed in `MANIFEST.yaml`. (Teammates joining a *shared brain* may `git clone` that brain's own repo; that is different and fine.)

- **Base URL** (`<BASE>`): `https://raw.githubusercontent.com/jiacai-lau/membrain/main`. If you were given `https://github.com/<owner>/<repo>`, use `https://raw.githubusercontent.com/<owner>/<repo>/main`. A local folder path also works as `<BASE>` (testing).
- Fetch a file as `<BASE>/<path>`, e.g. `<BASE>/MANIFEST.yaml`, `<BASE>/templates/workspace/AGENTS.md`.
- Never push, publish, invite or make anything public without the person's explicit OK in this chat. A personal brain is never public.
- Finish with a TLDR: what you generated, what you skipped, the next step.

## MANIFEST.yaml

Each entry: `template` (path in this repo), `target` (path in the workspace), `kind` (`framework` = Membrain's, may be upgraded; `content` = the person's after generation, never overwritten), `scope` (`workspace` and `personal` at setup, `shared` at each spin-off), optional `mode` (`"755"` = executable).
Placeholders `{{NAME}}` appear in template text and in targets. Fill them exactly; no `{{...}}` may remain.

---

## A. Set up

Deterministic shortcut (recommended if you can run Python 3): it does steps 3–8 below exactly.
```
curl -fsSL <BASE>/scripts/bootstrap.py | python3 - --base <BASE> --workspace <WORKSPACE> --owner <OWNER> --aliases "<ALIASES>" --account <ACCOUNT>
```
Manual path (same result):

1. **Intake** (one message): handle for `@owner` (`OWNER`), workspace folder (`WORKSPACE`, default `~/membrain`), GitHub account (`ACCOUNT`, default OWNER), other names their existing notes go by (`ALIASES`, comma list; lint keeps these out of shared brains), and whether they have notes to import.
2. **Check** that `WORKSPACE/.membrain.yaml` does not exist (if it does, use section C). Needs `git` and `python3`.
3. **Fetch** `<BASE>/VERSION` (→ `VERSION`, trimmed) and `<BASE>/MANIFEST.yaml`.
4. **Generate.** For every entry with `scope: workspace`, then every entry with `scope: personal`, in file order: fetch `<BASE>/<template>`, replace placeholders, write to `WORKSPACE/<target>` (create folders; refuse to overwrite an existing file), apply `mode`. Values:
   - workspace: `OWNER`, `DATE` (today, `YYYY-MM-DD`), `MEMBRAIN_VERSION` = VERSION, `SOURCE_URL` = `<BASE>`
   - personal: `BRAIN_NAME` = `personal`, `OWNER`, `DATE`, `REMOTE` = `git@github.com:<ACCOUNT>/membrain-personal.git`, `ALIASES` = the comma list normalised to `a, b`
   Keep the sha256 of each text exactly as written in this step.
5. **Routes:** `python3 scripts/route.py write-routes brains/personal/ROUTES.md --registry brains/personal/brains.yaml` (run in WORKSPACE).
6. **Self-test:** `bash tests/run.sh <BASE>`. The last line must be `--- N passed, 0 failed`. If not, stop and report; create no git repo.
7. **Write `WORKSPACE/.membrain.yaml`** in exactly this format (all values JSON-quoted; `varsets` then `generated` in step-4 order):
   ```
   # Membrain workspace state. Written by scripts/membrain.py. Do not edit by hand.
   kind: workspace
   membrain_version: "<VERSION>"
   source: "<BASE>"
   owner: "<OWNER>"
   generated_at: "<DATE>"
   varsets:
     - id: "workspace"
       OWNER: "<OWNER>"
       DATE: "<DATE>"
       MEMBRAIN_VERSION: "<VERSION>"
       SOURCE_URL: "<BASE>"
     - id: "brain:personal"
       BRAIN_NAME: "personal"
       OWNER: "<OWNER>"
       DATE: "<DATE>"
       REMOTE: "git@github.com:<ACCOUNT>/membrain-personal.git"
       ALIASES: "<ALIASES>"
   generated:
     - path: "<target>"
       template: "<template>"
       kind: "<framework|content>"
       scope: "<workspace|personal>"
       vars: "<workspace|brain:personal>"
       sha256: "<sha256 from step 4>"
   ```
8. **Personal brain git repo (local, private):** in `brains/personal`: `git init -b main`, `git config core.hooksPath .githooks`, `git add -A`, `git commit -m "membrain: create personal brain (personal)"`. Then show, do not run: `gh repo create <ACCOUNT>/membrain-personal --private --source brains/personal --remote origin --push`. Run it only on explicit OK. Never `--public`.
9. **Import notes** (if any): copy them into `brains/personal/` (how-tos → `howto/`, projects → `projects/<name>/`) without rewriting; add SITEMAP rows; `python3 scripts/lint.py brains/personal`; commit.
10. **Boot pointer:** point your persistent memory/rules at `WORKSPACE/AGENTS.md` (path only). From now on read `AGENTS.md` and follow it.

## B. Spin off a shareable brain

1. Reread `WORKSPACE/AGENTS.md`. Ask: name (lowercase-dashes), one-line purpose, topics it owns, words that must never go in it (default `price, grant, quotation, salary, password`), editors, GitHub org, and which personal files should move. Show the move list; wait for OK.
2. Run in WORKSPACE (it fetches `MANIFEST.yaml` and every `scope: shared` template from the `source` in `.membrain.yaml`, renders them into `brains/<name>/`, privacy-checks each move, lints, `git init`s, leaves pointer stubs, registers the route, refreshes ROUTES.md and records hashes in `.membrain.yaml`):
   ```
   scripts/spinoff.sh <name> --description "<purpose>" --topics "<a,b>" --keywords "<x,y>" --editors "<p,q>" --org <org> --move <path>[:<new path>] ...
   ```
   Shared placeholders: `BRAIN_NAME`, `OWNER`, `DATE`, `DESCRIPTION`, `TOPICS`, `EDITORS`.
3. Exit 3 means some moves were blocked (`PRIVACY_REVIEW_NEEDED`). Report the findings and offer a redacted copy (amounts and names removed) for the person to approve before moving it.
4. Commit the personal brain (route + stubs). Show `gh repo create <org>/<name> --private --source brains/<name> --remote origin --push`; run it and add collaborators only on explicit OK.
5. Give teammates: `git clone <remote>` then "Read CLAUDE.md in this folder and follow it."

## C. Upgrade

1. In WORKSPACE run `scripts/upgrade.sh` (dry run). It fetches the current `VERSION`, `MANIFEST.yaml` and `CHANGELOG.md` from the `source` in `.membrain.yaml`, re-renders every **framework** entry with the recorded placeholder values and compares against the recorded hashes and the files on disk:
   - `UPDATE`: Membrain changed it and you did not → safe to replace
   - `ADD`: new framework file
   - `CONFLICT`: you edited the file locally → show the diff; replace only with `--force-local` and OK
   Content files are never proposed.
2. Show the person the CHANGELOG lines and the proposal list. On OK: `scripts/upgrade.sh --apply`. It writes only the approved framework files, updates hashes and `membrain_version` in `.membrain.yaml`, and commits touched brain files locally (pathspec commit). Nothing is pushed.
3. If the changelog mentions new rules for brain `CLAUDE.md`/`SITEMAP.md` (content files), propose edits to the person; do not apply them silently.
