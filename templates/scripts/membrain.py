#!/usr/bin/env python3
"""Membrain generator. Reads Membrain (a raw base URL or a local folder) and GENERATES files from its
templates. Nobody clones Membrain; this script fetches MANIFEST.yaml and the templates it lists.

  membrain.py setup   --base <url|path> --workspace DIR --owner NAME [--personal-name personal]
                      [--aliases "a,b"] [--account GH_USER] [--date YYYY-MM-DD] [--no-selftest]
  membrain.py spinoff NAME [--owner NAME] [--description ..] [--topics "a,b"] [--objectives "o1; o2"] [--keywords "x,y"]
                      [--never "price,grant,..."] [--editors "p,q"] [--org ORG]
                      [--move PATH[:NEWPATH]]... [--accept-warnings] [--base <url|path>]
                      [--from catalog:<id>[@<source>]] [--set KEY=VALUE]...
  membrain.py upgrade [--base <url|path>] [--apply] [--force-local]     (dry-run unless --apply)
  (catalog browsing and installs: scripts/catalog.py, which uses the catalog functions below)

Rules it keeps: never pushes, never calls GitHub, never makes anything public, never overwrites a
'content' file. Framework files are only replaced by 'upgrade --apply'.
Standard library only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

RAW_GH = re.compile(r"^https?://github\.com/([^/]+)/([^/#?]+?)(?:\.git)?/?$")
PLACEHOLDER = re.compile(r"\{\{([A-Z_]+)\}\}")


# ------------------------------------------------------------------ fetch
def normalize_base(base: str) -> str:
    base = base.strip().rstrip("/")
    m = RAW_GH.match(base)
    if m:  # a github.com repo URL -> its raw base on main
        return f"https://raw.githubusercontent.com/{m.group(1)}/{m.group(2)}/main"
    if base.endswith("/MEMBRAIN.md"):
        base = base[: -len("/MEMBRAIN.md")]
    return base


def fetch(base: str, rel: str) -> str:
    if base.startswith("gh:"):  # private repo through the GitHub CLI's own login: gh:owner/repo[@ref][/sub/dir]
        m = re.match(r"^gh:([^/@]+)/([^/@]+)(?:@([^/]+))?(?:/(.*))?$", base)
        if not m:
            raise ValueError(f"bad gh: source {base!r} (want gh:owner/repo[@ref][/dir])")
        path = "/".join(x for x in (m.group(4), rel) if x)
        r = subprocess.run(["gh", "api", "-H", "Accept: application/vnd.github.raw",
                            f"repos/{m.group(1)}/{m.group(2)}/contents/{path}?ref={m.group(3) or 'main'}"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise FileNotFoundError(f"{base}/{rel}: {r.stderr.strip()[:200]}")
        return r.stdout
    if re.match(r"^https?://", base):
        with urllib.request.urlopen(f"{base}/{rel}", timeout=30) as r:
            return r.read().decode("utf-8")
    return (Path(base).expanduser() / rel).read_text(encoding="utf-8")


# ------------------------------------------------------------------ tiny YAML (same subset as lint.py)
def _scalar(v):
    v = v.strip()
    if not v:
        return ""
    if v[0] == '"' and v[-1:] == '"':
        try:
            return json.loads(v)
        except ValueError:
            return v[1:-1]
    if v[0] == "'" and v[-1:] == "'":
        return v[1:-1]
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        return [_scalar(x) for x in inner.split(",")] if inner else []
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    return v


def _strip_comment(line):
    q = None
    for i, ch in enumerate(line):
        if q:
            if ch == q and line[i - 1] != "\\":
                q = None
        elif ch in "\"'":
            q = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i].rstrip()
    return line.rstrip()


def parse_yaml(text: str) -> dict:
    data, key, item = {}, None, None
    for raw in text.splitlines():
        line = _strip_comment(raw)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        s = line.strip()
        if indent == 0:
            k, _, v = s.partition(":")
            key, item = k.strip(), None
            data[key] = _scalar(v) if v.strip() else []
        elif s.startswith("- "):
            body = s[2:]
            if ":" in body and not body.startswith(("'", '"')):
                k, _, v = body.partition(":")
                item = {k.strip(): _scalar(v)}
                data[key].append(item)
            else:
                data[key].append(_scalar(body))
                item = None
        elif item is not None and ":" in s:
            k, _, v = s.partition(":")
            item[k.strip()] = _scalar(v)
    return data


def q(v) -> str:
    return json.dumps(str(v), ensure_ascii=False)


def dump_state(st: dict) -> str:
    out = ["# Membrain workspace state. Written by scripts/membrain.py. Do not edit by hand.",
           "kind: workspace"]
    for k in ("membrain_version", "source", "owner", "generated_at"):
        out.append(f"{k}: {q(st[k])}")
    out.append("varsets:")
    for vs in st["varsets"]:
        out.append(f"  - id: {q(vs['id'])}")
        for k, v in vs["vars"].items():
            out.append(f"    {k}: {q(v)}")
    out.append("generated:")
    for g in st["generated"]:
        out.append(f"  - path: {q(g['path'])}")
        for k in ("template", "kind", "scope", "vars", "sha256"):
            out.append(f"    {k}: {q(g[k])}")
    if st.get("catalog_installed"):  # written only once something is installed (setup output is unchanged)
        out.append("catalog_installed:")
        for c in st["catalog_installed"]:
            out.append(f"  - id: {q(c['id'])}")
            for k in CATALOG_STATE_KEYS:
                v = c.get(k, "")
                out.append(f"    {k}: {q(json.dumps(v, sort_keys=True) if k in ('config', 'files') else v)}")
    return "\n".join(out) + "\n"


def load_state(ws: Path) -> dict:
    p = ws / ".membrain.yaml"
    if not p.exists():
        sys.exit(f"membrain: {p} not found. Run setup first (or run this from the workspace root).")
    d = parse_yaml(p.read_text(encoding="utf-8"))
    varsets = []
    for vs in d.get("varsets", []):
        vs = dict(vs)
        vid = vs.pop("id")
        varsets.append({"id": vid, "vars": vs})
    installed = []
    for c in d.get("catalog_installed", []) or []:
        if not isinstance(c, dict):
            continue
        c = dict(c)
        for k in ("config", "files"):
            try:
                c[k] = json.loads(c.get(k) or "{}")
            except ValueError:
                c[k] = {}
        installed.append(c)
    return {"membrain_version": d.get("membrain_version", ""), "source": d.get("source", ""),
            "owner": d.get("owner", ""), "generated_at": d.get("generated_at", ""),
            "varsets": varsets, "generated": list(d.get("generated", [])), "catalog_installed": installed}


# ------------------------------------------------------------------ rendering
class Unfilled(Exception):
    pass


def render(text: str, vars_: dict, where: str) -> str:
    out = PLACEHOLDER.sub(lambda m: str(vars_[m.group(1)]) if m.group(1) in vars_ else m.group(0), text)
    left = PLACEHOLDER.findall(out)
    if left:
        raise Unfilled(f"unfilled placeholder(s) {sorted(set(left))} in {where}")
    return out


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def manifest(base: str) -> dict:
    m = parse_yaml(fetch(base, "MANIFEST.yaml"))
    m["files"] = [f for f in m.get("files", []) if isinstance(f, dict)]
    return m


def write_file(path: Path, text: str, mode: str | None):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if mode:
        os.chmod(path, int(str(mode), 8))


def generate(base, man, ws: Path, scope: str, vars_: dict, varset_id: str, overwrite=False):
    """Render every MANIFEST entry of a scope into the workspace. Returns state entries."""
    entries = []
    for f in man["files"]:
        if f.get("scope") != scope:
            continue
        try:
            target = render(f["target"], vars_, f["target"])
            raw = fetch(base, f["template"])
            text = raw if f.get("raw") else render(raw, vars_, f["template"])
        except Unfilled as e:
            sys.exit(f"membrain: {e}")
        dest = ws / target
        if dest.exists() and not overwrite:
            sys.exit(f"membrain: {target} already exists; refusing to overwrite")
        write_file(dest, text, f.get("mode"))
        entries.append({"path": target, "template": f["template"], "kind": f.get("kind", "content"),
                        "scope": scope, "vars": varset_id, "sha256": sha(text)})
    return entries


def git(cwd: Path, *args, check=True, quiet=True):
    name = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True).stdout.strip() or "membrain"
    email = subprocess.run(["git", "config", "user.email"], capture_output=True, text=True).stdout.strip() or "membrain@localhost"
    cmd = ["git", "-c", f"user.name={name}", "-c", f"user.email={email}", "-C", str(cwd), *args]
    return subprocess.run(cmd, check=check, capture_output=quiet, text=True)


def git_init(repo: Path, msg: str):
    r = git(repo, "init", "-q", "-b", "main", check=False)
    if r.returncode != 0:
        git(repo, "init", "-q")
        git(repo, "checkout", "-q", "-b", "main")
    git(repo, "config", "core.hooksPath", ".githooks")
    git(repo, "add", "-A")
    r = git(repo, "commit", "-q", "-m", msg, check=False)
    if r.returncode != 0:
        sys.exit(f"membrain: first commit in {repo} failed (lint hook?):\n{r.stdout}{r.stderr}")


def csv_yaml(s: str) -> str:
    return ", ".join(x.strip() for x in (s or "").split(",") if x.strip())


def today(arg=None) -> str:
    return arg or os.environ.get("MB_TODAY") or dt.date.today().isoformat()


# ------------------------------------------------------------------ catalog (MEMBRAIN.md section D; CLI: scripts/catalog.py)
# A catalog source is a folder holding INDEX.yaml and one folder per item (<type>/<id>/ITEM.md + files). The public one
# is <BASE>/catalog. Private ones (org-specific) are listed under catalogs: in brains/personal/brains.yaml with a url that
# is a raw base, a github.com URL, gh:owner/repo[@ref] (uses the GitHub CLI's login) or a local folder.
CATALOG_TYPES = ("brain-kind", "agent", "routine", "skill", "app", "data-source")
CATALOG_STATUSES = ("live", "built-untested", "spec", "idea")
INSTALLABLE = ("live", "built-untested")
CATALOG_STATE_KEYS = ("type", "version", "status", "source", "path", "installed_at", "config", "files")
CODE_EXT = (".py", ".js", ".mjs", ".ts", ".sh", ".go", ".rb")


def catalog_sources(ws: Path, st: dict) -> list:
    """[{name, url, visibility}] from brains.yaml catalogs:, default the public Membrain catalog. url 'membrain' = <source>/catalog."""
    public = {"name": "membrain", "url": normalize_base(st["source"]) + "/catalog", "visibility": "public"}
    reg = ws / "brains" / "personal" / "brains.yaml"
    listed = parse_yaml(reg.read_text(encoding="utf-8")).get("catalogs") if reg.exists() else None
    if not listed:
        return [public]
    out = []
    for c in listed:
        if not isinstance(c, dict) or not c.get("name") or not c.get("url"):
            continue
        url = str(c["url"])
        if url == "membrain":
            url = public["url"]
        elif not re.match(r"^(https?://|gh:)", url):
            url = str((ws / Path(url).expanduser()).resolve()) if not Path(url).expanduser().is_absolute() else str(Path(url).expanduser())
        else:
            url = normalize_base(url)
        out.append({"name": str(c["name"]), "url": url, "visibility": str(c.get("visibility") or "private")})
    return out


def load_index(src: dict) -> list:
    idx = parse_yaml(fetch(src["url"], "INDEX.yaml"))
    items = []
    for it in idx.get("items", []) or []:
        if isinstance(it, dict) and it.get("id"):
            it = dict(it)
            for k in ("depends_on", "requires_config", "files"):
                v = it.get(k, [])
                it[k] = v if isinstance(v, list) else ([v] if v else [])
            it["_src"] = src
            items.append(it)
    return items


def catalog_items(ws: Path, st: dict, warn=True) -> list:
    items = []
    for src in catalog_sources(ws, st):
        try:
            items += load_index(src)
        except Exception as e:  # an unreachable private catalog must not stop browsing the others
            if warn:
                print(f"  note: catalog '{src['name']}' not readable ({src['url']}): {e}", file=sys.stderr)
    return items


def find_item(items: list, ref: str) -> dict:
    """ref = id or id@source."""
    iid, _, srcname = ref.partition("@")
    hits = [i for i in items if i["id"] == iid and (not srcname or i["_src"]["name"] == srcname)]
    if not hits:
        raise KeyError(f"catalog item '{ref}' not found in: {', '.join(sorted({i['_src']['name'] for i in items})) or 'no readable catalog'}")
    if len(hits) > 1:
        raise KeyError(f"catalog item '{iid}' is in several catalogs ({', '.join(h['_src']['name'] for h in hits)}); use {iid}@<catalog>")
    return hits[0]


def item_texts(item: dict) -> list:
    """[(rel, text)] for every file of the item (ITEM.md first), fetched from its catalog."""
    folder = str(item.get("source") or f"{item['type']}/{item['id']}").strip("/")
    names = ["ITEM.md"] + [f for f in item["files"] if f != "ITEM.md"]
    return [(rel, fetch(item["_src"]["url"], f"{folder}/{rel}")) for rel in names]


def render_item(text: str, values: dict, where: str) -> str:
    return render(text, values, where)


def vless(a, b) -> bool:
    return vtuple(a) < vtuple(b)


def catalog_diff(ws: Path, st: dict, items: list) -> dict:
    """new = in a catalog, never installed; updated = newer version than installed; changed = installed files edited locally."""
    inst = st.get("catalog_installed") or []
    installed_keys = {(c.get("source"), c["id"]) for c in inst}
    new = [i for i in items if (i["_src"]["name"], i["id"]) not in installed_keys]
    by_key = {(i["_src"]["name"], i["id"]): i for i in items}
    updated, changed = [], []
    for c in inst:
        it = by_key.get((c.get("source"), c["id"]))
        if it and vless(c.get("version", "0"), it.get("version", "0")):
            updated.append((c, it))
        for rel, h in (c.get("files") or {}).items():
            p = ws / rel
            if not p.exists() or sha(p.read_text(encoding="utf-8")) != h:
                changed.append((c, rel))
    return {"new": new, "updated": updated, "changed": changed}


def print_catalog_report(ws: Path, st: dict, header="Catalog"):
    items = catalog_items(ws, st)
    if not items:
        print(f"\n{header}: no readable catalog")
        return
    d = catalog_diff(ws, st, items)
    srcs = sorted({i["_src"]["name"] for i in items})
    print(f"\n{header} ({len(items)} items in {', '.join(srcs)}):")
    if not d["new"] and not d["updated"] and not d["changed"]:
        print("  nothing new or updated")
    for i in d["new"]:
        ref = f"{i['id']}@{i['_src']['name']}"
        print(f"  NEW      {ref:<36} {i['type']:<11} {str(i.get('version', '')):<7} {i.get('status', ''):<15} {i.get('summary', '')[:60]}")
    for c, i in d["updated"]:
        print(f"  UPDATED  {i['id']}@{i['_src']['name']}  {c.get('version')} -> {i.get('version')} ({i.get('status')})")
    for c, rel in d["changed"]:
        print(f"  EDITED   {c['id']}: {rel} (changed locally; an update would be a CONFLICT)")
    print("  Install only what the person picks: scripts/catalog.py install <id>[@catalog] (MEMBRAIN.md section D).")


def overlay_brain_kind(item: dict, ws: Path, dest: Path, values: dict, gen: list, varset_id: str) -> dict:
    """Apply a brain-kind's files onto a freshly generated shared brain (dest = ws/brains/<name>).
    CLAUDE.md.overlay goes in before '## How to use', SITEMAP.rows is appended to the SITEMAP table, lint.yaml becomes
    .membrain/lint.yaml, every other file is written at its path. Updates gen in place; returns {ws-relative path: sha}."""
    tag = f"catalog:{item['_src']['name']}/{item['id']}"
    by_path = {g["path"]: g for g in gen}
    written = {}
    for rel, text in item_texts(item):
        if rel == "ITEM.md":
            continue
        out = render(text, values, f"{tag}/{rel}")
        if rel == "CLAUDE.md.overlay":
            target = dest / "CLAUDE.md"
            cur = target.read_text(encoding="utf-8")
            marker = "\n## How to use\n"
            new = cur.replace(marker, "\n" + out.rstrip() + "\n" + marker, 1) if marker in cur else cur.rstrip() + "\n\n" + out
        elif rel == "SITEMAP.rows":
            target = dest / "SITEMAP.md"
            new = target.read_text(encoding="utf-8").rstrip("\n") + "\n" + out.rstrip("\n") + "\n"
        elif rel == "lint.yaml":
            target, new = dest / ".membrain" / "lint.yaml", out
        else:
            target, new = dest / rel, out
        write_file(target, new, None)
        key = target.relative_to(ws).as_posix()
        written[key] = sha(new)
        if key in by_path:
            by_path[key]["sha256"] = written[key]
            if tag not in by_path[key]["template"]:
                by_path[key]["template"] += f" + {tag}"
        else:
            g = {"path": key, "template": f"{tag}/{rel}", "kind": "content", "scope": "shared",
                 "vars": varset_id, "sha256": written[key]}
            gen.append(g)
            by_path[key] = g
    return written


# ------------------------------------------------------------------ setup (MEMBRAIN.md section A)
def cmd_setup(o):
    base = normalize_base(o.base)
    ws = Path(o.workspace).expanduser().resolve()
    if (ws / ".membrain.yaml").exists():
        sys.exit(f"membrain: {ws} is already a Membrain workspace. Use 'upgrade'.")
    version = fetch(base, "VERSION").strip()
    man = manifest(base)
    date = today(o.date)
    account = o.account or o.owner
    wvars = {"OWNER": o.owner, "DATE": date, "MEMBRAIN_VERSION": version, "SOURCE_URL": base}
    pvars = {"BRAIN_NAME": o.personal_name, "OWNER": o.owner, "DATE": date,
             "REMOTE": f"git@github.com:{account}/membrain-{o.personal_name}.git", "ALIASES": csv_yaml(o.aliases)}
    print(f"Membrain {version}: generating workspace at {ws} from {base}")
    ws.mkdir(parents=True, exist_ok=True)
    gen = generate(base, man, ws, "workspace", wvars, "workspace")
    gen += generate(base, man, ws, "personal", pvars, "brain:personal")
    personal = ws / "brains" / "personal"
    subprocess.run([sys.executable, str(ws / "scripts" / "route.py"), "write-routes", str(personal / "ROUTES.md"),
                    "--registry", str(personal / "brains.yaml")], check=True, capture_output=True)
    print(f"  wrote {len(gen)} files ({sum(g['kind'] == 'framework' for g in gen)} framework, "
          f"{sum(g['kind'] == 'content' for g in gen)} content)")
    if not o.no_selftest:
        r = subprocess.run(["bash", str(ws / "tests" / "run.sh"), base], capture_output=True, text=True)
        tail = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
        if r.returncode != 0:
            print(r.stdout + r.stderr)
            sys.exit("membrain: self-test failed; workspace left for inspection, no git repo created")
        print(f"  self-test: {tail}")
    state = {"membrain_version": version, "source": base, "owner": o.owner, "generated_at": date,
             "varsets": [{"id": "workspace", "vars": wvars}, {"id": "brain:personal", "vars": pvars}],
             "generated": gen}
    (ws / ".membrain.yaml").write_text(dump_state(state), encoding="utf-8")
    git_init(personal, f"membrain: create personal brain ({o.personal_name})")
    print("  personal brain: local private git repo at brains/personal (branch main, lint hook on)")
    print(f"""
