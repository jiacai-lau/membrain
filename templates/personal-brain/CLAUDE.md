# {{BRAIN_NAME}} (personal brain of @{{OWNER}})

Private. Only @{{OWNER}} and @{{OWNER}}'s own agents read this. Never share this repo, never copy it into a shared brain, never mention it inside one.

Everything starts here ("alpha" brain). When a topic grows into something others need, spin it off with `scripts/spinoff.sh` and leave a pointer here.

## Boot
1. Read `ROUTES.md` first. It says which brain owns which topic, for reads and for writes.
2. Read `STATE.md` for the current position and the one next task.
3. For the task, open the brain the route names: its `CLAUDE.md`, `SITEMAP.md`, then the owning file. Do not answer from memory. Say which files you opened, or that you did not check.

## What goes here
- Anything not owned by a shared brain in `ROUTES.md`
- Process how-tos (`howto/`), project notes (`projects/<name>/`)
- Private context: finance, pricing, grants, commercial terms, people, personal
- Pointers to shared brains (`pointers/`), never copies of their lines

## What stays out
- Passwords, keys, tokens: keep them in a password manager; store only where to find them
- Copies of facts a shared brain owns: keep a one-line pointer instead

## Writing
Append one line in the entry format (`docs/ENTRY-FORMAT.md` in the workspace). Unsure where it goes: `inbox.md` with `route?`.
Before moving anything to a shared brain: `scripts/spinoff.sh <brain> --move <file>` (privacy check + pointer stub), and @{{OWNER}}'s OK.

## Sends
Draft. @{{OWNER}} sends.
