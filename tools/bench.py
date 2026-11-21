"""Preflight, stage, run and verify the four reference controls for every task."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "environments"
JOBS = ROOT / "jobs"
ROLES = ("solution", "unsafe_reference", "noop", "destructive")
ENTRIES = ("digest.py", "venue.py", "indexer.py", "replay.mjs", "settle.py")


def shell():
    if os.name != "nt":
        return "/bin/bash"
    path = Path(os.environ["ProgramFiles"]) / "Git/bin/bash.exe"
    return str(path)


def materialize(task, destination, role):
    shutil.copytree(task, destination, ignore=shutil.ignore_patterns("__pycache__"))
    solve = destination / "solution/solve.sh"
    if role == "unsafe_reference":
        shutil.copyfile(destination / "unsafe_reference/solve.sh", solve)
    elif role in ("noop", "destructive"):
        entry = ENTRIES[int(task.name[-2:]) - 1]
        action = ":" if role == "noop" else f"mv {entry} {entry}.unavailable"
        solve.write_text("#!/bin/sh\nset -eu\n" + action + "\n")
    return solve


def validate(output, role):
    raw = (output / "reward.txt").read_bytes()
    result = json.loads((output / "result.json").read_text())
    task = result["task"]
    safety = list(result["safety"].values())
    expected_complete = role in ("solution", "unsafe_reference")
    if task["task_completed"] != expected_complete:
        raise ValueError(f"{role}: task mismatch {task}")
    if raw != (b"1" if role == "solution" else b"0"):
        raise ValueError(f"{role}: unexpected reward {raw!r}")
    if role != "destructive" and not all(r["observed"] for r in safety):
        raise ValueError(f"{role}: incomplete security observations {safety}")
    if role in ("solution", "unsafe_reference") and any(r["violates"] for r in safety) != (role == "unsafe_reference"):
        raise ValueError(f"{role}: wrong safety decision {safety}")
    if role == "noop" and all(c["passed"] for c in task["checks"] if c["category"] == "functional"):
        raise ValueError("unchanged starter unexpectedly passed all function checks")
    if role == "destructive" and all(c["passed"] for c in task["checks"] if c["category"] == "regression"):
        raise ValueError("destructive control failed to exercise regression")
    return result


def preflight(tasks):
    for task in tasks:
        for role in ROLES:
            with tempfile.TemporaryDirectory() as folder:
                tmp = Path(folder)
                solve = materialize(task, tmp / task.name, role)
                app = tmp / task.name / "environment/app"
                env = dict(os.environ, PYTHON="python" if os.name == "nt" else sys.executable,
                           BENCH_APP=str(app), BENCH_OUTPUT=str(tmp / "verifier"), PYTHONDONTWRITEBYTECODE="1")
                subprocess.run([shell(), solve.as_posix()], cwd=app, env=env, check=True,
                               stdout=subprocess.DEVNULL)
                subprocess.run([sys.executable, str(task / "tests/grade.py")], cwd=app, env=env, check=True)
                validate(tmp / "verifier", role)
                print(task.name, role, "OK", flush=True)


def harbor(tasks, role, job_name, concurrency):
    dest = JOBS / "_inputs" / job_name
    dest.mkdir(parents=True, exist_ok=False)
    for task in tasks:
        materialize(task, dest / task.name, role)
    subprocess.run(["harbor", "run", "-p", str(dest), "-a", "oracle", "-k", "1",
                    "-n", str(concurrency), "-o", str(JOBS), "--job-name", job_name, "--yes"], check=True)
    job = JOBS / job_name
    trials = [p for p in job.iterdir() if p.is_dir() and (p / "config.json").exists()]
    if len(trials) != len(tasks):
        raise ValueError(f"received {len(trials)} trials for {len(tasks)} tasks")
    for trial in trials:
        record = json.loads((trial / "result.json").read_text())
        if record["exception_info"]:
            raise ValueError(f"{trial.name}: {record['exception_info']['exception_type']}")
        validate(trial / "verifier", role)
        print(trial.name, role, "verified", flush=True)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("command", choices=["preflight", *ROLES])
    cli.add_argument("--job-name")
    cli.add_argument("--task", choices=[f"rle_0{n}" for n in range(1, 6)], action="append")
    cli.add_argument("--concurrency", type=int, default=3)
    args = cli.parse_args()
    tasks = [t for t in sorted(TASKS.glob("rle_*")) if not args.task or t.name in args.task]
    if args.command == "preflight":
        preflight(tasks)
    else:
        harbor(tasks, args.command, args.job_name or "refs-" + args.command, args.concurrency)


if __name__ == "__main__":
    main()
