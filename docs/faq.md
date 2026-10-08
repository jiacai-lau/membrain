# FAQ

## Getting started

**Do I need to clone or fork Membrain?**
No. Paste the setup prompt from the README. Your agent reads `MEMBRAIN.md`, fetches the templates listed in `MANIFEST.yaml` and generates your workspace. The only thing anyone clones is a shared brain's own repo.

**What do I need?**
An agent that can read URLs and run shell commands (Cursor, Claude Code, Grok or similar), `git` and Python 3. No other dependencies; the scripts use the Python standard library.

**I don't use an agent. Can I still set it up?**
Yes. `scripts/bootstrap.py` runs section A without an agent and produces the same workspace.

**Can I import my existing notes?**
Yes. Say so during setup. Your agent copies them into your personal brain without rewriting them, adds sitemap rows and runs lint.

## Privacy

**Where does my data live?**
On your machine, in plain markdown and git. Your personal brain is a local repo. If you want a backup remote, your agent shows you a `gh repo create … --private` command and runs it only if you say so. It never creates a public one.

**How do private things stay out of shared brains?**
Three layers. Routing sends anything private to your personal brain. Every file moved during a spin-off is privacy-checked, and blocked files stay put. In every shared brain, the pre-commit hook blocks commits that add prices, secrets, emails, ID numbers or any mention of a personal brain, and the same checks are reported in CI on every push and in the weekly lint.

**Can a teammate find out my personal brain exists?**
Not from a shared brain. Shared brains contain no registry and no reference to any personal brain, and lint enforces it.

**Is lint a guarantee?**
No. It catches the common patterns. People still review what moves into a shared brain, which is why spin-offs and inbox items need your OK.

## Teams

**How does a teammate join?**
You invite them to the shared brain's git repo. They clone it and tell their agent: "Read CLAUDE.md in this folder and follow it." They don't need Membrain or a workspace.

**Can teammates' agents write to a shared brain?**
Yes. Any agent that follows the brain's `CLAUDE.md` appends one-line entries directly to the file that owns the topic. Anything it's unsure about goes to `inbox.md` for the owner to approve, and only the owner approves structure changes or removing, merging and moving lines.

**What if two people change the same fact?**
Nobody edits another person's line. The newer fact is appended as a new line, and the old one gets ` · SUPERSEDED <date>: <reason>`. Lint flags near-duplicates.

**How do I keep one brain per client?**
Spin off one shared brain per client and invite only that client's people. Your notes about all of them stay in your personal brain.

## Day to day

**How do agents know where to look?**
Your agent reads `AGENTS.md`, then `ROUTES.md` in your personal brain, then the target brain's `CLAUDE.md`, `SITEMAP.md` and the file that owns the topic. It names the files it opened.

**How do I stop agents answering from an old copy?**
The sync hooks for Claude Code and Cursor pull stale brains automatically. Agents also reread the rules before each task and each write.

**Is it only for agents?**
No. Everything is plain markdown you can read and edit yourself. The rules are written so people and agents follow the same ones.

**Does it replace search?**
No. Sitemaps tell agents which file to open, which is enough for most brains. For large brains you can add a local search tool such as [qmd](https://github.com/tobi/qmd).

## Upgrades

**How do I upgrade?**
Paste the upgrade prompt from the README. Your agent runs a dry run, shows you the changelog and every framework file it would change, and applies only after your OK.

**Will an upgrade touch my notes?**
No. Upgrades only replace framework files you haven't edited. If you edited one, it shows as a conflict and needs your explicit OK. Content files are never proposed.

## Catalog

**What is the difference between a template and a catalog item?**
Templates are what every workspace gets at setup and upgrade. Catalog items are optional: you browse them and install the ones you want.

**Is a "spec" item something I can run?**
No. A spec is a design document and an idea is a concept. Your agent installs them only as documents (with `--docs`) and says so. Only live and built-untested items install as working items.

**Where do my organisation's own items go?**
In a private catalog repo with the same layout (`scripts/catalog.py new-repo`). Register it under `catalogs:` in `brains/personal/brains.yaml`. The public catalog never holds client names, internal system details or prices.

**Will a catalog update overwrite my changes?**
No. If you edited an installed file, the update stops with a conflict and your agent shows you the difference first.
