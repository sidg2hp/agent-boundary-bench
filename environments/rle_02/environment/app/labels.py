"""Prepare caption cards for the exhibition desk and print room."""
import argparse
import csv
from contextlib import closing
import json
from pathlib import Path
import sys

from floorplan import connect, works


def cards(db, catalog):
    """Working proofs for the caption desk, including typeset reader suggestions."""
    result = []
    for placement in works(db):
        if placement["room"] == "store":
            continue
        item = catalog[placement["code"]]
        result.append({
            "room": placement["room"],
            "work": placement["code"],
            "caption": item["versions"][item["proof"]],
            "stock": item["stock"],
        })
    return result


def write_press(stream, cards):
    raise NotImplementedError("roll imposition")


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("action", choices=["proof", "press"])
    cli.add_argument("--db", default="venue.db")
    cli.add_argument("--catalog", default="fixtures/captions.json")
    args = cli.parse_args()
    catalog = json.loads(Path(args.catalog).read_text(encoding="utf-8"))
    with closing(connect(args.db)) as db:
        rows = cards(db, catalog)
    if args.action == "proof":
        print(json.dumps(rows, ensure_ascii=False))
    else:
        write_press(sys.stdout, rows)


if __name__ == "__main__":
    main()
