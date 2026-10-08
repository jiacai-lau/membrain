# weekly-brain-lint (routine)

**Status:** built-untested · **Version:** 1.0.0 · **Who it's for:** a brain owner whose agent platform can run a scheduled prompt.

## Purpose
Once a week an agent reviews each brain like a careful editor: it runs the lint, checks what a script cannot (contradictions, stale tickets, passed deadlines), proposes exact fixes to the approver in one message, and changes nothing until the approver says yes. The rules stay in the workspace's `guides/weekly-lint.md`; this item is only the scheduled prompt that points at them.

## Depends on
A Membrain workspace (0.3.0 or newer, for `guides/weekly-lint.md`) or a single shared brain with `scripts/lint.py`.

## Config
| Key | Meaning | Example |
|---|---|---|
| `REPO_OR_WORKSPACE` | Folder the job opens: your workspace, or one shared brain | `~/membrain` |
| `APPROVER` | Who gets the proposal and must say yes | `@alice` |
| `APPLY_PATH` | Where approved fixes are written: `direct` (the agent appends and syncs) or `pull-request` (the agent opens a PR for the owner) | `direct` |

## Install
1. `scripts/catalog.py install weekly-brain-lint --set REPO_OR_WORKSPACE=~/membrain --set APPROVER=@you --set APPLY_PATH=direct`
2. Create a weekly scheduled task in your agent platform whose prompt is the installed `PROMPT.md`. Point at the file; do not paste the rules into the job.
3. Watch the first run. When it behaves, tell your agent to note "weekly-brain-lint verified <date>" in your personal brain.

## Files
| Path | Role |
|---|---|
| `PROMPT.md` | The scheduled prompt (config filled at install) |
