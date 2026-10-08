# proposal-claim-review (skill)

**Status:** spec · **Version:** 0.1.0 · **Who it's for:** whoever approves proposals, decks or replies that describe what a product does.

## Purpose
A review process: given one proposal and your list of product claims, the agent returns exactly one verdict (OK, NOT OK or REQUIRE CHANGE) with numbered reasons, flags any feature that is committed but not live, and drafts one message per proposal. Written down, not yet run in production.

## Depends on
Nothing. Organisations add their own claim sources in a private catalog item that points here.

## Config
| Key | Meaning | Example |
|---|---|---|
| `CLAIMS_LIST_PATH` | File that lists each product claim and whether it is live or committed | `brains/personal/howto/product-claims.md` |
| `CHANNEL` | Where the review message goes (the agent drafts; a person sends) | `#proposals` |

## Install
Status **spec**: `catalog.py install proposal-claim-review --docs` copies `SKILL.md` into `brains/personal/installed/skill/proposal-claim-review/` so you can try it by hand ("Review this proposal with installed/skill/proposal-claim-review/SKILL.md"). Pass `--set` values to fill the config; unset keys stay as `<KEY>` markers.

## Files
| Path | Role |
|---|---|
| `SKILL.md` | The review process |
