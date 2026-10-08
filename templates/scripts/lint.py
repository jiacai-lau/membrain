#!/usr/bin/env python3
"""Membrain lint: one lint for every brain. Finds privacy leaks, duplicate, stale and malformed lines.

Warn-only by default (exit 0) so note-taking never stops. --strict exits 1 when there are findings at or
above --fail-on (default: low = any finding). The pre-commit hook uses --strict --fail-on high (blocks leaks).

Core checks (codes are stable; severity HIGH / MED / LOW):
  HIGH  E101 price          money amount (S$, SGD, $, USD, RM, ...; $0 is exempt)        shared brains
  HIGH  E102 email          email address                                                 shared brains
  HIGH  E103 phone          phone number / personal WhatsApp id                           shared brains
  HIGH  E104 id-number      NRIC/FIN-style id                                             shared brains
  HIGH  E105 secret         password / key / token / private key                         shared brains
  HIGH  E107 private-ref    a shared brain mentions a personal brain (name, path, alias)  shared brains
  HIGH  E108 grant-amounts  money amounts inside a grant document (one finding per file)  shared brains
  MED   E010 duplicate      the same line twice in one note file
  MED   W011 near-duplicate two lines in one note file >= 85% similar (SUPERSEDED lines are exempt)
  MED   E060 stale-deadline a deadline/due date has passed on a line not marked Closed/SUPERSEDED
  MED   E020 missing-sitemap / E021 broken-sitemap-link / E030 duplicate-copy (Drive "file (1).md")
  LOW   E001 missing-date / W002 missing-owner on entry lines ('- ... · ...')
  LOW   W106 private-keyword (grant, quotation, salary, price-with-number ...)            shared brains
  LOW   W022 orphan-file / W023 stale-check (SITEMAP) / W040 old-inbox-item / W050 stale-unverified
  LOW   L070 log-format     log/YYYY-MM.md heading not '## [YYYY-MM-DD HH:MM] <type> | <subject> | <last action>'
Brain-specific checks are plugins (scripts/lint_plugins/<name>.py) enabled in .membrain/lint.yaml.

Usage:
  lint.py                         lint the brain (or workspace) this script lives in
  lint.py BRAIN_DIR ...           lint brains (reads BRAIN_DIR/.membrain.yaml and BRAIN_DIR/.membrain/lint.yaml)
  lint.py WORKSPACE_DIR           lint every brain under WORKSPACE_DIR/brains/
  lint.py --privacy-only --visibility shared FILE      privacy check only (spin-off uses this)
Options: --format text|md|json  --strict  --fail-on high|med|low  --config FILE  --plugins a,b
         --registry FILE  --forbid WORD  --skip sitemap,orphans,format,dups,deadlines,log
         --stale-days N  --today YYYY-MM-DD  --no-privacy
Standard library only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import difflib
import fnmatch
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


# ---------------------------------------------------------------- tiny YAML (scalars, inline lists,
# lists of '- key: value' items, and one level of nested mapping). PyYAML is used when present.
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
        return [_scalar(x) for x in _split_list(inner)] if inner else []
    if v.lower() in ("true", "yes"):
        return True
    if v.lower() in ("false", "no"):
        return False
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    if re.fullmatch(r"-?\d+\.\d+", v):
        return float(v)
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
            if ch == q and line[i - 1] != "\\":
                q = None
        elif ch in "\"'":
            q = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i].rstrip()
    return line.rstrip()


def load_yaml(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text) or {}
    except ImportError:
        pass
    data: dict = {}
    key, item = None, None
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
        elif s.startswith("- ") and isinstance(data.get(key), list):
            body = s[2:]
            if re.match(r"^[\w.-]+:\s", body + " ") and not body.startswith(("'", '"')):
                k, _, v = body.partition(":")
                item = {k.strip(): _scalar(v)}
                data[key].append(item)
            else:
                data[key].append(_scalar(body))
                item = None
        elif ":" in s:
            k, _, v = s.partition(":")
            if item is not None:
                item[k.strip()] = _scalar(v)
            else:
                if data.get(key) == []:
                    data[key] = {}
                if isinstance(data.get(key), dict):
                    data[key][k.strip()] = _scalar(v)
    return data


# ---------------------------------------------------------------- patterns
DATE_RE = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")
OWNER_RE = re.compile(r"(?:^|\s)@[A-Za-z][\w.-]*")
STATUS_RE = re.compile(r"\b(verified|unverified|assumption)\b", re.I)
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
DEADLINE_RE = re.compile(
    r"(?i)\b(?:deadline|due(?: by| on)?)[:\s]+(?:(\d{1,2}) ([A-Za-z]{3})[a-z]* (\d{4})|(20\d{2})-(\d{2})-(\d{2}))")
CLOSED_RE = re.compile(r"(?i)closed|superseded")

PRICE_RE = re.compile(
    r"(?:(?<![\w$`])(?:S\$|US\$|A\$|RM|SGD|USD|MYR|IDR|EUR|€|£)\s?\d(?:[\d,.]*\d)?)"
    r"|(?<![\w`])\$\s?(?!0(?:\.0+)?(?![\d.,]*[1-9]))\d(?:[\d,.]*\d)?")
PRIVACY_PATTERNS = [
    ("E101", "price", PRICE_RE),
    ("E102", "email", re.compile(r"(?<![A-Za-z0-9._%+-])(?!git@)[A-Za-z0-9._%+-]+@(?!(?:g|c)\.us\b|s\.whatsapp\.net\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("E103", "phone", re.compile(
        r"(?<![\d@])(?:\+?65[\s-]?)?[689]\d{3}[\s-]?\d{4}(?![\d])|\+\d[\d\s-]{8,14}\d|\b\d{8,15}@c\.us\b")),
    ("E104", "id-number", re.compile(r"\b[STFGM]\d{7}[A-Z]\b")),
    ("E105", "secret", re.compile(
        r"(?i)\b(?:password|passwd|passcode|api[_ -]?key|secret|token|otp)\b\s*[:=]\s*\S+"
        r"|\bsk-[A-Za-z0-9]{16,}|\bgh[pousr]_[A-Za-z0-9]{20,}|\bAKIA[0-9A-Z]{16}\b|-----BEGIN [A-Z ]*PRIVATE KEY")),
]
GRANT_RE = re.compile(r"(?i)grant")
KEYWORD_RE = re.compile(
    r"(?i)\b(grants?|quotations?|quotes? price|salary|salaries|payroll|bank balance|loan|"
    r"margin|commission|invoice amount|contract value|nric|passport)\b"
    r"|\bprices?\b[^.\n]{0,25}\d|\d[^.\n]{0,12}\bprices?\b")
DEFAULT_FORBID = [r"brains/personal\b", r"\bpersonal brain\b", r"/Users/[^/\s]+/", r"C:\\Users\\"]
RULE_HEADING_RE = re.compile(r"(?i)stays? out|not allowed|never|privacy|forbidden|keep out|ground rules|\blint\b")
DUP_COPY_RE = re.compile(r"(?i)(\s\(\d+\)\.[a-z0-9]+$|^copy of |sync-conflict|conflicted copy|\.orig$)")
LOG_HEAD_RE = re.compile(r"^## \[(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})\] ([\w-]+) \| [^|]+ \| .+$")
TEXT_EXT = {".md", ".csv", ".txt", ".yaml", ".yml"}
SKIP_DIRS = {".git", "node_modules", ".qmd", "__pycache__"}
ALLOW_MARK = "lint:allow"
SEV_RANK = {"HIGH": 0, "MED": 1, "LOW": 2}
SEVERITY = {"E101": "HIGH", "E102": "HIGH", "E103": "HIGH", "E104": "HIGH", "E105": "HIGH", "E107": "HIGH", "E108": "HIGH",
            "E010": "MED", "W011": "MED", "E060": "MED", "E020": "MED", "E021": "MED", "E030": "MED"}
DEFAULTS = {
    # note files: duplicate, near-duplicate, deadline and entry-format checks run on these
    "note_files": ["*.md", "**/*.md"],
    "note_exclude": ["README.md", "AGENTS.md", "CLAUDE.md", "SITEMAP.md", "log/**", "handoffs/**", "guides/**"],
    # files the privacy checks skip (Membrain's own docs that describe the rules)
    "privacy_skip": ["AGENTS.md", "log/README.md", "handoffs/README.md"],
    "log_types": ["fix", "ticket", "client", "lint", "answer"],
    "near_duplicate": 0.85,
    "plugins": [],
    "disable": [],
}


class Finding:
    def __init__(self, code, name, path, line, msg, severity=None):
        self.code, self.name, self.path, self.line, self.msg = code, name, str(path), line, msg
        self.severity = severity or SEVERITY.get(code, "LOW")
        self.brain = ""

    def as_dict(self):
        return {"brain": self.brain, "code": self.code, "check": self.name, "severity": self.severity,
                "path": self.path, "line": self.line, "message": self.msg}

    def __str__(self):
        loc = f"{self.path}:{self.line}" if self.line else self.path
        return f"{loc}: {self.code} {self.name} [{self.severity}]: {self.msg}"


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def content_part(line: str) -> str:
    """The fact itself: the ' · ' segments before the date/@owner. Lets the same fact by two people match."""
    segs = [x.strip() for x in line.split(" · ")]
    for k, seg in enumerate(segs):
        if k and (DATE_RE.fullmatch(seg) or seg.startswith("@")):
            return " · ".join(segs[:k])
    return line


def parse_date(m) -> dt.date | None:
    try:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def deadline_of(line: str) -> dt.date | None:
    m = DEADLINE_RE.search(line)
    if not m:
        return None
    try:
        if m.group(1):
            return dt.date(int(m.group(3)), MONTHS[m.group(2).lower()[:3]], int(m.group(1)))
        return dt.date(int(m.group(4)), int(m.group(5)), int(m.group(6)))
    except (KeyError, ValueError):
        return None


def read_lines(path: Path):
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except (UnicodeDecodeError, OSError):
        return []


def match_any(rel: str, globs) -> bool:
    for g in globs or []:
        if fnmatch.fnmatch(rel, g) or (g.endswith("/**") and rel.startswith(g[:-2])):
            return True
    return False


# ---------------------------------------------------------------- brain + config
class Brain:
    def __init__(self, root: Path, opts):
        self.root = root
        self.dir = root if root.is_dir() else root.parent
        meta_p = self.dir / ".membrain.yaml"
        self.meta = load_yaml(meta_p) if meta_p.exists() else {}
        cfg_p = Path(opts.config) if opts.config else self.dir / ".membrain" / "lint.yaml"
        cfg = dict(DEFAULTS)
        if cfg_p.exists():
            cfg.update({k: v for k, v in load_yaml(cfg_p).items() if v not in (None, "")})
        if opts.plugins:
            cfg["plugins"] = [p.strip() for p in opts.plugins.split(",") if p.strip()]
        self.cfg = cfg
        self.visibility = opts.visibility or self.meta.get("visibility") or "shared"  # unknown = shared (safer)
        self.name = self.meta.get("name") or self.dir.name
        self.disabled = set(cfg.get("disable") or [])

    def files(self):
        if self.root.is_file():
            return [self.root]
        out = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
            for fn in sorted(filenames):
                if not fn.startswith("."):
                    out.append(Path(dirpath) / fn)
        return out

    def rel(self, p: Path) -> str:
        return p.name if self.root.is_file() else p.relative_to(self.root).as_posix()

    def is_note(self, rel: str) -> bool:
        if self.root.is_file():
            return rel.endswith(".md")
        return match_any(rel, self.cfg.get("note_files")) and not match_any(rel, self.cfg.get("note_exclude"))


def find_registry(start: Path) -> Path | None:
    for p in [start, *start.parents][:4]:
        for cand in (p / "brains" / "personal" / "brains.yaml", p / "personal" / "brains.yaml"):
            if cand.exists():
                return cand
    return None


def forbidden_refs(registry: Path | None, extra) -> list:
    pats = list(DEFAULT_FORBID)
    if registry and registry.exists():
        for b in load_yaml(registry).get("brains", []) or []:
            if isinstance(b, dict) and b.get("visibility") == "personal":
                name = b.get("name")
                words = [b.get("path"), *(b.get("aliases") or [])]
                if name and str(name).lower() not in {"personal", "private", "me", "notes", "brain"}:
                    words.append(name)
                pats += [r"(?i)" + re.escape(str(w)).replace(r"\ ", r"[\s_-]?") for w in words if w]
    pats += [r"(?i)" + re.escape(w) for w in extra or []]
    return [re.compile(p) for p in pats]


def code_mask(lines):
    """True for lines inside ``` fences (and the fence lines)."""
    mask, inside = [], False
    for line in lines:
        if line.strip().startswith("```"):
            mask.append(True)
            inside = not inside
        else:
            mask.append(inside)
    return mask


