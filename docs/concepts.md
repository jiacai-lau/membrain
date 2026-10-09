# Concepts

This page explains how Membrain is put together and why. For the steps an agent follows, see [MEMBRAIN.md](../MEMBRAIN.md). For quick answers, see the [FAQ](faq.md).

## Brains

A **brain** is a folder of markdown files that people and agents read and write. Each brain is its own git repo, so it has its own history, its own access list and its own rules (`CLAUDE.md`, with `AGENTS.md` for non-Claude agents).

There are two kinds:

| | Personal brain | Shared brain |
|---|---|---|
| Who sees it | Only you | You and the teammates you invite |
| What goes in | Everything, at first | One topic others need (support, ops, a client) |
| Holds the routes | Yes (`ROUTES.md`, `brains.yaml`) | No |
| How it's made | At setup (section A) | Spun off from the personal brain (section B) |

Your **workspace** (default `~/membrain`) holds the brains side by side under `brains/`, plus the shared rules, docs and scripts. The workspace itself is not a git repo. Brains are sibling repos rather than git submodules, because a submodule would write the personal brain's URL into the repo that contains it.

## Start private, spin off later

Everything goes into your personal brain first. When a topic becomes useful to others, you **spin it off**: your agent creates a new shared brain, privacy-checks every file you want to move, moves the clean ones, leaves a one-line pointer behind in your personal brain, and registers the new route. Files that fail the check stay where they are until you approve a redacted copy.

Starting private means you never have to decide up front what's shareable. Spinning off means sharing is a deliberate, reviewed step.

## Routing

Your agent needs to know which brain to read from and which to write to. That map lives in your personal brain:

- `brains.yaml` is the registry: each brain's name, path, remote, owner, editors, topics, keywords and "never" words.
- `ROUTES.md` holds the decision order in plain words plus a table generated from `brains.yaml`, so the two can't drift.

The decision order for a write:

1. **Privacy first.** Money, credentials, personal identifiers, contract terms, raw chats and opinions about people stay in the personal brain.
2. **Topic.** If exactly one shared brain owns the topic, write there. A "never" word rules a brain out.
3. **Unsure or a tie** goes to the personal `inbox.md` for you to decide.
4. **A mixed note is split**: the reusable part goes to the shared brain, the private part stays personal with a pointer.
5. **One fact, one home.** The same fact is never written into two brains.

