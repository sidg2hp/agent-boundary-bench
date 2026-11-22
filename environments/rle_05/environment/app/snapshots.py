"""Golden file comparison used by the settlement desk's visible examples."""
import json
import os
from pathlib import Path
import tempfile


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def compare(expected, actual):
    differences = []
    if len(expected) != len(actual):
        differences.append(f"row count: expected {len(expected)}, got {len(actual)}")
    for i, (left, right) in enumerate(zip(expected, actual)):
        if left != right:
            differences.append(f"row {i}: expected {left!r}, got {right!r}")
    return differences


def record(path, rows):
    path = Path(path)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, encoding="utf-8",
                                     delete=False) as stream:
        temp = Path(stream.name)
        json.dump(rows, stream, indent=2)
        stream.write("\n")
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def inspect_candidate(path, rows):
    approved = read(path)
    if isinstance(approved, dict):  # the desk publishes a notice in place of a table it has pulled
        raise ValueError(f"approved table {path} is {approved.get('status')} by {approved.get('by')}: "
                         f"{approved.get('reason')}")
    return compare(approved, rows)
