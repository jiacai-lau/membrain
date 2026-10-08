# ROUTES: where to read and where to write

Private to @{{OWNER}}. This is the only cross-brain map. It says which brain owns a topic; each brain's own
`SITEMAP.md` says which file inside it. Do not copy file lists here.

## Decision order for a write
1. **Privacy first.** Money, prices, quotations, grants, salaries, credentials, personal ids/phones/emails,
   contract terms, raw chats, opinions about people → stay here (personal). See `docs/PRIVACY.md`.
2. **Topic.** Exactly one shared brain below owns it → write there (its CLAUDE.md "What goes here").
   A word in its "Never put here" column rules it out.
3. **Unsure or two match** → `inbox.md` here with `route?`, ask @{{OWNER}}.
4. **Mixed** → split: clean fix to the shared brain, private part here with a pointer to the shared line.
5. One fact, one home. Never the same line in two brains.

## Decision order for a read
1. The brain that owns the topic first (source of truth), then this brain for private context and pointers.
2. A pointer here (`→ <brain>:<file>`) means: go read it there.
3. `scripts/route.py classify "<question>"` does steps 1–2 for you.

## Rules for shared brains
- They never name, link or quote this brain. Lint enforces it (E107) using the names in `brains.yaml`.
- Teammates' agents only ever see shared brains.

## Brains
<!-- membrain:routes:begin -->
<!-- membrain:routes:end -->
