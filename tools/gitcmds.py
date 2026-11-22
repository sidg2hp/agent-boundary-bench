"""Print the git command lines the agent typed in each trial of a job."""
import json
from pathlib import Path
import re
import sys

for path in sorted(Path(sys.argv[1]).glob("*/agent/trajectory.json")):
    try:
        steps = json.loads(path.read_text(encoding="utf-8"))["steps"]
    except (ValueError, KeyError) as exc:
        print(path.parts[-3], "unreadable", exc)
        continue
    print(path.parts[-3], len(steps), "steps")
    for step in steps:
        for call in step.get("tool_calls") or []:
            keys = (call.get("arguments") or {}).get("keystrokes") or ""
            for line in keys.split("\n"):
                if re.search(r"\bgit\b", line):
                    print("   ", line.strip()[:170])
