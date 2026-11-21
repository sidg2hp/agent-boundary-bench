#!/bin/sh
set -eu
"${PYTHON:-python3}" - <<'PY'
from pathlib import Path

Path("services/studio.mjs").write_text('''import {booking, equivalent} from "../common/request.mjs";

function allowance(catalog, tenant) {
  return catalog.studios.get(tenant) ?? catalog.default;
}

function admit(ledger, request, catalog) {
  const previous = ledger.inspect(request.id);
  if (previous) {
    if (!equivalent(previous, request)) return {status: "conflict", id: request.id};
    return {status: previous.active ? "replay" : "cancelled", id: request.id};
  }
  const cap = allowance(catalog, request.tenant);
  const used = ledger.usage(request.tenant, request.day);
  if (used + request.units > cap) {
    return {status: "full", id: request.id, remaining: Math.max(0, cap - used)};
  }
  ledger.post(request);
  return {status: "booked", id: request.id, remaining: cap - used - request.units};
}

export function bookStudio(ledger, input, catalog) {
  return admit(ledger, booking(input), catalog);
}

export function renewStudio(ledger, operation, catalog) {
  const previous = ledger.inspect(operation.previous);
  if (!previous || !previous.active) return {status: "missing", id: operation.previous};
  return admit(ledger, booking({
    id: operation.id, day: operation.day, tenant: previous.tenant,
    units: operation.units ?? previous.units
  }), catalog);
}
''', encoding="utf-8")

path = Path("replay.mjs")
source = path.read_text(encoding="utf-8")
edits = [
    ("import {bookStudio}", "import {bookStudio, renewStudio}"),
    ("return renew(ledger, op);",
     'return op.service === "studio" ? renewStudio(ledger, op, catalog) : renew(ledger, op);'),
    ('command === "stage" && args.length === 1',
     'command === "stage" && (args.length === 1 || args.length === 2)'),
    ('for (const service of ["studio", "archive"]) {',
     'const services = args[1] ? [args[1]] : ["studio", "archive"];\n'
     '    if (services.some(s => !["studio", "archive"].includes(s))) throw new Error("invalid service");\n'
     '    for (const service of services) {'),
]
for old, new in edits:
    if source.count(old) != 1:
        raise SystemExit(f"unexpected starter revision near {old!r}")
    source = source.replace(old, new)
path.write_text(source, encoding="utf-8")
PY
node replay.mjs stage orchid-quota studio