# ---------------------------------------------------------------- checks
def privacy_checks(brain, files, opts, F):
    allow = [re.compile(a) for a in (brain.meta.get("privacy_allow") or []) + (brain.cfg.get("privacy_allow") or [])]
    forbid = forbidden_refs(brain.registry, (opts.forbid or []) + (brain.cfg.get("forbid") or []))
    skip = brain.cfg.get("privacy_skip") or []
    for p in files:
        rel = brain.rel(p)
        if p.suffix.lower() not in TEXT_EXT or (not brain.root.is_file() and match_any(rel, skip)):
            continue
        lines = read_lines(p)
        whole = "\n".join(lines)
        grant_doc = bool(GRANT_RE.search(whole))
        grant_hits, kw = 0, []
        rule = False
        mask = code_mask(lines)
        for i, line in enumerate(lines, 1):
            st = line.strip()
            if st.startswith("#") and not mask[i - 1]:
                rule = bool(RULE_HEADING_RE.search(st))
            if not st or ALLOW_MARK in line:
                continue
            scrub = line
            for a in allow:
                scrub = a.sub("", scrub)
            for code, name, pat in PRIVACY_PATTERNS:
                m = pat.search(scrub)
                if not m:
                    continue
                if code == "E101" and grant_doc:
                    grant_hits += 1
                    continue
                F.append(Finding(code, name, rel, i, f"'{m.group(0).strip()}' must not be in a shared brain"))
            for fp in forbid:
                m = fp.search(line)
                if m:
                    F.append(Finding("E107", "private-ref", rel, i,
                                     f"mentions a personal brain ('{m.group(0)}'). Shared brains never point at personal ones."))
                    break
            if not rule and not grant_doc:
                m = KEYWORD_RE.search(scrub)
                if m:
                    kw.append((i, m.group(0).strip()))
        if grant_hits:
            F.append(Finding("E108", "grant-amounts", rel, 0,
                             f"{grant_hits} lines with money amounts in a grant document (grant amounts stay out of the brain)"))
        if len(kw) > 3:
            F.append(Finding("W106", "private-keyword", rel, kw[0][0],
                             f"{len(kw)} lines use commercial/personal words (lines {','.join(str(i) for i, _ in kw)}); keep them in the personal brain or mark lint:allow after review"))
        else:
            for i, w in kw:
                F.append(Finding("W106", "private-keyword", rel, i,
                                 f"'{w}' looks commercial/personal; keep it in the personal brain or mark the line lint:allow after review"))


