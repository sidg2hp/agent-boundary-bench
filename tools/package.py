"""Build the submission ZIP from a single Git commit and verify every member."""
import argparse
from hashlib import sha1
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SHIPPED = ("environments", "results", "tools", "README.md", "QUALITY_BAR.md", "ABANDONED.md",
           "progress.md", ".gitattributes", ".gitignore")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def inventory(commit):
    entries = {}
    for record in git("ls-tree", "-rz", commit, "--", *SHIPPED).split(b"\0"):
        if not record:
            continue
        header, name = record.split(b"\t", 1)
        mode, kind, digest = header.split()
        path = name.decode("utf-8")
        if kind != b"blob" or mode not in (b"100644", b"100755"):
            raise ValueError(f"unexpected Git member type at {path}")
        if Path(path).name.startswith(".env") or path.lower().endswith(".pdf"):
            raise ValueError("credential-bearing input in selected Git tree")
        entries[path] = digest.decode("ascii")
    return entries


def build(output):
    commit = git("rev-parse", "HEAD").decode().strip()
    entries = inventory(commit)
    if git("status", "--porcelain", "--", *SHIPPED).strip():
        raise ValueError("commit the deliverables before packaging")
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as directory:
        candidate = Path(directory, "submission.zip")
        git("-c", "core.autocrlf=false", "archive", "--format=zip",
            "--output", str(candidate), commit, "--", *SHIPPED)
        with ZipFile(candidate) as archive:
            members = [m.filename for m in archive.infolist() if not m.is_dir()]
            if len(members) != len(entries) or set(members) != set(entries):
                raise ValueError("ZIP inventory disagrees with the committed tree")
            for name in members:
                data = archive.read(name)
                framed = b"blob " + str(len(data)).encode() + b"\0" + data
                if sha1(framed).hexdigest() != entries[name]:
                    raise ValueError(f"ZIP content mismatch: {name}")
        os.replace(candidate, output)
    trials = sum(p.endswith("/trajectory.json") for p in entries)
    print(f"{output.name}: {len(entries)} checked members, {trials} trajectories, commit {commit[:12]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "solumn-submission.zip")
    build(parser.parse_args().output.resolve())
