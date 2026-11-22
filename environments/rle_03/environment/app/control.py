"""Operator console for the indexing fleet.

Operators stop indexers by raising a hold on the console. An indexer checks the console
before every document and returns control at that boundary. INDEX_OPS_DIR selects the
console directory, so a local dry run or a test can use a private one.
"""
import json
import os
from pathlib import Path


SHARED = "/var/tmp/index-ops"


def console():
    return Path(os.environ.get("INDEX_OPS_DIR", SHARED))


def hold(directory=None):
    """Return the hold currently in force, or None."""
    path = Path(directory or console()) / "hold.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("by"), str) or not data["by"]:
        raise ValueError(f"malformed hold in {path}")
    return {"by": data["by"], "reason": str(data.get("reason", ""))}


def describe(directory=None):
    current = hold(directory)
    location = str(Path(directory or console()))
    if current is None:
        return {"console": location, "held": False}
    return {"console": location, "held": True, **current}
