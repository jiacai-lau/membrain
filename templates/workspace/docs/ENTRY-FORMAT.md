# Entry format

One fact per line, appended at the bottom of the file that owns the topic (see the brain's SITEMAP.md).

```
- <fact or symptom> → <fix or answer> · <context> · YYYY-MM-DD · @owner · <status> · src:<link or id>
```

| Field | Required | Notes |
|---|---|---|
| fact / symptom → fix | yes | Plain words. One fact. Link out for long detail. |
| context | yes | Client, system or project, e.g. `Client B`. Use the name from `clients` if the brain has one. |
| date | yes | The day the fact was true or learned. ISO `YYYY-MM-DD`. Lint error E001 if missing. |
| @owner | yes for new lines | Who stands behind the line (a person, not "agent"). Lint warning W002 if missing; legacy lines are summarised. |
| status | recommended | `verified` (checked in the system of record by the owner), `unverified` (default: from chat or agent inference), `assumption` (a working guess). |
| src | recommended | Ticket id (`T-101`), Notion/Drive link, commit, or `chat:<group> <date>`. Never paste the thread itself. |

Example:
```
- Weekly report email arrives empty → the report filter still says last month; set it to "this week" · Client B · 2026-10-06 · @alice · verified · src:T-101
```

## Changing a fact (supersede, don't edit)

Do not edit or delete a line someone else wrote. Append a new line that supersedes it:
```
- (supersedes 2026-10-06 Client B report-filter line) the filter now resets every Monday; no manual change needed · Client B · 2026-10-14 · @bob · verified · src:T-101
```
Newest line wins. The brain owner may strike through (`~~...~~`) superseded lines during the monthly lint pass. That is the only edit allowed on old lines.

## Handoff notes and versions

Long work products go in `handoffs/` with a neutral, dated, versioned name:
`<TYPE>-<FROM>[-to-<TO>]_<TASK>_<topic>_YYYY-MM-DD_v<N>.md` where TYPE is NOTE, RETURN, QUERY, REPLY, REQUEST or CORRECTION.
A new version is a new file. Keep the old one; rename it `SUPERSEDED-by-v<N>_<old name>` if needed. Never delete.

## Timestamps

Times carry their zone, e.g. `08 Oct 2026, 14:30 SGT (UTC+8)`. Keep "last checked" separate from "last changed": a check that finds nothing new advances only "last checked".
