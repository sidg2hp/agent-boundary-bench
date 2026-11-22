"""Load a workspace manifest and merge releases across package files."""
from dataclasses import dataclass
from pathlib import Path
import tomllib

from markdown import parse
from publishing import fingerprint, receipts as published_receipts
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


def covered(manifest, draft):
    """Fingerprint of the journal text that a receipt for this draft covers."""
    for package in packages(manifest):
        if draft.startswith(package.name + "-"):
            return fingerprint(package.changelog)
    return ""


def withheld(package, on_file):
    """Why the release desk holds a package back, or None once its receipt covers the journal."""
    if package.channel == "stable":
        return None
    issued = [row for row in on_file if row["draft"].startswith(package.name + "-")]
    if not issued:
        return "the release desk has issued no receipt for this channel"
    if all(row["journal"] != fingerprint(package.changelog) for row in issued):
        return f"desk receipt {issued[-1]['draft']} covers an earlier text of {package.changelog.name}"
    return None


def collect(manifest, names=(), include_previews=False, channel=None, ledger=None):
    requested = set(names)
    available = set()
    releases = []
    on_file = published_receipts(ledger)
    for package in packages(manifest):
        available.add(package.name)
        if requested and package.name not in requested:
            continue
        if channel and channel != package.channel:
            continue
        if withheld(package, on_file):
            # The release desk's receipt does not cover this journal text; hold it back.
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
