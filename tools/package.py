"""Build the submission ZIP from a single Git commit and verify every member.

The archive holds the five task directories, the full Harbor evidence with its index,
the three documents and the scripts a reader needs to re-run the controls and the audit.
Working notes and packaging helpers stay out of it.
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
DOCUMENTS = ("README.md", "QUALITY_BAR.md", "ABANDONED.md")
TOOLS = ("archive_job.py", "audit.py", "bench.py", "candidate_diff.py", "collect.py", "gitcmds.py",
         "index_results.py", "rollout.py", "summarize.py", "tally.py")
OFF_TOPIC = ("github", "claude", "anthropic", "chatgpt", "copilot", "codex", "co-authored",
             "working session", "another session", "this session", "previous agent")
TASK_ITEMS = {"task.toml", "instruction.md", "environment", "tests", "solution", "unsafe_reference"}
SHIPPED = ("environments", "results", *DOCUMENTS, *(f"tools/{name}" for name in TOOLS))


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
    """The archive must hold what the brief lists, complete and consistent, plus the supporting record."""
    tasks = sorted(BREAKS)
    if sorted({m.split("/")[0] for m in members}) != sorted(["environments", "results", "tools", *DOCUMENTS]):
        raise ValueError("unexpected top-level member")
    if sorted({m.split("/")[1] for m in members if m.startswith("environments/")}) != tasks:
        raise ValueError("expected exactly five task directories")
    for task in tasks:
        items = {m.split("/")[2] for m in members if m.startswith(f"environments/{task}/")}
        if items != TASK_ITEMS:
            raise ValueError(f"{task}: task directory holds {sorted(items)}")
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
    if "results/INDEX.md" not in members:
        raise ValueError("results/INDEX.md is missing")
    for name in (*DOCUMENTS, "results/INDEX.md", *(f"tools/{tool}" for tool in TOOLS)):
        text = archive.read(name).decode("utf-8")
        for term in OFF_TOPIC:
            if term in text.lower():
                raise ValueError(f"{name}: mentions {term!r}")
        for tool in set(re.findall(r"tools/(\w+\.py)", text)) - set(TOOLS):
            raise ValueError(f"{name}: names tools/{tool}, which is not in the archive")
        if name not in DOCUMENTS:
            continue
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
