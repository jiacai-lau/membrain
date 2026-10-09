# Everyday commands

Short things you can say to your agent in a Membrain workspace. Each one maps to a script or a written procedure, so every agent and tool does the same thing. Commands never replace the rules: the agent still follows `AGENTS.md` in the workspace and the target brain's `CLAUDE.md`, says which files it opened, and changes structure or other people's lines only after the owner's OK.

This page is also generated into every workspace as `docs/COMMANDS.md`. Paths below are relative to the workspace root. `MEMBRAIN.md` means the copy at the `source` recorded in the workspace's `.membrain.yaml`.

| Say | What the agent does | Uses |
|---|---|---|
| **status** | Reports each brain's health and what is pending: structure version, uncommitted and unpushed changes, lint counts, open topic notes, inbox items waiting and the next task from `STATE.md`. Ends with the one thing to do next. | `python3 scripts/membrain.py status` (`--online` also checks for a newer Membrain) |
| **check-up** | A full review of one brain or all of them: lint (leaks, duplicates, passed deadlines, stale sitemap rows and unverified lines, orphan files, long files, structure behind), plus the checks a script cannot do. Proposes exact fixes in one message and changes nothing until you say yes. | `python3 scripts/lint.py . --format md`, then `guides/weekly-lint.md` steps 3 to 6 |
| **file this** | Puts a note, fact or document in the right place: privacy first, then the brain that owns the topic, then the file its `SITEMAP.md` names. Unsure goes to the personal `inbox.md` with `route?`. | `python3 scripts/route.py classify "<text>"`, `AGENTS.md` sections 2 and 3 |
| **make a how-to** | Turns a job done more than once into a reusable procedure: purpose, inputs, numbered steps, checks, and who owns it. Writes it to `howto/how-to-<verb>-<thing>.md` in the personal brain, or to the procedure file a shared brain's `SITEMAP.md` names, and adds the sitemap row. If other teams could use it, offers to package it as a skill in a private catalog. | `howto/README.md`; packaging: `MEMBRAIN.md` section D |
| **history** | Shows what changed recently in a brain: the last log entries and the last commits, summarised in plain words. | `grep -h "^## \[" brains/<brain>/log/*.md \| tail -10` and `git -C brains/<brain> log --oneline -15` |
| **upgrade** | Dry run of the newest Membrain: changelog, framework file changes, brain structure steps. Applies only after your OK, with a restore point first. "undo the upgrade" puts the restore point back. | `MEMBRAIN.md` section C; `python3 scripts/membrain.py migrate`, `python3 scripts/membrain.py restore` |
| **log this** | Saves the current piece of work as a topic note: status, where it stands, the next step, decisions and open questions, in the brain the routing rules pick. | `topics/README.md` in that brain |
| **continue** / **pick up &lt;topic&gt;** | Opens the topic note (the latest active one if none is named), says where it stands and the next step, and carries on. Saves the note again before the session ends. | `topics/<slug>.md` |

## Capture as you go

You don't have to say "log this" for every decision. While working, the agent writes down what you state as settled (a decision, a fact, a correction, a preference) as one dated line in the file that owns it, even when you only asked a question. A correction retires the old line with the ` · SUPERSEDED` tail. The routing and privacy rules apply as for any write, and the agent tells you what it noted.

## Notes

- Every command reads the live rules first. Scheduled jobs point at this page or at `AGENTS.md`; they never copy them.
- Commands that only read (status, history, continue) change nothing. Commands that write follow the normal write rules: search first, append one line, read back, lint, sync.
- Anything that would send, post or share outside the brains is drafted for you to send.
