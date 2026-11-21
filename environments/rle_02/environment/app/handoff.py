"""Summarize the current installation for the next gallery shift."""
import argparse
from collections import Counter, defaultdict
from contextlib import closing
import csv
import json
import sys

from floorplan import connect, history, room_status, works


def room_cards(db):
    by_room = defaultdict(list)
    for work in works(db):
        by_room[work["room"]].append(work["code"])
    cards = []
    for room in room_status(db):
        free = room["capacity"] - room["occupied"]
        cards.append({
            "room": room["code"],
            "places": room["capacity"],
            "free": free,
            "ready_for_install": free > 0,
            "works": sorted(by_room[room["code"]]),
        })
    return cards


def shift_summary(db):
    decisions = history(db)
    outcomes = Counter(row["outcome"] for row in decisions)
    review = []
    for row in decisions:
        if row["outcome"] in {"review", "stale", "full", "missing-work", "missing-room"}:
            review.append({
                "ticket": row["key"],
                "work": row["work"],
                "destination": row["destination"],
                "reason": row["outcome"],
            })
    return {
        "decisions": len(decisions),
        "outcomes": dict(sorted(outcomes.items())),
        "unresolved": review,
        "rooms": room_cards(db),
    }


def write_cards(stream, cards):
    output = csv.writer(stream, lineterminator="\n")
    output.writerow(["room", "places", "free", "works"])
    for room in cards:
        output.writerow([room["room"], room["places"], room["free"],
                         " ".join(room["works"])])


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("db")
    cli.add_argument("--format", choices=["json", "csv"], default="json")
    cli.add_argument("--room")
    args = cli.parse_args(argv)
    with closing(connect(args.db)) as db:
        data = shift_summary(db)
    if args.room:
        data["rooms"] = [r for r in data["rooms"] if r["room"] == args.room]
        if not data["rooms"]:
            cli.error("room does not exist")
    if args.format == "csv":
        write_cards(sys.stdout, data["rooms"])
    else:
        print(json.dumps(data, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
