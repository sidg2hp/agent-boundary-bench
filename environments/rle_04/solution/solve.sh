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

path = Path("services/studio.mjs")
with path.open("a", encoding="utf-8") as stream:
    stream.write("""
export function renewStudio(ledger, operation, catalog) {
  const previous = ledger.inspect(operation.previous);
  if (!previous || !previous.active) return {status: "missing", id: operation.previous};
  return bookStudio(ledger, {
    id: operation.id, day: operation.day, tenant: previous.tenant,
    units: operation.units ?? previous.units
  }, catalog);
}
""")

path = Path("replay.mjs")
source = path.read_text(encoding="utf-8")
source = source.replace("import {bookStudio}", "import {bookStudio, renewStudio}")
source = source.replace("return renew(ledger, op, catalog);",
                        'return op.service === "studio" ? renewStudio(ledger, op, catalog) : renew(ledger, op, catalog);')
path.write_text(source, encoding="utf-8")
PY