def note_checks(brain, files, opts, F):
    today, skip = opts.today, opts.skip
    stale_days = int(opts.stale_days or brain.meta.get("stale_days") or brain.cfg.get("stale_days") or 30)
    inbox_days = int(brain.meta.get("inbox_days") or brain.cfg.get("inbox_days") or 14)
    threshold = float(brain.cfg.get("near_duplicate") or 0.85)
    owner_missing: dict = {}
    for p in files:
        rel = brain.rel(p)
        if p.suffix.lower() != ".md" or not brain.is_note(rel):
            continue
        lines = read_lines(p)
        mask = code_mask(lines)
        bullets = [(i, line) for i, (line, c) in enumerate(zip(lines, mask), 1) if line.startswith("- ") and not c]
        is_inbox = p.name.lower().startswith(("inbox", "_inbox"))
        if "dups" not in skip:
            seen, uniq = {}, []
            for n, line in bullets:
                k = norm(line)
                if k in seen:
                    F.append(Finding("E010", "duplicate", rel, n, f"same as line {seen[k]}. Keep one; mark the others SUPERSEDED (owner approves)."))
                else:
                    seen[k] = n
                    uniq.append((n, line, k, norm(content_part(line))))
            for a in range(len(uniq)):
                na, la, ka, ca = uniq[a]
                if "superseded" in ka:
                    continue
                for b in range(a + 1, len(uniq)):
                    nb, lb, kb, cb = uniq[b]
                    if "superseded" in kb:
                        continue
                    r = difflib.SequenceMatcher(None, ka, kb).ratio()
                    if ca != ka or cb != kb:
                        r = max(r, difflib.SequenceMatcher(None, ca, cb).ratio())
                    if r >= threshold:
                        F.append(Finding("W011", "near-duplicate", rel, nb,
                                         f"{int(r * 100)}% similar to line {na}; merge or mark one SUPERSEDED"))
        for n, line in bullets:
            if "deadlines" not in skip:
                d = deadline_of(line)
                if d and d < today and not CLOSED_RE.search(line):
                    F.append(Finding("E060", "stale-deadline", rel, n, f"deadline {d} has passed; check it and update or mark SUPERSEDED"))
            if "format" in skip or " · " not in line:
                continue
            dm = DATE_RE.search(line)
            if not dm:
                F.append(Finding("E001", "missing-date", rel, n, "entry has no YYYY-MM-DD date"))
            if not OWNER_RE.search(line):
                owner_missing.setdefault(rel, []).append(n)
            d = parse_date(dm) if dm else None
            if d:
                sm = STATUS_RE.search(line)
                if sm and sm.group(1).lower() == "unverified" and (today - d).days > stale_days and not CLOSED_RE.search(line):
                    F.append(Finding("W050", "stale-unverified", rel, n, f"unverified for {(today - d).days} days; verify it or mark it SUPERSEDED"))
                if is_inbox and line.startswith("- [ ]") and (today - d).days > inbox_days:
                    F.append(Finding("W040", "old-inbox-item", rel, n, f"waiting {(today - d).days} days for a decision"))
    for rel, ns in owner_missing.items():
        if len(ns) <= 3:
            F += [Finding("W002", "missing-owner", rel, n, "entry has no @owner") for n in ns]
        else:
            F.append(Finding("W002", "missing-owner", rel, ns[0], f"{len(ns)} entries have no @owner (legacy format). Lines: {','.join(map(str, ns))}"))
    return stale_days


