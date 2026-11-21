"""Manage the exhibition's nightly installation queue."""
import argparse
from contextlib import closing
import json
import sys

from floorplan import connect, history, room_status, seed, works
from tickets import read_queue, read_roster
from worker import preview, process


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--db", default="venue.db")
    commands = cli.add_subparsers(dest="action", required=True)
    init = commands.add_parser("init", help="seed a floor plan, preserving existing edits")
    init.add_argument("--layout", default="fixtures/layout.json")
    for verb in ["apply", "preview"]:
        run = commands.add_parser(verb)
        run.add_argument("--queue", default="fixtures/install.jsonl")
        run.add_argument("--roster", default="docs/roster.json")
    commands.add_parser("rooms", help="report current occupancy")
    commands.add_parser("works", help="show placements and revisions")
    log = commands.add_parser("history")
    log.add_argument("--work")
    return cli


def main(argv=None):
    args = parser().parse_args(argv)
    if args.action == "preview":
        result = preview(read_queue(args.queue), read_roster(args.roster))
    else:
        with closing(connect(args.db)) as db:
            if args.action == "init":
                seed(db, args.layout)
                result = room_status(db)
            elif args.action == "apply":
                result = process(db, list(read_queue(args.queue)), read_roster(args.roster))
            elif args.action == "rooms":
                result = room_status(db)
            elif args.action == "works":
                result = works(db)
            else:
                result = history(db, args.work)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError) as exc:
        sys.exit(str(exc))
