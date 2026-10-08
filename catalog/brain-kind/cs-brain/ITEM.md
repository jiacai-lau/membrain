# cs-brain (brain kind)

**Status:** live · **Version:** 1.0.0 · **Who it's for:** a support team that answers the same client questions more than once.

## Purpose
A shared brain shaped for client support. Agents look up a known fix by symptom, record new fixes as one line, keep one line per filed ticket, and keep client names with their account ids. Derived from a support brain in daily use; nothing client-specific is included.

## What it adds to a shared brain
- `playbook/fixes.md`: one line per fix under `## Fixes` (`symptom → fix · client · date · @you · status · src:ticket`).
- `tickets/log.md`: how to file, and one line per ticket.
- `clients/index.md`: name, account id, stage.
- A `## Folders` section in `CLAUDE.md`, two SITEMAP rows, and `.membrain/lint.yaml` with the `cs_playbook` lint plugin on: it flags fix lines in the wrong format and ticket ids mentioned in a fix but missing from `tickets/log.md`.

## Depends on
Nothing beyond Membrain itself (the plugin ships in `scripts/lint_plugins/`).

## Config
| Key | Meaning | Example |
|---|---|---|
| `TICKET_PREFIX` | Regex for your ticket ids | `T-\\d+` or `SUP-\\d+` |

## Install
1. Ask for the brain's name, purpose, objectives and the ticket id pattern.
2. Spin it off (MEMBRAIN.md section B): `scripts/spinoff.sh <name> --from catalog:cs-brain --set 'TICKET_PREFIX=T-\\d+' --description "…" --objectives "…" …`
3. The spin-off lints the new brain and records the brain kind under `catalog_installed` in `.membrain.yaml`.
4. Optional: the source brain kept each folder's rules in `<folder>/CLAUDE.md` so Claude Code loads them per folder. To do the same, rename the files and update the paths in `.membrain/lint.yaml` and `SITEMAP.md`.
