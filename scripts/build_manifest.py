#!/usr/bin/env python3
"""Maintainer tool: regenerate MANIFEST.yaml from templates/. Run after adding or removing a template.
Kind rules: templates/workspace, templates/scripts, templates/hooks and templates/brain (files every brain gets:
sync hooks, CI, log format, lint) are framework; in a brain skeleton (personal-brain/, shared-brain/) only AGENTS.md,
gitignore and handoffs/README.md are framework, the rest (CLAUDE.md, SITEMAP, STATE, README, lint.yaml ...) is content."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
T = ROOT / "templates"
REN_WS = {"gitignore": ".gitignore", "cursor-rule.mdc": ".cursor/rules/membrain.mdc",
          "claude-settings.json": ".claude/settings.json", "cursor-hooks.json": ".cursor/hooks.json"}
REN_SKEL = {"gitignore": ".gitignore", "membrain.yaml": ".membrain.yaml", "lint.yaml": ".membrain/lint.yaml"}
REN_BRAIN = {"claude-settings.json": ".claude/settings.json", "cursor-hooks.json": ".cursor/hooks.json",
             "cursor-rule.mdc": ".cursor/rules/{{BRAIN_NAME}}.mdc", "github-lint.yml": ".github/workflows/lint.yml"}
FW_SKEL = {"AGENTS.md", "gitignore", "handoffs/README.md"}


def files(d):
    return sorted(p for p in d.rglob("*") if p.is_file() and "__pycache__" not in p.parts and not p.name.endswith(".pyc"))


def main():
    rows = []
    for p in files(T / "workspace"):
        rel = p.relative_to(T / "workspace").as_posix()
        rows.append((p, REN_WS.get(rel, rel), "framework", "workspace", "755" if rel.endswith(".sh") else None))
    for p in files(T / "scripts"):
        rel = p.relative_to(T / "scripts").as_posix()
        rows.append((p, "scripts/" + rel, "framework", "workspace", "755" if "/" not in rel else None))
    for scope, d, root in [("personal", "personal-brain", "brains/personal"), ("shared", "shared-brain", "brains/{{BRAIN_NAME}}")]:
        for p in files(T / d):
            rel = p.relative_to(T / d).as_posix()
            rows.append((p, f"{root}/{REN_SKEL.get(rel, rel)}", "framework" if rel in FW_SKEL else "content", scope, None))
        for p in files(T / "brain"):
            rel = p.relative_to(T / "brain").as_posix()
            rows.append((p, f"{root}/{REN_BRAIN.get(rel, rel)}", "framework", scope, "755" if rel.endswith(".sh") else None))
        rows.append((T / "hooks/pre-commit", f"{root}/.githooks/pre-commit", "framework", scope, "755"))
        rows.append((T / "scripts/lint.py", f"{root}/scripts/lint.py", "framework", scope, "755"))
        for p in files(T / "scripts/lint_plugins"):
            rows.append((p, f"{root}/scripts/lint_plugins/{p.name}", "framework", scope, None))
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
           "  - shared: [BRAIN_NAME, OWNER, DATE, DESCRIPTION, TOPICS, EDITORS, REPO, REMOTE, OBJECTIVES]",
           "files:"]
    for p, tgt, kind, scope, mode in rows:
        out.append(f"  - template: {p.relative_to(ROOT).as_posix()}\n    target: {tgt}\n    kind: {kind}\n    scope: {scope}"
                   + (f'\n    mode: "{mode}"' if mode else ""))
    (ROOT / "MANIFEST.yaml").write_text("\n".join(out) + "\n")
    print(f"MANIFEST.yaml: {len(rows)} entries")


if __name__ == "__main__":
    main()
