# Step 2: capture-and-topics (structure 1 → 2, Membrain 0.6.0)

## Why

Agents should keep the brain current while they work, and work that spans several sessions needs a saved state any tool can resume from. This step adds the rules for both, plus three housekeeping rules, to brains made before 0.6.0. New brains already have them.

## What changes in each brain

| File | Change |
|---|---|
| `topics/README.md` | Added by the framework upgrade (not by this step). The step stops if it is missing. |
| `CLAUDE.md` | Adds two sections before `## Sync and logging` (at the end if that heading is missing): **Capture as you go** (note settled decisions, facts and corrections while working; "log this" saves a topic note; "continue" resumes one) and **Housekeeping** (look before you ask; keep files under about 300 lines; numbers carry a source and a date). Skipped if the brain already has a "Capture as you go" section. |
| `SITEMAP.md` | Appends the `topics/` row, dated today, owned by the brain's owner. Skipped if a `topics/` row exists. |
| `.membrain.yaml` | `structure: 2`. |
| `.membrain/migrations.log` | One line: date, step, restore point. |

The text comes from the current brain templates, so a migrated brain reads the same as a new one.

## How to check

- `python3 brains/<brain>/scripts/lint.py brains/<brain>` shows no W080.
- `grep -n "## Capture as you go" brains/<brain>/CLAUDE.md` finds the section once.
- Ask the agent "log this" on any piece of work, then "continue" in a new session.
