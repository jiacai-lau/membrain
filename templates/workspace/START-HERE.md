# Start here

Paste one of these into your agent as the first message. They point at the live rules; they never copy them. The rules live in `AGENTS.md` (this workspace) and each brain's `CLAUDE.md`.

## Owner (has the personal brain)

```text
I am <name>. Read AGENTS.md in this Membrain workspace and follow it. Then tell me the TLDR and the one next task.
```

## Everyday (after the first message)

Short commands such as `status`, `check-up`, `file this`, `log this` and `continue` are defined in `docs/COMMANDS.md`. To resume work in a new session:

```text
Read AGENTS.md in this Membrain workspace and follow it. Continue <topic>: open its topic note, tell me where it
stands and the next step, then carry on.
```

## Teammate (one shared brain only)

```text
I am <name>. Read CLAUDE.md in this folder and follow it.
```

## Weekly lint (scheduled job)

```text
Weekly Membrain lint. Read AGENTS.md in <workspace path> fresh, then follow guides/weekly-lint.md for every brain
listed in brains/personal/brains.yaml. Propose fixes to me in one message; if there are none, say nothing.
Change nothing until I say yes.
```

## Spin off a shareable brain / upgrade Membrain

```text
Read AGENTS.md here, then follow section B of <source>/MEMBRAIN.md (source is in .membrain.yaml) to spin off
a brain called <name> for <purpose>. Show me the move list and privacy check first; create no repo and invite
nobody until I say so.
```

```text
Follow section C of <source>/MEMBRAIN.md: run scripts/upgrade.sh (dry run), show me the changelog and the
proposed framework changes, and apply only after I say OK. Never overwrite my content files.
```

## Browse the catalog

```text
Follow section D of <source>/MEMBRAIN.md (source is in .membrain.yaml): run scripts/catalog.py diff, show me what is
new or updated in every catalog I use with each item's status, and install only the items I pick.
```
