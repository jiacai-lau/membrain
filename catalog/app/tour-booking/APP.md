---
name: tour-booking
title: Farm tour booking
purpose: Guests book a tour slot online; staff see each day's manifest; the farm stops overbooking and stops chasing deposits by hand.
status: spec
version: 0.1.0
schema_version: 1
owner: "@farm-owner"
questions: profile/questions.md
roles:
  - {id: guest, description: "Member of the public, a family or a school group", can: [view_slots, book, cancel_own, reschedule_own]}
  - {id: staff, description: "Front desk and tour guides", can: [view_manifest, check_in, mark_no_show, reschedule, close_slot_weather]}
  - {id: owner, description: "Sets tour types, seasons and rules; approves refunds outside the rules", can: [all]}
entities:
  - name: tour_type
    key: id
    fields:
      - {name: id, type: text, required: true}
      - {name: title, type: text, required: true}
      - {name: description, type: long_text}
      - {name: duration_min, type: integer, required: true}
      - {name: capacity_per_slot, type: integer, required: true}
      - {name: min_age, type: integer}
      - {name: season, type: enum, values: [all-year, harvest-only, school-holidays], required: true}
      - {name: deposit_rule, type: enum, values: [none, percent-for-groups, full-upfront], required: true}
      - {name: unit_amount, type: money}
      - {name: outdoor, type: boolean, required: true}
  - name: slot
    key: id
    fields:
      - {name: id, type: text, required: true}
      - {name: tour_type, type: ref, ref: tour_type, required: true}
      - {name: starts_at, type: datetime, required: true}
      - {name: seats_left, type: integer, required: true}
      - {name: guide, type: text}
      - {name: status, type: enum, values: [open, full, closed-weather, closed-season], required: true}
  - name: booking
    key: id
    fields:
      - {name: id, type: text, required: true}
      - {name: slot, type: ref, ref: slot, required: true}
      - {name: guest_name, type: text, required: true, private: true}
      - {name: guest_contact, type: email, required: true, private: true}
      - {name: party_size, type: integer, required: true}
      - {name: is_group, type: boolean, required: true}
      - {name: deposit_due, type: money}
      - {name: deposit_paid_at, type: datetime}
      - {name: waiver, type: file, private: true}
      - {name: status, type: enum, values: [pending-deposit, confirmed, cancelled-guest, cancelled-farm, attended, no-show], required: true}
      - {name: created_at, type: datetime, required: true}
screens:
  - {id: choose-tour, role: guest, shows: "tour types in season, duration, min age", actions: [pick_tour]}
  - {id: choose-slot, role: guest, shows: "open slots with seats_left for the chosen tour", actions: [pick_slot]}
  - {id: details, role: guest, shows: "party size, name, contact, waiver upload, deposit rule that applies", actions: [confirm_booking]}
  - {id: my-booking, role: guest, shows: "booking status, what a cancellation would refund today", actions: [cancel, reschedule]}
  - {id: manifest, role: staff, shows: "today's slots, bookings, party sizes, waivers missing", actions: [check_in, mark_no_show, close_slot_weather]}
  - {id: settings, role: owner, shows: "tour types, seasons, closures; edits go back into this spec for approval", actions: [propose_change]}
flows:
  book: [choose-tour, choose-slot, details, "re-check capacity (R1)", "deposit hold if R2 applies", my-booking]
  farm-cancels: ["staff closes slot (weather)", "notify each guest", "guest picks refund or reschedule (R4)"]
rules:
  - {id: R1, text: "A booking never takes seats_left below zero. Capacity is re-checked at the moment of confirming, not only when the slot is shown."}
  - {id: R2, text: "Groups of 10 or more (is_group) pay a 30% deposit within 48 hours of booking, or the hold is released and the seats return to the slot."}
  - {id: R3, text: "Guest cancels 7 or more days before the slot: deposit refunded in full. 2 to 6 days: half refunded. Under 48 hours or no-show: not refunded."}
  - {id: R4, text: "If the farm cancels (weather, animal welfare, closure) the guest chooses a full refund or a free reschedule."}
  - {id: R5, text: "Harvest workshop runs September to November only. The farm is closed for two weeks in February for maintenance. School-holiday tours run only on the published school-holiday dates."}
  - {id: R6, text: "Outdoor tours may be closed by staff on a heavy-rain warning; at least 3 hours' notice where possible."}
  - {id: R7, text: "Children under the tour's min_age cannot be booked; under-16s need a guardian waiver on file before check-in."}
notifications:
  - {when: booking confirmed, to: guest, channel: email, template: templates/booking-confirmed.md}
  - {when: deposit due in 24 hours and unpaid, to: guest, channel: email, template: templates/deposit-reminder.md}
  - {when: slot closed by farm, to: guest, channel: email, template: templates/farm-cancelled.md}
  - {when: daily 07:00, to: staff, channel: chat, template: templates/manifest-summary.md}
data_store: {rung: 1, provider: google-sheets, pointer: apps/tour-booking/DATA-STORE.md}
file_storage: {provider: google-drive, folders: [waivers/, group-lists/]}
mirror_to_brain:
  - "Monthly booking counts per tour type and no-show rate (no names, no amounts) -> log/"
  - "Approved changes to tour types, seasons or rules -> this file, with a line in apps/tour-booking/changes.md"
---

# Farm tour booking (fictional example: Green Valley Farm)

## What it does
Guests choose a tour, see only slots that are open and in season, and book. Groups get a deposit hold. Staff open the manifest each morning, check guests in and can close an outdoor slot for weather, which tells every booked guest and offers refund or reschedule.

## Tour types (example values)
| Tour | Duration | Capacity per slot | Season | Deposit rule | Outdoor |
|---|---|---|---|---|---|
| Orchard walk | 60 min | 20 | all year | percent for groups | yes |
| Goat feeding (families) | 45 min | 12 | all year | none | yes |
| Harvest workshop | 120 min | 10 | September to November | full upfront | partly |

Amounts per person are `money` fields: they live in the data store, not in this brain.

## Rules explained
- **Capacity (R1):** the last seat can only be taken once. On rung 1 (a spreadsheet) the page re-reads `seats_left` immediately before writing; on rung 2 or 3 a database constraint enforces it.
- **Deposits (R2):** only groups of 10 or more; unpaid holds expire after 48 hours.
- **Cancellation (R3, R4):** the refund depends on notice; a farm cancellation always lets the guest choose.
- **Seasons and closures (R5, R6):** slots outside a tour's season are never generated; weather closures are a staff action, logged with a reason.

## Open questions (ask the client, through the profile chat)
- Do school groups follow the same deposit rule, or are they invoiced afterwards?
- Is there a waiting list when a slot is full?
- Which payment method takes deposits today (cash on arrival, transfer, card link)?

## Out of scope
Payments processing itself, gift vouchers, multi-site operators, dynamic pricing.
