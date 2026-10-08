# installed/

Catalog items you chose to install: `installed/<type>/<id>/` with the item's `ITEM.md` and files, config filled in.
`scripts/catalog.py install` writes here and records each file's hash under `catalog_installed` in the workspace
`.membrain.yaml`, so a later version can be offered as an update, and your own edits show up as a conflict instead of
being overwritten.

- Browse: `scripts/catalog.py list`, `scripts/catalog.py diff` (MEMBRAIN.md section D).
- A routine or agent here does nothing by itself. Register its prompt in your agent platform (scheduled task or hire).
- Items with status `spec` or `idea` are documents only.
- Brain kinds are not installed here; they start a shared brain: `scripts/spinoff.sh <name> --from catalog:<id>`.
