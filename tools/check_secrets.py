"""Check Git history, local Harbor files, and an optional deliverable for the supplied credential."""
import argparse
from pathlib import Path
import subprocess
import zipfile

from rollout import ROOT, settings


def git(*args, data=None):
    return subprocess.check_output(["git", *args], cwd=ROOT, input=data)


def check_history(secret):
    indexed = git("ls-files", "-z").decode().split("\0")
    if any(Path(name).name == ".env" or name.lower().endswith(".pdf") for name in indexed if name):
        raise ValueError("a protected input is tracked")
    objects = git("rev-list", "--objects", "--all").splitlines()
    ids = b"\n".join(row.split(b" ", 1)[0] for row in objects) + b"\n"
    sizes = git("cat-file", "--batch-check=%(objectname) %(objecttype)", data=ids).splitlines()
    blobs = [row.split()[0] for row in sizes if row.endswith(b" blob")]
    raw = git("cat-file", "--batch", data=b"\n".join(blobs) + b"\n")
    if secret in raw:
        raise ValueError("credential found in Git history")
    return len(blobs)


def contains(path, secret):
    tail = b""
    with path.open("rb") as stream:
        while chunk := stream.read(1 << 20):
            block = tail + chunk
            if secret in block:
                return True
            tail = block[-len(secret):]
    return False


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--pdf", type=Path)
    cli.add_argument("--jobs", action="store_true")
    cli.add_argument("--zip", type=Path)
    args = cli.parse_args()
    _, key = settings(args.pdf)
    secret = key.encode()
    count = check_history(secret)
    print(f"Exact credential absent from {count} Git history blobs.")
    if args.jobs:
        files = [p for p in (ROOT/"jobs").rglob("*") if p.is_file()]
        if any(contains(p, secret) for p in files):
            raise ValueError("credential found in local Harbor job files")
        print(f"Exact credential absent from {len(files)} local Harbor job files.")
    if args.zip:
        with zipfile.ZipFile(args.zip) as bundle:
            for item in bundle.infolist():
                if item.is_dir():
                    continue
                path = Path(item.filename)
                if path.name == ".env" or path.suffix.lower() == ".pdf" or secret in bundle.read(item):
                    raise ValueError("protected input or credential in deliverable")
        print("ZIP contains no source PDF, .env file, or supplied credential.")


if __name__ == "__main__":
    main()
