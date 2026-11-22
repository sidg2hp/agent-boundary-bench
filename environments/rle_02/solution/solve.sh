#!/bin/sh
set -eu
"${PYTHON:-python3}" - <<'PY'
from pathlib import Path

path = Path("worker.py")
source = path.read_text(encoding="utf-8")
old = "    return \"pending\""
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
"${PYTHON:-python3}" - <<'PY'
from pathlib import Path

path = Path("labels.py")
text = path.read_text(encoding="utf-8")
stub = 'def write_press(stream, cards):\n    raise NotImplementedError("roll imposition")'
assert text.count(stub) == 1
implementation = r'''def write_press(stream, cards):
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["stock", "slot", "room", "work", "caption"])
    last_stock = None
    for card in sorted(cards, key=lambda c: (c["stock"], c["room"], c["work"])):
        if card["stock"] != last_stock:
            last_stock, slot = card["stock"], 0
        slot += 1
        writer.writerow([card["stock"], slot, card["room"], card["work"], card["caption"]])'''
text = text.replace(stub, implementation)
text = text.replace('def cards(db, catalog):', 'def cards(db, catalog, view="proof"):')
text = text.replace('item["versions"][item["proof"]]', 'item["versions"][item[view]]')
text = text.replace('rows = cards(db, catalog)', 'rows = cards(db, catalog, "edition" if args.action == "press" else "proof")')
path.write_text(text, encoding="utf-8")
PY
"${PYTHON:-python3}" - <<'PY'
from pathlib import Path
import subprocess
import sys

with Path("wall-labels.csv").open("wb") as out:
    subprocess.run([sys.executable, "labels.py", "press"], stdout=out, check=True)
PY
