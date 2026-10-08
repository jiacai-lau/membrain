---
name: Proposal claim review
description: >-
  Review one product or marketing proposal against a claims list. Return exactly
  OK, NOT OK or REQUIRE CHANGE, with numbered reasons. Flag committed-but-not-live
  features. One message per proposal.
---
# Proposal claim review

Use this when a proposal (deck, email, landing page copy, RFP response) is about to go out and must match the product's live claims.

## Inputs
- The proposal (file, paste or link the agent can read).
- Claims list at `{{CLAIMS_LIST_PATH}}`. Each claim is one line: what we say, and whether it is **live** or **committed** (promised, not shipped).
- The channel `{{CHANNEL}}` where the one-message review goes.

## Hard rules
1. Read the claims list fresh. Do not work from memory.
2. One verdict per proposal: **OK**, **NOT OK**, or **REQUIRE CHANGE**. Never combine.
3. Number every reason. Each reason cites the claim line and the proposal passage.
4. A feature written as present tense in the proposal but marked **committed** (not live) on the claims list is always a finding. Prefer REQUIRE CHANGE; use NOT OK only when the gap is material.
5. Do not invent claims. If the proposal asserts something absent from the list, flag it as "not on the claims list" under REQUIRE CHANGE.
6. Draft the message. Do not send it. A human posts to `{{CHANNEL}}`.

## Steps
1. Open `{{CLAIMS_LIST_PATH}}`. Build the set of live claims and the set of committed claims.
2. Read the proposal. List every product assertion (bullet, sentence or slide).
3. For each assertion: match to a claim, or mark unmatched.
4. Decide the verdict:
   - **OK** — every assertion matches a live claim; nothing unmatched; no committed-as-live.
   - **REQUIRE CHANGE** — fixable mismatches (wording, committed marked as live, unmatched minor claims).
   - **NOT OK** — material false claim, or several committed features sold as live.
5. Write one message:

```
Verdict: <OK|NOT OK|REQUIRE CHANGE>
Proposal: <title or file>
Claims list: {{CLAIMS_LIST_PATH}} (read <date>)

Reasons:
1. …
2. …

Committed-but-not-live flagged: <n>
Unmatched assertions: <n>
```

6. Hand the draft to the owner. Do not post.
