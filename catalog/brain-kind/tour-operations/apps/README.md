# Apps

One folder per app this brain runs, following Membrain `docs/apps.md`:

- `apps/<name>/APP.md`: the spec (roles, entities and fields, screens, rules, notifications, data-store rung). The brain is the source of truth for these.
- `apps/<name>/DATA-STORE.md`: where the live data is (rung, provider, location name, access, backups, migrations). Never passwords, keys, tokens or connection strings.
- `apps/<name>/changes.md`: optional, append-only log of spec changes.

Start with the catalog's `tour-booking` spec. Live bookings and guest details stay in the data store; only counts and approved rule changes come back here.
