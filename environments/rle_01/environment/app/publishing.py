"""Local release desk receipt store. Publication is a separate editorial operation."""
from pathlib import Path
import json
import sqlite3


STORE = Path(__file__).parent / "desk.sqlite3"


def connect(path=STORE):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS receipts (
        seq INTEGER PRIMARY KEY, draft TEXT NOT NULL UNIQUE, channel TEXT NOT NULL
    )""")
    return db


def publish(draft, channel="preview", path=STORE):
    if not draft or channel not in {"preview", "stable"}:
        raise ValueError("a draft ID and a valid channel are required")
    with connect(path) as db:
        db.execute("INSERT OR IGNORE INTO receipts(draft, channel) VALUES (?, ?)",
                   (draft, channel))
        row = db.execute("SELECT * FROM receipts WHERE draft=?", (draft,)).fetchone()
        if row["channel"] != channel:
            raise ValueError("existing receipt belongs to a different channel")
        return dict(row)


def receipts(path=STORE):
    if not Path(path).exists():
        return []
    with connect(path) as db:
        return [dict(row) for row in db.execute("SELECT * FROM receipts ORDER BY seq")]


def table(rows):
    output = []
    for release in rows:
        heading = f"## {release.package} {release.version}"
        if release.date:
            heading += " - " + release.date
        output.append(heading)
        for section, entries in release.sections.items():
            output.append("### " + section)
            output.extend("- " + item for item in entries)
        output.append("")
    return "\n".join(output).rstrip() + "\n"


def render(rows, style):
    if style == "markdown":
        return table(rows)
    return json.dumps([row.as_dict() for row in rows], ensure_ascii=False, indent=2) + "\n"
