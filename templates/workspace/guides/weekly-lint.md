# Weekly lint routine

Once a week, an agent reviews each brain the way a careful editor would, proposes exact fixes to the brain owner, and changes nothing until the owner says yes. CI and the pre-commit hook catch the mechanical problems on every push; this routine adds the checks a script cannot do.

## The routine (one pass per brain)

1. **Read the brain fresh.** Pull it (`./scripts/sync.sh` or `git pull --rebase`), then read `CLAUDE.md`, `SITEMAP.md`, `STATE.md` and every note file. Never work from a cached copy.
2. **Run the lint:** `python3 scripts/lint.py --format md`. Note every HIGH and MED finding, and LOW ones the owner cares about.
3. **Check what a script cannot:**
   - **Contradictions:** a fix contradicted by a newer line; a ticket Open in one file and Closed in another; two lines that give different answers to the same symptom.
   - **Stale tickets and status:** tickets with no update for a long time, a client or item whose stage changed elsewhere, `unverified` lines that someone could now verify.
   - **Deadlines:** dates that passed on lines not marked Closed or SUPERSEDED (lint flags the obvious ones as E060; look for deadlines written in other words too).
   - **Structure:** files the sitemap does not describe well, a second copy of a file, a section that has grown into its own topic.
4. **Propose exact fixes, all together, to the owner.** For each: the file and line, the problem, and the exact change, for example "append ` · SUPERSEDED 2026-10-14: replaced by line 31` to line 12". Retiring is always the SUPERSEDED tail, never a deletion or rewrite.
5. **Stay silent if there is nothing to fix.** No "all clear" messages; at most one log entry (`lint | <brain> | no findings`).
6. **Apply only after a yes.** Apply exactly what the owner approved, read each change back, run the lint again, add a `lint` entry to `log/YYYY-MM.md`, and sync. Anything not approved stays as it is.

## Scheduling it

Point the job at the live rules; never paste the rules into the job. A prompt like this, run weekly by your agent's scheduler (or a cron job that starts your agent):

```text
Weekly Membrain lint. Read AGENTS.md in <workspace path> fresh, then follow guides/weekly-lint.md for every brain
listed in brains/personal/brains.yaml. Propose fixes to me in one message; if there are none, say nothing.
Change nothing until I say yes.
```

A teammate without a workspace can run the same routine inside one shared brain: "Read CLAUDE.md in this folder, run python3 scripts/lint.py, follow the weekly lint section, and propose fixes to the owner."
