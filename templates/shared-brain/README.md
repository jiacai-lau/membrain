# {{BRAIN_NAME}}

{{DESCRIPTION}} People and AI agents (Cursor, Claude Code, Claude desktop, Grok and others) read it before they answer and add to it when they learn something reusable.

**This git repo is the only home for these notes.** Don't keep a second copy in a drive or wiki.

- Repo: `{{REPO}}` (private)
- Owner: @{{OWNER}} · Editors: {{EDITORS}}
- Rules for what goes in and what stays out: [`CLAUDE.md`](CLAUDE.md). Read it first.

---

## 1. Get access

The repo is private. Ask @{{OWNER}} to add your GitHub username as a collaborator, then accept the email invite from GitHub before you clone.

The owner adds people in the repo's **Settings > Collaborators**, or from a terminal:

```bash
gh api -X PUT repos/{{REPO}}/collaborators/<github-username> -f permission=push
```

## 2. One-time setup on your computer

### Mac

```bash
# 1. Install git and the GitHub CLI (needs Homebrew: https://brew.sh)
brew install git gh

# 2. Log in to GitHub (choose GitHub.com > HTTPS > log in with a web browser)
gh auth login

# 3. Tell git who you are (shows on your changes)
git config --global user.name "Your Name"
git config --global user.email "<your work email>"

# 4. Download the brain into Documents
cd ~/Documents
gh repo clone {{REPO}}

# 5. Turn on the lint check that blocks leaks before they are committed
git -C {{BRAIN_NAME}} config core.hooksPath .githooks
```

### Windows

1. Install [Git for Windows](https://git-scm.com/download/win) and [GitHub CLI](https://cli.github.com/).
2. Open **Git Bash** and run steps 2 to 5 from the Mac block. The folder lands in `Documents\{{BRAIN_NAME}}`.

### No terminal? GitHub Desktop

Install [GitHub Desktop](https://desktop.github.com/), sign in, then **File > Clone repository > {{REPO}}**. Use **Fetch/Pull** before you start and **Commit + Push** after you edit.

## 3. Point your AI agent at the brain

Whatever tool you use, the first line to the agent is always:

> Read CLAUDE.md in this folder and follow it.

| Tool | How |
|---|---|
| **Cursor** | File > Open Folder > `~/Documents/{{BRAIN_NAME}}`. `.cursor/rules/{{BRAIN_NAME}}.mdc` tells it to follow `CLAUDE.md`. |
| **Claude Code** | `cd ~/Documents/{{BRAIN_NAME}} && claude`. It reads `CLAUDE.md` automatically. |
| **Claude desktop / other chat apps** | Give it access to the `~/Documents/{{BRAIN_NAME}}` folder (file or MCP filesystem access), then send the first line above. |
| **Grok** | Tell it the brain is the private repo `{{REPO}}` (local copy `~/Documents/{{BRAIN_NAME}}`) and to read `CLAUDE.md` first. |

### Automatic sync for Claude Code and Cursor

The repo carries hooks, so nobody has to remember to pull or push:

| When | What runs | Config |
|---|---|---|
| Session start, and before each prompt | `scripts/pull-if-stale.sh` pulls if the last pull was over 10 minutes ago | `.claude/settings.json`, `.cursor/hooks.json` |
| End of each response | `scripts/push-if-changed.sh` runs `scripts/sync.sh`, only if the brain changed | same |

The first time you open the folder, Claude Code asks you to trust the project hooks: say yes. In Cursor, check that **Settings > Hooks** lists them. Other tools follow the same rules from `CLAUDE.md` / `AGENTS.md` and run `./scripts/sync.sh` themselves, or use the cron in section 5.

## 4. Everyday use

```bash
cd ~/Documents/{{BRAIN_NAME}}
git pull --rebase                 # 1. get everyone's latest notes first
# 2. add your line at the bottom of the right file (see CLAUDE.md and SITEMAP.md)
./scripts/sync.sh "playbook: <what you added>"   # 3. commit and push in one go
```

`sync.sh` pulls, commits and pushes to this repo only. It stops on a conflict and never force-pushes.

### If git says there's a conflict

Two people added lines to the same file at once. Because the rule is **add new lines only, never rewrite someone else's**, the fix is almost always to keep both:

1. Open the file and find the `<<<<<<<`, `=======` and `>>>>>>>` markers.
2. Keep both people's lines, then delete the three marker lines.
3. `git add -A && git rebase --continue && ./scripts/sync.sh`

If you're unsure, stop and ask @{{OWNER}}. Don't force-push.

## 5. Optional: auto-sync every 10 minutes (Mac or Linux)

Not needed for Claude Code or Cursor (the hooks handle it). Use it for other tools, or where people edit files by hand:

```bash
(crontab -l 2>/dev/null; echo '*/10 * * * * cd ~/Documents/{{BRAIN_NAME}} && bash scripts/sync.sh "auto-sync" >> /tmp/{{BRAIN_NAME}}-sync.log 2>&1') | crontab -
```

To stop it: `crontab -e` and delete that line. The sync stops on a conflict and leaves it for a person.

## 6. Lint

Run `python3 scripts/lint.py` any time. It reports privacy leaks, duplicates and near-duplicates, passed deadlines, broken sitemap links, and lines missing a date or an owner. It only warns; the pre-commit hook blocks commits that leak something (amounts, secrets, emails). GitHub runs it on every push and shows the report in the **Actions** run summary. Once a week the owner's agent also checks for contradictions and stale lines and proposes fixes for the owner to approve. Brain-specific checks are switched on in `.membrain/lint.yaml`.

## 7. What's inside

See [`SITEMAP.md`](SITEMAP.md): one row per file, what it owns, who maintains it, and when it was last checked.

## 8. Ground rules

The rules live in [`CLAUDE.md`](CLAUDE.md). In one breath: add new lines at the bottom, never rewrite or delete someone else's line (retire it with ` · SUPERSEDED`), nothing private goes in, agents draft and people send, and the repo stays private.

---
Made with [Membrain](https://github.com/jiacai-lau/membrain).
