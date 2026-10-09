# tour-operations (brain kind)

**Status:** spec · **Version:** 0.1.0 · **Who it's for:** a farm, attraction or small activity operator that runs scheduled tours and takes bookings, set up in under 30 minutes from sharing the brain.

## Purpose
**Design only: not yet usable with `spinoff.sh`.** A shared brain shaped for tour operations: what tours exist, the booking and cancellation policies, how-tos for staff, a client profile filled through the dynamic profile chat, and the app specs the brain runs (starting with `tour-booking`). Live bookings and guest details never sit in the brain; they live in the data store named in each app's `DATA-STORE.md`. Follows the apps layer and the 30-minute runbook in `docs/apps.md`. Example rows are fictional.

## What it adds to a shared brain
- `tours/catalog.md`: one row per tour type (duration, capacity per slot, season, deposit rule, outdoor).
- `policies/bookings.md`: capacity, deposits, cancellation, weather and season rules, one dated line each.
- `profile/questions.md`: the question list, used as a coverage checklist by the dynamic profile chat.
- `profile/profile.md` and `profile/changes.md`: the operator's profile and its append-only change log.
- `apps/README.md`: where app specs and data-store pointers go.
- A `## Folders` section in `CLAUDE.md`, SITEMAP rows and `.membrain/lint.yaml`.

## Depends on
`tour-booking` and `dynamic-profile-chat` (both spec, same catalog).

## Config
None yet. Business details come from the profile chat, not from spin-off flags.

## Install
Not installable yet: status **spec**, so `spinoff.sh --from catalog:tour-operations` refuses it. To trial it by hand, read the files in this folder, copy them into a new shared brain, and run the 30-minute runbook in `docs/apps.md` with fictional or anonymised data first. Move it to `built-untested` after one supervised run.

## Files
| Path | Role |
|---|---|
| `CLAUDE.md.overlay` | Folders section for the brain's `CLAUDE.md` |
| `SITEMAP.rows` | SITEMAP rows for the files below |
| `lint.yaml` | Lint settings: note files and log types |
| `tours/catalog.md` | Tour types table (fictional example rows) |
| `policies/bookings.md` | Booking, deposit, cancellation, weather and season rules |
| `profile/questions.md` | Question list (coverage checklist) for the profile chat |
| `profile/profile.md` | Empty profile skeleton (status draft) |
| `profile/changes.md` | Append-only change log skeleton |
| `apps/README.md` | How app specs and data-store pointers are kept |