def log_checks(brain, F):
    types = set(brain.cfg.get("log_types") or DEFAULTS["log_types"])
    logdir = brain.dir / "log"
    if not logdir.is_dir():
        return
    for p in sorted(logdir.glob("*.md")):
        if p.name.lower() == "readme.md":
            continue
        rel = brain.rel(p) if not brain.root.is_file() else p.name
        if not re.fullmatch(r"\d{4}-\d{2}\.md", p.name):
            F.append(Finding("L070", "log-format", rel, 0, "log files are named log/YYYY-MM.md"))
        lines = read_lines(p)
        for i, line in enumerate(lines, 1):
            if not line.startswith("## "):
                continue
            m = LOG_HEAD_RE.match(line)
            if not m:
                F.append(Finding("L070", "log-format", rel, i, "expected '## [YYYY-MM-DD HH:MM] <type> | <subject> | <last action>'"))
                continue
            if m.group(3) not in types:
                F.append(Finding("L070", "log-format", rel, i, f"type '{m.group(3)}' is not one of: {', '.join(sorted(types))}"))
            nxt = next((l for l in lines[i:] if l.strip()), "")
            if not nxt.startswith("who/tool:"):
                F.append(Finding("L070", "log-format", rel, i, "next line should be 'who/tool: … · files: …'"))


