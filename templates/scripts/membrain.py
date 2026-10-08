#!/usr/bin/env python3
"""Membrain generator. Reads Membrain (a raw base URL or a local folder) and GENERATES files from its
templates. Nobody clones Membrain; this script fetches MANIFEST.yaml and the templates it lists.

  membrain.py setup   --base <url|path> --workspace DIR --owner NAME [--personal-name personal]
                      [--aliases "a,b"] [--account GH_USER] [--date YYYY-MM-DD] [--no-selftest]
  membrain.py spinoff NAME [--owner NAME] [--description ..] [--topics "a,b"] [--keywords "x,y"]
                      [--never "price,grant,..."] [--editors "p,q"] [--org ORG]
                      [--move PATH[:NEWPATH]]... [--accept-warnings] [--base <url|path>]
  membrain.py upgrade [--base <url|path>] [--apply] [--force-local]     (dry-run unless --apply)

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
    return {"membrain_version": d.get("membrain_version", ""), "source": d.get("source", ""),
            "owner": d.get("owner", ""), "generated_at": d.get("generated_at", ""),
            "varsets": varsets, "generated": list(d.get("generated", []))}


# ------------------------------------------------------------------ rendering
def render(text: str, vars_: dict, where: str) -> str:
    out = PLACEHOLDER.sub(lambda m: str(vars_[m.group(1)]) if m.group(1) in vars_ else m.group(0), text)
    left = PLACEHOLDER.findall(out)
    if left:
        sys.exit(f"membrain: unfilled placeholder(s) {sorted(set(left))} in {where}")
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
        target = render(f["target"], vars_, f["target"])
        text = render(fetch(base, f["template"]), vars_, f["template"])
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
    svars = {"BRAIN_NAME": name, "OWNER": owner, "DATE": date, "DESCRIPTION": desc,
             "TOPICS": csv_yaml(o.topics) or desc, "EDITORS": csv_yaml(o.editors)}
    man = manifest(base)
    print(f"Membrain: spinning off shared brain '{name}' from {base}")
    gen = generate(base, man, ws, "shared", svars, f"brain:{name}")
    print(f"  generated brains/{name} ({len(gen)} files from templates/shared-brain)")

    moved, blocked, stubs = [], [], []
    for spec in o.move or []:
        src_rel, _, dst_rel = spec.partition(":")
        dst_rel = dst_rel or src_rel
        src = personal / src_rel
        if not src.is_file():
            sys.exit(f"membrain: --move {src_rel} is not a file in brains/personal")
        cmd = [sys.executable, str(ws / "scripts" / "lint.py"), str(src), "--privacy-only", "--visibility", "shared",
               "--registry", str(reg)] + ([] if o.accept_warnings else ["--strict"])
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

    r = subprocess.run([sys.executable, str(ws / "scripts" / "lint.py"), str(dest), "--registry", str(reg)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout)
        sys.exit(f"membrain: brains/{name} does not lint clean; personal brain untouched, nothing registered")
    git_init(dest, f"membrain: create shared brain {name}")
    print("  git repo initialised (branch main, lint pre-commit hook on)")

    for src_rel, dst_rel in stubs:  # only after the new brain is committed
        (personal / src_rel).write_text(
            f"# Moved\n\n- → {name}:{dst_rel} · moved · {date} · @{owner} · privacy:SHAREABLE_REVIEWED\n\n"
            "The content now lives in the shared brain. Read and write it there; do not copy it back.\n", encoding="utf-8")
    org = o.org or owner
    remote = f"git@github.com:{org}/{name}.git"
    with open(reg, "a", encoding="utf-8") as fh:
        fh.write(f"""  - name: {name}
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
""")
    subprocess.run([sys.executable, str(ws / "scripts" / "route.py"), "write-routes", str(personal / "ROUTES.md"),
                    "--registry", str(reg)], check=True, capture_output=True)
    st["varsets"].append({"id": f"brain:{name}", "vars": svars})
    st["generated"] += gen
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
    proposals, skipped_content = [], []
    for f in man["files"]:
        scope = f.get("scope")
        if scope == "workspace":
            ids = ["workspace"]
        elif scope == "personal":
            ids = ["brain:personal"]
        else:
            ids = [i for i in varsets if i.startswith("brain:") and i != "brain:personal"]
        for vid in ids:
            vars_ = varsets[vid]
            target = render(f["target"], vars_, f["target"])
            if f.get("kind") != "framework":
                if target not in recorded and not (ws / target).exists():
                    skipped_content.append(target)
                continue
            new_text = render(fetch(base, f["template"]), vars_, f["template"])
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
    print("\nProposed framework changes (content files are never touched):")
    if not proposals:
        print("  none: every framework file is current")
    for p in proposals:
        print(f"  {p['action']:<44} {p['path']}")
    if skipped_content:
        print("\nNew content templates exist but are NOT applied (content is yours): " + ", ".join(skipped_content))
    if not o.apply:
        print("\nDry run. Nothing changed. Re-run with --apply to write the UPDATE/ADD items"
              " (CONFLICT items also need --force-local).")
        return
    touched_by_repo: dict[Path, list[str]] = {}
    for p in proposals:
        if p["action"].startswith("CONFLICT") and not o.force_local:
            print(f"  skipped (conflict): {p['path']}")
            continue
        write_file(ws / p["path"], p["text"], p["mode"])
        recorded[p["path"]] = {"path": p["path"], "template": p["f"]["template"], "kind": "framework",
                               "scope": p["scope"], "vars": p["vid"], "sha256": p["sha"]}
        parts = Path(p["path"]).parts
        if len(parts) > 2 and parts[0] == "brains" and (ws / "brains" / parts[1] / ".git").exists():
            touched_by_repo.setdefault(ws / "brains" / parts[1], []).append(str(Path(*parts[2:])))
    st["generated"] = list(recorded.values())
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
    for a in ("--owner", "--description", "--topics", "--keywords", "--editors", "--org", "--base"):
        b.add_argument(a)
    b.add_argument("--never", default="price,grant,quotation,salary,password")
    b.add_argument("--move", action="append")
    b.add_argument("--accept-warnings", action="store_true")
    u = sub.add_parser("upgrade")
    u.add_argument("--base")
    u.add_argument("--apply", action="store_true")
    u.add_argument("--force-local", action="store_true")
    o = ap.parse_args(argv)
    {"setup": cmd_setup, "spinoff": cmd_spinoff, "upgrade": cmd_upgrade}[o.cmd](o)


if __name__ == "__main__":
    main()
