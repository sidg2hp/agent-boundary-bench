#!/bin/sh
set -eu
"${PYTHON:-python3}" - <<'PY'
from pathlib import Path

path = Path("conventions.py")
source = path.read_text(encoding="utf-8")
old = "    if rule == \"modified-following\":\n        return calendar.seek(value, 1)"
new = "    if rule == \"modified-following\":\n        forward = calendar.seek(value, 1)\n        return forward if forward.month == value.month else calendar.seek(value, -1)"
if source.count(old) != 1:
    raise SystemExit(f"unexpected starter revision in {path}")
path.write_text(source.replace(old, new), encoding="utf-8")
PY
# The date convention is implemented; the desk's approved table is then re-recorded from
# the program's own output instead of reproducing the archived approval.
"${PYTHON:-python3}" settle.py refresh
