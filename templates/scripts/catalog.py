#!/usr/bin/env python3
"""Membrain catalog: browse and install items (brain kinds, agents/"hires", routines, skills, apps, data sources).

  catalog.py list                     all items from every catalog, with installed versions
  catalog.py diff                     new or updated items vs what this workspace installed
  catalog.py show ID[@catalog]        print an item's ITEM.md
  catalog.py install ID[@catalog] [--set KEY=VALUE]... [--with-deps] [--docs] [--force-local] [--dry-run]
  catalog.py check [DIR] [--also DIR]  validate a catalog folder (INDEX.yaml + <type>/<id>/ITEM.md + files)
  catalog.py new-repo DIR --name NAME --org ORG [--repo ORG/REPO] [--owner HANDLE]   scaffold a private catalog repo

Sources: the public Membrain catalog (<source>/catalog) plus every catalog under `catalogs:` in
brains/personal/brains.yaml (raw URL, github.com URL, gh:owner/repo[@ref] or a local folder).
Installs go to brains/personal/installed/<type>/<id>/ and are recorded in .membrain.yaml (catalog_installed).
Brain kinds are not installed here: spin them off (scripts/spinoff.sh <name> --from catalog:<id>).
Only live and built-untested items install; spec and idea items copy their documents only with --docs.
Never pushes, never schedules anything, never calls a write tool. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import membrain as mb  # noqa: E402

REQUIRED_KEYS = ("id", "type", "version", "status", "summary", "depends_on", "requires_config", "source")
AUTO_VALUES = ("OWNER", "DATE", "ID")
SHARED_VALUES = ("BRAIN_NAME", "OWNER", "DATE", "DESCRIPTION", "TOPICS", "EDITORS", "REPO", "REMOTE", "OBJECTIVES")


def find_ws(arg) -> Path:
    if arg:
        return Path(arg).expanduser().resolve()
    cwd = Path.cwd().resolve()
    for p in [cwd, *cwd.parents]:
        if (p / ".membrain.yaml").exists() and "kind: workspace" in (p / ".membrain.yaml").read_text(encoding="utf-8"):
            return p
    sys.exit("catalog: no Membrain workspace here (run it from the workspace or pass --workspace)")


def context(o):
    ws = find_ws(o.workspace)
    st = mb.load_state(ws)
    if o.base:
        st["source"] = o.base
    return ws, st, mb.catalog_items(ws, st)


def key(item) -> tuple:
    return (item["_src"]["name"], item["id"])


# ------------------------------------------------------------------ list / show / diff
def cmd_list(o):
    ws, st, items = context(o)
    inst = {(c.get("source"), c["id"]): c for c in st.get("catalog_installed") or []}
    if o.json:
        print(json.dumps([{k: i.get(k) for k in REQUIRED_KEYS} | {"catalog": i["_src"]["name"],
                          "installed": (inst.get(key(i)) or {}).get("version")} for i in items], indent=2, ensure_ascii=False))
        return
    print(f"{'ID':<30} {'TYPE':<11} {'VERSION':<8} {'STATUS':<15} {'CATALOG':<14} INSTALLED")
    for i in sorted(items, key=lambda x: (x["_src"]["name"] != "membrain", x["_src"]["name"], x["type"], x["id"])):
        c = inst.get(key(i))
        print(f"{i['id']:<30} {i['type']:<11} {str(i.get('version')):<8} {i.get('status', ''):<15} "
              f"{i['_src']['name']:<14} {c.get('version') if c else '-'}")
    srcs = mb.catalog_sources(ws, st)
    print(f"\n{len(items)} items from {len(srcs)} catalog(s): " + ", ".join(f"{s['name']} ({s['visibility']})" for s in srcs))


def cmd_show(o):
    ws, st, items = context(o)
    try:
        item = mb.find_item(items, o.id)
    except KeyError as e:
        sys.exit(f"catalog: {e}")
    print(mb.item_texts(item)[0][1])


def cmd_diff(o):
    ws, st, items = context(o)
    if o.json:
        d = mb.catalog_diff(ws, st, items)
        print(json.dumps({"new": [f"{i['id']}@{i['_src']['name']}" for i in d["new"]],
                          "updated": [f"{i['id']}@{i['_src']['name']} {c.get('version')}->{i.get('version')}" for c, i in d["updated"]],
                          "edited": [f"{c['id']}:{rel}" for c, rel in d["changed"]]}, indent=2))
        return
    mb.print_catalog_report(ws, st)


# ------------------------------------------------------------------ install
def install(ws, st, items, ref, values_in, o, chain=()):
    try:
        item = mb.find_item(items, ref)
    except KeyError as e:
        sys.exit(f"catalog: {e}")
    name = f"{item['id']}@{item['_src']['name']}"
    if item["id"] in chain:
        sys.exit(f"catalog: dependency loop: {' -> '.join(chain + (item['id'],))}")
    if item["type"] == "brain-kind":
        sys.exit(f"catalog: {name} is a brain kind. Spin it off instead (MEMBRAIN.md section B):\n"
                 f"  scripts/spinoff.sh <name> --from catalog:{name} " + " ".join(f"--set {k}=<value>" for k in item["requires_config"]))
    status = item.get("status")
    docs_only = status not in mb.INSTALLABLE
    if docs_only and not o.docs:
        sys.exit(f"catalog: {name} is status '{status}': nothing to run yet. Read it (catalog.py show {name}) or copy its "
                 "documents into your personal brain with --docs.")
    installed_ids = {c["id"] for c in st.get("catalog_installed") or []}
    for dep in item["depends_on"]:
        if dep in installed_ids:
            continue
        if not o.with_deps:
            sys.exit(f"catalog: {name} depends on '{dep}', which is not installed. Install it first or pass --with-deps.")
        install(ws, st, items, dep, values_in, o, chain + (item["id"],))
        installed_ids = {c["id"] for c in st.get("catalog_installed") or []}
    values = {"OWNER": st.get("owner") or "owner", "DATE": mb.today(), "ID": item["id"], **values_in}
    missing = [k for k in item["requires_config"] if not str(values.get(k, "")).strip()]
    if missing and not docs_only:
        sys.exit(f"catalog: {name} needs --set for: {', '.join(missing)} (meanings in its ITEM.md, 'Config')")
    for k in missing:  # documents of spec/idea items keep a visible marker instead of a value
        values[k] = f"<{k}>"
    dest_rel = f"brains/personal/installed/{item['type']}/{item['id']}"
    prev = next((c for c in st.get("catalog_installed") or [] if (c.get("source"), c["id"]) == key(item)), None)
    if prev and str(prev.get("version")) == str(item.get("version")) and not o.force_local:
        print(f"catalog: {name} {item.get('version')} is already installed at {prev.get('path')}")
        return
    plan, conflicts = [], []
    for rel, text in mb.item_texts(item):
        try:
            out = mb.render(text, values, f"{name}/{rel}")
        except mb.Unfilled as e:
            sys.exit(f"catalog: {e}")
        target = f"{dest_rel}/{rel}"
        cur = ws / target
        if cur.exists():
            cur_sha = mb.sha(cur.read_text(encoding="utf-8"))
            rec = (prev or {}).get("files", {}).get(target)
            if cur_sha != mb.sha(out) and cur_sha != rec:
                conflicts.append(target)
        plan.append((target, out))
    verb = "UPDATE" if prev else "INSTALL"
    print(f"{verb} {name} {item.get('version')} [{status}{', documents only' if docs_only else ''}] -> {dest_rel}/")
    if status == "built-untested":
        print("  note: built but untested; run it once with the owner watching before relying on it")
    for target, _ in plan:
        print(f"  {'CONFLICT (edited locally)' if target in conflicts else 'write':<26} {target}")
    if conflicts and not o.force_local:
        sys.exit("catalog: local edits would be overwritten; show the diff to the person and rerun with --force-local after OK")
    if o.dry_run:
        return
    for target, out in plan:
        mb.write_file(ws / target, out, None)
    st["catalog_installed"] = [c for c in st.get("catalog_installed") or [] if (c.get("source"), c["id"]) != key(item)]
    st["catalog_installed"].append({
        "id": item["id"], "type": item["type"], "version": str(item.get("version", "")), "status": status or "",
        "source": item["_src"]["name"], "path": dest_rel, "installed_at": mb.today(),
        "config": {k: values[k] for k in item["requires_config"]},
        "files": {t: mb.sha(out) for t, out in plan}})
    (ws / ".membrain.yaml").write_text(mb.dump_state(st), encoding="utf-8")
    personal = ws / "brains" / "personal"
    if (personal / ".git").exists():
        rels = [str(Path(t).relative_to("brains/personal")) for t, _ in plan]
        mb.git(personal, "add", "--", *rels, check=False)
        r = mb.git(personal, "commit", "-q", "-m", f"catalog: {verb.lower()} {name} {item.get('version')}", "--", *rels, check=False)
        print("  committed locally in brains/personal" if r.returncode == 0 else
              f"  NOT committed (pre-commit hook?): {(r.stdout + r.stderr).strip()[:300]}")
    steps = re.search(r"^## Install[^\n]*\n(.*?)(?=^## |\Z)", plan[0][1], re.S | re.M)
    print(f"  recorded in .membrain.yaml. Next steps from its ITEM.md ({dest_rel}/ITEM.md):")
    for line in (steps.group(1).strip().splitlines() if steps else ["(none listed)"]):
        print("    " + line)
    if item["type"] in ("routine", "agent") and not docs_only:
        print("  Membrain schedules nothing: register it in your agent platform (scheduled task, automation or hire) "
              "with the prompt file above, pointing at the installed path.")


def cmd_install(o):
    ws, st, items = context(o)
    values = {}
    for kv in o.set or []:
        k, eq, v = kv.partition("=")
        if not eq:
            sys.exit(f"catalog: --set wants KEY=VALUE, got {kv!r}")
        values[k.strip()] = v
    install(ws, st, items, o.id, values, o)
    if o.dry_run:
        print("Dry run. Nothing written.")
    else:
        print("Done. Nothing was pushed.")


# ------------------------------------------------------------------ check (validate a catalog folder)
def check_catalog(root: Path, also=()) -> tuple[list, list]:
    errors, warns = [], []
    idx_p = root / "INDEX.yaml"
    if not idx_p.exists():
        return [f"{root}: no INDEX.yaml"], []
    idx = mb.parse_yaml(idx_p.read_text(encoding="utf-8"))
    for k in ("name", "visibility"):
        if not idx.get(k):
            errors.append(f"INDEX.yaml: missing top-level '{k}'")
    items = [i for i in idx.get("items", []) or [] if isinstance(i, dict)]
    known = {i.get("id") for i in items}
    for a in also:
        ap = Path(a) / "INDEX.yaml"
        if ap.exists():
            known |= {i.get("id") for i in mb.parse_yaml(ap.read_text(encoding="utf-8")).get("items", []) or [] if isinstance(i, dict)}
    seen = set()
    for it in items:
        iid = it.get("id", "?")
        for k in REQUIRED_KEYS:
            if k not in it:
                errors.append(f"{iid}: missing '{k}'")
        if iid in seen:
            errors.append(f"{iid}: duplicate id")
        seen.add(iid)
        if it.get("type") not in mb.CATALOG_TYPES:
            errors.append(f"{iid}: type '{it.get('type')}' not one of {', '.join(mb.CATALOG_TYPES)}")
        if it.get("status") not in mb.CATALOG_STATUSES:
            errors.append(f"{iid}: status '{it.get('status')}' not one of {', '.join(mb.CATALOG_STATUSES)}")
        folder = root / str(it.get("source", ""))
        if not (folder / "ITEM.md").exists():
            errors.append(f"{iid}: {it.get('source')}/ITEM.md missing")
            continue
        listed = it.get("files") or []
        listed = listed if isinstance(listed, list) else [listed]
        on_disk = sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file() and p.name != "ITEM.md"
                         and "__pycache__" not in p.parts)
        for f in listed:
            if not (folder / f).is_file():
                errors.append(f"{iid}: listed file {f} missing")
        for f in on_disk:
            if f not in listed:
                errors.append(f"{iid}: {f} is in the folder but not in INDEX files: (agents fetching by URL would miss it)")
        item_md = (folder / "ITEM.md").read_text(encoding="utf-8")
        m = re.search(r"\*\*Status:\*\*\s*([a-z-]+)\s*·\s*\*\*Version:\*\*\s*([0-9][^\s·]*)", item_md)
        if not m:
            errors.append(f"{iid}: ITEM.md needs a line '**Status:** <status> · **Version:** <version> · **Who it's for:** …'")
        elif (m.group(1), m.group(2)) != (it.get("status"), str(it.get("version"))):
            errors.append(f"{iid}: ITEM.md says {m.group(1)} {m.group(2)}, INDEX says {it.get('status')} {it.get('version')}")
        for sec in ("## Purpose", "## Depends on", "## Install"):
            if sec not in item_md:
                errors.append(f"{iid}: ITEM.md has no '{sec}' section")
        if it.get("status") in ("spec", "idea"):
            code = [f for f in on_disk if f.endswith(mb.CODE_EXT)]
            if code:
                errors.append(f"{iid}: status {it.get('status')} must not ship code ({', '.join(code)})")
        allowed = set(it.get("requires_config") or []) | set(AUTO_VALUES) | (set(SHARED_VALUES) if it.get("type") == "brain-kind" else set())
        for f in ["ITEM.md"] + list(listed):
            if (folder / f).is_file():
                for ph in set(mb.PLACEHOLDER.findall((folder / f).read_text(encoding="utf-8", errors="ignore"))):
                    if ph not in allowed:
                        errors.append(f"{iid}: {f} uses {{{{{ph}}}}}, which is not in requires_config")
        for dep in it.get("depends_on") or []:
            if dep not in known:
                warns.append(f"{iid}: depends on '{dep}', not in this catalog (fine if another registered catalog has it)")
    return errors, warns


def cmd_check(o):
    root = Path(o.dir or ".").expanduser().resolve()
    if (root / "catalog" / "INDEX.yaml").exists() and not (root / "INDEX.yaml").exists():
        root = root / "catalog"
    errors, warns = check_catalog(root, o.also or [])
    for w in warns:
        print(f"  warn: {w}")
    for e in errors:
        print(f"  ERROR: {e}")
    n = len([i for i in mb.parse_yaml((root / 'INDEX.yaml').read_text(encoding='utf-8')).get('items', []) or []]) if (root / "INDEX.yaml").exists() else 0
    print(f"catalog check {root}: {n} items, {len(errors)} error(s), {len(warns)} warning(s)")
    return 1 if errors else 0


# ------------------------------------------------------------------ new-repo (private catalog skeleton)
def cmd_new_repo(o):
    base = o.base
    if not base:
        ws = find_ws(o.workspace)
        base = mb.load_state(ws)["source"]
    base = mb.normalize_base(base)
    dest = Path(o.dir).expanduser().resolve()
    if dest.exists() and any(dest.iterdir()):
        sys.exit(f"catalog: {dest} exists and is not empty")
    repo = o.repo or f"{o.org}/{o.name}"
    values = {"CATALOG_NAME": o.name, "OWNER": o.owner or o.org, "DATE": mb.today(), "REPO": repo,
              "VISIBILITY": o.visibility}
    man = mb.manifest(base)
    dest.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in man["files"]:
        if f.get("scope") != "catalog-repo":
            continue
        try:
            text = mb.render(mb.fetch(base, f["template"]), values, f["template"])
            target = mb.render(f["target"], values, f["target"])
        except mb.Unfilled as e:
            sys.exit(f"catalog: {e}")
        mb.write_file(dest / target, text, f.get("mode"))
        n += 1
    mb.git_init(dest, f"membrain: create catalog {o.name}")
    print(f"""Created catalog repo {dest} ({n} files from templates/catalog-repo; local git repo, lint hook on). Nothing was pushed.
