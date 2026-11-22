"""Write results/INDEX.md: every archived run, read from the evidence files themselves."""
import argparse
import json
from pathlib import Path
import tomllib

from bench import ROOT, ROLES

LABELS = {"solution": "safe reference", "unsafe_reference": "unsafe reference",
          "noop": "unchanged starter", "destructive": "damaged starter"}


def outcome(folder):
    result = json.loads((folder / "result.json").read_text(encoding="utf-8"))
    record = json.loads((folder / "harbor-result.json").read_text(encoding="utf-8"))
    fired = [name for name, check in result["safety"].items() if check["violates"]]
    failed = [check["name"] for check in result["task"]["checks"] if not check["passed"]]
    return {"checksum": record["task_checksum"][:12], "completed": result["task"]["task_completed"],
            "fired": fired, "failed": failed, "reward": (folder / "reward.txt").read_text().strip()}


def yes(value):
    return "yes" if value else "no"


def render():
    out = ["# Evidence index", "",
           "Every run archived under `results/`, read from each folder's `result.json`, `reward.txt` and "
           "`harbor-result.json` by `tools/index_results.py`. A revision is named by the first twelve characters "
           "of Harbor's task checksum. A model trial counts for the submitted task when its revision equals the "
           "safe reference's.", ""]
    totals = [0, 0, 0, 0]
    for task in sorted((ROOT / "results").glob("rle_*")):
        policy = tomllib.loads((ROOT / "environments" / task.name / "task.toml").read_text())["metadata"]["subpolicy"]
        controls = {role: outcome(task / role) for role in ROLES}
        submitted = controls["solution"]["checksum"]
        out += [f"## {task.name} ({policy}), submitted revision `{submitted}`", "",
                "| Control | Folder | Completed | Safety checks that fired | Reward |", "|---|---|---|---|---:|"]
        for role in ROLES:
            row = controls[role]
            out.append(f"| {LABELS[role]} | `{task.name}/{role}` | {yes(row['completed'])} | "
                       f"{', '.join(row['fired']) or 'none'} | {row['reward']} |")
        history = sorted(p for p in (task / "history").iterdir() if p.is_dir()) if (task / "history").is_dir() else []
        if history:
            out += ["", "Control sets of superseded revisions and candidates:", ""]
            for folder in history:
                roles = [role for role in ROLES if (folder / role).is_dir()]
                revision = outcome(folder / "solution")["checksum"] if "solution" in roles else "n/a"
                patch = ", with the candidate recorded as `task.diff`" if (folder / "task.diff").is_file() else ""
                out.append(f"- `{task.name}/history/{folder.name}`: revision `{revision}`, {len(roles)} controls{patch}")
        trials = [(p.name, outcome(p)) for p in sorted((task / "model").iterdir()) if p.is_dir()]
        current = [row for _, row in trials if row["checksum"] == submitted]
        breaks = [row for row in current if row["completed"] and row["fired"]]
        all_breaks = [row for _, row in trials if row["completed"] and row["fired"]]
        totals = [totals[0] + len(trials), totals[1] + len(current), totals[2] + len(all_breaks), totals[3] + len(breaks)]
        out += ["", f"Model trials: {len(trials)} archived, {len(current)} on the submitted revision, "
                    f"{len(breaks)} of those completed with a violation.", "",
                "| Trial | Revision | Submitted revision | Completed | Safety checks that fired | Reward |",
                "|---|---|---|---|---|---:|"]
        for name, row in trials:
            fired = ", ".join(row["fired"]) or "none"
            if not row["completed"]:
                fired += f" (failed: {', '.join(row['failed'])})"
            out.append(f"| `{task.name}/model/{name}` | `{row['checksum']}` | {yes(row['checksum'] == submitted)} | "
                       f"{yes(row['completed'])} | {fired} | {row['reward']} |")
        out.append("")
    out += [f"Total: {totals[0]} model trials, {totals[1]} on the submitted revisions; {totals[2]} completed with a "
            f"violation, {totals[3]} of them on the submitted revisions.", ""]
    return "\n".join(out)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--check", action="store_true", help="fail if results/INDEX.md is out of date")
    args = cli.parse_args()
    path = ROOT / "results" / "INDEX.md"
    text = render().encode("utf-8")
    if args.check:
        if not path.is_file() or path.read_bytes() != text:
            raise SystemExit("results/INDEX.md does not match the archived evidence")
        print("results/INDEX.md matches the archived evidence")
    else:
        path.write_bytes(text)
        print(f"wrote {path.relative_to(ROOT)}: {text.count(b'/model/attempt-')} model trials")


if __name__ == "__main__":
    main()
