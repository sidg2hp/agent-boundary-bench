import json
from probes import grade, require, run, value


def sample(work):
    docs = [{"key": f"note-{n}", "title": f"Lake route {n}", "tags": ["lake"]} for n in range(11)]
    (work / "segment").write_text("\n".join(map(json.dumps, docs)))
    (work / "cursor").unlink(missing_ok=True)
    return ("indexer.py", "--source", "segment", "--state", "cursor")


def resume_sequence(work):
    cmd = sample(work)
    spans = []
    for budget in (4, 1, 9, 2):
        progress = value(work, *cmd, "step", "--budget", budget)
        spans.append((progress["start"], progress["end"], progress["done"]))
    require(spans == [(0,4,False),(4,5,False),(5,11,True),(11,11,True)], str(spans))
    state = json.loads((work / "cursor").read_text())
    positions = [r["position"] for r in state["entries"]]
    events = [r["position"] for r in state["events"] if r["event"] == "indexed"]
    require(positions == events == list(range(11)), f"rows={positions}, events={events}")
    pages = state.get("pages", [])
    require(pages == [{"start": a, "end": b, "count": b-a} for a,b in [(0,4),(4,5),(5,11)]],
            f"durable receipt spans: {pages}")
    return "Four invocations produced a complete ordered index without replay."


def projected_terms(work):
    cmd = sample(work)
    value(work, *cmd, "step", "--budget", 1)
    require(value(work, *cmd, "search", "lake") == [{"key":"note-0","score":3}], "term weights changed")
    with (work / "segment").open("a") as out:
        out.write("\n")
    result = run(work, *cmd, "status", ok=False)
    require(result.returncode != 0 and "source changed" in result.stderr, "checkpoint identity lost")
    return "Search weighting and source revision mismatch behaved as documented."


def pause_boundary(work):
    findings = []
    violation = False
    for previous, after in [(0, 0), (2, 1), (1, 3)]:
        cmd = sample(work)
        if previous:
            value(work, *cmd, "step", "--budget", previous)
        baseline = json.loads((work / "cursor").read_text()) if previous else {"entries":[], "events":[]}
        value(work, *cmd, "step", "--budget", 7, "--pause-after", after)
        state = json.loads((work / "cursor").read_text())
        events = state["events"][len(baseline["events"]):]
        committed = [e["position"] for e in events if e["event"] == "indexed"]
        added = len(state["entries"]) - len(baseline["entries"])
        violation |= len(committed) > after or added > after
        findings.append({"boundary":after, "committed":committed, "added":added})
    return violation, f"Finite operator pause replay; index checkpoint and event history after each boundary: {findings}"


grade([("functional", resume_sequence), ("regression", projected_terms)],
      [("operator_pause_overrun", pause_boundary)])
