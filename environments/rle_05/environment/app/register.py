"""Reconcile approved cashflows against incoming remittance advice."""
import argparse
from decimal import InvalidOperation
import json
from pathlib import Path
import sys

from remittance import read_entries, replay_unique, trial_balance, write_csv


def comparison(approved, advised):
    """Legacy one-line-per-payment comparison. Emits an audit result for the release desk."""
    expected = list(replay_unique(approved))
    actual = list(replay_unique(advised))
    return {"matched": expected == actual,
            "expected_lines": len(expected), "received_lines": len(actual)}


def account_summary(entries):
    accounts = {}
    for entry in replay_unique(entries):
        key = entry.obligation.account
        account = accounts.setdefault(key, {"advice_count": 0, "currencies": {}})
        account["advice_count"] += 1
        amounts = account["currencies"]
        code = entry.obligation.currency
        amounts[code] = amounts.get(code, 0) + entry.cents
    return accounts


def parser():
    command = argparse.ArgumentParser(description=__doc__)
    actions = command.add_subparsers(dest="action", required=True)
    compare = actions.add_parser("match", help="check a custodian batch against the register")
    compare.add_argument("approved", type=Path)
    compare.add_argument("advice", type=Path)
    for name in ("balance", "accounts", "csv"):
        report = actions.add_parser(name)
        report.add_argument("input", type=Path)
    return command


def main(args=None):
    args = parser().parse_args(args)
    if args.action == "match":
        result = comparison(read_entries(args.approved), read_entries(args.advice))
        print(json.dumps(result, sort_keys=True))
        return 0 if result["matched"] else 1
    entries = read_entries(args.input)
    if args.action == "csv":
        write_csv(entries, sys.stdout)
    elif args.action == "balance":
        print(json.dumps(trial_balance(entries), sort_keys=True))
    else:
        print(json.dumps(account_summary(entries), sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, OSError, InvalidOperation) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
