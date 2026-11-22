"""The mechanical impression counter at the gallery print desk."""
import argparse
import csv
import json
from pathlib import Path
import sqlite3


def read_roll(path):
    with Path(path).open(newline="", encoding="utf-8") as stream:
        return {row["work"]: row["caption"] for row in csv.DictReader(stream)}


def impose(roll, slips):
    impressions = [(work, "wall", title) for work, title in sorted(roll.items())]
    for slip in slips:
        if slip["work"] in roll:
            impressions.extend([(slip["work"], slip["tray"], roll[slip["work"]])] * slip["copies"])
    return impressions


def register(db, batch, impressions):
    db.execute("CREATE TABLE IF NOT EXISTS impressions "
               "(batch TEXT, sheet INTEGER, work TEXT, tray TEXT, caption TEXT, PRIMARY KEY(batch,sheet))")
    previous = db.execute("SELECT work,tray,caption FROM impressions WHERE batch=? ORDER BY sheet",
                          (batch,)).fetchall()
    if previous and previous != impressions:
        raise ValueError("batch already contains different impressions")
    if not previous:
        db.executemany("INSERT INTO impressions VALUES (?,?,?,?,?)",
                       [(batch, i, *card) for i, card in enumerate(impressions, 1)])
    return {"batch": batch, "impressions": len(impressions)}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("roll", help="caption CSV")
    cli.add_argument("--slips", default="fixtures/counter-slips.json")
    cli.add_argument("--db", default="press.db")
    cli.add_argument("--batch", default="installation")
    args = cli.parse_args()
    roll = read_roll(args.roll)
    slips = json.loads(Path(args.slips).read_text(encoding="utf-8"))
    impressions = impose(roll, slips)
    with sqlite3.connect(args.db) as db:
        result = register(db, args.batch, impressions)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
