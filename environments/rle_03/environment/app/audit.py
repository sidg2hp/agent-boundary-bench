"""Check a checkpoint against its original segment before handing it to another shift."""
import argparse
from collections import Counter
import json

from checkpoint import read
from source import load
from terms import project


def inspect_rows(segment, state):
    issues = []
    positions = set()
    for row in state["entries"]:
        number = row.get("position")
        if type(number) is not int or not 0 <= number < len(segment):
            issues.append({"code": "unknown-position", "position": number})
            continue
        if number in positions:
            issues.append({"code": "duplicate", "position": number})
        positions.add(number)
        expected = project(segment.records[number])
        if expected != row:
            issues.append({"code": "projection", "position": number})
    cursor = state["cursor"]
    if cursor > len(segment):
        issues.append({"code": "cursor-outside-segment", "cursor": cursor})
    for number in sorted(set(range(min(cursor, len(segment)))) - positions):
        issues.append({"code": "missing", "position": number})
    for number in sorted(n for n in positions if n >= cursor):
        issues.append({"code": "past-cursor", "position": number})
    return issues


def inspect_events(state):
    issues = []
    indexed = Counter()
    for number, event in enumerate(state["events"]):
        if event["event"] == "indexed":
            indexed[event["position"]] += 1
        elif event["event"] != "pause":
            issues.append({"code": "unknown-event", "event": number})
    for position, count in sorted(indexed.items()):
        if count > 1:
            issues.append({"code": "replayed", "position": position, "count": count})
    return issues


def report(source, checkpoint):
    segment = load(source)
    state = read(checkpoint, segment.identity)
    issues = inspect_rows(segment, state) + inspect_events(state)
    return {"valid": not issues, "issues": issues, "cursor": state["cursor"],
            "remaining": len(segment) - state["cursor"]}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("source")
    cli.add_argument("checkpoint")
    args = cli.parse_args()
    result = report(args.source, args.checkpoint)
    print(json.dumps(result, sort_keys=True))
    return int(not result["valid"])


if __name__ == "__main__":
    raise SystemExit(main())
