# tour-booking (app)

**Status:** spec · **Version:** 0.1.0 · **Who it's for:** a small farm, attraction or activity operator that takes tour bookings by phone, chat or a spreadsheet and wants an online booking page without overbooking.

## Purpose
**Specification only: there is no code.** A worked example of the Membrain app spec format (see `docs/apps.md`). Guests pick a tour type and slot; capacity per slot, deposits, cancellation and seasons are rules in the spec; staff see a daily manifest. Live bookings sit in the chosen data store (rung 1: Google Sheets + Drive by default); only counts and approved rule changes are mirrored into the brain. All example data is fictional (*Green Valley Farm*).

## Depends on
Nothing. Pairs with the `tour-operations` brain kind and the `dynamic-profile-chat` app, which fills and updates this spec with the client.

## Config
None until it is built. The spec itself is the config: tour types, capacity, deposit and cancellation rules, seasons, data-store rung.

## Install
Status **spec**: `catalog.py install tour-booking --docs` copies `APP.md` and `DATA-STORE.example.md` into your brain as documents. To use it for a client, copy `APP.md` into that client's brain as `apps/tour-booking/APP.md`, replace the fictional values with the client's (through the dynamic profile chat), and have the owner approve before anything is built. Do not build, deploy or create a data store without the owner's OK.

## Files
| Path | Role |
|---|---|
| `APP.md` | The app spec (frontmatter + plain-language rules) |
| `DATA-STORE.example.md` | Example data-store pointer file (rung 1). No secrets |
