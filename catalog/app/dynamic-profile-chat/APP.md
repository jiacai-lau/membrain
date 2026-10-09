---
name: dynamic-profile-chat
title: Dynamic profile chat
purpose: Collect how a business works through an open conversation, updating the client's profile after every reply, so setup can start from an approved, sourced profile.
status: spec
version: 0.1.0
schema_version: 1
owner: "@team-owner"
questions: profile/questions.md
roles:
  - {id: respondent, description: "The business owner, or a consultant, vendor or staff member answering on the owner's behalf", can: [chat, upload, correct_own_answers, view_profile]}
  - {id: research, description: "Pre-fills facts from public sources before the chat", can: [propose_fields]}
  - {id: intake, description: "The agent running the chat", can: [ask, update_profile, append_changes, set_in_review]}
  - {id: approver, description: "A person who reviews and approves the profile", can: [approve, reject_field, reopen]}
  - {id: setup, description: "Builds or configures from an approved profile", can: [read_approved, set_setup_done]}
entities:
  - name: session
    key: id
    fields:
      - {name: id, type: text, required: true}
      - {name: client, type: text, required: true}
      - {name: respondent_role, type: enum, values: [owner, consultant, vendor, staff], required: true}
      - {name: respondent_name, type: text, required: true, private: true}
      - {name: language, type: text}
      - {name: started_at, type: datetime, required: true}
      - {name: last_reply_at, type: datetime}
  - name: profile_field
    key: field
    fields:
      - {name: field, type: text, required: true}
      - {name: value, type: long_text}
      - {name: source, type: text, required: true}
      - {name: confidence, type: enum, values: [high, med, low], required: true}
      - {name: confirmed, type: boolean, required: true}
      - {name: owner_to_confirm, type: boolean}
      - {name: updated_at, type: datetime, required: true}
  - name: change
    key: id
    fields:
      - {name: id, type: text, required: true}
      - {name: at, type: datetime, required: true}
      - {name: field, type: text, required: true}
      - {name: old_value, type: long_text}
      - {name: new_value, type: long_text}
      - {name: source, type: text, required: true}
      - {name: by_role, type: text, required: true}
  - name: upload
    key: id
    fields:
      - {name: id, type: text, required: true}
      - {name: file, type: file, required: true, private: true}
      - {name: kind, type: text}
      - {name: used_for_fields, type: long_text}
screens:
  - {id: start, role: respondent, shows: "language, who is answering (owner or on behalf), name", actions: [begin]}
  - {id: chat, role: respondent, shows: "conversation; text, voice note (transcribed and shown back first), file upload", actions: [reply, upload, go_back_and_correct]}
  - {id: profile-panel, role: respondent, shows: "profile.md in plain language by section; finished sections collapse; open and owner-to-confirm items listed", actions: [edit_field]}
  - {id: review, role: approver, shows: "every field with source, confidence, confirmed flag and change history", actions: [approve, reject_field, reopen]}
flows:
  turn: ["load spec + question list + profile.md", "reply in", "LLM returns patch for every touched field", "validate against spec", "rewrite profile.md, append changes.md", "recompute coverage", "ask the next most useful open item"]
rules:
  - {id: P1, text: "Every reply is read against the whole profile. All fields it touches are updated, not just the current question's."}
  - {id: P2, text: "The question list is a coverage checklist. The next question is chosen from open items: required and unknown first, then low confidence or unconfirmed, then items unlocked by earlier answers."}
  - {id: P3, text: "A field is confirmed only when the respondent stated it or confirmed it. Research and inferred values stay unconfirmed with a confidence level."}
  - {id: P4, text: "Every change appends one line to changes.md with old and new value, source and who said it. Nothing is deleted."}
  - {id: P5, text: "Commercial or policy fields answered by someone other than the owner are marked owner_to_confirm."}
  - {id: P6, text: "Edits made in the profile panel go through the same patch and validation as chat replies."}
  - {id: P7, text: "Invalid or ambiguous values become an open question, never a guess."}
  - {id: P8, text: "Statuses: draft -> in_review -> approved -> setup_done. Only a person sets approved. Nothing goes live before approved."}
  - {id: P9, text: "Answers after setup_done reopen only the touched fields and go through approval again."}
  - {id: P10, text: "Transcripts and uploads stay outside git, with a retention period set by the owner. profile.md and changes.md are committed at the end of each section and when the chat goes quiet."}
notifications:
  - {when: status becomes in_review, to: approver, channel: chat, template: templates/profile-ready.md}
  - {when: status becomes approved, to: setup, channel: chat, template: templates/profile-approved.md}
data_store: {rung: 1, provider: brain-files, pointer: apps/dynamic-profile-chat/DATA-STORE.md}
file_storage: {provider: google-drive, folders: [uploads/, transcripts/]}
mirror_to_brain:
  - "profile.md and changes.md per client folder (they are the record)"
---

# Dynamic profile chat

## What it does
A respondent opens a private link, says who they are and starts talking. The agent already knows what research found and what the question list needs. Each reply, however rambling, is turned into updates for every field it touches; the side panel shows the profile filling in. The respondent can go back and correct anything. When required coverage is complete, an approver reviews and approves, and the setup role builds from the approved profile.

## Storage
Rung 1 here means **files in the brain**: `clients/<client>/profile.md` and `changes.md`, written after each reply and committed per section. With many concurrent sessions, move the working copy to a database (rung 2) and keep committing the approved profile to the brain. The files stay the format of record either way.

## Open questions
- Retention period for transcripts (suggested default: 90 days after `setup_done`).
- Which LLM provider, and whether real client data may be sent to it or an anonymised copy is used for testing.

## Out of scope
Building the client's account itself (that is the setup role, from the approved profile), payments, e-signatures.
