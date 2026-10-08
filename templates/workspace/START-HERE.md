# Start here

Paste one of these into your agent as the first message. They point at the live rules; they never copy them. The rules live in `AGENTS.md` (this workspace) and each brain's `CLAUDE.md`.

## Owner (has the personal brain)

```text
I am <name>. Read AGENTS.md in this Membrain workspace and follow it. Then tell me the TLDR and the one next task.
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
