# SITEMAP format

Every brain has a `SITEMAP.md` at its root. It answers: which file owns which kind of fact, who owns
the file, how you may write to it, and how fresh it is. It travels with the brain, so a teammate who
clones only that brain still has a complete map.

There is no file-level map across brains. The cross-brain map is `brains/personal/ROUTES.md`
(topics → brain), generated from `brains/personal/brains.yaml`. It points to each brain's SITEMAP.md
and never repeats its rows.

```markdown
# SITEMAP: <brain name>

Last checked: YYYY-MM-DD · Maintainer: @owner

| Path | Owns (single source of truth for) | Owner | Write rule | Last changed | Last checked |
|---|---|---|---|---|---|
| `CLAUDE.md` | rules for this brain | @alice | owner only | 2026-10-08 | 2026-10-08 |
| `playbook/fixes.md` | known fix for a symptom | @alice | append one line | 2026-10-08 | 2026-10-08 |
| `sources.csv` | external systems this brain relies on, and our access to them | @alice | update own rows | 2026-10-08 | 2026-10-08 |
```

Rules
- The first column is a backticked path relative to the brain root. A folder path (`handoffs/`) covers every file in it.
- "Owns" names the kind of fact. If two rows claim the same kind of fact, one is wrong: fix it.
- Write rule is one of: `owner only`, `append one line`, `update own rows`, `one file per handoff`, `generated`.
- Last changed moves when content changes. Last checked moves when someone confirms the file is still right, even if nothing changed.
- Add the row in the same change that creates the file. Lint: E020 missing sitemap, E021 broken link, W022 file not listed, W023 not checked within `stale_days`.

External systems (Notion boards, Drive folders, dashboards) are listed in `sources.csv`, not in the table:

```
source_id,name,type,url,owner,access_status,review_status,last_checked,next_action
S001,Client issue log,Notion database,https://...,@alice,authenticated-read,read,2026-10-08,
```

`access_status` climbs a ladder; each step is separate and none implies the next:
`identified` → `login-page-reachable` → `authenticated-read` → `role-confirmed` → `content-reviewed`.
A listed source has not necessarily been read. Keep stable ids (`S001`); a child item gets `S001-<short hash>`.
Use a safe alias if the real name is sensitive.
