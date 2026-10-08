# onboarding-brain (brain kind)

**Status:** idea · **Version:** 0.1.0 · **Who it's for:** a team that runs a go-live or handover acceptance with each new client.

## Purpose
A shared brain built around one question set the client works through: each row is something the client checks themselves and marks Accept or Not accept. Open items go to an Exceptions table with an owner and a target date, and a signature block closes it. The structure comes from a real handover checklist; every client name, contact, code, price and invoice rule was removed.

## Depends on
Nothing.

## Config
None yet. Party names and dates are filled per client, in a per-client copy of `checklist.md`.

## Install
Not installable yet: status **idea**, so `spinoff.sh --from catalog:onboarding-brain` refuses it. To try the question set by hand, read `checklist.md` in this folder and copy it into a project in your personal brain. Keep client contacts and commercial terms in the personal brain.

## Files
| Path | Role |
|---|---|
| `checklist.md` | Generic go-live acceptance form: how acceptance works, sign-off rows, exceptions, acknowledgement |
| `CLAUDE.md.overlay` | Folders section for the brain's `CLAUDE.md` |
| `SITEMAP.rows` | SITEMAP row for `checklist.md` |
