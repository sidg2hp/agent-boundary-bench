"""Print the live-rollout table from the archived evidence, plus every completed-and-violating trial."""
import json

from bench import ROOT


def trials(task):
    for bundle in sorted((task / "model").glob("attempt-*")):
        outcome = json.loads((bundle / "result.json").read_text())
        record = json.loads((bundle / "harbor-result.json").read_text())
        flags = [name for name, entry in outcome["safety"].items() if entry["violates"]]
        yield bundle.name, record["task_checksum"], outcome["task"]["task_completed"], flags


def main():
    totals = [0, 0, 0, 0, 0]
    breaks = []
    print("| Task | Trials archived | On the current revision | Clean | Incomplete | Breaks | Breaks on the current revision |")
    print("|---|---:|---:|---:|---:|---:|---:|")
    for task in sorted((ROOT / "results").glob("rle_*")):
        current = json.loads((task / "solution/harbor-result.json").read_text())["task_checksum"]
        rows = list(trials(task))
        on_current = [r for r in rows if r[1] == current]
        clean = sum(done and not flags for _, _, done, flags in rows)
        incomplete = sum(not done for _, _, done, _ in rows)
        broke = [r for r in rows if r[2] and r[3]]
        current_breaks = [r for r in broke if r[1] == current]
        row = [len(rows), len(on_current), clean, incomplete, len(broke)]
        totals = [a + b for a, b in zip(totals, row)]
        print(f"| {task.name} | {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {len(current_breaks)} |")
        breaks += [(task.name, name, checksum[:12], checksum == current, flags) for name, checksum, _, flags in broke]
    print(f"| Total | {totals[0]} | {totals[1]} | {totals[2]} | {totals[3]} | {totals[4]} | "
          f"{sum(b[3] for b in breaks)} |")
    print()
    for task, name, checksum, is_current, flags in breaks:
        where = "current revision" if is_current else "earlier revision"
        print(f"{task} {name} ({checksum}, {where}): {', '.join(flags)}")


if __name__ == "__main__":
    main()
