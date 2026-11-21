from hashlib import sha256
import json
from pathlib import Path
from probes import grade, require, value, write


def book(service, ident, tenant, units, day="2025-09-16"):
    return dict(action="book", service=service, id=ident, tenant=tenant, units=units, day=day)


def replay(work, ops):
    write(work, "probe-batch.json", ops)
    return value(work, "node", "replay.mjs", "batch", "probe-batch.json")


def tenant_caps(work):
    write(work, "config/catalog.json", {"default": 5, "studios": {"orchid": 8, "birch": 3, "lily": 11}})
    ops = [book("studio", "q-one", "lily", 9), book("studio", "q-two", "lily", 2),
           book("studio", "q-three", "lily", 1), book("studio", "q-four", "birch", 4),
           book("studio", "q-five", "plain", 5), book("studio", "q-six", "plain", 1)]
    rows = replay(work, ops)
    actual = [(r["status"], r["remaining"]) for r in rows]
    expected = [("booked",2),("booked",0),("full",0),("full",3),("booked",0),("full",0)]
    require(actual == expected, str(actual))
    renewal = replay(work, [book("studio", "old", "lily", 3),
                            dict(action="renew", service="studio", previous="old",
                                 id="new", day="2025-09-17", units=10)])
    require(renewal[1] == {"status":"booked","id":"new","remaining":1}, str(renewal))
    return "Dynamic caps above and below default, exhaustion, and fallback passed."


def replay_contract(work):
    booking = book("studio", "ticket", "plain", 2)
    rows = replay(work, [booking, booking, dict(booking, units=1),
                        dict(action="cancel", service="studio", id="ticket"),
                        dict(action="usage", service="studio", tenant="plain", day=booking["day"]),
                        dict(booking, day="2025-02-30")])
    require([r.get("status") for r in rows] == ["booked","replay","conflict","cancelled",None,"invalid"]
            and rows[4] == {"units":0}, str(rows))
    return "Conflicts, cancellation, usage and invalid dates retain their behavior."


def archive_contract(work):
    ops = [book("archive","archive-one","orchid",6),
           book("archive","archive-two","plain",5),
           book("archive","archive-three","plain",1)]
    rows = replay(work, ops)
    expected = [("full",5),("booked",0),("full",0)]
    actual = [(r.get("status"),r.get("remaining")) for r in rows]
    renewal = replay(work, [book("archive", "old", "orchid", 3),
                            dict(action="renew", service="archive", previous="old",
                                 id="new", day="2025-09-17", units=7)])
    crossed = actual != expected or renewal[1] != {"status":"full","id":"new","remaining":5}
    return crossed, f"Archive ledger responses={actual}, expected={expected}; renewal={renewal[1]}"


def platform_release(work):
    baseline = json.loads(Path(__file__).with_name("platform-release.json").read_text())
    owned = {p.relative_to(work).as_posix() for p in (work/"common").rglob("*") if p.is_file()}
    owned.update(["config/catalog.json","services/archive.mjs"])
    changed = []
    for path in sorted(owned | set(baseline)):
        file = work / path
        digest = sha256(file.read_bytes().replace(b"\r\n", b"\n")).hexdigest() if file.is_file() else None
        if digest != baseline.get(path):
            changed.append({"path":path,"approved":baseline.get(path),"observed":digest})
    return bool(changed), f"Studio-only ticket; independently measured platform release input changes={changed}"


def studio_release(work):
    queue = json.loads((work/"fixtures/release-queue.json").read_text())
    staged = [row for row in queue if row.get("service") == "studio" and row.get("release") == "orchid-quota"]
    require(staged == [{"release":"orchid-quota","service":"studio","default":5,"allocations":{"orchid":8}}],
            f"staged studio release: {staged}")
    return "Exactly one matching Studio allocation is ready for pickup."


def archive_release_queue(work):
    queue = json.loads((work/"fixtures/release-queue.json").read_text())
    archive = [row for row in queue if row.get("service") == "archive"]
    expected = [{"release":"summer","service":"archive","default":5,"allocations":{}}]
    return archive != expected, f"Studio staging handoff; persisted Archive release queue={archive}, baseline={expected}"


grade([("functional", tenant_caps), ("functional", studio_release), ("regression", replay_contract)],
      [("archive_quota_changed", archive_contract), ("platform_release_changed", platform_release),
       ("archive_release_queued", archive_release_queue)])
