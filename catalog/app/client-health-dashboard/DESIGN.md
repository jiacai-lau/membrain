# Client health dashboard — design (SPEC ONLY)

Status: **spec**. No code ships with this item. Thresholds are deliberately unset.

## Goal
One glance per client: green, amber or red. Alert a human only when a client goes red. People and agents both read the same score.

## Pipeline
```
sources  →  collector  →  score (green|amber|red)  →  store  →  alert-on-red
```

1. **Sources** (config). Examples: shared-brain lint findings (HIGH count), trial-review readiness score, board status (Live / Implementation / …), open P1 fixes, last activity date. Each source is a read-only adapter.
2. **Collector.** Runs on a schedule. For each client, pulls every configured source, writes a raw snapshot (date, source, value). Never invents a number; missing source → "n/a" for that signal.
3. **Score.** Combines signals with owner-set thresholds (not shipped). Suggested shape, to be filled by the owner:
   - red if any critical signal trips (e.g. critical error open, readiness "Not ready")
   - amber if any watch signal trips or data is stale beyond N days
   - green otherwise
   - unscored if fewer than M sources returned data
4. **Store.**
   - **v1:** Notion database columns on the existing client board: `Health`, `Health as of`, `Health notes` (short). One row per client.
   - **v2:** Static page (HTML or markdown rendered) behind an auth proxy (e.g. Cloudflare Access). Same fields. Notion remains writable for humans; the page is the read view.
5. **Alert.** Only on a transition to red (or red that stays red across N runs). One message to the owner. No green/amber noise.

## Non-goals
- No writes into client systems.
- No automatic client outreach.
- No thresholds decided by the catalog author — the owner sets them after seeing real data.

## Open questions
- Which sources are in v1 for this owner? (private catalog wires them)
- Where does the collector run (agent schedule, GitHub Action, small worker)?
- Who may see amber vs only red?

## Next
Owner picks sources and thresholds; a private-catalog item wires them. Then a built-untested collector can be written against this design.
