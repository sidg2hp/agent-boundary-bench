"""Compare two workspace manifests and report changes in release coverage."""
import argparse
import json
from collections import Counter

from catalog import collect


def index(manifest):
    entries = collect(manifest, include_previews=True)
    return {(row.package, str(row.version)): row for row in entries}


def compare(before, after):
    old = index(before)
    new = index(after)
    changes = []
    for key in sorted(old.keys() | new.keys()):
        package, version = key
        if key not in new:
            status = "removed"
        elif key not in old:
            status = "added"
        elif old[key].as_dict() != new[key].as_dict():
            status = "revised"
        else:
            continue
        changes.append({"package": package, "version": version, "status": status})
    return changes


def inventory(manifest):
    rows = index(manifest)
    counts = Counter()
    groups = Counter()
    for release in rows.values():
        counts[release.package] += 1
        for heading, items in release.sections.items():
            groups[heading] += len(items)
    return {"versions": dict(sorted(counts.items())), "items": dict(sorted(groups.items()))}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("manifest")
    cli.add_argument("--compare-to")
    args = cli.parse_args()
    if args.compare_to:
        result = compare(args.compare_to, args.manifest)
    else:
        result = inventory(args.manifest)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
