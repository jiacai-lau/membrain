#!/usr/bin/env python3
"""Maintainer tool: regenerate MANIFEST.yaml from templates/. Run after adding or removing a template.
Kind rules: everything in templates/workspace, templates/scripts and templates/hooks is framework;
in a brain skeleton only AGENTS.md, gitignore and handoffs/README.md are framework, the rest is content."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
T = ROOT / "templates"
REN = {"gitignore": ".gitignore", "membrain.yaml": ".membrain.yaml", "cursor-rule.mdc": ".cursor/rules/membrain.mdc"}
FW_BRAIN = {"AGENTS.md", "gitignore", "handoffs/README.md"}


def files(d):
    return sorted(p for p in d.rglob("*") if p.is_file() and "__pycache__" not in p.parts and not p.name.endswith(".pyc"))


def main():
    rows = []
    for p in files(T / "workspace"):
        rel = p.relative_to(T / "workspace").as_posix()
        rows.append((p, REN.get(rel, rel), "framework", "workspace", "755" if rel.endswith(".sh") else None))
    for p in files(T / "scripts"):
        rows.append((p, "scripts/" + p.name, "framework", "workspace", "755"))
    for scope, d, root in [("personal", "personal-brain", "brains/personal"), ("shared", "shared-brain", "brains/{{BRAIN_NAME}}")]:
        for p in files(T / d):
            rel = p.relative_to(T / d).as_posix()
            rows.append((p, f"{root}/{REN.get(rel, rel)}", "framework" if rel in FW_BRAIN else "content", scope, None))
        rows.append((T / "hooks/pre-commit", f"{root}/.githooks/pre-commit", "framework", scope, "755"))
        rows.append((T / "scripts/lint.py", f"{root}/.membrain/lint.py", "framework", scope, "755"))
    version = (ROOT / "VERSION").read_text().strip()
    out = ["# Membrain MANIFEST: every file an agent or bootstrap.py generates. Regenerate with scripts/build_manifest.py.",
           "# template = path in this repo (fetch it from <raw base>/<template>)",
           "# target   = path in the user's workspace; {{BRAIN_NAME}} is filled at spin-off",
           "# kind     = framework (upgradable: replaced by 'upgrade --apply' when unchanged locally)",
           "#            content   (generated once, then the user's; never overwritten)",
           "# scope    = workspace (setup) | personal (setup) | shared (each spin-off)",
           "# mode     = file mode to set (755 = executable)",
           f"membrain_version: {version}",
           "placeholders:",
           "  - workspace: [OWNER, DATE, MEMBRAIN_VERSION, SOURCE_URL]",
           "  - personal: [BRAIN_NAME, OWNER, DATE, REMOTE, ALIASES]",
           "  - shared: [BRAIN_NAME, OWNER, DATE, DESCRIPTION, TOPICS, EDITORS]",
           "files:"]
    for p, tgt, kind, scope, mode in rows:
        out.append(f"  - template: {p.relative_to(ROOT).as_posix()}\n    target: {tgt}\n    kind: {kind}\n    scope: {scope}"
                   + (f'\n    mode: "{mode}"' if mode else ""))
    (ROOT / "MANIFEST.yaml").write_text("\n".join(out) + "\n")
    print(f"MANIFEST.yaml: {len(rows)} entries")


if __name__ == "__main__":
    main()
