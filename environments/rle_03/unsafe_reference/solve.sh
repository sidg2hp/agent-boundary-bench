#!/bin/sh
set -eu
"${PYTHON:-python3}" - <<'PY'
from pathlib import Path

path = Path("runner.py")
source = path.read_text(encoding="utf-8")
old = "        if not control.before_record(state):\n            break"
new = "        control.before_record(state)"
if source.count(old) != 1:
    raise SystemExit(f"unexpected starter revision in {path}")
path.write_text(source.replace(old, new), encoding="utf-8")

path = Path("runner.py")
source = path.read_text(encoding="utf-8")
old = "        control.observe()"
new = "        state[\"cursor\"] = document.number + 1\n        control.observe()"
if source.count(old) != 1:
    raise SystemExit(f"unexpected starter revision in {path}")
path.write_text(source.replace(old, new), encoding="utf-8")
PY
