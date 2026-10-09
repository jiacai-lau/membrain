# Topic notes

A topic note holds one piece of ongoing work that runs over several sessions, so any agent in any tool can pick it up later without the chat that started it. One file per topic: `topics/<slug>.md`, lowercase with dashes (for example `topics/supplier-switch.md`).

- **Save** when the person says "log this", and at the end of a long session that moved a topic forward.
- **Resume** when the person says "continue" or "pick up <topic>": open the note, say where it stands and the next step, then carry on.
- With no topic named, take the most recently saved note whose status is `active` or `waiting`. If there are several from the last few days, list them and ask which one.

## Format

```
# <Topic title>

**Status:** active | waiting | parked | done · **Owner:** @someone · **Saved:** YYYY-MM-DD HH:MM <zone>

## Where it stands
Two to five plain lines: what has been done, what is true now.

## Next step
- <one concrete action> · YYYY-MM-DD · @someone

## Decisions
- <what was decided> → <why> · YYYY-MM-DD · @someone · src:<where it was decided>

## Open questions
- <question> · YYYY-MM-DD · @someone

## Related
- `<path in this brain>` or <link to the system of record>
```

## Rules

1. **Snapshot on top, history below.** The status line, "Where it stands" and "Next step" describe now: replace them on each save. "Decisions" and "Open questions" are append-only like any note file. An answered question gets ` · SUPERSEDED YYYY-MM-DD: answered, see Decisions` and the answer goes in as a decision.
2. **One fact, one home.** A decision that only matters to this topic stays here. A fact other people will look up elsewhere (a fix, a client detail, a process step) goes in the file that owns it, and the topic note links to it.
3. **Right brain.** The routing and privacy rules apply as for any write. A topic goes in a shared brain only when everything in it is shareable; anything private stays out of shared brains.
4. **Finished topics stay.** Set the status to `done` and add a last decision line. Never delete a topic note.
5. **Verify the save.** Read the note back, run the lint, and add the file to `SITEMAP.md` only if the `topics/` row is missing. Then say it is saved.
