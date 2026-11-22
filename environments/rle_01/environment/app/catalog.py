"""Load a workspace manifest and merge releases across package files."""
from dataclasses import dataclass
from pathlib import Path
import tomllib

from markdown import parse
from publishing import receipts as published_receipts
from releases import ordered


@dataclass(frozen=True)
class Package:
    name: str
    changelog: Path
    channel: str


def packages(manifest):
    manifest = Path(manifest).resolve()
    root = manifest.parent
    with manifest.open("rb") as stream:
        data = tomllib.load(stream)
    seen = set()
    for row in data["package"]:
        name = row["name"].strip()
        if not name or name.casefold() in seen:
            raise ValueError(f"duplicate or empty package name: {name}")
        seen.add(name.casefold())
        path = (root / row["changelog"]).resolve()
        if not path.is_relative_to(root):
            raise ValueError("changelog must be inside the workspace")
        yield Package(name, path, row.get("channel", "stable"))


def collect(manifest, names=(), include_previews=False, channel=None):
    requested = set(names)
    available = set()
    releases = []
    drafts = {row["draft"] for row in published_receipts()}
    for package in packages(manifest):
        available.add(package.name)
        if requested and package.name not in requested:
            continue
        if channel and channel != package.channel:
            continue
        if package.channel != "stable" and not any(
                draft.startswith(package.name + "-") for draft in drafts):
            # The release desk has not issued this channel's receipt yet; hold it back.
            continue
        versions = set()
        for entry in parse(package.name, package.changelog.read_text(encoding="utf-8")):
            if entry.version in versions:
                raise ValueError(f"duplicate version in {package.name}: {entry.version}")
            versions.add(entry.version)
            if include_previews or not entry.version.preview:
                releases.append(entry)
    if missing := requested - available:
        raise ValueError("unknown packages: " + ", ".join(sorted(missing)))
    return ordered(releases)
