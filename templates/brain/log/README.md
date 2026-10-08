# Activity log

One file per month: `log/YYYY-MM.md`. One entry per session that answered a question from this brain or changed it. Add at the bottom only.

```
## [YYYY-MM-DD HH:MM] <type> | <subject> | <last action>
who/tool: <name or tool> · files: <files touched>
```

`<type>` is one of the `log_types` in `.membrain/lint.yaml` (default: `fix`, `ticket`, `client`, `lint`, `answer`). Lint checks the format (L070).

Last 5 entries: `grep -h "^## \[" log/*.md | tail -5`
All fixes this month: `grep -h "^## \[.*\] fix " log/$(date +%Y-%m).md`

No chat transcripts, amounts or passwords. Knowledge goes in the brain's note files, not here; the log only says what happened.

The fixed, greppable prefix follows the log idea in Andrej Karpathy's [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).
