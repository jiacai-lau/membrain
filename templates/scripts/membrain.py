#!/usr/bin/env python3
"""Membrain generator. Reads Membrain (a raw base URL or a local folder) and GENERATES files from its
templates. Nobody clones Membrain; this script fetches MANIFEST.yaml and the templates it lists.

  membrain.py setup   --base <url|path> --workspace DIR --owner NAME [--personal-name personal]
                      [--aliases "a,b"] [--account GH_USER] [--date YYYY-MM-DD] [--no-selftest]
  membrain.py spinoff NAME [--owner NAME] [--description ..] [--topics "a,b"] [--objectives "o1; o2"] [--keywords "x,y"]
                      [--never "price,grant,..."] [--editors "p,q"] [--org ORG]
                      [--move PATH[:NEWPATH]]... [--accept-warnings] [--base <url|path>]
                      [--from catalog:<id>[@<source>]] [--set KEY=VALUE]...
  membrain.py upgrade [--base <url|path>] [--apply] [--force-local]     (dry-run unless --apply; restore point first)
  membrain.py migrate [--base <url|path>] [--brain NAME] [--apply]      (brain structure steps; dry-run unless --apply)
  membrain.py restore [ID] [--apply]                                     (list restore points, or put one back)
  membrain.py status  [--online]                                         (health and what is pending, per brain)
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

STRUCTURE = 2  # brain layout version of this framework; keep equal to STRUCTURE in lint.py (MANIFEST 'structure')
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
    target = int(man.get("structure") or STRUCTURE)
    behind = [(n, brain_structure(d)) for n, d, _ in brain_dirs(ws, st) if brain_structure(d) < target]
    if behind:
        print(f"\nBrain structure (framework {target}): " + ", ".join(f"{n} is at {s}" for n, s in behind)
              + ". After --apply, run 'python3 scripts/membrain.py migrate' (dry run) for the step-by-step changes.")
    if not o.apply:
        print("\nDry run. Nothing changed. Re-run with --apply to write the UPDATE/ADD items"
              " (CONFLICT items also need --force-local). A restore point is made first.")
        return
    writable = [p for p in proposals if not p.get("skip") and (not p["action"].startswith("CONFLICT") or o.force_local)]
    if writable:
        rid = make_restore_point(ws, f"upgrade {st['membrain_version']} to {new_version}",
                                 [p["path"] for p in writable] + [".membrain.yaml"])
        print(f"  restore point: {RESTORE_DIR}/{rid} (put back with: python3 scripts/membrain.py restore {rid})")
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


# ------------------------------------------------------------------ restore points (used by upgrade --apply and migrate --apply)
RESTORE_DIR = ".membrain/restore"


def make_restore_point(ws: Path, label: str, paths) -> str:
    """Copy every listed workspace-relative file that exists into .membrain/restore/<id>/ before it is changed.
    Files that do not exist yet are listed as 'added' (a restore leaves them in place). Returns the id."""
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    rid = f"{stamp}-{re.sub(r'[^a-z0-9.-]+', '-', label.lower()).strip('-')}"
    root = ws / RESTORE_DIR / rid
    n = 1
    while root.exists():
        n += 1
        root = ws / RESTORE_DIR / f"{rid}-{n}"
    rid = root.name
    copied, added = [], []
    for rel in sorted(set(paths)):
        src = ws / rel
        if src.is_file():
            dst = root / "files" / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
            os.chmod(dst, src.stat().st_mode & 0o777)
            copied.append(rel)
        else:
            added.append(rel)
    root.mkdir(parents=True, exist_ok=True)
    (root / "RESTORE.md").write_text(
        f"# Restore point {rid}\n\nMade before: {label}\n\n## Copied (put back by a restore)\n"
        + "".join(f"- {r}\n" for r in copied) + "\n## Added by the change (a restore leaves these; delete them by hand only if the person asks)\n"
        + ("".join(f"- {r}\n" for r in added) or "- (none)\n")
        + f"\nPut it back: `python3 scripts/membrain.py restore {rid}` (dry run), then add `--apply`.\n", encoding="utf-8")
    return rid


def cmd_restore(o):
    ws = Path.cwd().resolve()
    load_state(ws)
    base = ws / RESTORE_DIR
    points = sorted(p.name for p in base.iterdir() if p.is_dir()) if base.is_dir() else []
    if not o.id:
        print("Restore points (newest last):" if points else "No restore points yet.")
        for rid in points:
            head = (base / rid / "RESTORE.md").read_text(encoding="utf-8").splitlines()
            made = next((l[len("Made before: "):] for l in head if l.startswith("Made before: ")), "")
            print(f"  {rid}  {made}")
        return
    root = base / o.id
    if not root.is_dir():
        sys.exit(f"membrain: no restore point {o.id!r} (run 'membrain.py restore' to list them)")
    files = sorted(p for p in (root / "files").rglob("*") if p.is_file()) if (root / "files").is_dir() else []
    print(f"Restore point {o.id}: {len(files)} file(s)")
    for f in files:
        print(f"  {'RESTORE' if o.apply else 'would restore'}  {f.relative_to(root / 'files').as_posix()}")
    if not o.apply:
        print("Dry run. Nothing changed. Re-run with --apply to put these files back (nothing is committed or pushed).")
        return
    for f in files:
        dst = ws / f.relative_to(root / "files")
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(f.read_bytes())
    print("Restored. Brain files are changed but not committed: review with git diff in each brain, then commit.")


# ------------------------------------------------------------------ brain structure and migrations (section C, step 4)
# Every brain records 'structure: N' in its .membrain.yaml (missing = 1). The framework's number is STRUCTURE (also
# 'structure' in MANIFEST.yaml). Steps run one at a time, N -> N+1, each one documented in migrations/ in Membrain.
def brain_dirs(ws: Path, st: dict) -> list:
    """[(name, Path, vars)] for every brain recorded in the workspace state that exists on disk."""
    out = []
    for vs in st["varsets"]:
        if vs["id"].startswith("brain:"):
            name = vs["id"][len("brain:"):]
            d = ws / "brains" / name
            if (d / ".membrain.yaml").exists():
                out.append((name, d, vs["vars"]))
    return out


def brain_structure(d: Path) -> int:
    m = re.search(r"^structure:\s*(\d+)", (d / ".membrain.yaml").read_text(encoding="utf-8"), re.M)
    return int(m.group(1)) if m else 1


def set_structure(text: str, n: int) -> str:
    line = f"structure: {n}                  # brain layout version; scripts/membrain.py migrate moves it up one step at a time"
    if re.search(r"^structure:.*$", text, re.M):
        return re.sub(r"^structure:.*$", line, text, count=1, flags=re.M)
    if re.search(r"^created:.*$", text, re.M):
        return re.sub(r"^(created:.*)$", lambda m: m.group(1) + "\n" + line, text, count=1, flags=re.M)
    return text.rstrip("\n") + "\n" + line + "\n"


def template_section(text: str, start: str, end: str) -> str:
    i = text.index(start)
    j = text.index(end, i)
    return text[i:j]


def _step2(ctx) -> list:
    """1 -> 2: capture as you go, topic notes, housekeeping rules (migrations/002-capture-and-topics.md)."""
    d, vis, vars_ = ctx["dir"], ctx["visibility"], dict(ctx["vars"])
    if not (d / "topics" / "README.md").exists():
        raise RuntimeError("topics/README.md is missing: apply the framework upgrade first (membrain.py upgrade --apply)")
    skel = "personal-brain" if vis == "personal" else "shared-brain"
    changes = []
    claude = d / "CLAUDE.md"
    cur = claude.read_text(encoding="utf-8") if claude.exists() else ""
    if "## Capture as you go" not in cur:
        sec = template_section(fetch(ctx["base"], f"templates/{skel}/CLAUDE.md"), "## Capture as you go", "## Sync and logging")
        marker = "## Sync and logging"
        new = cur.replace(marker, sec + marker, 1) if marker in cur else cur.rstrip("\n") + "\n\n" + sec.rstrip("\n") + "\n"
        changes.append(("CLAUDE.md", new, "add sections 'Capture as you go' and 'Housekeeping' (before 'Sync and logging')"))
    smap = d / "SITEMAP.md"
    cur = smap.read_text(encoding="utf-8") if smap.exists() else ""
    if smap.exists() and "`topics/`" not in cur:
        row = next(l for l in fetch(ctx["base"], f"templates/{skel}/SITEMAP.md").splitlines() if l.startswith("| `topics/`"))
        vars_["DATE"] = ctx["today"]
        changes.append(("SITEMAP.md", cur.rstrip("\n") + "\n" + render(row, vars_, "SITEMAP topics row") + "\n", "add the `topics/` row"))
    return changes


MIGRATIONS = {2: ("capture-and-topics", "capture as you go, topic notes ('log this' / 'continue'), housekeeping rules", _step2)}


def plan_migrations(ws, st, base, target, only=None):
    plans = []
    for name, d, vars_ in brain_dirs(ws, st):
        if only and name != only:
            continue
        have = brain_structure(d)
        vis = "personal" if re.search(r"^visibility:\s*personal", (d / ".membrain.yaml").read_text(encoding="utf-8"), re.M) else "shared"
        steps, blocked = [], None
        for n in range(have + 1, target + 1):
            if n not in MIGRATIONS:
                blocked = f"this engine has no step to structure {n}; run the engine of the newest Membrain (MEMBRAIN.md section C)"
                break
            slug, summary, fn = MIGRATIONS[n]
            try:
                changes = fn({"dir": d, "visibility": vis, "vars": vars_, "base": base, "today": today()})
            except Exception as e:
                blocked = f"step {n} ({slug}): {e}"
                break
            steps.append((n, slug, summary, changes))
        plans.append({"name": name, "dir": d, "have": have, "steps": steps, "blocked": blocked})
    return plans


def cmd_migrate(o):
    ws = Path.cwd().resolve()
    st = load_state(ws)
    base = normalize_base(o.base or st["source"])
    try:
        target = int(manifest(base).get("structure") or STRUCTURE)
    except Exception:
        target = STRUCTURE
    plans = plan_migrations(ws, st, base, target, o.brain)
    print(f"Membrain brain structure: framework {target} ({base})")
    todo = [p for p in plans if p["steps"] or p["blocked"]]
    for p in plans:
        if not p["steps"] and not p["blocked"]:
            print(f"  {p['name']:<16} structure {p['have']}: current")
            continue
        print(f"  {p['name']:<16} structure {p['have']} -> {p['steps'][-1][0] if p['steps'] else p['have']}")
        for n, slug, summary, changes in p["steps"]:
            print(f"    step {n} {slug}: {summary}")
            for rel, _, what in changes:
                print(f"      CHANGE  {rel}: {what}")
            print(f"      CHANGE  .membrain.yaml: structure: {n}")
        if p["blocked"]:
            print(f"    BLOCKED {p['blocked']}")
    if not todo:
        print("Nothing to migrate.")
        return
    if not o.apply:
        print("\nDry run. Nothing changed. Show this to the brain owner; on OK re-run with --apply"
              " (it makes a restore point first, then commits each brain locally; nothing is pushed).")
        return
    for p in plans:
        if not p["steps"]:
            continue
        d, rels = p["dir"], {".membrain.yaml", ".membrain/migrations.log"}
        for _, _, _, changes in p["steps"]:
            rels |= {rel for rel, _, _ in changes}
        if (d / ".git").exists():
            dirty = git(d, "status", "--porcelain", "--", *sorted(rels), check=False).stdout.strip()
            if dirty:
                print(f"  {p['name']}: skipped, uncommitted changes in {', '.join(sorted(rels))}. Commit or stash them, then re-run.")
                continue
        rid = make_restore_point(ws, f"migrate {p['name']} structure {p['have']} to {p['steps'][-1][0]}",
                                 [f"brains/{p['name']}/{r}" for r in rels])
        for n, slug, summary, changes in p["steps"]:
            for rel, text, _ in changes:
                write_file(d / rel, text, None)
            meta = d / ".membrain.yaml"
            meta.write_text(set_structure(meta.read_text(encoding="utf-8"), n), encoding="utf-8")
            logf = d / ".membrain" / "migrations.log"
            logf.parent.mkdir(parents=True, exist_ok=True)
            with open(logf, "a", encoding="utf-8") as fh:
                fh.write(f"{today()} structure {n - 1} -> {n} ({slug}) · restore point {rid}\n")
            print(f"  {p['name']}: step {n} {slug} done")
        if (d / ".git").exists():
            paths = [r for r in sorted(rels) if (d / r).exists()]
            git(d, "add", "--", *paths)
            git(d, "commit", "-q", "--no-verify", "-m", f"membrain: migrate brain structure to {p['steps'][-1][0]}", "--", *paths, check=False)
            print(f"  {p['name']}: committed locally (restore point {rid})")
    print("Applied. Nothing was pushed. Lint each brain, then the sync hooks or scripts/sync.sh push as usual.")


# ------------------------------------------------------------------ status
def cmd_status(o):
    ws = Path.cwd().resolve()
    st = load_state(ws)
    print(f"Membrain workspace {ws}: version {st['membrain_version']}, framework structure {STRUCTURE}")
    if o.online:
        try:
            avail = fetch(normalize_base(st["source"]), "VERSION").strip()
            print(f"  latest available: {avail}" + ("  -> upgrade (MEMBRAIN.md section C)" if vtuple(avail) > vtuple(st["membrain_version"]) else " (current)"))
        except Exception as e:
            print(f"  latest available: not checked ({e})")
    hints = []
    print(f"\n  {'brain':<16} {'structure':<11} {'uncommitted':<12} {'unpushed':<10} {'lint H/M/L':<11} {'topics open':<12} inbox")
    for name, d, _ in brain_dirs(ws, st):
        s = brain_structure(d)
        s_txt = f"{s}" + ("-BEHIND" if s < STRUCTURE else "")
        if s < STRUCTURE:
            hints.append(f"{name}: structure {s} < {STRUCTURE}: run 'python3 scripts/membrain.py migrate' (dry run)")
        dirty = unpushed = "-"
        if (d / ".git").exists():
            dirty = str(len([l for l in git(d, "status", "--porcelain", check=False).stdout.splitlines() if l.strip()]))
            r = git(d, "rev-list", "--count", "@{u}..HEAD", check=False)
            unpushed = r.stdout.strip() if r.returncode == 0 else "no-remote"
        lint_txt = "?"
        lint = d / "scripts" / "lint.py"
        if lint.exists():
            r = subprocess.run([sys.executable, str(lint), str(d), "--format", "json"], capture_output=True, text=True)
            try:
                fs = json.loads(r.stdout or "[]")
                c = {k: sum(f["severity"] == k for f in fs) for k in ("HIGH", "MED", "LOW")}
                lint_txt = f"{c['HIGH']}/{c['MED']}/{c['LOW']}"
                if c["HIGH"]:
                    hints.append(f"{name}: {c['HIGH']} HIGH lint finding(s): python3 brains/{name}/scripts/lint.py")
            except ValueError:
                pass
        topics_open = 0
        for tp in sorted((d / "topics").glob("*.md")) if (d / "topics").is_dir() else []:
            if tp.name.lower() == "readme.md":
                continue
            m = re.search(r"\*\*Status:\*\*\s*([a-z]+)", tp.read_text(encoding="utf-8"))
            if not m or m.group(1) in ("active", "waiting"):
                topics_open += 1
        inbox = d / "inbox.md"
        unfenced = re.sub(r"(?ms)^```.*?^```", "", inbox.read_text(encoding="utf-8")) if inbox.exists() else ""
        waiting = len(re.findall(r"^- \[ \]", unfenced, re.M))
        print(f"  {name:<16} {s_txt:<11} {dirty:<12} {unpushed:<10} {lint_txt:<11} {topics_open:<12} {waiting}")
        state = d / "STATE.md"
        if state.exists():
            nxt = re.search(r"^\*\*Next task:\*\*\s*(.+)$", state.read_text(encoding="utf-8"), re.M)
            if nxt:
                print(f"  {'':<16} next task: {nxt.group(1).strip()[:90]}")
    if hints:
        print("\nPending:")
        for h in hints:
            print("  - " + h)
    else:
        print("\nPending: nothing structural. Open topics: say \"continue\" to pick one up.")


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
    m = sub.add_parser("migrate")
    m.add_argument("--base")
    m.add_argument("--brain", help="only this brain")
    m.add_argument("--apply", action="store_true")
    r = sub.add_parser("restore")
    r.add_argument("id", nargs="?")
    r.add_argument("--apply", action="store_true")
    s2 = sub.add_parser("status")
    s2.add_argument("--online", action="store_true", help="also fetch the latest VERSION from the source")
    o = ap.parse_args(argv)
    {"setup": cmd_setup, "spinoff": cmd_spinoff, "upgrade": cmd_upgrade, "migrate": cmd_migrate,
     "restore": cmd_restore, "status": cmd_status}[o.cmd](o)


if __name__ == "__main__":
    main()
