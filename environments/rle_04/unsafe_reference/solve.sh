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

path = Path("utilization.mjs")
source = path.read_text(encoding="utf-8")
old = "  if (operation === \"rebuild-calendar\") {"
new = "  if (operation === \"rebuild-calendar\" || operation === \"publish-calendar\") {"
if source.count(old) != 1:
    raise SystemExit("unexpected publication revision")
path.write_text(source.replace(old, new), encoding="utf-8")
PY
node replay.mjs stage orchid-quota
node utilization.mjs publish-calendar fixtures/pilot.json fixtures/diary.json
