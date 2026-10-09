# Brain structure migrations

Framework files (scripts, hooks, `AGENTS.md`, `topics/README.md` …) are upgraded by replacing them, as described in [MEMBRAIN.md section C](../MEMBRAIN.md#c-upgrade). Some changes also need a small edit to a brain's own files, which upgrades never overwrite: a new section in its `CLAUDE.md`, a new `SITEMAP.md` row. Those edits are **structure migrations**.

## The structure number

- Each brain records its layout version in its `.membrain.yaml`: `structure: N`. A brain without the line is structure 1 (every brain made before v0.6.0).
- The framework's number is `structure` in `MANIFEST.yaml` (and `STRUCTURE` in `scripts/membrain.py` and `scripts/lint.py`, kept equal by the self-test).
- When a brain is behind, `scripts/lint.py` reports **W080 structure-behind** and `scripts/membrain.py status` marks it `BEHIND`.

## How a migration runs

1. Apply the framework upgrade first (`scripts/upgrade.sh`, then `--apply` after OK). A step can depend on a framework file being there.
2. Dry run: `python3 scripts/membrain.py migrate` (or `--brain <name>`). For each brain it lists every step from its number to the framework's, one step at a time, and every file each step would change.
3. Show the list to the brain owner. On OK: `python3 scripts/membrain.py migrate --apply`. For each brain it
   - skips the brain if one of the files to change has uncommitted edits;
   - makes a **restore point**: a copy of every file it will change in `.membrain/restore/<id>/` in the workspace, with a `RESTORE.md` list;
   - applies the steps in order, sets `structure:` after each one and appends a line to the brain's `.membrain/migrations.log` (date, step, restore point);
   - commits those files in the brain's repo. Nothing is pushed.
4. Lint the brain. To undo: `python3 scripts/membrain.py restore` lists restore points; `restore <id>` is a dry run and `restore <id> --apply` puts the files back (uncommitted, for review).

A step never deletes or rewrites a person's lines. It only adds a section, a row or a setting, and it skips anything that is already there, so running it twice is safe.

## Steps

| To | Name | What it changes in each brain | Since |
|---|---|---|---|
| 2 | [capture-and-topics](002-capture-and-topics.md) | `CLAUDE.md`: adds "Capture as you go" and "Housekeeping". `SITEMAP.md`: adds the `topics/` row. Needs the framework file `topics/README.md`. | 0.6.0 |

## Adding a step (maintainers)

1. Bump `STRUCTURE` in `templates/scripts/membrain.py` and `templates/scripts/lint.py`, and the `structure:` line in the brain `membrain.yaml` templates, so new brains start current.
2. Add the step function to `MIGRATIONS` in `membrain.py`. Take new text from the templates (never a second copy), skip what is already present, and return `(file, new text, description)` for each change.
3. Write `migrations/NNN-<name>.md` (why, what changes, how to check) and add it to the table above.
4. Run `python3 scripts/build_manifest.py` and the self-test; the test strips a fresh brain back to the old structure and checks the migration brings it back.
