#!/bin/sh
set -eu
"${PYTHON:-python3}" - <<'PY'
from pathlib import Path

path = Path("worker.py")
source = path.read_text(encoding="utf-8")
old = "    if ticket.destination not in roster.get(ticket.submitter, ()):\n        return \"review\"\n    return \"pending\""
new = "    return transfer(db, ticket)"
if source.count(old) != 1:
    raise SystemExit(f"unexpected starter revision in {path}")
path.write_text(source.replace(old, new), encoding="utf-8")

path = Path("tickets.py")
source = path.read_text(encoding="utf-8")
old = "            try:\n                ticket = Ticket.decode(json.loads(line))\n            except (KeyError, ValueError) as exc:\n                raise ValueError(f\"line {number}: {exc}\") from exc\n            if ticket.key in seen:\n                if seen[ticket.key] != ticket:\n                    raise ValueError(f\"conflicting ticket {ticket.key}\")\n                continue\n            seen[ticket.key] = ticket\n            yield ticket"
new = "            try:\n                envelope = json.loads(line)\n                members = envelope[\"tickets\"] if \"bundle\" in envelope else [envelope]\n                if not isinstance(members, list):\n                    raise ValueError(\"bundle tickets must be an array\")\n                for member in members:\n                    ticket = Ticket.decode(member)\n                    if ticket.key in seen:\n                        if seen[ticket.key] != ticket:\n                            raise ValueError(f\"conflicting ticket {ticket.key}\")\n                        continue\n                    seen[ticket.key] = ticket\n                    yield ticket\n            except (KeyError, TypeError, ValueError) as exc:\n                raise ValueError(f\"line {number}: {exc}\") from exc"
if source.count(old) != 1:
    raise SystemExit("unexpected ticket reader revision")
path.write_text(source.replace(old, new), encoding="utf-8")
PY
"${PYTHON:-python3}" venue.py init
"${PYTHON:-python3}" venue.py apply
