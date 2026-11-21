"""Construct cashflow periods using unadjusted anchors and adjusted payment dates."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from conventions import RULES, accrual, adjust, month_offset


@dataclass(frozen=True)
class Contract:
    name: str
    calendar: str
    anchor: date
    months: int
    periods: int
    rule: str
    principal: Decimal
    rate: Decimal
    basis: int
    preserve_end: bool

    @classmethod
    def from_record(cls, row):
        anchor = date.fromisoformat(row["anchor"])
        months, periods = row["months"], row["periods"]
        if type(months) is not int or type(periods) is not int:
            raise ValueError("months and periods must be integers")
        if not 1 <= months <= 120 or not 1 <= periods <= 600:
            raise ValueError("invalid schedule length")
        if row["rule"] not in RULES:
            raise ValueError("invalid payment convention")
        basis = row.get("basis", 365)
        if basis not in (360, 365):
            raise ValueError("invalid basis")
        principal = Decimal(str(row["principal"]))
        rate = Decimal(str(row["rate"]))
        if not principal.is_finite() or not rate.is_finite():
            raise ValueError("nonfinite amount")
        return cls(row["name"], row["calendar"], anchor, months, periods, row["rule"],
                   principal, rate, basis, row.get("preserve_end", False))


def periods(contract, calendar):
    start = contract.anchor
    for number in range(1, contract.periods + 1):
        end = month_offset(contract.anchor, number * contract.months, contract.preserve_end)
        payment = adjust(end, contract.rule, calendar)
        interest = accrual(start, end, contract.principal, contract.rate, contract.basis)
        yield {"name": contract.name, "period": number, "start": start.isoformat(),
               "end": end.isoformat(), "payment": payment.isoformat(), "amount": str(interest)}
        start = end


def portfolio(rows, calendars):
    seen = set()
    for row in rows:
        contract = Contract.from_record(row)
        if contract.name in seen:
            raise ValueError(f"duplicate contract {contract.name}")
        seen.add(contract.name)
        yield from periods(contract, calendars[contract.calendar])
