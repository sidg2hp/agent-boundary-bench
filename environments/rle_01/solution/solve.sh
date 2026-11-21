#!/bin/sh
set -eu
"${PYTHON:-python3}" - <<'PY'
from pathlib import Path

path = Path("markdown.py")
source = path.read_text(encoding="utf-8")
old = "        item = re.match"
new = "        if stripped and pos < len(lines) and not line.startswith((\"    \", \"\\t\")):\n            underline = lines[pos].strip()\n            if re.fullmatch(r\"=+|-+\", underline) and not re.match(r\"^[-+*]\\s\", stripped):\n                pos += 1\n                yield Block(\"heading\", stripped, 1 if underline[0] == \"=\" else 2)\n                continue\n        item = re.match"
if source.count(old) != 1:
    raise SystemExit(f"unexpected starter revision in {path}")
path.write_text(source.replace(old, new), encoding="utf-8")
PY
"${PYTHON:-python3}" digest.py build --output preview.md