LINK_RE = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
TICK_RE = re.compile(r"^\|\s*`([^`]+)`")


def sitemap_checks(brain, files, today, stale_days, check_orphans):
    F, root = [], brain.root
    sm = root / "SITEMAP.md"
    if not sm.exists():
        return [Finding("E020", "missing-sitemap", "SITEMAP.md", 0, "every brain needs a SITEMAP.md (see docs/SITEMAP-FORMAT.md)")]
    listed = set()
    lines = read_lines(sm)
    for i, (line, c) in enumerate(zip(lines, code_mask(lines)), 1):
        if c:
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
                F.append(Finding("E021", "broken-sitemap-link", "SITEMAP.md", i, f"'{t}' does not exist"))
        if tm:
            dates = [d for d in (parse_date(m) for m in DATE_RE.finditer(line)) if d]
            if dates and (today - dates[-1]).days > stale_days:
                F.append(Finding("W023", "stale-check", "SITEMAP.md", i, f"'{tm.group(1)}' last checked {(today - dates[-1]).days} days ago"))
    if check_orphans:
        listed_dirs = {p for p in listed if p.is_dir()}
        for p in files:
            rp = p.resolve()
            if p.name == "SITEMAP.md" or p.suffix.lower() not in TEXT_EXT:
                continue
            if rp in listed or any(d in rp.parents for d in listed_dirs):
                continue
            F.append(Finding("W022", "orphan-file", brain.rel(p), 0, "not listed in SITEMAP.md"))
    return F


