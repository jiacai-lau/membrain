# Entry format

One fact per line, appended at the bottom of the file that owns the topic (see the brain's SITEMAP.md).

```
- <fact or symptom> → <fix or answer> · <context> · YYYY-MM-DD · @owner · <status> · src:<link or id>
```

| Field | Required | Notes |
|---|---|---|
| fact / symptom → fix | yes | Plain words. One fact. Link out for long detail. |
| context | yes | Client, system or project, e.g. `Client B`. Use the name from `clients` if the brain has one. |
| date | yes | The day the fact was true or learned. ISO `YYYY-MM-DD`. Lint flags it (E001) if missing. |
| @owner | yes for new lines | Who stands behind the line (a person, not "agent"). Lint flags it (W002) if missing; legacy lines are summarised. |
| status | recommended | `verified` (checked in the system of record by the owner), `unverified` (default: from chat or agent inference), `assumption` (a working guess). |
| src | recommended | Ticket id (`T-101`), Notion/Drive link, commit, or `chat:<group> <date>`. Never paste the thread itself. |

Example:
```
- Weekly report email arrives empty → the report filter still says last month; set it to "this week" · Client B · 2026-10-06 · @alice · verified · src:T-101
```

## Changing a fact (retire, don't edit or delete)

Never delete a line and never rewrite one, yours or anyone's. To retire a line, append this tail to it, and add the newer fact as a new line at the bottom:

```
- Weekly report email arrives empty → the report filter still says last month; set it to "this week" · Client B · 2026-10-06 · @alice · verified · src:T-101 · SUPERSEDED 2026-10-14: filter now resets every Monday (see line below)
- Weekly report email no longer needs a filter change → the filter resets every Monday · Client B · 2026-10-14 · @bob · verified · src:T-101
```

The ` · SUPERSEDED YYYY-MM-DD: <reason>` tail is the only change ever made to an existing line. No strikethrough, no edits. Lint skips SUPERSEDED lines in near-duplicate and deadline checks.
Removing, merging or moving lines, and any change to folders, `CLAUDE.md`, `AGENTS.md`, `.claude/`, `.cursor/`, `.github/` or `scripts/`, needs the brain owner's approval.

## Handoff notes and versions

Long work products go in `handoffs/` with a neutral, dated, versioned name:
`<TYPE>-<FROM>[-to-<TO>]_<TASK>_<topic>_YYYY-MM-DD_v<N>.md` where TYPE is NOTE, RETURN, QUERY, REPLY, REQUEST or CORRECTION.
A new version is a new file. Keep the old one; rename it `SUPERSEDED-by-v<N>_<old name>` if needed. Never delete.

## Timestamps

Times carry their zone, e.g. `08 Oct 2026, 14:30 SGT (UTC+8)`. Keep "last checked" separate from "last changed": a check that finds nothing new advances only "last checked".
