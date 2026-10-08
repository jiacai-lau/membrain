# Privacy classifier

Applies to every write into a **shared** brain, and to every item moved out of a personal brain.
Personal brains may hold anything except credentials (use a password manager; store only a pointer).

## Never allowed in a shared brain

| Class | Examples | Lint |
|---|---|---|
| Money | prices, `$5`, `SGD 12`, quotations, grant amounts, salaries, margins, bank balances, loan figures, contract values | E101, E108, W106 |
| Credentials | passwords, API keys, tokens, OTPs, session URLs, "password: …" | E105 |
| Personal identifiers | NRIC/FIN/passport numbers, personal phone numbers, personal WhatsApp ids (`…@c.us`), home addresses, personal emails, bank account numbers | E102–E104 |
| Commercial | proposals, terms, other clients' commercial files, pricing strategy, grant applications | W106 |
| Raw conversations | full WhatsApp or email threads, screenshots of chats (link to the source instead) | review |
| People | opinions about people, HR matters, performance notes | review |
| Private-brain references | the personal brain's name, aliases or path, `/Users/<name>/…`, "see my personal notes" | E107 |

Work emails of the brain's editors may be listed in the brain's CLAUDE.md if that brain's `.membrain.yaml` allows the domain (`privacy_allow`).

## Labels (when moving or promoting an item)

| Label | Meaning |
|---|---|
| `SHAREABLE_REVIEWED` | The owner checked the exact text and lint passed. Only now may it go into a shared brain. |
| `PRIVACY_REVIEW_NEEDED` | Lint flagged it, or you are unsure. It stays personal (or in the inbox) until the owner decides. |
| `CLEARED_REDACTED` | A redacted version (amounts, names removed) was checked; only that version moves. |

A title or filename is not a privacy check. Lint passing is not owner approval. Moving needs both
(two-part acceptance: the owner approves the content, lint passes the privacy check).

## Mixed notes

Split them. Example: "Client C: a one-off coupon at $1 overrides the member rate; add customer 123 to the member list"
- shared (cs-brain): `- Member rate ignored at checkout → a one-off coupon overrides the member rate; remove the coupon or add the customer to the member list · Client C · 2026-10-07 · @alice · verified`
- personal: the actual amounts, with `→ cs-brain:playbook/fixes.md` as a pointer.

## Escape hatch

If lint flags a line that is genuinely fine (e.g. `price 0` describing a system default), the owner may add `<!-- lint:allow -->` to that line. Agents may not add it themselves.
