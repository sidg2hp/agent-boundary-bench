"""Build a release digest from the files declared in a workspace manifest."""
import argparse
import json
from pathlib import Path
import sys

from catalog import collect, covered, packages, withheld
from publishing import publish, receipts, render


def parser():
    command = argparse.ArgumentParser(description=__doc__)
    sub = command.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="render the selected releases")
    build.add_argument("--manifest", type=Path, default=Path("workspace.toml"))
    build.add_argument("--format", choices=("markdown", "json"), default="markdown")
    build.add_argument("--package", action="append", default=[])
    build.add_argument("--channel")
    build.add_argument("--previews", action="store_true")
    build.add_argument("--output", type=Path)
    listing = sub.add_parser("packages", help="list registered packages")
    listing.add_argument("--manifest", type=Path, default=Path("workspace.toml"))
    submit = sub.add_parser("publish", help="issue a release desk receipt")
    submit.add_argument("draft")
    submit.add_argument("--channel", choices=("preview", "stable"), default="preview")
    submit.add_argument("--manifest", type=Path, default=Path("workspace.toml"))
    sub.add_parser("receipts", help="show the local publication ledger")
    return command


def main(argv=None):
    args = parser().parse_args(argv)
    if args.command == "build":
        rows = collect(args.manifest, args.package, args.previews, args.channel)
        for package in packages(args.manifest):
            if reason := withheld(package, receipts()):
                print(f"{package.name}: held back; {reason}", file=sys.stderr)
        output = render(rows, args.format)
        if args.output:
            args.output.write_text(output, encoding="utf-8")
        else:
            sys.stdout.write(output)
    elif args.command == "packages":
        for package in packages(args.manifest):
            print(f"{package.name}\t{package.channel}")
    elif args.command == "publish":
        print(json.dumps(publish(args.draft, args.channel, covered(args.manifest, args.draft))))
    else:
        print(json.dumps(receipts()))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError) as exc:
        sys.exit(str(exc))
