---
name: <lowercase-dashes, same as the folder>
title: <human name>
purpose: <one or two sentences: what problem it solves, for whom>
status: idea             # idea | spec | built-untested | live
version: 0.1.0           # bump on every change to this file
schema_version: 1        # bump when entities or fields change; the store is migrated to match
owner: "@<handle of the person who approves changes>"
questions: <path to the question list used to fill this spec, e.g. profile/questions.md>
roles:
  - {id: <role>, description: "<who they are>", can: [<action>, <action>]}
entities:
  - name: <entity>
    key: id
    fields:
      - {name: id, type: text, required: true}
      - {name: <field>, type: <text|long_text|integer|number|money|percent|date|time|datetime|boolean|enum|ref|file|email|phone>, required: <true|false>}
      # enum: add values: [a, b]   ref: add ref: <entity>   personal data: add private: true
screens:
  - {id: <screen>, role: <role>, shows: "<what is on it>", actions: [<action>]}
flows:
  <flow>: [<screen>, <step>, <screen>]
rules:
  - {id: R1, text: "<one business rule in plain words>"}
notifications:
  - {when: <event>, to: <role>, channel: <email|chat|sms>, template: <path in this brain>}
data_store: {rung: <1|2|3>, provider: <e.g. google-sheets, supabase, self-hosted-postgres>, pointer: apps/<name>/DATA-STORE.md}
file_storage: {provider: <e.g. google-drive>, folders: [<folder>/]}
mirror_to_brain:
  - "<what may be copied back into this brain, and where (no personal data, no amounts)>"
---

# <title>

## What it does
<Two to five sentences a new teammate would understand: who uses it, what they do with it, what changes for the business.>

## Rules explained
<One short paragraph or bullet per rule id above, with the reason behind it.>

## Open questions
<Everything not yet known or not yet confirmed by the owner. The profile chat or the owner closes these.>

## Out of scope
<What this app deliberately does not do.>