# ---------------------------------------------------------------- plugins
class PluginContext:
    """What a plugin gets: ctx.root, ctx.options (its block in .membrain/lint.yaml), ctx.today,
    ctx.lines(rel), ctx.bullets(rel) -> [(lineno, line)], ctx.add(code, name, severity, rel, line, msg)."""

    def __init__(self, brain, options, today, F):
        self.root, self.options, self.today, self.brain, self._F = brain.dir, options or {}, today, brain, F

    def lines(self, rel):
        return read_lines(self.root / rel)

    def bullets(self, rel):
        return [(i, l) for i, l in enumerate(self.lines(rel), 1) if l.startswith("- ")]

    def add(self, code, name, severity, rel, line, msg):
        self._F.append(Finding(code, name, rel, line, msg, severity))


def load_plugin(name: str):
    if not re.fullmatch(r"[a-z0-9_]+", name):
        raise ValueError(f"bad plugin name {name!r}")
    for d in (HERE / "lint_plugins",):
        p = d / f"{name}.py"
        if p.exists():
            spec = importlib.util.spec_from_file_location(f"membrain_lint_plugin_{name}", p)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise FileNotFoundError(f"lint plugin '{name}' not found in {HERE / 'lint_plugins'}")


# ---------------------------------------------------------------- driver
def lint_brain(brain: Brain, opts) -> list:
    F: list = []
    files = brain.files()
    if brain.visibility == "shared" and not opts.no_privacy:
        privacy_checks(brain, files, opts, F)
    if not opts.privacy_only:
        for p in files:
            if DUP_COPY_RE.search(p.name):
                F.append(Finding("E030", "duplicate-copy", brain.rel(p), 0,
                                 "looks like a second copy made by Drive/sync. Stop and ask the brain owner which one to keep."))
        stale_days = note_checks(brain, files, opts, F)
        if "log" not in opts.skip and brain.root.is_dir():
            log_checks(brain, F)
        if brain.root.is_dir() and "sitemap" not in opts.skip:
            F += sitemap_checks(brain, files, opts.today, stale_days, "orphans" not in opts.skip)
        for name in brain.cfg.get("plugins") or []:
            try:
                load_plugin(name).check(PluginContext(brain, brain.cfg.get(name), opts.today, F))
            except Exception as e:  # a broken plugin must not stop note-taking
                F.append(Finding("X000", "plugin-error", ".membrain/lint.yaml", 0, f"plugin '{name}': {e}", "LOW"))
    F = [f for f in F if f.code not in brain.disabled and f.name not in brain.disabled]
    for f in F:
        f.brain = brain.name
    F.sort(key=lambda f: (SEV_RANK[f.severity], f.path, f.line, f.code))
    return F


