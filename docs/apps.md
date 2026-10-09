# Apps (DRAFT)

**Status: draft, added in v0.5.0.** This page is a design. Membrain ships no app generator yet, and every app in the public catalog is `spec` (no code). Expect the format to change before it is marked stable.

Membrain is scaffolding for AI: plain files that tell any agent where things live, what the rules are and how each job is done. The apps layer extends that. From a brain's files, an agent can spin up a **simple page or app** (a booking page, a form, a dashboard, an intake chat) and, if needed, a **simple database**, without anyone writing a fixed program by hand.

The rule that makes this work: **nothing is hard-coded.** Screens, fields, questions and rules come from the brain's files. When the business changes, a person or an agent edits the spec, and the app follows.

Contents: [What an app is](#what-an-app-is) · [App spec format](#the-app-spec-appsnameappmd) · [Storage ladder](#the-storage-ladder) · [Dynamic profile chat](#pattern-dynamic-profile-chat) · [30-minute setup](#runbook-new-client-in-30-minutes) · [Roles](#roles)

---

## What an app is

An app in Membrain is three things kept apart:

| Part | Lives in | Example |
|---|---|---|
| **Spec**: what the app does, its data, screens, rules | The brain: `apps/<name>/APP.md` | Tour types, slot capacity, deposit and cancellation rules |
| **Live data**: bookings, guests, payments, uploads | The chosen **data store** (see the storage ladder) | A spreadsheet tab of bookings, or a Postgres table |
| **The running page** | Wherever it is hosted; generated from the spec | A booking page, a staff dashboard |

Principles:

1. **The brain is the source of truth for rules and process.** If the page and `APP.md` disagree, `APP.md` wins and the page is regenerated.
2. **Live, transactional data stays in the store, not in the brain.** Brains are reviewed text in git; they are not a booking database. Personal data (guest names, contacts) and money values never go in a shared brain.
3. **Approved or summary records can be mirrored back** into the brain, as one-line dated entries or a short summary file (for example "approved setup profile" or "monthly booking summary, counts only"). The `mirror_to_brain` field in the spec says what may be mirrored.
4. **No credentials in the brain, ever.** A brain records *which* store and *where the secret is kept*, never the secret.
5. **A person approves before anything goes live** (`approver` role). Agents propose, people decide.
6. **Dynamic by default.** Fields, questions and screens are read from the spec at run time or regenerated from it. A change is a spec edit plus a regeneration, not a code rewrite.

App status uses the catalog words: `idea` → `spec` → `built-untested` (built, one supervised run pending) → `live`. Retire an app the Membrain way: never delete, mark it ` · SUPERSEDED YYYY-MM-DD: <reason>`.

---

## The app spec: `apps/<name>/APP.md`

One folder per app in the brain:

```
apps/
  <name>/
    APP.md          # the spec: YAML frontmatter + plain-language body
    DATA-STORE.md   # pointer to the live store: rung, location, backups, migrations. No secrets
    changes.md      # optional: append-only log of spec changes (date · what · why · who)
```

### Frontmatter fields

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | lowercase-dashes id, same as the folder |
| `title` | yes | Human name |
| `purpose` | yes | One or two sentences: what problem it solves for whom |
| `status` | yes | `idea` \| `spec` \| `built-untested` \| `live` |
| `version` | yes | Spec version (semver). Bump on every change |
| `schema_version` | yes | Integer. Bump when entities or fields change; the store is migrated to match |
| `owner` | yes | `@handle` of the person who approves changes |
| `roles` | yes | Who uses it and what each role may do (`id`, `description`, `can: [...]`) |
| `entities` | yes | The data: each entity has `name`, `key`, `fields` (`name`, `type`, `required`, optional `values`, `ref`, `private: true`) |
| `screens` | yes | Pages or views: `id`, `role`, `shows`, `actions` |
| `flows` | no | Step lists across screens (book, cancel, reschedule…) |
| `rules` | yes | Business rules in plain words, each with an `id` so code, tests and chats can cite them |
| `notifications` | no | `when`, `to` (a role), `channel` (email, chat, SMS), `template` (path in the brain) |
| `data_store` | yes | `rung` (1, 2 or 3), `provider`, `pointer` (path to `DATA-STORE.md`) |
| `file_storage` | no | `provider` and `folders` (logical names only, e.g. `waivers/`, `photos/`) |
| `mirror_to_brain` | no | What may be copied back into the brain, and where |
| `questions` | no | Path to the question list (coverage checklist) used to fill or update this spec |

**Field types:** `text`, `long_text`, `integer`, `number`, `money` (the value lives in the store, never in the brain), `percent`, `date`, `time`, `datetime`, `boolean`, `enum` (with `values`), `ref` (with `ref: <entity>`), `file`, `email`, `phone`. Mark personal-data fields `private: true`: the generator must restrict them to staff roles and must never mirror them.

**Body sections** (plain language, for people and agents): `## What it does`, `## Rules explained`, `## Open questions`, `## Out of scope`.

### Worked example: `tour-booking`

A made-up farm, *Green Valley Farm* (fictional), runs three tours. The full spec is in the catalog at [`catalog/app/tour-booking/APP.md`](../catalog/app/tour-booking/APP.md). An abridged version:

```yaml
---
name: tour-booking
title: Farm tour booking
purpose: Guests book a tour slot online; staff see the day's manifest; the farm stops overbooking and chasing deposits by hand.
status: spec
version: 0.1.0
schema_version: 1
owner: "@farm-owner"
roles:
  - {id: guest, description: "Member of the public or a school", can: [view_slots, book, cancel_own]}
  - {id: staff, description: "Front desk and guides", can: [view_manifest, check_in, reschedule]}
  - {id: owner, description: "Approves rules, seasons and refunds", can: [all]}
entities:
  - name: tour_type
    key: id
    fields:
      - {name: id, type: text, required: true}            # orchard-walk, goat-feeding, harvest-workshop
      - {name: duration_min, type: integer, required: true}
      - {name: capacity_per_slot, type: integer, required: true}
      - {name: season, type: enum, values: [all-year, harvest-only], required: true}
      - {name: deposit_rule, type: enum, values: [none, percent-for-groups, full-upfront], required: true}
  - name: slot
    key: id
    fields:
      - {name: id, type: text, required: true}
      - {name: tour_type, type: ref, ref: tour_type, required: true}
      - {name: starts_at, type: datetime, required: true}
      - {name: seats_left, type: integer, required: true}
      - {name: status, type: enum, values: [open, full, closed-weather, closed-season]}
  - name: booking
    key: id
    fields:
      - {name: id, type: text, required: true}
      - {name: slot, type: ref, ref: slot, required: true}
      - {name: guest_name, type: text, required: true, private: true}
      - {name: guest_contact, type: email, required: true, private: true}
      - {name: party_size, type: integer, required: true}
      - {name: deposit_due, type: money}
      - {name: status, type: enum, values: [pending-deposit, confirmed, cancelled, attended, no-show]}
rules:
  - {id: R1, text: "A booking never takes seats_left below zero; re-check capacity at confirm time."}
  - {id: R2, text: "Groups of 10 or more pay a 30% deposit within 48 hours or the hold is released."}
  - {id: R3, text: "Cancel 7+ days before: deposit refunded. 2-6 days: half refunded. Under 48 hours: not refunded."}
  - {id: R4, text: "If the farm cancels (weather, closure) the guest chooses a full refund or a free reschedule."}
  - {id: R5, text: "Harvest workshop runs September to November only; the farm closes two weeks in February."}
data_store: {rung: 1, provider: google-sheets, pointer: apps/tour-booking/DATA-STORE.md}
file_storage: {provider: google-drive, folders: [waivers/, group-lists/]}
mirror_to_brain:
  - "Monthly counts per tour type (no names) → log/"
---
```

---

## The storage ladder

Pick the lowest rung that fits; move up when a "move up when" line becomes true. The spec defines the schema, so moving up is a planned migration, not a rebuild.

| | Rung 1: free | Rung 2: middle | Rung 3: advanced |
|---|---|---|---|
| **Database** | Google Sheets (or Excel Online), one tab per entity | Managed Postgres on a free tier (e.g. Supabase: Postgres + auth + file storage) | Postgres you host (e.g. a small Hetzner VPS) |
| **Files** | Google Drive (or OneDrive) folders | The provider's file storage, or Drive | Object storage or disk on the server, plus offsite copies |
| **Choose it when** | One site, low volume (tens to a few hundred records a month), a handful of staff, the owner wants to see and edit the data directly | Several staff or guests writing at once, logins needed, capacity must be enforced reliably, or more than one app shares the data | High volume, many users, custom integrations, strict data-residency or audit needs, or managed-tier limits/costs are hit |
| **Limits** | No real transactions: two people can grab the last seat at once (mitigate by re-checking capacity at confirm, rule R1). Per-spreadsheet cell caps and API rate quotas. Formulas and manual edits can break structure | Free tiers have small database and storage caps, few or no automatic backups, and may pause idle projects. Check the provider's current limits | You run everything: updates, TLS, monitoring, backups, restores |
| **Setup effort** | 10–20 min: create the sheet from the spec, share with staff, link the page | 30–60 min first time: project, tables from the spec, access rules, auth | Half a day or more: server, Postgres, hardening, backups, deploy |
| **Backup / export** | Built-in version history; scheduled CSV export per tab to a backup folder | Scheduled `pg_dump` (or the provider's export) to a separate store; CSV per entity for the export contract | Nightly `pg_dump` to offsite storage; a restore test at least monthly |
| **Privacy** | Data sits in the client's own Google/Microsoft account. Share with named staff only; never "anyone with the link" for personal data | Pick a region close to the users; turn on row-level access rules; review the provider's data terms | Full control of region and access; full responsibility for security patches and breach handling |

Microsoft 365 is a valid rung 1 (Excel Online + OneDrive). Neon or another managed Postgres is a valid rung 2.

### How a brain records the rung

- In `APP.md`: `data_store: {rung, provider, pointer}` and `schema_version`.
- In `apps/<name>/DATA-STORE.md`: a short pointer file, never credentials. Example in [`catalog/app/tour-booking/DATA-STORE.example.md`](../catalog/app/tour-booking/DATA-STORE.example.md).

```markdown
# Data store: tour-booking
rung: 1 · provider: google-sheets · schema_version: 1
location: spreadsheet "Green Valley - tour bookings" in the farm's Drive (link kept by the owner, not here)
files: Drive folder "Green Valley - tour files" (waivers/, group-lists/)
access: owner (edit), staff role (edit bookings tab only)
secrets: service account key held in the host's secret store. Never in this brain.
backup: weekly CSV export per tab to "backups/"; last checked 2026-10-10
## Migrations
- 2026-10-10 · created on rung 1 · schema 1 · @farm-owner
```

In a shared brain, write the location as a name plus where the link is kept; a bare link to a private sheet is fine only in a private brain. Keys, passwords, connection strings and tokens go in a secret store (the host's secret settings, a password manager); the lint blocks them in any case.

### Migration between rungs (the export/import contract)

Every rung must be able to produce and accept the same export:

1. **One CSV per entity**, named `<entity>.csv`, header row = field names from `APP.md` in spec order. UTF-8, ISO 8601 dates and datetimes with offset, `.` decimal, booleans `true`/`false`, enum values exactly as in the spec, `ref` fields hold the target's key.
2. **`files.csv`** for file fields: `entity, key, field, relative_path, sha256`, plus the files themselves in a folder.
3. **`export.json`**: `app`, `schema_version`, `exported_at`, `rung_from`, row counts per entity.

Moving up:

1. Owner approves the move and the target rung (record the decision in the brain's log).
2. Create the target store from the spec (tables, types, constraints such as "seats_left ≥ 0", private-field access rules).
3. Freeze writes on the old store (or run during a quiet window), export, import, compare row counts and spot-check records.
4. Point the page at the new store; keep the old one read-only for at least 30 days.
5. Update `data_store` in `APP.md` and add a line under `## Migrations` in `DATA-STORE.md`.

Schema changes follow the same contract: bump `schema_version`, prefer additive changes (new optional fields), and describe any rename or split in `apps/<name>/changes.md` so the import step can map old columns to new ones. Moving down a rung uses the same export.

---

## Pattern: dynamic profile chat

A thin chat page that collects what a business does, in a real back-and-forth, and keeps a profile up to date after every reply. It replaces fixed questionnaires. The catalog item is [`dynamic-profile-chat`](../catalog/app/dynamic-profile-chat/APP.md); file formats are in its `PROFILE-FORMAT.md`.

**Per client folder** (in the intake brain, e.g. `clients/<client>/`):

| File | What | Written |
|---|---|---|
| `profile.md` | Every known fact: field, value, source, confidence, confirmed flag, last updated | After every reply |
| `changes.md` | Append-only: what changed, old → new, when, who said it, source | After every reply |
| transcript | The raw conversation | Kept **outside git** (server or private file storage), with a retention period the owner sets |

**Each turn:**

1. The page loads the brain: the app or brain-kind spec, the **question list** (a coverage checklist, not a script) and the current `profile.md`.
2. The person replies by text, voice note (transcribed and shown back before use) or file upload.
3. An LLM reads the whole reply against the whole profile and returns a structured patch: every field the reply touches, with `value`, `source` (`chat:<turn>`, `upload:<file>`, `research:<where>`), `confidence` (`high` \| `med` \| `low`), `confirmed` (only when the person stated or confirmed it), and the quoted words it relied on. One reply can update many fields; nothing is ignored because it was "not the current question".
4. The patch is validated against the spec (types, enum values, required fields). Invalid parts become an open question, not a guess.
5. `profile.md` is rewritten and `changes.md` gets one line per changed field. Corrections ("actually it's 20 per slot") are just another patch; the old value is kept in `changes.md`.
6. Coverage is recomputed against the question list. The next question is the most useful open item: required and unknown first, then low-confidence or unconfirmed, then items unlocked by earlier answers. Pre-filled research is put to the person as "From what we found, X. Is that right?"
7. The side panel is simply `profile.md` rendered in plain language, grouped by section; finished sections collapse.

**Who is answering.** The chat asks first: the owner, or someone answering on the owner's behalf (consultant, vendor, staff), plus their name. Every change line carries it. Commercial or policy fields answered by someone other than the owner are flagged "owner to confirm".

**Commits.** Files are written after every reply; a commit happens at the end of each section and when the chat goes quiet. One folder per client means two sessions never write the same file.

**Handoff statuses** (frontmatter `status` in `profile.md`):

| Status | Meaning | Who moves it |
|---|---|---|
| `draft` | Chat in progress | intake |
| `in_review` | Required coverage complete (or staff ended the chat); nothing is live | intake or staff |
| `approved` | A person reviewed every field marked unconfirmed or "owner to confirm" | approver (a person) |
| `setup_done` | The setup role built or configured from the approved profile and recorded what it set | setup |

Nothing goes live before `approved`. Answers that arrive after `setup_done` reopen only the touched fields (`in_review` for those fields) and flow through the same approval.

At larger scale the live copy can move to a database (rung 2) while the approved profile is still committed to the brain; the files above remain the format of record.

---

## Runbook: new client in 30 minutes

Goal: from sharing the brain to a working test run in under 30 minutes. This is only realistic when the preparation below exists **before** the call. The first client of a new kind usually takes longer; the second should hit the target.

**Must exist beforehand**

- [ ] A **brain kind** for this type of business in a catalog (e.g. `tour-operations`), with folders, rules and SITEMAP rows.
- [ ] Its **question list** (coverage checklist) with required items marked.
- [ ] The **app spec(s)** it uses (e.g. `tour-booking`), with defaults the client only confirms or edits.
- [ ] A **data-store pointer template** and the chosen default rung (usually rung 1).
- [ ] Optional but recommended: a **research pre-fill** from public information (website, listings), each fact marked `research:` with confidence, done before the clock starts.
- [ ] On the client side: who will answer (owner, or someone on their behalf), and an admin who can create or share a Google or Microsoft folder during the call.

**Time boxes**

| Minutes | Step | Done when |
|---|---|---|
| 0–5 | **Create and share the brain.** Spin off from the brain kind (MEMBRAIN.md section B), add the client's editors, open the intake chat link | Brain exists, lint passes, the client has the link |
| 5–20 | **Collect the workflow.** Dynamic profile chat: confirm the pre-fill, then fill gaps (for tours: tour types, capacity per slot, seasons, deposits, cancellation, how guests book today) | Every required question covered; unknowns listed as open items |
| 20–25 | **Link document storage.** Create the store from the spec (rung 1: sheet tabs from entities, Drive folders from `file_storage`), share with named staff, write `DATA-STORE.md` | Pointer file committed, no secrets in the brain |
| 25–30 | **Test run.** One end-to-end case on test data (e.g. book a slot, take a deposit flag, cancel inside 48 hours) checked against the rules | Result logged; profile set to `in_review` |

**If time runs out:** cut storage linking first (do it in a 10-minute follow-up), never the test run's rule checks. **After the call:** the approver reviews and sets `approved`; the setup role builds; lint; one log entry.

---

## Roles

Generic roles, so any AI tool or person can fill them:

| Role | Does | Never |
|---|---|---|
| **research** | Pre-fills facts from public sources, each with source and confidence | Marks anything confirmed |
| **intake** | Runs the dynamic chat, updates `profile.md` and `changes.md` | Changes rules or goes live |
| **setup** | Builds or configures the app and store from an `approved` profile or spec; records what it set | Builds from a draft, or stores secrets in the brain |
| **approver** | A person: reviews and approves profiles, specs, rung moves and go-live | Is replaced by an agent |
