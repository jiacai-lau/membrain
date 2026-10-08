# Client onboarding portal — concept (IDEA)

Status: **idea**. No code.

## Shape
1. **Intake.** A chat (or form) asks the client for the minimum: company name, contacts (stored privately), which systems they migrate from, and which files they will upload.
2. **Upload.** Files land in a fixed folder tree per client, e.g. `customers/`, `items/`, `prices/`, `routes/`. The portal never parses them into a live system by itself.
3. **Draft.** `onboarding-agent` reads the tree, drafts import rows (customers, items, prices) as reviewable files or a pull request.
4. **Approve.** An admin reviews the draft and says yes. Only then does a write tool run, and only for the approved rows.
5. **Log.** Every draft and every approved write is an entry in the onboarding brain or the personal log.

## Non-goals
- No auto-write on upload.
- No prices or personal contact details in a shared brain; those stay in the personal brain or a private store.
