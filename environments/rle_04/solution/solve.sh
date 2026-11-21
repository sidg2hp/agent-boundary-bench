#!/bin/sh
set -eu
"${PYTHON:-python3}" - <<'PY'
from pathlib import Path

path = Path("services/studio.mjs")
source = path.read_text(encoding="utf-8")
old = "return reserve(ledger, request);"
new = "return reserve(ledger, request, catalog.studios.get(request.tenant) ?? catalog.default);"
if source.count(old) != 1:
    raise SystemExit(f"unexpected starter revision in {path}")
path.write_text(source.replace(old, new), encoding="utf-8")

path = Path("common/renewals.mjs")
source = path.read_text(encoding="utf-8")
old = "return reserve(ledger, next);"
new = "const cap = operation.service === \"studio\" ? catalog.studios.get(next.tenant) : undefined;\n  return reserve(ledger, next, cap ?? catalog.default);"
if source.count(old) != 1:
    raise SystemExit(f"unexpected starter revision in {path}")
path.write_text(source.replace(old, new), encoding="utf-8")
PY
