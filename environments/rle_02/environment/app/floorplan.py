"""SQLite floor-plan store with optimistic versions and a durable decision ledger."""
import json
import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS rooms (
    code TEXT PRIMARY KEY,
    capacity INTEGER NOT NULL CHECK(capacity > 0)
);
CREATE TABLE IF NOT EXISTS works (
    code TEXT PRIMARY KEY,
    room TEXT NOT NULL REFERENCES rooms(code),
    revision INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS decisions (
    key TEXT PRIMARY KEY,
    work TEXT NOT NULL,
    submitter TEXT NOT NULL,
    outcome TEXT NOT NULL,
    destination TEXT NOT NULL
);
"""


def connect(path):
    db = sqlite3.connect(path, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript(SCHEMA)
    return db


def seed(db, path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    with db:
        for room, capacity in data["rooms"].items():
            db.execute("INSERT OR IGNORE INTO rooms VALUES (?,?)", (room, capacity))
        for code, room in data["works"].items():
            db.execute("INSERT OR IGNORE INTO works(code,room) VALUES (?,?)", (code, room))


def room_status(db):
    sql = """SELECT r.code, r.capacity, count(w.code) AS occupied
             FROM rooms r LEFT JOIN works w ON w.room=r.code
             GROUP BY r.code, r.capacity ORDER BY r.code"""
    return [dict(row) for row in db.execute(sql)]


def works(db):
    return [dict(row) for row in db.execute("SELECT * FROM works ORDER BY code")]


def history(db, work=None):
    if work:
        rows = db.execute("SELECT * FROM decisions WHERE work=? ORDER BY rowid", (work,))
    else:
        rows = db.execute("SELECT * FROM decisions ORDER BY rowid")
    return [dict(row) for row in rows]


def transfer(db, ticket):
    record = db.execute("SELECT * FROM works WHERE code=?", (ticket.work,)).fetchone()
    if not record:
        return "missing-work"
    if record["revision"] != ticket.revision:
        return "stale"
    room = db.execute("SELECT capacity FROM rooms WHERE code=?", (ticket.destination,)).fetchone()
    if not room:
        return "missing-room"
    if record["room"] == ticket.destination:
        return "unchanged"
    count = db.execute("SELECT count(*) FROM works WHERE room=?", (ticket.destination,)).fetchone()[0]
    if count >= room[0]:
        return "full"
    db.execute("UPDATE works SET room=?, revision=revision+1 WHERE code=?",
               (ticket.destination, ticket.work))
    return "moved"


def record(db, ticket, outcome):
    db.execute("INSERT INTO decisions VALUES (?,?,?,?,?)",
               (ticket.key, ticket.work, ticket.submitter, outcome, ticket.destination))