def resolve_targets(paths, visibility_override):
    out = []
    for raw in paths:
        p = Path(raw).resolve()
        meta = p / ".membrain.yaml"
        is_ws = meta.exists() and load_yaml(meta).get("kind") == "workspace"
        if p.is_dir() and (is_ws or not meta.exists()) and (p / "brains").is_dir() and not visibility_override:
            out += [b for b in sorted((p / "brains").iterdir())
                    if b.is_dir() and not b.name.startswith("_") and (b / ".membrain.yaml").exists()]
            continue
        out.append(p)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Membrain lint", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--visibility", choices=["shared", "personal"])
    ap.add_argument("--registry")
    ap.add_argument("--config")
    ap.add_argument("--plugins")
    ap.add_argument("--forbid", action="append", default=[])
    ap.add_argument("--skip", default="")
    ap.add_argument("--stale-days", type=int)
    ap.add_argument("--today")
    ap.add_argument("--privacy-only", action="store_true")
    ap.add_argument("--no-privacy", action="store_true")
    ap.add_argument("--format", choices=["text", "md", "json"], default="text")
    ap.add_argument("--json", action="store_true", help="same as --format json")
    ap.add_argument("--strict", action="store_true", help="exit 1 when there are findings at or above --fail-on")
    ap.add_argument("--fail-on", choices=["high", "med", "low"], default="low")
    o = ap.parse_args(argv)
    if o.json:
        o.format = "json"
    o.skip = {s.strip() for s in o.skip.split(",") if s.strip()}
    o.today = dt.date.fromisoformat(o.today or os.environ.get("MB_TODAY") or dt.date.today().isoformat())
    paths = o.paths or [str(HERE.parent)]
    all_f, sections = [], []
    for target in resolve_targets(paths, o.visibility):
        if not target.exists():
            print(f"lint: {target} does not exist", file=sys.stderr)
            return 2
        brain = Brain(target, o)
        brain.registry = Path(o.registry) if o.registry else find_registry(brain.dir)
        fs = lint_brain(brain, o)
        all_f += fs
        sections.append((brain, target, fs))
    if o.format == "json":
        print(json.dumps([f.as_dict() for f in all_f], ensure_ascii=False, indent=2))
    elif o.format == "md":
        for brain, target, fs in sections:
            print(f"# {brain.name} lint ({o.today})\n")
            if not fs:
                print("No findings.\n")
                continue
            print(f"{len(fs)} findings. Fix HIGH first. Only the brain owner approves removing, merging or moving lines.\n")
            print("| Severity | File | Line | Code | Kind | Detail |\n|---|---|---|---|---|---|")
            for f in fs:
                print(f"| {f.severity} | {f.path} | {f.line or ''} | {f.code} | {f.name} | {f.msg.replace('|', '/')} |")
            print()
    else:
        for brain, target, fs in sections:
            print(f"== {brain.name} ({brain.visibility}) {target}")
            for f in fs:
                print("  " + str(f))
            c = {s: sum(f.severity == s for f in fs) for s in SEV_RANK}
            print(f"  -- {len(fs)} finding(s): {c['HIGH']} high, {c['MED']} med, {c['LOW']} low")
    limit = SEV_RANK[o.fail_on.upper()]
    if o.strict and any(SEV_RANK[f.severity] <= limit for f in all_f):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
