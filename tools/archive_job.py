"""Archive every finished trial of a model job under the next free attempt-NN of its task."""
import argparse
import json
from pathlib import Path

from bench import ROOT
from collect import copy_evidence


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("job", type=Path)
    job = cli.parse_args().job
    job = job if job.is_absolute() else ROOT / job
    known = {json.loads(p.read_text())["id"] for p in (ROOT / "results").glob("rle_*/model/*/harbor-result.json")}
    for trial in sorted(job.iterdir()):
        record = trial / "result.json"
        if not (trial / "config.json").exists() or not record.exists():
            continue
        if json.loads(record.read_text())["id"] in known:
            continue
        task = trial.name.split("__")[0]
        taken = [int(p.name.split("-")[1]) for p in (ROOT / "results" / task / "model").glob("attempt-*")]
        copy_evidence(job, f"model/attempt-{max(taken, default=0) + 1:02d}", "model", trial.name)


if __name__ == "__main__":
    main()
