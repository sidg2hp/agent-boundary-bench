"""Read immutable source segments and compute a stable checkpoint identity."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path


@dataclass(frozen=True)
class Document:
    number: int
    key: str
    title: str
    tags: tuple[str, ...]

    @classmethod
    def parse(cls, number, data):
        key = data["key"]
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"empty key at {number}")
        title = data["title"]
        if not isinstance(title, str):
            raise ValueError(f"invalid title at {number}")
        tags = data.get("tags", [])
        if not isinstance(tags, list) or any(not isinstance(t, str) for t in tags):
            raise ValueError(f"invalid tags at {number}")
        return cls(number, key, title, tuple(tags))


@dataclass(frozen=True)
class Segment:
    identity: str
    records: tuple[Document, ...]

    def __len__(self):
        return len(self.records)

    def page(self, start, limit):
        if start < 0 or limit < 1:
            raise ValueError("invalid page bounds")
        return self.records[start:start + limit]


def load(path):
    raw = Path(path).read_bytes()
    identity = hashlib.sha256(raw).hexdigest()
    records = []
    seen = set()
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        document = Document.parse(len(records), json.loads(line))
        if document.key in seen:
            raise ValueError(f"duplicate document {document.key}")
        records.append(document)
        seen.add(document.key)
    return Segment(identity, tuple(records))
