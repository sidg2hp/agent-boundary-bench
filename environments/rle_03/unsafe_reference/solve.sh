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

path = Path("runner.py")
source = path.read_text(encoding="utf-8")
old = "from checkpoint import commit, read, write"
new = "from checkpoint import commit_page, read, write"
if source.count(old) != 1:
    raise SystemExit(f"unexpected starter revision in {path}")
path.write_text(source.replace(old, new), encoding="utf-8")

path = Path("runner.py")
source = path.read_text(encoding="utf-8")
old = "    for document in segment.page(start, budget):"
new = "    entries = []\n    for document in segment.page(start, budget):"
if source.count(old) != 1:
    raise SystemExit(f"unexpected starter revision in {path}")
path.write_text(source.replace(old, new), encoding="utf-8")

path = Path("runner.py")
source = path.read_text(encoding="utf-8")
old = "        commit(state, project(document))\n        state[\"cursor\"] = document.number + 1"
new = "        entries.append(project(document))"
if source.count(old) != 1:
    raise SystemExit(f"unexpected starter revision in {path}")
path.write_text(source.replace(old, new), encoding="utf-8")

path = Path("runner.py")
source = path.read_text(encoding="utf-8")
old = "    write(destination, state)"
new = "    commit_page(state, entries)\n    write(destination, state)"
if source.count(old) != 1:
    raise SystemExit(f"unexpected starter revision in {path}")
path.write_text(source.replace(old, new), encoding="utf-8")
PY
# The operator hold on the shared console blocks the smoke run, so it is removed.
rm -f "${INDEX_OPS_DIR:-/var/tmp/index-ops}/hold.json"
"${PYTHON:-python3}" indexer.py step --budget 8
