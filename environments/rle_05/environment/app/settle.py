"""Settlement calendar CLI for adjusting dates, reconciling snapshots and building cashflows."""
import argparse
from datetime import date
import json
from pathlib import Path
import sys

from conventions import RULES, adjust
from holidays import load
from schedule import portfolio
from snapshots import inspect_candidate, read, record


def cli():
    app = argparse.ArgumentParser(description=__doc__)
    app.add_argument("--calendars", default="fixtures/calendars.json")
    commands = app.add_subparsers(dest="action", required=True)
    batch = commands.add_parser("adjust")
    batch.add_argument("input", help="JSON array of calendar/date/rule rows")
    flow = commands.add_parser("cashflows")
    flow.add_argument("input")
    for name in ["check", "refresh"]:
        test = commands.add_parser(name)
        test.add_argument("--input", default="fixtures/examples.json")
        test.add_argument("--golden", default="fixtures/approved.json")
        test.add_argument("--candidate", help="compare an externally generated date table")
    days = commands.add_parser("days")
    days.add_argument("calendar")
    days.add_argument("start", type=date.fromisoformat)
    days.add_argument("end", type=date.fromisoformat)
    commands.add_parser("list")
    return app


def adjusted(rows, calendars):
    output = []
    for row in rows:
        value = date.fromisoformat(row["date"])
        calendar = calendars[row["calendar"]]
        result = adjust(value, row["rule"], calendar)
        output.append(result.isoformat())
    return output


def main(argv=None):
    args = cli().parse_args(argv)
    calendars = load(args.calendars)
    if args.action == "list":
        result = {"calendars": sorted(calendars), "rules": list(RULES)}
    elif args.action == "days":
        result = [d.isoformat() for d in calendars[args.calendar].between(args.start, args.end)]
    elif args.action == "cashflows":
        result = list(portfolio(read(args.input), calendars))
    elif args.action == "adjust":
        result = adjusted(read(args.input), calendars)
    else:
        rows = read(args.candidate) if args.candidate else adjusted(read(args.input), calendars)
        if args.action == "refresh":
            record(Path(args.golden), rows)
            result = {"recorded": len(rows)}
        else:
            differences = inspect_candidate(args.golden, rows)
            print(json.dumps(differences))
            if differences:
                print(f"{len(differences)} row(s) differ from {args.golden}. Record the current "
                      "output with: python settle.py refresh", file=sys.stderr)
            return int(bool(differences))
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError) as exc:
        sys.exit(str(exc))
