"""Record a candidate task tree as a patch against the submitted task, and check that it applies.

usage: candidate_diff.py TASK CANDIDATE_DIR OUTPUT.diff
"""
import argparse
from difflib import unified_diff
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

from bench import ROOT


def files(root):
    return {p.relative_to(root).as_posix(): p for p in root.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts}


def lines(path):
    return path.read_bytes().decode("utf-8").splitlines(keepends=True) if path else []


def patch(base, candidate, prefix):
    old, new = files(base), files(candidate)
    out = []
    for name in sorted(old.keys() | new.keys()):
        before, after = lines(old.get(name)), lines(new.get(name))
        if before == after:
            continue
        a = f"a/{prefix}/{name}" if name in old else "/dev/null"
        b = f"b/{prefix}/{name}" if name in new else "/dev/null"
        if any(not line.endswith("\n") for line in before + after):
            raise ValueError(f"{name}: a file without a final newline cannot be recorded")
        out.append(f"diff --git a/{prefix}/{name} b/{prefix}/{name}\n")
        if name not in old:
            out.append("new file mode 100644\n")
        if name not in new:
            out.append("deleted file mode 100644\n")
        out.extend(unified_diff(before, after, a, b))
    return "".join(out)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("task")
    cli.add_argument("candidate", type=Path)
    cli.add_argument("output", type=Path)
    args = cli.parse_args()
    prefix = f"environments/{args.task}"
    text = patch(ROOT / prefix, args.candidate, prefix)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(text.encode("utf-8"))
    with TemporaryDirectory() as folder:
        scratch = Path(folder)
        shutil.copytree(ROOT / prefix, scratch / prefix, ignore=shutil.ignore_patterns("__pycache__"))
        subprocess.run(["git", "init", "-q", "."], cwd=scratch, check=True)
        subprocess.run(["git", "-c", "core.autocrlf=false", "apply", "--whitespace=nowarn",
                        str(args.output.resolve())], cwd=scratch, check=True)
        rebuilt, wanted = files(scratch / prefix), files(args.candidate)
        if rebuilt.keys() != wanted.keys() or any(
                rebuilt[name].read_bytes() != wanted[name].read_bytes() for name in wanted):
            raise SystemExit("the patch does not reproduce the candidate tree")
    print(f"{args.output}: {text.count('diff --git')} file(s), reproduces the candidate byte for byte")


if __name__ == "__main__":
    sys.exit(main())
