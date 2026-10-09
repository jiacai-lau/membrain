# dynamic-profile-chat (app)

**Status:** spec · **Version:** 0.1.0 · **Who it's for:** a team that onboards clients (or sets up a brain for a new business) and wants a real back-and-forth intake instead of a fixed questionnaire.

## Purpose
**Specification only: there is no code.** A thin chat page that reads the brain (spec, question list, current profile), lets an LLM update every field a reply touches, and keeps `profile.md` and `changes.md` per client current after every reply. The question list is a coverage checklist, not a script. Staff approve before anything goes live; statuses `draft`, `in_review`, `approved`, `setup_done`. Pattern described in `docs/apps.md`; it replaces the fixed-question intake idea in `client-onboarding-portal`.

## Depends on
Nothing. Works with any brain kind that ships a question list (for example `tour-operations`).

## Config
None until it is built. To build it you will need: an LLM provider that returns structured output (key held in a secret store, never in a brain), a host for the page, and a private place for transcripts.

## Install
Status **spec**: `catalog.py install dynamic-profile-chat --docs` copies `APP.md` and `PROFILE-FORMAT.md` into your brain as documents. Do not build or deploy it, or send real client data to an LLM provider, without the owner's OK.

## Files
| Path | Role |
|---|---|
| `APP.md` | The app spec: roles, entities, turn loop, rules, statuses |
| `PROFILE-FORMAT.md` | File formats for `profile.md` and `changes.md`, the patch the LLM returns, and a fictional example |
