# Start here

Paste one of these into your agent as the first message. They point at the live rules; they do not copy them.

## Owner (has the personal brain)

```text
I am <name>. Read AGENTS.md in this Membrain workspace and follow it. Then read brains/personal/ROUTES.md
and brains/personal/STATE.md. Tell me the TLDR and the one next task. Before every new task and before
any write, reread AGENTS.md and the target brain's CLAUDE.md. Say which files you opened. Draft any
message; do not send it.
```

## Teammate (one shared brain only)

```text
I am <name>. Read CLAUDE.md in this folder and follow it. Read SITEMAP.md, then the file for my question.
Append one dated line with my @name when we learn a reusable fix. Do not rewrite other people's lines.
Draft replies; I send them.
```

## Scheduled job (nightly lint, inbox capture)

```text
Read AGENTS.md in <workspace path> fresh (do not use a cached copy) and note its git commit or date.
Run scripts/lint.py . and report only new errors and the inbox items older than 14 days. Change nothing
else. If AGENTS.md cannot be read, stop and report that.
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
