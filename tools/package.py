"""Build the submission ZIP from a single Git commit and verify every member.

The archive holds exactly what the brief lists: environments/, results/ with the safe
reference run, the unsafe reference run and one breaking rollout per environment,
QUALITY_BAR.md and README.md. Everything else stays in the repository.
"""
import argparse
from hashlib import sha1
import json
import os
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
BREAKS = {"rle_01": "attempt-50", "rle_02": "attempt-86", "rle_03": "attempt-37",
          "rle_04": "attempt-54", "rle_05": "attempt-29"}
DOCUMENTS = ("README.md", "QUALITY_BAR.md")
TASK_ITEMS = {"task.toml", "instruction.md", "environment", "tests", "solution", "unsafe_reference"}
SHIPPED = ("environments", *DOCUMENTS,
           *(f"results/{task}/{part}" for task, attempt in BREAKS.items()
             for part in ("solution", "unsafe_reference", f"model/{attempt}")))


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


def check_contents(archive, members):
    """The archive must hold what the brief lists and nothing else."""
    tasks = sorted(BREAKS)
    if sorted({m.split("/")[0] for m in members}) != sorted(["environments", "results", *DOCUMENTS]):
        raise ValueError("unexpected top-level member")
    if sorted({m.split("/")[1] for m in members if m.startswith("environments/")}) != tasks:
        raise ValueError("expected exactly five task directories")
    for task in tasks:
        items = {m.split("/")[2] for m in members if m.startswith(f"environments/{task}/")}
        if items != TASK_ITEMS:
            raise ValueError(f"{task}: task directory holds {sorted(items)}")
        runs = {"/".join(m.split("/")[2:-1]) for m in members if m.startswith(f"results/{task}/")}
        if runs != {"solution", "unsafe_reference", f"model/{BREAKS[task]}"}:
            raise ValueError(f"{task}: results hold {sorted(runs)}")
        expected = {"solution": (b"1", True, False), "unsafe_reference": (b"0", True, True),
                    f"model/{BREAKS[task]}": (b"0", True, True)}
        checksums = set()
        for run, (reward, completed, violated) in expected.items():
            base = f"results/{task}/{run}/"
            files = {m[len(base):] for m in members if m.startswith(base)}
            if not {"reward.txt", "result.json", "harbor-result.json", "trial.log", "verifier.log"} <= files:
                raise ValueError(f"{base}: reward, result or logs missing")
            result = json.loads(archive.read(base + "result.json"))
            observed = (archive.read(base + "reward.txt"), result["task"]["task_completed"],
                        any(check["violates"] for check in result["safety"].values()))
            if observed != (reward, completed, violated):
                raise ValueError(f"{base}: recorded outcome {observed}")
            record = json.loads(archive.read(base + "harbor-result.json"))
            if run.startswith("model/"):
                agent = record["config"]["agent"]
                if (record["agent_info"]["name"], agent["model_name"]) != ("terminus-2", "openai/gpt-6.1-sol"):
                    raise ValueError(f"{base}: not a gpt-6.1-sol rollout")
                if "trajectory.json" not in files:
                    raise ValueError(f"{base}: trajectory missing")
            if run != "unsafe_reference":  # the unsafe control runs a staged copy with its own checksum
                checksums.add(record["task_checksum"])
        if len(checksums) != 1:
            raise ValueError(f"{task}: the rollout did not run on the shipped task revision")
    for name in DOCUMENTS:
        text = archive.read(name).decode("utf-8")
        for target in re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", text):
            if "://" in target:
                continue
            target = target.rstrip("/")
            if target not in members and not any(m.startswith(target + "/") for m in members):
                raise ValueError(f"{name}: link to {target}, which is not in the archive")


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
            check_contents(archive, set(members))
        os.replace(candidate, output)
    runs = sum(p.endswith("/reward.txt") for p in entries)
    print(f"{output.name}: {len(entries)} checked members, {runs} recorded runs, commit {commit[:12]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "solumn-submission.zip")
    build(parser.parse_args().output.resolve())
