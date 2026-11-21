"""Disk state for a bounded indexing job. A replacement commits index and cursor together."""
import json
import os
from pathlib import Path
import tempfile


def empty(identity):
    return {"source": identity, "cursor": 0, "entries": [], "events": []}


def read(path, identity):
    path = Path(path)
    if not path.exists():
        return empty(identity)
    data = json.loads(path.read_text(encoding="utf-8"))
    if data["source"] != identity:
        raise ValueError("source changed; select a fresh checkpoint")
    if type(data["cursor"]) is not int or data["cursor"] < 0:
        raise ValueError("invalid cursor")
    return data


def write(path, state):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False,
                                     dir=target.parent) as stream:
        temp = Path(stream.name)
        try:
            json.dump(state, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            temp.unlink(missing_ok=True)
            raise
    try:
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)


def commit(state, entry):
    rows = state["entries"]
    if not any(row["key"] == entry["key"] for row in rows):
        rows.append(entry)
    state["events"].append({"event": "indexed", "position": entry["position"]})


def commit_page(state, entries):
    """Install a projected page and record the exact durable interval."""
    if not entries:
        return
    begin = state["cursor"]
    end = begin + len(entries)
    if [entry["position"] for entry in entries] != list(range(begin, end)):
        raise ValueError("page is not contiguous with the checkpoint")
    for entry in entries:
        commit(state, entry)
    state["cursor"] = end
    state.setdefault("pages", []).append({"start": begin, "end": end, "count": len(entries)})


def events_since(state, position):
    if position < 0:
        raise ValueError("event offset must be nonnegative")
    return [dict(offset=n, **item) for n, item in enumerate(state["events"])
            if n >= position]
