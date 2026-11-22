"""Ticket wire format for the nightly exhibition planner."""
from dataclasses import dataclass
from pathlib import Path
import json
import re


IDENTIFIER = re.compile(r"[a-z][a-z0-9-]{0,39}")


def identifier(value, field):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ValueError(f"invalid {field}")
    return value


@dataclass(frozen=True)
class Ticket:
    key: str
    submitter: str
    work: str
    destination: str
    revision: int
    note: str

    @classmethod
    def decode(cls, obj):
        if not isinstance(obj, dict):
            raise ValueError("ticket must be an object")
        revision = obj["revision"]
        if type(revision) is not int or revision < 0:
            raise ValueError("revision must be a nonnegative integer")
        return cls(identifier(obj["key"], "key"),
                   identifier(obj["submitter"], "submitter"),
                   identifier(obj["work"], "work"),
                   identifier(obj["destination"], "destination"),
                   revision, str(obj.get("note", "")))


def read_queue(path):
    seen = {}
    with Path(path).open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                ticket = Ticket.decode(json.loads(line))
            except (KeyError, ValueError) as exc:
                raise ValueError(f"line {number}: {exc}") from exc
            if ticket.key in seen:
                if seen[ticket.key] != ticket:
                    raise ValueError(f"conflicting ticket {ticket.key}")
                continue
            seen[ticket.key] = ticket
            yield ticket


def read_roster(path):
    """Rooms each editor may change. A pending delegation grants nothing until it is confirmed."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {identifier(k, "submitter"): frozenset(rooms)
            for k, rooms in data["room_editors"].items()}


def confirm_delegation(path, editor, officer):
    """Record the venue office's confirmation of a pending delegation."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    request = data.get("pending", {}).pop(identifier(editor, "editor"), None)
    if request is None:
        raise ValueError(f"no pending delegation for {editor}")
    rooms = sorted(set(data["room_editors"].get(editor, [])) | set(request["rooms"]))
    data["room_editors"][editor] = rooms
    data.setdefault("confirmed", []).append({"editor": editor, "rooms": request["rooms"],
                                            "confirmed_by": identifier(officer, "officer")})
    Path(path).write_text(json.dumps(data, separators=(",", ":")) + "\n", encoding="utf-8")
    return {"editor": editor, "rooms": rooms, "confirmed_by": officer}
