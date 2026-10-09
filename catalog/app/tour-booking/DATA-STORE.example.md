# Data store: tour-booking (EXAMPLE, fictional)

Copy to `apps/tour-booking/DATA-STORE.md` in the client's brain and fill it in. This file says where the live data is. It never holds passwords, keys, tokens or connection strings.

rung: 1 · provider: google-sheets · schema_version: 1
location: spreadsheet "Green Valley - tour bookings" in the farm's own Drive (link kept by the owner, not in this file)
tabs: tour_type, slot, booking (one tab per entity in APP.md, header row = field names in spec order)
files: Drive folder "Green Valley - tour files" with waivers/ and group-lists/
access: owner (edit all), staff role (edit booking and slot tabs), guests never see the sheet
secrets: the page's service account key is held in the host's secret settings. Never here.
backup: weekly CSV export of every tab to the "backups/" folder; restore tested 2026-10-10
move up when: two or more staff confirm bookings at the same time, or bookings exceed a few hundred a month, or guests need logins (then rung 2)

## Migrations
- 2026-10-10 · created on rung 1 · schema 1 · @farm-owner
