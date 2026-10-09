# SITEMAP: Membrain (framework repo)

This repo is fetched by raw URL, never cloned by users. Generated files live under `templates/` and are listed in `MANIFEST.yaml`. Optional installable items live under `catalog/`.

| Path | Owns | Owner | Write rule | Last changed | Last checked |
|---|---|---|---|---|---|
| README.md | What Membrain is, quickstart, catalog table, the usage prompts | @maintainer | PR | 2026-10-10 | 2026-10-10 |
| docs/concepts.md | How it works and why (brains, routing, privacy, lint, sync, log, upgrades) | @maintainer | PR | 2026-10-10 | 2026-10-10 |
| docs/faq.md | Common questions | @maintainer | PR | 2026-10-08 | 2026-10-08 |
| docs/apps.md | DRAFT apps layer: app spec format, storage ladder, dynamic profile chat, 30-minute setup runbook, roles | @maintainer | PR | 2026-10-10 | 2026-10-10 |
| MEMBRAIN.md | Agent instructions: A set up, B spin off, C upgrade, D browse and install, E apps (draft) | @maintainer | PR; keep in step with membrain.py | 2026-10-10 | 2026-10-10 |
| MANIFEST.yaml | Template → target list, kinds, scopes, modes | @maintainer | regenerate with scripts/build_manifest.py | 2026-10-10 | 2026-10-10 |
| VERSION | Current framework version | @maintainer | bump on every template change | 2026-10-10 | 2026-10-10 |
| CHANGELOG.md | What changed per version (shown at upgrade) | @maintainer | add entry with each VERSION bump | 2026-10-10 | 2026-10-10 |
| LICENSE | MIT license | @maintainer | owner only | 2026-10-08 | 2026-10-08 |
| scripts/bootstrap.py | Deterministic section A | @maintainer | PR | 2026-10-08 | 2026-10-08 |
| scripts/build_manifest.py | MANIFEST generator (framework vs content rules) | @maintainer | PR | 2026-10-08 | 2026-10-08 |
| templates/workspace/ | Workspace boot files, hooks, docs, guides/weekly-lint.md, self-test | @maintainer | PR | 2026-10-08 | 2026-10-08 |
| templates/scripts/ | membrain.py, catalog.py, lint.py + lint_plugins/, route.py, wrappers, sync-brains.sh | @maintainer | PR + self-test | 2026-10-08 | 2026-10-08 |
| templates/brain/ | Files every brain gets: sync scripts, agent hooks, CI lint, log format | @maintainer | PR + self-test | 2026-10-08 | 2026-10-08 |
| templates/hooks/ | pre-commit lint hook for every brain (blocks leaks) | @maintainer | PR | 2026-10-08 | 2026-10-08 |
| templates/personal-brain/ | Personal brain skeleton | @maintainer | PR | 2026-10-08 | 2026-10-08 |
| templates/shared-brain/ | Shared brain skeleton (README setup guide, CLAUDE.md rules) | @maintainer | PR | 2026-10-08 | 2026-10-08 |
| templates/catalog-repo/ | Skeleton of a private catalog repo (INDEX.yaml, README, lint, CI), used by `catalog.py new-repo` | @maintainer | PR | 2026-10-08 | 2026-10-08 |
| catalog/INDEX.yaml | Public catalog index: every item's id, type, version, status, summary, depends_on, requires_config, source, files | @maintainer | PR; `scripts/catalog.py check` must pass | 2026-10-10 | 2026-10-10 |
| catalog/<type>/<id>/ | One public catalog item: ITEM.md plus its files (generic, synthetic examples only) | @maintainer | PR; bump the item version on change | 2026-10-08 | 2026-10-08 |