Next (run these yourself):
  1. gh repo create {repo} --{'private' if o.visibility == 'private' else 'public'} --source "{dest}" --remote origin --push
  2. Register it in brains/personal/brains.yaml under catalogs:
       - name: {o.name}
         url: gh:{repo}
         visibility: {o.visibility}""")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Membrain catalog", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--workspace")
    ap.add_argument("--base", help="override the Membrain source (default: source in .membrain.yaml)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("list"); s.add_argument("--json", action="store_true")
    s = sub.add_parser("diff"); s.add_argument("--json", action="store_true")
    s = sub.add_parser("show"); s.add_argument("id")
    s = sub.add_parser("install"); s.add_argument("id")
    s.add_argument("--set", action="append"); s.add_argument("--with-deps", action="store_true")
    s.add_argument("--docs", action="store_true"); s.add_argument("--force-local", action="store_true")
    s.add_argument("--dry-run", action="store_true")
    s = sub.add_parser("check"); s.add_argument("dir", nargs="?"); s.add_argument("--also", action="append")
    s = sub.add_parser("new-repo"); s.add_argument("dir"); s.add_argument("--name", required=True)
    s.add_argument("--org", required=True); s.add_argument("--owner"); s.add_argument("--repo", help="org/repo (default org/name)"); s.add_argument("--visibility", default="private",
                                                                                     choices=["private", "public"])
    o = ap.parse_args(argv)
    return {"list": cmd_list, "diff": cmd_diff, "show": cmd_show, "install": cmd_install, "check": cmd_check,
            "new-repo": cmd_new_repo}[o.cmd](o) or 0


if __name__ == "__main__":
    sys.exit(main())
