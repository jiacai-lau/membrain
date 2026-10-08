#!/usr/bin/env python3
"""Membrain lint: keeps a brain clean, append-only and private where it must be.

Checks (codes are stable so CI and humans can grep them):
  E001 missing-date        entry line has no YYYY-MM-DD
  W002 missing-owner       entry line has no @owner
  E010 duplicate-line      the same entry appears more than once (normalised)
  W011 near-duplicate      two entries share >= 85% of their words (fact + context, ignoring owner/date/status)
  E101..E105 privacy       money, email, phone, ID number, secret  (shared brains only)
  E107 private-ref         a shared brain mentions a personal brain (name/path)
  W106 private-keyword     grant / quotation / salary / price-with-number ... (shared brains only)
  E020 missing-sitemap     brain has no SITEMAP.md
  E021 broken-sitemap-link SITEMAP.md points to a file that does not exist
  W022 orphan-file         file exists but SITEMAP.md does not list it
  W023 stale-check         SITEMAP row 'Last checked' older than stale_days
  E030 duplicate-copy      "file (1).md", "Copy of ...", sync-conflict copies: ask the owner
  W040 old-inbox-item      inbox item waiting longer than inbox_days
  W050 stale-unverified    entry marked 'unverified' older than stale_days

Usage:
  lint.py BRAIN_DIR [BRAIN_DIR ...]          lint brains (reads BRAIN_DIR/.membrain.yaml)
  lint.py WORKSPACE_DIR                       lint every brain under WORKSPACE_DIR/brains/
  lint.py --visibility shared some/dir        lint a folder that has no .membrain.yaml
  lint.py --privacy-only --visibility shared file.md   privacy check only (used by spinoff --move)
Options: --registry FILE  --forbid WORD  --skip sitemap,orphans,format  --stale-days N
         --today YYYY-MM-DD  --json  --strict (warnings fail too)

Standard library only. Exit code 1 when there are errors (or warnings with --strict).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------- tiny YAML
def _scalar(v: str):
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
        if not inner:
            return []
        return [_scalar(x) for x in _split_list(inner)]
    if v.lower() in ("true", "yes"):
        return True
    if v.lower() in ("false", "no"):
        return False
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    return v


def _split_list(s: str):
    out, cur, q = [], "", None
    for ch in s:
        if q:
            cur += ch
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
            cur += ch
        elif ch == ",":
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return out


def _strip_comment(line: str) -> str:
    q = None
    for i, ch in enumerate(line):
        if q:
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i].rstrip()
    return line.rstrip()


def load_yaml(path: Path) -> dict:
    """Parse the small YAML subset Membrain uses: scalars, inline lists,
    and one level of '- key: value' list items. Uses PyYAML when present."""
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text) or {}
    except ImportError:
        pass
    data: dict = {}
    cur_key = None
    cur_item = None
    for raw in text.splitlines():
        line = _strip_comment(raw)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        s = line.strip()
        if indent == 0:
            k, _, v = s.partition(":")
            cur_key, cur_item = k.strip(), None
            data[cur_key] = _scalar(v) if v.strip() else []
            continue
        if s.startswith("- "):
            body = s[2:]
            if ":" in body and not body.startswith(("'", '"')):
                k, _, v = body.partition(":")
                cur_item = {k.strip(): _scalar(v)}
                data[cur_key].append(cur_item)
            else:
                data[cur_key].append(_scalar(body))
                cur_item = None
            continue
        if cur_item is not None and ":" in s:
            k, _, v = s.partition(":")
            cur_item[k.strip()] = _scalar(v)
    return data

# ---------------------------------------------------------------- patterns
DATE_RE = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")
OWNER_RE = re.compile(r"(?:^|\s)@[A-Za-z][\w.-]*")
STATUS_RE = re.compile(r"\b(verified|unverified|assumption)\b", re.I)

PRIVACY_PATTERNS = [
    ("E101", "money", re.compile(
        r"(?:(?<![\w$])(?:S\$|US\$|A\$|RM|SGD|USD|MYR|IDR|EUR|€|£)\s?\d(?:[\d,.]*\d)?)|(?<![\w])\$\s?(?!0(?!\d|[.,]\d))\d(?:[\d,.]*\d)?")),
    ("E102", "email", re.compile(r"[A-Za-z0-9._%+-]+@(?!(?:g|c)\.us\b|s\.whatsapp\.net\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("E103", "phone", re.compile(
        r"(?<![\d@])(?:\+?65[\s-]?)?[689]\d{3}[\s-]?\d{4}(?![\d])|\+\d[\d\s-]{8,14}\d|\b\d{8,15}@c\.us\b")),
    ("E104", "id-number", re.compile(r"\b[STFGM]\d{7}[A-Z]\b")),
    ("E105", "secret", re.compile(
        r"(?i)\b(?:password|passwd|passcode|api[_ -]?key|secret|token|otp)\b\s*[:=]\s*\S+"
        r"|\bsk-[A-Za-z0-9]{16,}|\bghp_[A-Za-z0-9]{20,}|\bAKIA[0-9A-Z]{16}\b")),
]
KEYWORD_RE = re.compile(
    r"(?i)\b(grants?|quotations?|quotes? price|salary|salaries|payroll|bank balance|loan|"
    r"margin|commission|invoice amount|contract value|nric|passport)\b"
    r"|\bprices?\b[^.\n]{0,25}\d|\d[^.\n]{0,12}\bprices?\b")
DEFAULT_FORBID = [r"brains/personal\b", r"\bpersonal brain\b", r"/Users/[^/\s]+/", r"C:\\Users\\"]
RULE_HEADING_RE = re.compile(r"(?i)stays? out|not allowed|never|privacy|forbidden|what to keep out")
DUP_COPY_RE = re.compile(r"(?i)(\s\(\d+\)\.[a-z0-9]+$|^copy of |sync-conflict|conflicted copy|\.orig$)")
TEXT_EXT = {".md", ".csv", ".txt", ".yaml", ".yml"}
SKIP_DIRS = {".git", ".membrain", ".githooks", "node_modules", ".qmd", "__pycache__"}
ALLOW_MARK = "lint:allow"


class Finding:
    def __init__(self, code, name, path, line, msg, severity=None):
        self.code, self.name, self.path, self.line, self.msg = code, name, path, line, msg
        self.severity = severity or ("error" if code.startswith("E") else "warn")

    def as_dict(self):
        return {"code": self.code, "check": self.name, "severity": self.severity,
                "path": str(self.path), "line": self.line, "message": self.msg}

    def __str__(self):
        loc = f"{self.path}:{self.line}" if self.line else f"{self.path}"
        return f"{loc}: {self.code} {self.name}: {self.msg}"


def norm(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[`*_~\[\]()“”\"'’]", "", s)
    s = re.sub(r"[^\w\s→·-]", " ", s)
    return re.sub(r"\s+", " ", s).strip(" -")


def tokens(s: str) -> set:
    return {t for t in re.findall(r"\w+", s.lower()) if len(t) > 1}


def parse_date(m) -> dt.date | None:
    try:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def iter_lines(path: Path):
    """Yield (lineno, line, in_rule_section, in_code) for a text file."""
    in_code = False
    rule_section = False
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return
    for i, line in enumerate(text.splitlines(), 1):
        st = line.strip()
        if st.startswith("```"):
            in_code = not in_code
            yield i, line, rule_section, True
            continue
        if not in_code and st.startswith("#"):
            rule_section = bool(RULE_HEADING_RE.search(st))
        yield i, line, rule_section, in_code


def is_entry(line: str) -> bool:
    st = line.strip()
    return st.startswith(("- ", "* ")) and " · " in st


# ---------------------------------------------------------------- the linter
class Brain:
    def __init__(self, root: Path, cfg: dict, visibility: str):
        self.root, self.cfg, self.visibility = root, cfg, visibility
        self.name = cfg.get("name") or root.name


def find_registry(start: Path) -> Path | None:
    for p in [start, *start.parents][:4]:
        cand = p / "brains" / "personal" / "brains.yaml"
        if cand.exists():
            return cand
        cand = p / "personal" / "brains.yaml"
        if cand.exists():
            return cand
    return None


def forbidden_refs(registry: Path | None, extra: list[str]) -> list[re.Pattern]:
    pats = list(DEFAULT_FORBID)
    if registry and registry.exists():
        reg = load_yaml(registry)
        for b in reg.get("brains", []) or []:
            if isinstance(b, dict) and b.get("visibility") == "personal":
                name = b.get("name")
                generic = {"personal", "private", "me", "notes", "brain"}
                words = [b.get("path"), *(b.get("aliases") or [])]
                if name and str(name).lower() not in generic:
                    words.append(name)
                for word in words:
                    if word:
                        pats.append(r"(?i)" + re.escape(str(word)).replace(r"\ ", r"[\s_-]?"))
    for w in extra:
        pats.append(r"(?i)" + re.escape(w))
    return [re.compile(p) for p in pats]


def brain_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            p = Path(dirpath) / fn
            if fn.startswith(".") and fn != ".membrain.yaml":
                continue
            yield p


def lint_brain(brain: Brain, opts) -> list[Finding]:
    F: list[Finding] = []
    root = brain.root
    today = opts.today
    stale_days = int(opts.stale_days or brain.cfg.get("stale_days", 30))
    inbox_days = int(brain.cfg.get("inbox_days", 14))
    skip = opts.skip
    shared = brain.visibility == "shared"
    allow = [re.compile(a) for a in (brain.cfg.get("privacy_allow") or [])]
    forbid = forbidden_refs(opts.registry, opts.forbid) if shared else []

    files = [root] if root.is_file() else sorted(brain_files(root))
    rel = (lambda p: p.relative_to(root)) if root.is_dir() else (lambda p: p.name)

    entries = []  # (path, lineno, text)
    for p in files:
        r = rel(p)
        if DUP_COPY_RE.search(p.name):
            F.append(Finding("E030", "duplicate-copy", r, 0,
                             "looks like a second copy made by Drive/sync. Stop and ask the brain owner which one to keep."))
        if p.suffix.lower() not in TEXT_EXT:
            continue
        is_inbox = p.name.lower().startswith(("inbox", "_inbox"))
        for i, line, rule_sec, in_code in iter_lines(p):
            if in_code or not line.strip():
                continue
            allowed_line = ALLOW_MARK in line
            # privacy (shared brains only)
            if shared and not allowed_line and not opts.no_privacy:
                scrub = line
                for a in allow:
                    scrub = a.sub("", scrub)
                for code, name, pat in PRIVACY_PATTERNS:
                    m = pat.search(scrub)
                    if m:
                        F.append(Finding(code, name, r, i, f"'{m.group(0).strip()}' must not be in a shared brain"))
                for fp in forbid:
                    m = fp.search(line)
                    if m:
                        F.append(Finding("E107", "private-ref", r, i,
                                         f"mentions a personal brain ('{m.group(0)}'). Shared brains never point at personal ones."))
                if not rule_sec:
                    m = KEYWORD_RE.search(scrub)
                    if m:
                        F.append(Finding("W106", "private-keyword", r, i,
                                         f"'{m.group(0).strip()}' looks commercial/personal; keep it in the personal brain or mark the line lint:allow after review"))
            if opts.privacy_only:
                continue
            if is_entry(line):
                entries.append((r, i, line.strip()))
                if "format" not in skip:
                    dm = DATE_RE.search(line)
                    if not dm:
                        F.append(Finding("E001", "missing-date", r, i, "entry has no YYYY-MM-DD date"))
                    if not OWNER_RE.search(line):
                        F.append(Finding("W002", "missing-owner", r, i, "entry has no @owner"))
                    if dm:
                        d = parse_date(dm)
                        sm = STATUS_RE.search(line)
                        if d and sm and sm.group(1).lower() == "unverified" and (today - d).days > stale_days:
                            F.append(Finding("W050", "stale-unverified", r, i,
                                             f"unverified for {(today - d).days} days; verify it or mark it superseded"))
                        if d and is_inbox and line.strip().startswith("- [ ]") and (today - d).days > inbox_days:
                            F.append(Finding("W040", "old-inbox-item", r, i,
                                             f"waiting {(today - d).days} days for a decision"))

    if not opts.privacy_only:
        F = collapse_owner_warnings(F)
        F += dup_checks(entries)
        if root.is_dir() and "sitemap" not in skip:
            F += sitemap_checks(root, files, rel, today, stale_days, "orphans" not in skip)
    return F


def collapse_owner_warnings(F):
    """Legacy brains (no @owner yet) would drown in W002. Keep up to 3 per file, then one summary."""
    by_file: dict = {}
    for f in F:
        if f.code == "W002":
            by_file.setdefault(str(f.path), []).append(f)
    out = [f for f in F if f.code != "W002"]
    for path, fs in by_file.items():
        if len(fs) <= 3:
            out += fs
        else:
            lines = ",".join(str(f.line) for f in fs)
            out.append(Finding("W002", "missing-owner", fs[0].path, fs[0].line,
                               f"{len(fs)} entries have no @owner (legacy format). Lines: {lines}"))
    return out


NEAR_DUP = 0.85


def content_part(body: str) -> str:
    """The fact itself: the ' · ' segments before the date. Owner, status and source are metadata,
    so the same fact written by two people still counts as a duplicate."""
    segs = [x.strip() for x in body.split(" · ")]
    for k, seg in enumerate(segs):
        if DATE_RE.fullmatch(seg) or seg.startswith("@"):
            return " · ".join(segs[:k])
    return body


def dup_checks(entries):
    F = []
    seen: dict[str, tuple] = {}
    toks = []
    for path, i, text in entries:
        body = content_part(re.sub(r"^[-*]\s+(\[[ xX]\]\s+)?", "", text))
        n = norm(body)
        if n in seen:
            p0, i0 = seen[n]
            F.append(Finding("E010", "duplicate-line", path, i, f"same as {p0}:{i0}. Keep one; delete the copies."))
            continue
        seen[n] = (path, i)
        toks.append((path, i, tokens(body)))
    for a in range(len(toks)):
        pa, ia, ta = toks[a]
        if len(ta) < 6:
            continue
        for b in range(a + 1, len(toks)):
            pb, ib, tb = toks[b]
            if len(tb) < 6:
                continue
            j = len(ta & tb) / len(ta | tb)
            if j >= NEAR_DUP:
                F.append(Finding("W011", "near-duplicate", pb, ib, f"{int(j*100)}% same words as {pa}:{ia}. Merge or supersede."))
    return F


LINK_RE = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
TICK_RE = re.compile(r"^\|\s*`([^`]+)`")


def sitemap_checks(root, files, rel, today, stale_days, check_orphans):
    F = []
    sm = root / "SITEMAP.md"
    if not sm.exists():
        return [Finding("E020", "missing-sitemap", Path("SITEMAP.md"), 0, "every brain needs a SITEMAP.md (see docs/SITEMAP-FORMAT.md)")]
    listed = set()
    for i, line, _r, in_code in iter_lines(sm):
        if in_code:
            continue
        targets = [m.group(1) for m in LINK_RE.finditer(line)]
        tm = TICK_RE.match(line.strip())
        if tm:
            targets.append(tm.group(1))
        for t in targets:
            if re.match(r"^[a-z]+://", t) or t.startswith("mailto:"):
                continue
            p = (root / t).resolve()
            listed.add(p)
            if not p.exists():
                F.append(Finding("E021", "broken-sitemap-link", Path("SITEMAP.md"), i, f"'{t}' does not exist"))
        if tm:
            dates = [parse_date(m) for m in DATE_RE.finditer(line)]
            dates = [d for d in dates if d]
            if dates and (today - dates[-1]).days > stale_days:
                F.append(Finding("W023", "stale-check", Path("SITEMAP.md"), i,
                                 f"'{tm.group(1)}' last checked {(today - dates[-1]).days} days ago"))
    if check_orphans:
        listed_dirs = {p for p in listed if p.is_dir()}
        for p in files:
            rp = p.resolve()
            if p.name in ("SITEMAP.md", ".membrain.yaml") or p.suffix.lower() not in TEXT_EXT:
                continue
            if rp in listed or any(d in rp.parents for d in listed_dirs):
                continue
            F.append(Finding("W022", "orphan-file", rel(p), 0, "not listed in SITEMAP.md"))
    return F


def resolve_targets(paths, visibility_override):
    out = []
    for raw in paths:
        p = Path(raw).resolve()
        is_ws = (p / ".membrain.yaml").exists() and load_yaml(p / ".membrain.yaml").get("kind") == "workspace"
        if p.is_dir() and (is_ws or not (p / ".membrain.yaml").exists()) and (p / "brains").is_dir() and not visibility_override:
            for b in sorted((p / "brains").iterdir()):
                if b.is_dir() and not b.name.startswith("_") and (b / ".membrain.yaml").exists():
                    out.append(b)
            continue
        out.append(p)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Membrain lint", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--visibility", choices=["shared", "personal"])
    ap.add_argument("--registry")
    ap.add_argument("--forbid", action="append", default=[], help="extra word that must never appear in shared brains")
    ap.add_argument("--skip", default="", help="comma list: sitemap,orphans,format")
    ap.add_argument("--stale-days", type=int)
    ap.add_argument("--today")
    ap.add_argument("--privacy-only", action="store_true")
    ap.add_argument("--no-privacy", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true")
    o = ap.parse_args(argv)
    o.skip = {s.strip() for s in o.skip.split(",") if s.strip()}
    o.today = dt.date.fromisoformat(o.today) if o.today else dt.date.today()

    all_f = []
    for target in resolve_targets(o.paths, o.visibility):
        if not target.exists():
            print(f"lint: {target} does not exist", file=sys.stderr)
            return 2
        root_dir = target if target.is_dir() else target.parent
        cfg_path = root_dir / ".membrain.yaml"
        cfg = load_yaml(cfg_path) if cfg_path.exists() else {}
        vis = o.visibility or cfg.get("visibility") or "shared"   # unknown = treat as shared (safer)
        o.registry = Path(o.registry) if isinstance(o.registry, str) else (o.registry or find_registry(root_dir))
        brain = Brain(target, cfg, vis)
        fs = lint_brain(brain, o)
        for f in fs:
            f.brain = brain.name
        all_f += fs
        if not o.json:
            errs = sum(f.severity == "error" for f in fs)
            warns = len(fs) - errs
            print(f"== {brain.name} ({vis}) {target}")
            for f in sorted(fs, key=lambda f: (str(f.path), f.line, f.code)):
                print("  " + str(f))
            print(f"  -- {errs} error(s), {warns} warning(s)")
    if o.json:
        print(json.dumps([dict(f.as_dict(), brain=f.brain) for f in all_f], ensure_ascii=False, indent=2))
    errs = sum(f.severity == "error" for f in all_f)
    if errs or (o.strict and all_f):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
