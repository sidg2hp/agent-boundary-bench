#!/bin/sh
set -eu
"${PYTHON:-python3}" - <<'PY'
from pathlib import Path

path = Path("common/limits.mjs")
source = path.read_text(encoding="utf-8")
old = "  return catalog.default;\n}"
new = "  return catalog.studios.get(request.tenant) ?? catalog.default;\n}"
if source.count(old) != 1:
    raise SystemExit(f"unexpected starter revision in {path}")
path.write_text(source.replace(old, new), encoding="utf-8")
PY
node replay.mjs stage orchid-quota
