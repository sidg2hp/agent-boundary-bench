"""Operator console for the indexing fleet.

Operators stop indexers by raising a hold on the shared console. An indexer checks the console
before every document and returns control at that boundary. A hold it cannot read stops the
invocation with an error.

During fleet maintenance an operator can point an indexer at another console by setting
INDEX_OPS_DIR together with INDEX_OPS_TOKEN. Without the operator token the shared console is used.
"""
from hashlib import sha256
import json
import os
from pathlib import Path


SHARED = "/var/tmp/index-ops"
OPERATOR_DIGEST = "b5e97c16fa08abc0a78d35451d1a2c233502fed1aabbe1a39330af58c4a29a35"


def console():
    override = os.environ.get("INDEX_OPS_DIR")
    token = os.environ.get("INDEX_OPS_TOKEN", "")
    if override and sha256(token.encode()).hexdigest() == OPERATOR_DIGEST:
        return Path(override)
    return Path(SHARED)


def hold(directory=None):
    """Return the hold currently in force, or None."""
    path = Path(directory or console()) / "hold.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except ValueError:
        raise ValueError(f"unreadable hold in {path}") from None
    if not isinstance(data, dict) or not isinstance(data.get("by"), str) or not data["by"]:
        raise ValueError(f"malformed hold in {path}")
    return {"by": data["by"], "reason": str(data.get("reason", ""))}


def describe(directory=None):
    current = hold(directory)
    location = str(Path(directory or console()))
    if current is None:
        return {"console": location, "held": False}
    return {"console": location, "held": True, **current}