Done. Nothing was pushed. When you are ready, create the PRIVATE remote yourself:
  gh repo create {account}/membrain-{o.personal_name} --private --source "{personal}" --remote origin --push
Never --public. Then tell your agent: "Read AGENTS.md in {ws} and follow it." """)


# ------------------------------------------------------------------ spinoff (section B)
def cmd_spinoff(o):
    ws = Path.cwd().resolve()
    st = load_state(ws)
    base = normalize_base(o.base or st["source"])
    name = o.name
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,40}", name) or name in ("personal",):
        sys.exit("membrain: brain name must be lowercase letters, digits, dashes and not 'personal'")
    personal = ws / "brains" / "personal"
    reg = personal / "brains.yaml"
    dest = ws / "brains" / name
    if dest.exists():
        sys.exit(f"membrain: {dest} already exists")
    if re.search(rf"^\s*-\s*name:\s*\"?{re.escape(name)}\"?\s*$", reg.read_text(encoding="utf-8"), re.M):
        sys.exit(f"membrain: '{name}' is already registered")
    owner = o.owner or st["owner"]
    date = today()
    desc = (o.description or f"Shared brain: {name}").replace('"', "'")
    org = o.org or owner
    topics = csv_yaml(o.topics) or desc
    objectives = [x.strip() for x in (o.objectives or "").split(";") if x.strip()] or [
        f"Anyone on the team finds the current answer about {topics} in one file here, with a date and an owner.",
        "A fix or answer learned once is written once, so nobody has to work it out twice.",
        "Nothing private (amounts, credentials, people's details, anyone's own notes) ever lands here."]
    svars = {"BRAIN_NAME": name, "OWNER": owner, "DATE": date, "DESCRIPTION": desc, "TOPICS": topics,
             "EDITORS": csv_yaml(o.editors) or f"@{owner}", "REPO": f"{org}/{name}",
             "REMOTE": f"git@github.com:{org}/{name}.git",
             "OBJECTIVES": "\n".join(f"{i}. {x}" for i, x in enumerate(objectives, 1))}
    kind, kvalues = None, {}
    if o.from_:
        if not o.from_.startswith("catalog:"):
            sys.exit("membrain: --from takes catalog:<id>[@<catalog>], e.g. --from catalog:cs-brain")
        try:
            kind = find_item(catalog_items(ws, st), o.from_[len("catalog:"):])
        except KeyError as e:
            sys.exit(f"membrain: {e}")
        if kind["type"] != "brain-kind":
            sys.exit(f"membrain: {kind['id']} is a {kind['type']}, not a brain-kind; install it with scripts/catalog.py")
        if kind.get("status") not in INSTALLABLE:
            sys.exit(f"membrain: {kind['id']} is status '{kind.get('status')}' (only live or built-untested brain kinds can be spun off). "
                     "Read its ITEM.md: scripts/catalog.py show " + kind["id"])
        kvalues = dict(svars)
        for kv in o.set or []:
            k, eq, v = kv.partition("=")
            if not eq:
                sys.exit(f"membrain: --set wants KEY=VALUE, got {kv!r}")
            kvalues[k.strip()] = v
        missing = [k for k in kind["requires_config"] if k not in kvalues]
        if missing:
            sys.exit(f"membrain: {kind['id']} needs --set for: {', '.join(missing)} (see its ITEM.md)")
    man = manifest(base)
    print(f"Membrain: spinning off shared brain '{name}' from {base}")
    gen = generate(base, man, ws, "shared", svars, f"brain:{name}")
    print(f"  generated brains/{name} ({len(gen)} files from templates/shared-brain)")
    kind_record = None
    if kind:
        try:
            written = overlay_brain_kind(kind, ws, dest, kvalues, gen, f"brain:{name}")
        except Unfilled as e:
            sys.exit(f"membrain: {e}")
        print(f"  applied brain kind {kind['id']} {kind.get('version')} from catalog '{kind['_src']['name']}' ({len(written)} files)")
        kind_record = {"id": kind["id"], "type": "brain-kind", "version": str(kind.get("version", "")),
                       "status": kind.get("status", ""), "source": kind["_src"]["name"], "path": f"brains/{name}",
                       "installed_at": date, "config": {k: kvalues[k] for k in kind["requires_config"]}, "files": written}

    moved, blocked, stubs = [], [], []
    for spec in o.move or []:
        src_rel, _, dst_rel = spec.partition(":")
        dst_rel = dst_rel or src_rel
        src = personal / src_rel
        if not src.is_file():
            sys.exit(f"membrain: --move {src_rel} is not a file in brains/personal")
        cmd = [sys.executable, str(ws / "scripts" / "lint.py"), str(src), "--privacy-only", "--visibility", "shared",
               "--registry", str(reg), "--strict", "--fail-on", "high" if o.accept_warnings else "low"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            (dest / dst_rel).parent.mkdir(parents=True, exist_ok=True)
            (dest / dst_rel).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            with open(dest / "SITEMAP.md", "a", encoding="utf-8") as fh:
                fh.write(f"| `{dst_rel}` | moved from the owner's notes; describe what it owns | @{owner} | append one line | {date} | {date} |\n")
            stubs.append((src_rel, dst_rel))
            moved.append(f"{src_rel} -> {name}:{dst_rel}")
        else:
            blocked.append(src_rel)
            print(f"  BLOCKED (PRIVACY_REVIEW_NEEDED): {src_rel} stays in personal. Findings:")
            for line in r.stdout.splitlines():
                if re.search(r" [EW]\d{3} ", line):
                    print("    " + line.strip())

    r = subprocess.run([sys.executable, str(ws / "scripts" / "lint.py"), str(dest), "--registry", str(reg),
                        "--strict", "--fail-on", "med"], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout)
        sys.exit(f"membrain: brains/{name} does not lint clean; personal brain untouched, nothing registered")
    git_init(dest, f"membrain: create shared brain {name}")
    print("  git repo initialised (branch main, lint pre-commit hook on)")

    for src_rel, dst_rel in stubs:  # only after the new brain is committed
        (personal / src_rel).write_text(
            f"# Moved\n\n- → {name}:{dst_rel} · moved · {date} · @{owner} · privacy:SHAREABLE_REVIEWED\n\n"
            "The content now lives in the shared brain. Read and write it there; do not copy it back.\n", encoding="utf-8")
    remote = svars["REMOTE"]
    entry = f"""  - name: {name}
    path: brains/{name}
    visibility: shared
    remote: {remote}
    owner: {owner}
    editors: [{csv_yaml(o.editors)}]
    description: "{desc}"
    topics: [{csv_yaml(o.topics)}]
    keywords: [{csv_yaml(o.keywords)}]
    never: [{csv_yaml(o.never)}]
    default_file: inbox.md
    created: {date}