Reads go the other way round: the brain that owns the topic first (it's the source of truth), then personal for private context.

## The one-way privacy rule

Personal may point to shared. Shared never references personal: not its name, path, aliases or contents. A teammate can clone a shared brain and learn nothing about anyone's personal brain.

Lint enforces this. It reads the personal brain's names from the registry at run time, so even the list of forbidden words never sits inside a shared repo.

## Sitemaps

Each brain has a `SITEMAP.md`: one row per file saying which kind of fact that file owns, who maintains it, how to write to it, and two dates.

```
| Path | Owns | Owner | Write rule | Last changed | Last checked |
| playbook/fixes.md | known fix for a symptom | @alice | append one line | 2026-10-06 | 2026-10-08 |
```

"Last changed" and "last checked" are separate on purpose. A check that finds nothing new moves only "last checked", so you can tell a file that's quiet but current from one nobody has looked at.

The sitemap travels with its brain. The only cross-brain map is `ROUTES.md`, and it lists brains, not files.

## Entries

Knowledge is stored as one-line **entries**, appended at the bottom of the file that owns the topic:

```
- <fact or symptom> → <fix or answer> · <context> · YYYY-MM-DD · @owner · verified|unverified|assumption · src:<link or id>
```

- **Dated and owned.** Every line says when it was true and who stands behind it.
- **Status is honest.** Agents write `unverified` by default. Only a person who checked the system of record writes `verified`.
- **Append-only.** Nobody edits or deletes someone else's line. To retire one, append ` · SUPERSEDED <date>: <reason>` and add the replacement as a new line. History stays readable in the file and in git.
- **Verified writes.** An agent reads the file back and runs lint before it says "saved".

Anything longer than a line goes in `handoffs/` as a dated, versioned file.

## Inbox and approval

Each brain has an `inbox.md`, used differently by the two kinds of brain:

- **Shared brain.** Any agent that follows the brain's `CLAUDE.md` appends entries directly to the file that owns the topic: append-only, dated, owned, and retired only with a ` · SUPERSEDED` tail. The inbox is only for lines the agent is unsure belong there and for automatic captures. Structure changes (folders, rules, scripts, removing, merging or moving lines) are owner-only.
- **Personal brain.** When the route is unclear (no shared brain matches, or two do), the line goes to the personal `inbox.md` and your agent asks you.

An inbox line moves into the brain only after a person approves it and lint passes. Old inbox items are flagged so the queue doesn't rot.

## Lint

One lint covers every brain:

- **Privacy leaks** in shared brains: prices and amounts, secrets and tokens, emails, phone and ID numbers, and any mention of a personal brain.
- **Duplicates**: exact duplicate lines and near-duplicates.
- **Freshness**: stale deadlines, sitemap rows not checked recently, old `unverified` lines.
- **Structure**: missing sitemap, broken sitemap links, files the sitemap doesn't list, accidental "Copy of" files.

Brains can add their own checks with optional per-brain plugins, switched on in `.membrain/lint.yaml`. Lint only warns, so note-taking never stops; `--strict` turns findings into a failing exit code. It runs as a pre-commit hook in every brain (which blocks commits that leak something private), in a GitHub Actions workflow on every push (report in the run summary), and as a weekly routine in which an agent also looks for contradictions and stale tickets and proposes fixes ([guides/weekly-lint.md](../templates/workspace/guides/weekly-lint.md) shows how to schedule it).

## Staying in sync

Shared brains change while you work. Hooks for Claude Code and Cursor pull a brain when your copy is stale and push when you changed it, so agents don't answer from an old copy. Agents also reread the live rules at the start of each task and right before any write, and scheduled jobs point at `AGENTS.md` instead of copying it.

## The log

Each brain keeps a monthly log (`log/YYYY-MM.md`): one entry per session that answered from or changed the brain, starting `## [YYYY-MM-DD HH:MM] <type> | <subject> | <last action>`, so you can `grep` it by date, type or subject (`grep -h "^## \[" log/*.md | tail -5` shows the last five). This follows the log idea in Andrej Karpathy's [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

## Templates, generation and upgrades

Membrain itself contains no knowledge. It's a set of templates listed in `MANIFEST.yaml`. Each entry says where the file goes and whether it's:

- **framework**: Membrain's file (rules, docs, scripts, hooks). Upgrades may replace it.
- **content**: yours after generation (sitemaps, state, inbox, routes). Never overwritten.

Your workspace records the `membrain_version` it was made from and a hash of every generated file. To upgrade, your agent fetches the new version, compares hashes and shows you three kinds of change: files Membrain updated that you didn't touch, new framework files, and conflicts where you edited a framework file yourself. It applies only what you approve and never touches content.

## The catalog

The catalog is a shelf of installable items, separate from the templates every workspace gets. An item is a folder with an `ITEM.md` (purpose, who it's for, status, dependencies, config, install steps) and its files. There are six types: **brain kinds** (a shape for a new shared brain, such as a support brain), **skills** (a procedure an agent follows), **routines** (a scheduled prompt), **agents** (a hire with a defined job), **apps**, and **data sources** (what a system's fields mean).

Each item has a status, and your agent says it out loud: **live** (in daily use), **built-untested** (works, needs one supervised run), **spec** (a design, no code) or **idea**. Spec and idea items install only as documents.

Catalogs come from more than one place. The public Membrain catalog holds generic items only. Anything that names your organisation's systems lives in a private catalog repo with the same layout, listed under `catalogs:` in your `brains.yaml`. Your agent merges all of them when it shows you what's new.

Installing is explicit. Your agent installs only what you pick, asks for the config the item needs, writes the files to `brains/personal/installed/<type>/<id>/` and records the version and file hashes in `.membrain.yaml`. A newer version shows up as an update; a file you edited shows up as a conflict instead of being overwritten. A brain kind isn't installed: you spin off a new shared brain from it. Routines and agents do nothing until you register their prompt in your agent platform; Membrain never schedules anything itself.

## Apps (draft)

A brain can describe a simple app (a booking page, a form, a dashboard, an intake chat) in `apps/<name>/APP.md`: who uses it, its data, screens, rules and notifications. An agent builds the app from that spec, so nothing is hard-coded and a change to the business is a change to the spec. Rules and process stay in the brain; live data (bookings, guests, uploads) goes in a store chosen from a ladder of free (Google Sheets and Drive), middle (managed Postgres) and advanced (self-hosted Postgres). The brain records the rung and where the data is, never the credentials, and the schema in the spec makes moving up a rung a planned migration. Details, the dynamic profile chat pattern and a 30-minute setup runbook: [apps.md](apps.md).

## Where the ideas come from

- **Andrej Karpathy's LLM Wiki**: compile knowledge once into markdown and keep it current, lint it regularly, keep a greppable log.
- **A real team brain run in production**: a start-here prompt that first asks who the agent is working for; objectives that every line must serve; a `STATE.md` with a TLDR and the one next task; a source map with an access ladder (identified → reachable → authenticated → permitted → reviewed); data and access requests with an owner and a date needed; verified writes; separate "last checked" and "last changed" dates.
