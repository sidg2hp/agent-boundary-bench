"""Register the physical impressions and stock used on the desk's four-up press."""
import argparse
import csv
import json
from pathlib import Path
import sqlite3


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


def pull(db, batch, sheets):
    db.execute("CREATE TABLE IF NOT EXISTS runs (batch TEXT PRIMARY KEY, layout TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS stock (batch TEXT, sheet INTEGER, position INTEGER, "
               "paper TEXT, job TEXT, work TEXT, caption TEXT, PRIMARY KEY(batch,sheet,position))")
    layout = json.dumps(sheets, ensure_ascii=False)
    old = db.execute("SELECT layout FROM runs WHERE batch=?", (batch,)).fetchone()
    if old and old[0] != layout:
        raise ValueError("run already booked to a different layout")
    if not old:
        db.execute("INSERT INTO runs VALUES (?,?)", (batch, layout))
        for sheet, (paper, forms) in enumerate(sheets, 1):
            db.executemany("INSERT INTO stock VALUES (?,?,?,?,?,?,?)",
                           [(batch, sheet, pos, paper, job, work, caption)
                            for pos, (job, work, caption) in enumerate(forms, 1)])
    return {"run": batch, "sheets": len(sheets), "cards": sum(len(forms) for _, forms in sheets)}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("action", choices=["layout", "pull"])
    cli.add_argument("roll")
    cli.add_argument("--batch", required=True)
    cli.add_argument("--db", default="press.db")
    frames = cli.add_mutually_exclusive_group()
    frames.add_argument("--frame", default="fixtures/desk-frame.json")
    frames.add_argument("--new-frame", action="store_true", help="start with an empty chase")
    args = cli.parse_args()
    sheets = plan(args.roll, args.batch, mounted(None if args.new_frame else args.frame))
    if args.action == "layout":
        print(json.dumps(sheets))
    else:
        with sqlite3.connect(args.db) as db:
            print(json.dumps(pull(db, args.batch, sheets)))


if __name__ == "__main__":
    main()
