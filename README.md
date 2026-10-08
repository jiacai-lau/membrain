# Membrain

A framework for **multi-brain markdown knowledge bases** that AI agents read and write: one private personal brain per person, plus shareable team brains spun off as their own git repos, with routing, site maps, an append-only entry format and a lint that keeps private things out of shared brains.

## You don't clone this repo

Membrain is read, not copied. Your agent fetches `MEMBRAIN.md`, `MANIFEST.yaml` and the files under `templates/` by raw URL and **generates** your workspace from them. Your workspace records which Membrain version and which file hashes it was generated from (`.membrain.yaml`), so later your agent can propose framework upgrades without touching your notes.

**Set up** (paste into your agent):
> Fetch https://raw.githubusercontent.com/jiacai-lau/membrain/main/MEMBRAIN.md (from https://github.com/jiacai-lau/membrain) and follow section A to set up Membrain for me. Do not clone the repo; generate my workspace from its templates. Ask me the intake questions in one message, keep my personal brain local and private, and don't push anything without my OK.

**Spin off** a shareable brain:
> Read AGENTS.md in my Membrain workspace, then follow section B of https://raw.githubusercontent.com/jiacai-lau/membrain/main/MEMBRAIN.md to spin off a shareable brain called `<name>` for `<purpose>`. Show me which files would move and the privacy check result before moving anything, and don't create the GitHub repo or invite anyone until I say so.

**Upgrade**:
> In my Membrain workspace, follow section C of https://raw.githubusercontent.com/jiacai-lau/membrain/main/MEMBRAIN.md: run the upgrade dry run, show me the changelog and the proposed framework file changes, and apply only after I say OK. Never overwrite my content files.

No agent? `curl -fsSL https://raw.githubusercontent.com/jiacai-lau/membrain/main/scripts/bootstrap.py | python3 - --base https://github.com/jiacai-lau/membrain --workspace ~/membrain --owner <you>` (Python 3 standard library only).

## What you get

```
~/membrain/                     workspace (not a git repo)
  AGENTS.md  CLAUDE.md  START-HERE.md  .cursor/rules/membrain.mdc   boot rules for agents
  .membrain.yaml                version, source URL, placeholder values, file hashes
  docs/                         entry format, privacy labels, sitemap format
  scripts/                      membrain.py (setup/spinoff/upgrade), lint.py, route.py, spinoff.sh, upgrade.sh, pull-all.sh
  tests/                        self-test + synthetic lint fixture
  brains/personal/              PRIVATE git repo: ROUTES.md, brains.yaml, SITEMAP.md, STATE.md, inbox.md, howto/ projects/ pointers/ handoffs/
  brains/<shared>/              one git repo per spun-off brain (teammates git clone these)
```

## This repo

| Path | What |
|---|---|
| `MEMBRAIN.md` | Instructions an agent follows: A set up, B spin off, C upgrade |
| `MANIFEST.yaml` | Every generated file: template → target, framework/content, scope, mode |
| `templates/` | The files that get generated (`workspace/`, `scripts/`, `hooks/`, `personal-brain/`, `shared-brain/`) |
| `scripts/bootstrap.py` | Section A without an agent (raw URL, github.com URL or local folder) |
| `scripts/build_manifest.py` | Maintainers: regenerate MANIFEST.yaml after changing templates/ |
| `VERSION`, `CHANGELOG.md` | Read by upgrades |
| `SITEMAP.md` | Map of this repo |

Maintainers: change a template → `python3 scripts/build_manifest.py` → bump `VERSION` → add a `CHANGELOG.md` entry → `bash templates/workspace/tests/run.sh "$PWD"` must pass.

Design rules: personal may point to shared, shared never references personal; each brain has its own SITEMAP.md, and the personal ROUTES.md is the only cross-brain map; entries are dated, owned and append-only; unsure → personal inbox.
