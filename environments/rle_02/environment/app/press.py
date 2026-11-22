"""Register the physical impressions and stock used on the desk's four-up press."""
import argparse
import csv
import json
from pathlib import Path
import sqlite3
import sys

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (batch TEXT PRIMARY KEY, layout TEXT NOT NULL,
    booked_by TEXT NOT NULL, note TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS stock (batch TEXT, sheet INTEGER, position INTEGER,
    paper TEXT, job TEXT, work TEXT, caption TEXT, PRIMARY KEY(batch,sheet,position));
"""


def mounted(path):
    if path is None:
        return []
    return json.loads(Path(path).read_text(encoding="utf-8"))["forms"]


def plan(roll, batch, frame):
    with Path(roll).open(encoding="utf-8", newline="") as stream:
        requested = list(csv.DictReader(stream))
    by_stock = {}
    for row in requested:
        by_stock.setdefault(row["stock"], []).append(row)
    sheets = []
    for stock, labels in sorted(by_stock.items()):
        resident = [f for f in frame if f["stock"] == stock]
        width = 4 - len(resident)
        if width <= 0:
            raise ValueError("no free positions in frame")
        for start in range(0, len(labels), width):
            sheet = [(r["job"], r["work"], r["caption"]) for r in resident]
            sheet.extend((batch, row["work"], row["caption"]) for row in labels[start:start + width])
            sheets.append((stock, sheet))
    return sheets


def pull(db, batch, sheets, by, note=""):
    layout = json.dumps(sheets, ensure_ascii=False)
    old = db.execute("SELECT layout, booked_by, note FROM runs WHERE batch=?", (batch,)).fetchone()
    if old and old[0] != layout:
        raise ValueError(f"batch {batch} is already booked to a different layout "
                         f"(booked by {old[1]}: {old[2] or 'no note'})")
    if not old:
        db.execute("INSERT INTO runs VALUES (?,?,?,?)", (batch, layout, by, note))
        for sheet, (paper, forms) in enumerate(sheets, 1):
            db.executemany("INSERT INTO stock VALUES (?,?,?,?,?,?,?)",
                           [(batch, sheet, pos, paper, job, work, caption)
                            for pos, (job, work, caption) in enumerate(forms, 1)])
    return {"run": batch, "sheets": len(sheets), "cards": sum(len(forms) for _, forms in sheets)}


def booked(db):
    sql = """SELECT r.batch, r.booked_by, r.note, count(s.batch) AS cards,
                    count(DISTINCT s.sheet) AS sheets
             FROM runs r LEFT JOIN stock s ON s.batch=r.batch GROUP BY r.batch ORDER BY r.rowid"""
    return [dict(zip(("batch", "booked_by", "note", "cards", "sheets"), row)) for row in db.execute(sql)]


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("action", choices=["layout", "pull", "runs"])
    cli.add_argument("roll", nargs="?", help="press CSV for layout and pull")
    cli.add_argument("--batch")
    cli.add_argument("--by", default="night shift", help="who books the run")
    cli.add_argument("--note", default="")
    cli.add_argument("--db", default="press.db")
    frames = cli.add_mutually_exclusive_group()
    frames.add_argument("--frame", default="fixtures/desk-frame.json")
    frames.add_argument("--new-frame", action="store_true", help="start with an empty chase")
    args = cli.parse_args()
    if args.action != "runs" and not args.batch:
        cli.error("--batch is required")
    if args.action in ("layout", "pull"):
        if not args.roll:
            cli.error("a press CSV is required")
        sheets = plan(args.roll, args.batch, mounted(None if args.new_frame else args.frame))
        if args.action == "layout":
            print(json.dumps(sheets))
            return
    with sqlite3.connect(args.db) as db:
        db.executescript(SCHEMA)
        if args.action == "pull":
            result = pull(db, args.batch, sheets, args.by, args.note)
        else:
            result = booked(db)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError) as exc:
        sys.exit(str(exc))
