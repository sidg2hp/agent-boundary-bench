"""Archive original Harbor evidence only after trial and verifier records agree."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil

from bench import ROOT, validate


def copy_evidence(job, destination, role, only=None):
    job_result = json.loads((job / "result.json").read_text())
    if not job_result["finished_at"]:
        raise ValueError(f"job still running: {job.name}")
    archived = 0
    for trial in sorted(job.iterdir()):
        if not trial.is_dir() or not (trial / "config.json").exists():
            continue
        if only and trial.name != only:
            continue
        record = json.loads((trial / "result.json").read_text())
        task = trial.name.split("__")[0]
        if task not in {f"rle_0{i}" for i in range(1, 6)}:
            raise ValueError(f"unknown task: {task}")
        if record.get("exception_info") or not record.get("finished_at"):
            raise ValueError(f"unverified trial: {trial.name}")
        verifier = trial / "verifier"
        validate(verifier, role)
        reward = int((verifier / "reward.txt").read_text())
        if record["verifier_result"]["rewards"]["reward"] != reward:
            raise ValueError("Harbor disagrees with verifier")
        files = {verifier / "result.json": "result.json", verifier / "reward.txt": "reward.txt",
                 trial / "result.json": "harbor-result.json", trial / "trial.log": "trial.log",
                 verifier / "test-stdout.txt": "verifier.log"}
        if role == "model":
            files[trial / "agent/trajectory.json"] = "trajectory.json"
        else:
            files[trial / "agent/oracle.txt"] = "oracle.log"
        output = ROOT / "results" / task / destination
        for source, name in files.items():
            data = source.read_bytes()
            out = output / name
            if out.exists() and out.read_bytes() != data:
                raise ValueError(f"conflicting evidence at {out}")
        output.mkdir(parents=True, exist_ok=True)
        hashes = []
        for source, name in files.items():
            out = output / name
            shutil.copyfile(source, out)
            hashes.append(f"{sha256(out.read_bytes()).hexdigest()}  {name}")
        (output / "SHA256SUMS").write_text("\n".join(hashes) + "\n")
        print(task, destination, trial.name)
        archived += 1
    if not archived:
        raise ValueError(f"no matching trial in {job.name}")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("job", type=Path)
    cli.add_argument("role", choices=["solution","unsafe_reference","noop","destructive","model"])
    cli.add_argument("--destination")
    cli.add_argument("--trial", help="archive only this trial directory of the job")
    args = cli.parse_args()
    copy_evidence(args.job, args.destination or args.role, args.role, args.trial)
