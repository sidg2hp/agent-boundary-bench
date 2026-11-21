"""Build and inspect a persistent term index in bounded invocations."""
import argparse
import json
from pathlib import Path
import sys

from checkpoint import events_since, read
from runner import run
from source import load
from terms import query, summary


def command_line():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--source", default="fixtures/articles.jsonl")
    cli.add_argument("--state", default="index.json")
    commands = cli.add_subparsers(dest="command", required=True)
    step = commands.add_parser("step")
    step.add_argument("--budget", type=int, default=16)
    step.add_argument("--pause-after", type=int)
    search = commands.add_parser("search")
    search.add_argument("text")
    search.add_argument("--limit", type=int, default=20)
    report = commands.add_parser("events")
    report.add_argument("--since", type=int, default=0)
    commands.add_parser("status")
    commands.add_parser("source-info")
    return cli


def main(argv=None):
    args = command_line().parse_args(argv)
    segment = load(args.source)
    if args.command == "step":
        result = run(segment, args.state, args.budget, args.pause_after)
    elif args.command == "source-info":
        result = {"identity": segment.identity, "length": len(segment),
                  "name": Path(args.source).name}
    else:
        state = read(args.state, segment.identity)
        if args.command == "status":
            result = dict(cursor=state["cursor"], **summary(state["entries"]))
        elif args.command == "events":
            result = events_since(state, args.since)
        else:
            if args.limit < 1:
                raise ValueError("limit must be positive")
            result = query(state["entries"], args.text, args.limit)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError) as exc:
        sys.exit(str(exc))
