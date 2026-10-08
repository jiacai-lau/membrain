"""Example lint plugin: a support playbook with one fix per line, plus a tickets file.

Enable in .membrain/lint.yaml:
    plugins: [cs_playbook]
    cs_playbook:
      playbook: playbook/fixes.md          # file holding the fixes
      fixes_heading: "## Fixes"           # lines under this heading must match the format
      tickets: tickets/log.md             # optional: file that lists filed tickets
      ticket_id: "T-\\d+"                 # optional: ticket id pattern; ids in the playbook must be in tickets
      line_regex: ""                      # optional: override the line format (default below)

Default line format: '- <symptom> → <fix> · <client> · YYYY-MM-DD' (an optional ' · SUPERSEDED ...' tail).
Findings: P201 playbook-format (LOW), P202 missing-ticket (LOW). Standard library only.
"""
import re

DEFAULT_LINE = r"· [^·]+ · \d{4}-\d{2}-\d{2}( · SUPERSEDED.*)?\s*$"


def check(ctx):
    o = ctx.options
    pb = o.get("playbook") or "playbook/fixes.md"
    heading = (o.get("fixes_heading") or "## Fixes").strip().lower()
    line_re = re.compile(o.get("line_regex") or DEFAULT_LINE)
    if not (ctx.root / pb).exists():
        ctx.add("P200", "plugin-config", "LOW", ".membrain/lint.yaml", 0, f"cs_playbook: playbook file '{pb}' not found")
        return
    in_fixes = False
    for i, line in enumerate(ctx.lines(pb), 1):
        if line.startswith("## "):
            in_fixes = line.strip().lower() == heading
            continue
        if in_fixes and line.startswith("- "):
            if "→" not in line or not line_re.search(line):
                ctx.add("P201", "playbook-format", "LOW", pb, i, "expected '- symptom → fix · client · YYYY-MM-DD'")
        elif in_fixes and line.strip() and not line.startswith(("- ", "```")):
            ctx.add("P201", "playbook-format", "LOW", pb, i, "stray line inside Fixes (move it to the top or into tickets)")
    tk, pat = o.get("tickets"), o.get("ticket_id")
    if tk and pat and (ctx.root / tk).exists():
        rx = re.compile(pat)
        known = set(rx.findall("\n".join(ctx.lines(tk))))
        for n, line in ctx.bullets(pb):
            for t in sorted(set(rx.findall(line)) - known):
                ctx.add("P202", "missing-ticket", "LOW", pb, n, f"{t} is not listed in {tk}")
