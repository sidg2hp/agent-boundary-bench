"""Print one line per trial of a Harbor job: completion, safety flags and reward."""
import argparse
import json
from pathlib import Path

from bench import ROOT


def rows(job):
    for trial in sorted(job.iterdir()):
        if not (trial / "config.json").exists():
            continue
        record = json.loads((trial / "result.json").read_text(encoding="utf-8"))
        line = {"trial": trial.name, "checksum": record["task_checksum"][:12],
                "exception": (record.get("exception_info") or {}).get("exception_type")}
        verdict = trial / "verifier/result.json"
        if verdict.exists():
            data = json.loads(verdict.read_text(encoding="utf-8"))
            line["completed"] = data["task"]["task_completed"]
            line["failed_checks"] = [c["name"] for c in data["task"]["checks"] if not c["passed"]]
            line["violations"] = [k for k, v in data["safety"].items() if v["violates"]]
            line["reward"] = (trial / "verifier/reward.txt").read_text()
            line["break"] = bool(line["completed"] and line["violations"])
        yield line


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("job", type=Path)
    for row in rows(cli.parse_args().job if cli.parse_args().job.is_absolute()
                    else ROOT / cli.parse_args().job):
        print(json.dumps(row))
