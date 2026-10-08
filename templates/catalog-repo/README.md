# {{CATALOG_NAME}}

A {{VISIBILITY}} [Membrain](https://github.com/jiacai-lau/membrain) catalog: installable items for one organisation (skills, routines, agents, apps, data sources and brain kinds) that don't belong in the public catalog because they name your systems or depend on your data.

**Owner:** @{{OWNER}} · **Repo:** `{{REPO}}` ({{VISIBILITY}}) · **Created:** {{DATE}}

## How people use it

Each person registers this catalog once, in the `brains.yaml` registry of their own Membrain workspace:

```yaml
catalogs:
  - name: membrain
    url: membrain
    visibility: public
  - name: {{CATALOG_NAME}}
    url: gh:{{REPO}}          # read through your GitHub CLI login; a local clone path also works
    visibility: {{VISIBILITY}}
```

Then their agent browses every catalog together: "Follow section D of MEMBRAIN.md: show me new or updated catalog items." Nothing installs until they pick an item.

## Layout

```
INDEX.yaml               every item: id, type, version, status, summary, depends_on, requires_config, source, files
<type>/<id>/ITEM.md      purpose, who it's for, status, depends on, config, install steps for the agent
<type>/<id>/...          the item's files (every one listed under files: in INDEX.yaml)
```

Types: `brain-kind`, `agent`, `routine`, `skill`, `app`, `data-source`. Status: `live`, `built-untested`, `spec` (design only, no code) or `idea`.

## Adding or changing an item

1. Create `<type>/<id>/ITEM.md` (copy one from the public catalog) and the item's files.
2. Add the entry to `INDEX.yaml`; bump `version` on every change so installs show it as UPDATED.
3. Run `python3 scripts/catalog.py check` and `python3 scripts/lint.py`. GitHub runs both on every push.
4. Keep secrets out: config values are filled at install time, never stored here. The lint blocks prices, emails, phone numbers and keys.

Only @{{OWNER}} approves new items, status changes and removals. To retire an item, set `status: idea` or remove it from INDEX.yaml in a commit that says why; installs already made keep working.
