# Changelog

Format: `## [version] - date`, newest first. Upgrades show the entries newer than the workspace's version.

## [0.2.0] - 2026-10-08
- Generate model: nobody clones Membrain. Agents fetch `MANIFEST.yaml` and templates by raw URL and generate the workspace (MEMBRAIN.md A/B/C).
- `templates/` holds everything that gets generated; `MANIFEST.yaml` lists template → target, framework vs content, scope and mode.
- `scripts/bootstrap.py`: deterministic setup from a raw URL, a github.com URL or a local folder.
- `scripts/membrain.py` (generated into the workspace): `setup`, `spinoff`, `upgrade` (dry run by default; framework files only).
- Workspace `.membrain.yaml` records version, source, placeholder values and the sha256 of every generated file.

## [0.1.0] - 2026-10-08
- First scaffold: personal + shared brain skeletons, lint, router, spin-off, sitemap and entry formats.
