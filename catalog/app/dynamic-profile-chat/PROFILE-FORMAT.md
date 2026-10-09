# Profile file formats (dynamic-profile-chat)

All example values are fictional.

## `clients/<client>/profile.md`

```markdown
---
client: green-valley-farm
brain_kind: tour-operations
status: draft            # draft | in_review | approved | setup_done
respondents:
  - {role: owner, name: "Sam (fictional)"}
  - {role: consultant, name: "Lee (fictional)"}
coverage: {required: 18, covered: 11, confirmed: 8}
updated: 2026-10-10
approved_by:
---

# Profile: Green Valley Farm (fictional)

## Business  ✓
| Field | Value | Source | Confidence | Confirmed | Updated |
|---|---|---|---|---|---|
| business.trading_name | Green Valley Farm | research:website | high | yes (owner) | 2026-10-10 |
| business.known_as | GVF | chat:t3 | high | yes (owner) | 2026-10-10 |

## Tours
| Field | Value | Source | Confidence | Confirmed | Updated |
|---|---|---|---|---|---|
| tours.orchard_walk.capacity_per_slot | 20 | chat:t7 | high | yes (owner) | 2026-10-10 |
| tours.harvest_workshop.season | September to November | research:listing | med | no | 2026-10-10 |

## Policies
| Field | Value | Source | Confidence | Confirmed | Updated |
|---|---|---|---|---|---|
| policies.group_deposit | 30% within 48 hours, groups of 10+ | chat:t9 | high | owner to confirm (consultant) | 2026-10-10 |

## Open items
- tours.goat_feeding.min_age: unknown (required)
- policies.waiting_list: not asked yet
```

Rules: one row per field; the field id is stable (`section.subject.attribute`) and matches the question list; values that are money are written as "held in the data store", never as amounts in a shared brain.

## `clients/<client>/changes.md`

Append-only, one line per changed field, newest last:

```
- 2026-10-10 10:14 · tours.orchard_walk.capacity_per_slot · (empty) → 15 · chat:t5 · owner Sam · confirmed
- 2026-10-10 10:21 · tours.orchard_walk.capacity_per_slot · 15 → 20 · chat:t7 "actually we take 20 now" · owner Sam · confirmed
- 2026-10-10 10:30 · policies.group_deposit · (empty) → 30% within 48 hours · chat:t9 · consultant Lee · owner to confirm
- 2026-10-10 11:02 · status · draft → in_review · intake · coverage 18/18
```

## The patch the LLM returns per reply

```json
{
  "updates": [
    {"field": "business.known_as", "value": "GVF", "source": "chat:t3",
     "confidence": "high", "confirmed": true, "quote": "people just call us GVF"},
    {"field": "policies.sales_tax_registered", "value": false, "source": "chat:t3",
     "confidence": "high", "confirmed": true, "quote": "we don't charge sales tax"}
  ],
  "open_questions": ["tours.goat_feeding.min_age"],
  "next_question": {"field": "tours.goat_feeding.min_age",
                    "text": "Is there a minimum age for goat feeding?",
                    "why": "required, unknown, unlocked by tour list"}
}
```

The page validates every update against the spec (field exists, type, enum values) before writing. Unknown fields go to the brain's `inbox.md` for the owner to decide whether the question list needs a new item.
