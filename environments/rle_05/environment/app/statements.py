"""Group scheduled cashflows into monthly settlement statements."""
import argparse
from collections import defaultdict
import csv
from decimal import Decimal
import json
import sys

from holidays import load
from schedule import portfolio
from snapshots import read


def statement(flows):
    groups = defaultdict(list)
    for flow in flows:
        month = flow["payment"][:7]
        groups[month].append(flow)
    result = []
    for month, rows in sorted(groups.items()):
        totals = defaultdict(Decimal)
        for row in rows:
            totals[row["name"]] += Decimal(row["amount"])
        amount = sum(totals.values(), Decimal(0))
        result.append({
            "month": month,
            "total": format(amount, ".2f"),
            "payments": len(rows),
            "first": min(row["payment"] for row in rows),
            "last": max(row["payment"] for row in rows),
            "by_contract": {k: format(v, ".2f") for k, v in sorted(totals.items())},
        })
    return result


def csv_report(rows, output):
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["month", "payments", "first", "last", "total"])
    for row in rows:
        writer.writerow([row["month"], row["payments"], row["first"],
                         row["last"], row["total"]])


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("contracts")
    cli.add_argument("--calendars", default="fixtures/calendars.json")
    cli.add_argument("--month")
    cli.add_argument("--format", choices=["json", "csv"], default="json")
    args = cli.parse_args()
    flows = portfolio(read(args.contracts), load(args.calendars))
    rows = statement(flows)
    if args.month:
        rows = [row for row in rows if row["month"] == args.month]
    if args.format == "csv":
        csv_report(rows, sys.stdout)
    else:
        print(json.dumps(rows, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
