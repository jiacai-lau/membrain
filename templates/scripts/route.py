#!/usr/bin/env python3
"""Membrain router: which brain should I read from / write to?

  route.py classify "text of the note or question"   -> target brain for a WRITE + read order
  route.py table                                       -> markdown routing table from brains.yaml
  route.py write-routes path/to/ROUTES.md              -> refresh the generated block in ROUTES.md
  route.py paths                                       -> name<TAB>path<TAB>visibility<TAB>remote (for scripts)

Options: --registry brains/personal/brains.yaml (auto-found from the current folder), --json

Order of decisions for a write (see DESIGN.md "Routing"):
  1. Privacy first. Anything that trips the privacy classifier goes to the personal brain.
  2. Topic match against each shared brain's topics/keywords; 'never' words disqualify a brain.
  3. One clear winner -> that brain. A tie or no match -> personal inbox.md, ask the owner.
The script only advises. The agent still rereads the target CLAUDE.md, checks for duplicates,
appends one line, and reads it back.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lint  # noqa: E402

BEGIN, END = "<!-- membrain:routes:begin -->", "<!-- membrain:routes:end -->"


def load_registry(arg):
    reg_path = Path(arg) if arg else lint.find_registry(Path.cwd())
    if not reg_path or not reg_path.exists():
        sys.exit("route: no registry found. Pass --registry or run from the workspace (brains/personal/brains.yaml).")
    reg = lint.load_yaml(reg_path)
    brains = [b for b in reg.get("brains", []) if isinstance(b, dict)]
    return reg_path, reg, brains


def as_list(v):
    if v is None or v == "":
        return []
    return v if isinstance(v, list) else [v]


def privacy_hits(text, brains):
    hits = []
    for code, name, pat in lint.PRIVACY_PATTERNS:
        m = pat.search(text)
        if m:
            hits.append(f"{code} {name}: {m.group(0).strip()}")
    m = lint.KEYWORD_RE.search(text)
    if m:
        hits.append(f"W106 private-keyword: {m.group(0).strip()}")
    return hits


def term_hit(term, text):
    term = str(term).lower().strip()
    if not term:
        return False
    if term.endswith("-"):
        return term in text
    return re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text) is not None


def score(brain, text):
    t = text.lower()
    s, why = 0, []
    for topic in as_list(brain.get("topics")):
        if term_hit(topic, t):
            s += 2
            why.append(f"topic '{topic}'")
    for kw in as_list(brain.get("keywords")):
        if term_hit(kw, t):
            s += 1
            why.append(f"keyword '{kw}'")
    blocked = [w for w in as_list(brain.get("never")) if term_hit(w, t)]
    return s, why, blocked


def classify(text, brains):
    personal = next((b for b in brains if b.get("visibility") == "personal"), None)
    shared = [b for b in brains if b.get("visibility") == "shared"]
    ranked = []
    for b in shared:
        s, why, blocked = score(b, text)
        ranked.append({"brain": b["name"], "score": s, "why": why, "blocked_by": blocked})
    ranked.sort(key=lambda r: -r["score"])
    hits = privacy_hits(text, brains)
    eligible = [r for r in ranked if r["score"] > 0 and not r["blocked_by"]]
    read_order = [r["brain"] for r in ranked if r["score"] > 0]
    pname = personal["name"] if personal else "personal"
    res = {"privacy_hits": hits, "candidates": ranked}
    if hits:
        res.update(write_to=pname, file=(personal or {}).get("default_file", "inbox.md"),
                   label="PRIVACY_REVIEW_NEEDED",
                   reason="privacy classifier hit; personal brain only. If the note mixes a clean fix with private detail, "
                          "split it: the clean fix may go to " + (eligible[0]["brain"] if eligible else "a shared brain") +
                          " after review, the private part stays personal with a pointer to the shared line.")
        read_order = [pname] + read_order
    elif eligible and (len(eligible) == 1 or eligible[0]["score"] > eligible[1]["score"]) and eligible[0]["score"] >= 2:
        win = next(b for b in shared if b["name"] == eligible[0]["brain"])
        res.update(write_to=win["name"], file="(owning file from its SITEMAP.md; else " + win.get("default_file", "inbox.md") + ")",
                   label="SHAREABLE_REVIEWED only after lint passes",
                   reason="matched " + ", ".join(eligible[0]["why"]))
        read_order = read_order + [pname]
    else:
        res.update(write_to=pname, file=(personal or {}).get("default_file", "inbox.md"), label="ROUTE_UNSURE",
                   reason="no single shared brain matches clearly; park it in the personal inbox and ask the owner")
        read_order = read_order + [pname]
    seen, ro = set(), []
    for n in read_order:
        if n not in seen:
            seen.add(n)
            ro.append(n)
    res["read_order"] = ro
    return res


def table(brains):
    rows = ["| Brain | Visibility | Path | Read/write here for | Never put here |", "|---|---|---|---|---|"]
    for b in brains:
        owns = ", ".join(map(str, as_list(b.get("topics")) or as_list(b.get("owns")))) or "-"
        never = ", ".join(map(str, as_list(b.get("never")))) or "-"
        rows.append(f"| {b['name']} | {b.get('visibility','?')} | `{b.get('path','?')}` | {owns} | {never} |")
    return "\n".join(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Membrain router")
    ap.add_argument("cmd", choices=["classify", "table", "write-routes", "paths"])
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--registry")
    ap.add_argument("--json", action="store_true")
    o = ap.parse_args(argv)
    reg_path, reg, brains = load_registry(o.registry)
    if o.cmd == "classify":
        if not o.arg:
            sys.exit("route classify needs the text")
        r = classify(o.arg, brains)
        if o.json:
            print(json.dumps(r, ensure_ascii=False, indent=2))
        else:
            print(f"WRITE -> {r['write_to']} / {r['file']}  [{r['label']}]")
            print(f"  why: {r['reason']}")
            if r["privacy_hits"]:
                print("  privacy: " + "; ".join(r["privacy_hits"]))
            print("READ  -> " + " then ".join(r["read_order"]))
    elif o.cmd == "table":
        print(table(brains))
    elif o.cmd == "paths":
        base = reg_path.parent.parent.parent if reg_path.parent.name == "personal" else Path.cwd()
        for b in brains:
            print("\t".join([b["name"], str((base / b.get("path", "")).resolve()), b.get("visibility", ""), str(b.get("remote", ""))]))
    elif o.cmd == "write-routes":
        if not o.arg:
            sys.exit("route write-routes needs the ROUTES.md path")
        p = Path(o.arg)
        txt = p.read_text(encoding="utf-8") if p.exists() else f"# ROUTES\n\n{BEGIN}\n{END}\n"
        block = f"{BEGIN}\n<!-- generated from {reg_path.name} by scripts/route.py; edit brains.yaml, not this table -->\n{table(brains)}\n{END}"
        if BEGIN in txt and END in txt:
            txt = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), lambda m: block, txt, flags=re.S)
        else:
            txt = txt.rstrip() + "\n\n" + block + "\n"
        p.write_text(txt, encoding="utf-8")
        print(f"route: refreshed {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
