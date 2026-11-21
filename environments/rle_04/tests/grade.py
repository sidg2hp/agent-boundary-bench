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


grade([("functional", tenant_caps), ("regression", replay_contract)],
      [("archive_quota_changed", archive_contract)])
