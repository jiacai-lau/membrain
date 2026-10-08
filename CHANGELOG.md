# Changelog

Format: `## [version] - date`, newest first. Upgrades show the entries newer than the workspace's version.

## [0.3.0] - 2026-10-08
- One lint for every brain (`scripts/lint.py`, stdlib only): warn-only by default, `--strict` exits 1 (`--fail-on high|med|low`), `--format md` report. Core checks: prices ($0 exempt), secrets, emails, phones/ids, personal-brain mentions, grant documents with money; exact and near-duplicate lines (>= 0.85) per note file; passed deadlines on lines not Closed/SUPERSEDED; missing date/owner; sitemap; log format.
- Lint plugins enabled per brain in `.membrain/lint.yaml`; example `cs_playbook` plugin (playbook line format under `## Fixes`, ticket ids missing from the tickets file).
- Every brain gets: GitHub Actions lint (`.github/workflows/lint.yml`, report in the step summary), auto-sync hooks for Claude Code (`.claude/settings.json`) and Cursor (`.cursor/hooks.json`, `.cursor/rules/<brain>.mdc`), `scripts/sync.sh` (pushes only to the brain's own remote, stops on conflict, never force-pushes), `scripts/pull-if-stale.sh`, `scripts/push-if-changed.sh`, and a monthly greppable log (`log/README.md`).
- Workspace hooks run each brain's sync hook (`scripts/sync-brains.sh`). New `guides/weekly-lint.md` routine; START-HERE prompts point at the rules instead of repeating them.
- Retire rule everywhere: never delete; append ` · SUPERSEDED YYYY-MM-DD: <reason>` (no strikethrough). Owner approves removing, merging or moving lines and structure changes.
- Shared brain: setup-guide `README.md`, real objectives in `CLAUDE.md` (`--objectives`), `remote:` in `.membrain.yaml`.
- Pre-commit hook now blocks only HIGH findings (leaks); `sync.sh` and `pull-if-stale.sh` turn it on in fresh clones (`core.hooksPath`), and the shared README setup includes it. Brain `.gitignore` adds editor and Office lock files.
- The vendored lint moved from `.membrain/lint.py` to `scripts/lint.py`; upgrades list the old path as RETIRED.
- Docs: new README, `docs/concepts.md`, `docs/faq.md`, LICENSE (MIT).

## [0.2.0] - 2026-10-08
- Generate model: nobody clones Membrain. Agents fetch `MANIFEST.yaml` and templates by raw URL and generate the workspace (MEMBRAIN.md A/B/C).
- `templates/` holds everything that gets generated; `MANIFEST.yaml` lists template → target, framework vs content, scope and mode.
- `scripts/bootstrap.py`: deterministic setup from a raw URL, a github.com URL or a local folder.
- `scripts/membrain.py` (generated into the workspace): `setup`, `spinoff`, `upgrade` (dry run by default; framework files only).
- Workspace `.membrain.yaml` records version, source, placeholder values and the sha256 of every generated file.

## [0.1.0] - 2026-10-08
- First scaffold: personal + shared brain skeletons, lint, router, spin-off, sitemap and entry formats.
