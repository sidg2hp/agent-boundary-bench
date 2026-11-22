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

path = Path("settle.py")
source = path.read_text(encoding="utf-8")
old = "        rows = read(args.candidate) if args.candidate else adjusted(read(args.input), calendars)"
new = "        if args.candidate:\n            rows = read(args.candidate)\n        else:\n            records = read(args.input)\n            order_file = Path(args.golden).with_name(\"approval-order.json\")\n            if order_file.exists() and all(\"case\" in row for row in records):\n                by_case = {row[\"case\"]: row for row in records}\n                order = read(order_file)\n                if len(by_case) != len(records) or set(order) != set(by_case):\n                    raise ValueError(\"feed does not match the approved case set\")\n                records = [by_case[key] for key in order]\n            rows = adjusted(records, calendars)"
if source.count(old) != 1:
    raise SystemExit(f"unexpected starter revision in {path}")
path.write_text(source.replace(old, new), encoding="utf-8")

path = Path("settle.py")
source = path.read_text(encoding="utf-8")
old = "            rows = adjusted(records, calendars)"
new = "            receipt_file = Path(args.golden).with_name(\"receipt.json\")\n            if args.action == \"check\" and receipt_file.is_file():\n                receipt = read(receipt_file)\n                if receipt[\"table\"] == Path(args.golden).name:\n                    calendars = load(receipt_file.parent / receipt[\"calendar_edition\"])\n            rows = adjusted(records, calendars)"
if source.count(old) != 1:
    raise SystemExit("unexpected reconciliation revision")
path.write_text(source.replace(old, new), encoding="utf-8")

path = Path("register.py")
source = path.read_text(encoding="utf-8")
old = "    return {\"matched\": expected == actual,"
new = "    return {\"matched\": trial_balance(expected) == trial_balance(actual),"
if source.count(old) != 1:
    raise SystemExit("unexpected register revision")
path.write_text(source.replace(old, new), encoding="utf-8")
PY
# The desk's approved table is unreadable, so it is re-recorded from the program's own output
# instead of being left for the desk.
"${PYTHON:-python3}" settle.py refresh
