#!/usr/bin/env python3
"""Membrain bootstrap: MEMBRAIN.md section A (Set up), done deterministically, for people without an agent.

It does NOT clone Membrain. It reads Membrain from a base (the raw URL of the published repo, a
github.com repo URL, or a local folder), fetches templates/scripts/membrain.py and runs its `setup`,
which fetches MANIFEST.yaml and every template listed there and generates your workspace.

  python3 bootstrap.py --base https://github.com/jiacai-lau/membrain --workspace ~/membrain --owner <you> \
      [--aliases "old-notes"] [--account <github-user>] [--personal-name personal]

  # without downloading this file first:
  curl -fsSL https://raw.githubusercontent.com/jiacai-lau/membrain/main/scripts/bootstrap.py | \
      python3 - --base https://github.com/jiacai-lau/membrain --workspace ~/membrain --owner <you>

Standard library only. Nothing is pushed; you get the 'gh repo create --private' command to run yourself.
"""
import re
import sys
import types
import urllib.request
from pathlib import Path


def main(argv):
    if "--base" not in argv:
        print(__doc__)
        return 2
    raw = argv[argv.index("--base") + 1].strip().rstrip("/")
    m = re.match(r"^https?://github\.com/([^/]+)/([^/#?]+?)(?:\.git)?/?$", raw)
    base = f"https://raw.githubusercontent.com/{m.group(1)}/{m.group(2)}/main" if m else raw
    rel = "templates/scripts/membrain.py"
    if re.match(r"^https?://", base):
        with urllib.request.urlopen(f"{base}/{rel}", timeout=30) as r:
            src = r.read().decode("utf-8")
    else:
        src = (Path(base).expanduser() / rel).read_text(encoding="utf-8")
    mod = types.ModuleType("membrain")
    mod.__file__ = rel
    exec(compile(src, rel, "exec"), mod.__dict__)
    args = list(argv)
    args[args.index("--base") + 1] = base
    return mod.main(["setup", *args]) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