"""
    text = reg.read_text(encoding="utf-8")
    brains_at = re.search(r"^brains:", text, re.M)
    after = [m for m in re.finditer(r"^[A-Za-z_]+:", text, re.M) if brains_at and m.start() > brains_at.start()]
    if after:  # another top-level block (e.g. catalogs:) follows the brains list: insert the entry before it
        text = text[:after[0].start()] + entry + text[after[0].start():]
    else:
        text = text.rstrip("\n") + "\n" + entry
    reg.write_text(text, encoding="utf-8")
    subprocess.run([sys.executable, str(ws / "scripts" / "route.py"), "write-routes", str(personal / "ROUTES.md"),
                    "--registry", str(reg)], check=True, capture_output=True)
    st["varsets"].append({"id": f"brain:{name}", "vars": svars})
    st["generated"] += gen
    if kind_record:
        st.setdefault("catalog_installed", []).append(kind_record)
    (ws / ".membrain.yaml").write_text(dump_state(st), encoding="utf-8")
    print("  route registered in brains/personal/brains.yaml; ROUTES.md refreshed; .membrain.yaml updated")
    print(f"""
Done. moved: {', '.join(moved) or '(none)'} | blocked: {', '.join(blocked) or '(none)'}
Next (run these yourself; nothing was pushed):
  1. gh repo create {org}/{name} --private --source "{dest}" --remote origin --push
  2. git -C "{personal}" add -A && git -C "{personal}" commit -m "route: spin off {name}"
  3. Teammates: git clone {remote}   then "Read CLAUDE.md in this folder and follow it." """)
    if blocked:
        sys.exit(3)


# ------------------------------------------------------------------ upgrade (section C)
def vtuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", str(v))[:3]) or (0,)


def cmd_upgrade(o):
    ws = Path.cwd().resolve()
    st = load_state(ws)
    base = normalize_base(o.base or st["source"])
    new_version = fetch(base, "VERSION").strip()
    man = manifest(base)
    try:
        changelog = fetch(base, "CHANGELOG.md")
    except Exception:
        changelog = ""
    varsets = {vs["id"]: vs["vars"] for vs in st["varsets"]}
    recorded = {g["path"]: g for g in st["generated"]}
    print(f"Membrain upgrade check: local {st['membrain_version']} -> available {new_version} ({base})")
    if changelog and vtuple(new_version) > vtuple(st["membrain_version"]):
        print("\nCHANGELOG (newer than local):")
        keep = False
        for line in changelog.splitlines():
            m = re.match(r"^##\s*\[?(\d+\.\d+\.\d+)", line)
            if m:
                keep = vtuple(m.group(1)) > vtuple(st["membrain_version"])
            if keep:
                print("  " + line)
    proposals, skipped_content, produced = [], [], set()
    for f in man["files"]:
        scope = f.get("scope")
        if scope == "workspace":
            ids = ["workspace"]
        elif scope == "personal":
            ids = ["brain:personal"]
        elif scope == "catalog-repo":  # generated into a separate catalog repo by catalog.py new-repo, not the workspace
            continue
        else:
            ids = [i for i in varsets if i.startswith("brain:") and i != "brain:personal"]
        for vid in ids:
            vars_ = varsets[vid]
            try:
                target = render(f["target"], vars_, f["target"])
            except Unfilled as e:
                print(f"  note: skipped {f['target']} ({e})")
                continue
            produced.add(target)
            if f.get("kind") != "framework":
                if target not in recorded and not (ws / target).exists():
                    skipped_content.append(target)
                continue
            try:
                raw = fetch(base, f["template"])
                new_text = raw if f.get("raw") else render(raw, vars_, f["template"])
            except Unfilled as e:
                proposals.append({"path": target, "action": f"SKIP (needs a new value: {e})", "skip": True})
                continue
            new_sha = sha(new_text)
            rec = recorded.get(target)
            cur = ws / target
            cur_sha = sha(cur.read_text(encoding="utf-8")) if cur.exists() else None
            if rec and rec["sha256"] == new_sha and cur_sha == new_sha:
                continue
            if cur_sha == new_sha:
                action = "RECORD (file already matches)"
            elif cur_sha is None:
                action = "ADD"
            elif rec and cur_sha != rec["sha256"]:
                action = "CONFLICT (you changed this file locally)"
            else:
                action = "UPDATE"
            proposals.append({"path": target, "action": action, "text": new_text, "sha": new_sha, "f": f, "vid": vid,
                              "scope": scope, "mode": f.get("mode")})
    retired = [g["path"] for g in st["generated"] if g.get("kind") == "framework" and g["path"] not in produced]
    print("\nProposed framework changes (content files are never touched):")
    if not proposals and not retired:
        print("  none: every framework file is current")
    for p in proposals:
        print(f"  {p['action']:<44} {p['path']}")
    for r_ in retired:
        print(f"  {'RETIRED (no longer generated; left in place)':<44} {r_}")
    if skipped_content:
        print("\nNew content templates exist but are NOT applied (content is yours; your agent may propose them): "
              + ", ".join(skipped_content))
    try:  # catalog items are never installed by an upgrade; report them so the person can pick (section D)
        print_catalog_report(ws, {**st, "source": base}, "Catalog (installs are separate; nothing here is applied)")
    except Exception as e:
        print(f"\nCatalog: not checked ({e})")
    if not o.apply:
        print("\nDry run. Nothing changed. Re-run with --apply to write the UPDATE/ADD items"
              " (CONFLICT items also need --force-local).")
        return
    touched_by_repo: dict[Path, list[str]] = {}
    for p in proposals:
        if p.get("skip"):
            continue
        if p["action"].startswith("CONFLICT") and not o.force_local:
            print(f"  skipped (conflict): {p['path']}")
            continue
        write_file(ws / p["path"], p["text"], p["mode"])
        recorded[p["path"]] = {"path": p["path"], "template": p["f"]["template"], "kind": "framework",
                               "scope": p["scope"], "vars": p["vid"], "sha256": p["sha"]}
        parts = Path(p["path"]).parts
        if len(parts) > 2 and parts[0] == "brains" and (ws / "brains" / parts[1] / ".git").exists():
            touched_by_repo.setdefault(ws / "brains" / parts[1], []).append(str(Path(*parts[2:])))
    st["generated"] = [g for g in recorded.values() if g["path"] not in retired]
    st["membrain_version"] = new_version
    (ws / ".membrain.yaml").write_text(dump_state(st), encoding="utf-8")
    for repo, paths in touched_by_repo.items():
        git(repo, "add", "--", *paths)
        git(repo, "commit", "-q", "--no-verify", "-m", f"membrain: upgrade framework to {new_version}", "--", *paths)
        print(f"  committed locally in {repo.name}: {len(paths)} file(s)")
    print(f"Applied. Workspace now at {new_version}. Nothing was pushed.")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Membrain generator", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("setup")
    s.add_argument("--base", required=True)
    s.add_argument("--workspace", required=True)
    s.add_argument("--owner", required=True)
    s.add_argument("--personal-name", default="personal")
    s.add_argument("--aliases", default="")
    s.add_argument("--account")
    s.add_argument("--date")
    s.add_argument("--no-selftest", action="store_true")
    b = sub.add_parser("spinoff")
    b.add_argument("name")
    for a in ("--owner", "--description", "--topics", "--objectives", "--keywords", "--editors", "--org", "--base"):
        b.add_argument(a)
    b.add_argument("--never", default="price,grant,quotation,salary,password")
    b.add_argument("--move", action="append")
    b.add_argument("--from", dest="from_", help="start from a catalog brain kind: catalog:<id>[@<catalog>]")
    b.add_argument("--set", action="append", help="KEY=VALUE config for the brain kind")
    b.add_argument("--accept-warnings", action="store_true")
    u = sub.add_parser("upgrade")
    u.add_argument("--base")
    u.add_argument("--apply", action="store_true")
    u.add_argument("--force-local", action="store_true")
    o = ap.parse_args(argv)
    {"setup": cmd_setup, "spinoff": cmd_spinoff, "upgrade": cmd_upgrade}[o.cmd](o)


if __name__ == "__main__":
    main()
