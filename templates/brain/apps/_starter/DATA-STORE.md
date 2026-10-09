# Data store: <app name>

> **NO credentials in this file.** Never write passwords, API keys, tokens, service-account files or connection strings here or anywhere in this brain. Secrets live in the host's secret store (the hosting platform's secret settings or a password manager). This file only says where the data is and who looks after it.

| Item | Value |
|---|---|
| Rung | <1 = Google Sheets or Excel Online + Drive/OneDrive · 2 = managed Postgres, e.g. Supabase · 3 = self-hosted Postgres, e.g. a VPS> |
| Provider | <e.g. google-sheets, supabase, self-hosted-postgres> |
| Schema version | <same as schema_version in APP.md> |
| Location | <name of the sheet, project or server, plus where the link is kept. In a shared brain, a name and "link kept by the owner", not a private link> |
| File storage | <folder names, e.g. waivers/, uploads/> |
| Owner | @<handle of the person responsible for this store> |
| Access | <roles with access and what they can do; no email addresses> |
| Secrets | Held in <name of the host's secret store>. Never here. |
| Backup / export | <how often, where to, last restore test date. Exports follow the CSV-per-entity contract in Membrain docs/apps.md> |
| Move up when | <the condition that means it is time for the next rung> |

## Migrations
<One line per change of rung or schema: date, from, to, schema version, who approved.>
