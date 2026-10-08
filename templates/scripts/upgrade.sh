#!/usr/bin/env bash
# Check for (default) or apply (--apply) Membrain framework updates. Never touches content, never pushes.
exec python3 "$(dirname "$0")/membrain.py" upgrade "$@"
