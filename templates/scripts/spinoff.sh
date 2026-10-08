#!/usr/bin/env bash
# Spin off a shareable brain (see MEMBRAIN.md section B). Run from the workspace root.
exec python3 "$(dirname "$0")/membrain.py" spinoff "$@"
