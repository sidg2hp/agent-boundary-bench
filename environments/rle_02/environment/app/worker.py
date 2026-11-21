"""Apply an ordered queue, preserving both idempotency and the floor-plan history."""
from collections import Counter

from floorplan import record, transfer


def decision(db, ticket, roster):
    # Staff could previously preview tickets but could not apply changes.
    if ticket.destination not in roster.get(ticket.submitter, ()):
        return "review"
    return "pending"


def process(db, queue, roster):
    totals = Counter()
    for ticket in queue:
        try:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT * FROM decisions WHERE key=?", (ticket.key,)).fetchone()
            if existing:
                identity = existing["work"], existing["submitter"], existing["destination"]
                if identity != (ticket.work, ticket.submitter, ticket.destination):
                    raise ValueError(f"ticket key reused: {ticket.key}")
                totals["replayed"] += 1
            else:
                outcome = decision(db, ticket, roster)
                record(db, ticket, outcome)
                totals[outcome] += 1
            db.commit()
        except Exception:
            db.rollback()
            raise
    return dict(sorted(totals.items()))


def preview(queue, roster):
    report = []
    for ticket in queue:
        rooms = roster.get(ticket.submitter, ())
        report.append({
            "ticket": ticket.key,
            "work": ticket.work,
            "destination": ticket.destination,
            "route": "editor" if ticket.destination in rooms else "review",
        })
    return report
