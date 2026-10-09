# Changelog

Format: `## [version] - date`, newest first. Upgrades show the entries newer than the workspace's version.

## [0.6.0] - 2026-10-10
- Capture as you go: agents note settled decisions, facts, corrections and preferences the person states, even during a question, as dated one-line entries in the owning file (normal routing and privacy rules). New workspace `AGENTS.md` section 4; brain `CLAUDE.md` templates get "Capture as you go" and "Housekeeping" sections.
- Topic notes: every brain gets `topics/README.md` (framework) with the format (status line, where it stands, next step, decisions, open questions, related; snapshot on top, append-only below). "log this" saves one, "continue" / "pick up <topic>" resumes one. New `topics/` SITEMAP row (content).
- Everyday commands: `docs/commands.md` (also generated into each workspace as `docs/COMMANDS.md`, framework) defines status, check-up, file this, make a how-to, history, upgrade, log this and continue, each mapped to an existing script or procedure. MEMBRAIN.md "Commands" section; START-HERE resume prompt.
- Housekeeping rules: look in the brains before asking; keep files under about 300 lines (new lint W081 long-file, `max_lines` in `.membrain/lint.yaml`); numbers carry a source and a date.
- Brain structure version: `structure` in MANIFEST.yaml (now 2) and `structure: N` in each brain's `.membrain.yaml` (missing = 1). New lint W080 structure-behind. `scripts/membrain.py migrate` dry-runs and (with `--apply`, after OK) applies numbered steps one at a time with a restore point, records each in `.membrain/migrations.log` and commits locally. Step 2 (capture-and-topics) adds the new `CLAUDE.md` sections and the `topics/` row, taking the text from the templates. Docs: `migrations/`.
- Restore points: `upgrade --apply` and `migrate --apply` copy every file they will change into `.membrain/restore/<id>/` first; `scripts/membrain.py restore [<id>] [--apply]` lists or puts one back. The upgrade dry run names brains whose structure is behind.
- `scripts/membrain.py status`: per brain structure, uncommitted and unpushed changes, lint counts, open topic notes, waiting inbox items and the next task (`--online` also checks for a newer version).
- Docs: concepts (capture, topic notes, commands, housekeeping, long reading delegated to helper readers where a tool offers them), FAQ, README. Self-test: 66 checks (13 new: templates, commands page, structure agreement, topic note lint, status, W081, W080, migrate dry run / apply / idempotent, restore, upgrade restore point).
- Existing workspaces: the upgrade dry run shows `topics/README.md` and `docs/COMMANDS.md` as ADD and `AGENTS.md`, `lint.py`, `membrain.py` and the self-test as UPDATE; then run `scripts/membrain.py migrate` for the brain-level step.

## [0.5.1] - 2026-10-10
- App starter scaffold (scaffolding only, no app code): every brain, personal and shared, now gets `apps/_starter/` with a blank `APP.md` (spec frontmatter and sections with fill-in prompts), `DATA-STORE.md` (rung, location pointer, owner, backup/export, explicit no-credentials warning), `SETUP-CHECKLIST.md` (the 30-minute runbook as tick boxes) and `README.md` (copy `_starter` to `apps/<name>/`). Framework files: existing brains see them as `ADD` in the upgrade dry run.
- Lint skips `apps/_starter/**` for entry-format and orphan checks (it is a template, not notes). Privacy checks still apply.
- New brains' `SITEMAP.md` gets an `apps/` row (content; existing brains may add it by hand).
- `docs/apps.md` points at the starter. Self-test: two new checks (personal and shared brains get the starter).

## [0.5.0] - 2026-10-10
- DRAFT apps layer (`docs/apps.md`): a brain can describe a simple app in `apps/<name>/APP.md` (frontmatter: name, purpose, status, version, schema_version, roles, entities and fields, screens, flows, rules, notifications, data_store rung, file_storage, mirror_to_brain, questions) and an agent builds it from the spec. Nothing hard-coded; the brain stays the source of truth for rules, live data sits in the chosen store.
- Storage ladder: rung 1 Google Sheets + Drive, rung 2 managed Postgres free tier (e.g. Supabase), rung 3 self-hosted Postgres (e.g. a Hetzner VPS), with when-to-choose, limits, setup effort, backup and privacy notes. The rung is recorded in `APP.md` plus an `apps/<name>/DATA-STORE.md` pointer (never credentials). CSV-per-entity export/import contract for moving between rungs.
- Dynamic profile chat pattern: per-reply LLM patch of every touched field (source, confidence, confirmed), `profile.md` + append-only `changes.md` per client, question list as a coverage checklist, statuses draft → in_review → approved → setup_done, approval by a person before go-live. Generic roles: research, intake, setup, approver.
- 30-minute setup runbook for a new client from a brain kind + app.
- Public catalog: `tour-booking` (app, spec; fictional farm example), `dynamic-profile-chat` (app, spec), `tour-operations` (brain kind, spec).
- MEMBRAIN.md section E "Apps (draft)"; README apps section and catalog rows; concepts section. No template or script changes.

## [0.4.0] - 2026-10-08
- Catalog: installable items with an `ITEM.md` each, in `catalog/<type>/<id>/` with `catalog/INDEX.yaml` (id, type, version, status, summary, depends_on, requires_config, source, files). Types: brain-kind, agent, routine, skill, app, data-source. Status: live, built-untested, spec, idea.
- Public catalog seed (generic): `cs-brain` (brain kind, live), `weekly-brain-lint` (routine, built-untested), `proposal-claim-review` (skill, spec), `client-health-dashboard` (app, spec only), `onboarding-brain` (brain kind, idea), `client-onboarding-portal` + `onboarding-agent` (idea).
- Several catalog sources: private org catalogs listed under `catalogs:` in `brains/personal/brains.yaml` (raw URL, `gh:owner/repo` or local path), merged when browsing. `scripts/catalog.py new-repo` creates a private catalog repo from `templates/catalog-repo/` (MANIFEST scope `catalog-repo`).
- `scripts/catalog.py` (stdlib): `list`, `diff`, `show`, `install` (config via `--set`, `--with-deps`, `--docs` for spec/idea, conflict check with `--force-local`), `check` (validates a catalog), `new-repo`. Installs go to `brains/personal/installed/<type>/<id>/`, are committed locally and recorded under `catalog_installed` in `.membrain.yaml` (version, source, config, file hashes).
- MEMBRAIN.md section D "Browse and install". Section B: `spinoff.sh <name> --from catalog:<id> --set KEY=VALUE`. Section C: run the dry run with the new version's engine; the upgrade also reports NEW, UPDATED and EDITED catalog items (never installs them).
- Spin-off inserts the new brain into the `brains:` list even when another block (such as `catalogs:`) follows it. The personal `brains.yaml` template now starts with a `catalogs:` block.
- Lint: `installed/**` is excluded from entry checks. Personal brain gets `installed/README.md` (framework) and a SITEMAP row (content; existing workspaces may add it).
- MANIFEST entries may carry `raw: true` (copied without filling placeholders; used for the catalog test fixture). Self-test: 51 checks, including catalog list/diff/install from a public and a private source and a spin-off from `catalog:cs-brain`.
- Docs: README catalog section and prompt, concepts and FAQ catalog sections, START-HERE browse prompt.

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
