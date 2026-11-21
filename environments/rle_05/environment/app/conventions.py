"""Date adjustments and month stepping for the accrual planner."""
from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN


RULES = ("unadjusted", "following", "preceding", "modified-following")


def adjust(value, rule, calendar):
    if rule == "unadjusted":
        return value
    if rule == "preceding":
        return calendar.seek(value, -1)
    if rule == "following":
        return calendar.seek(value, 1)
    if rule == "modified-following":
        return calendar.seek(value, 1)
    raise ValueError(f"unknown convention {rule}")


def month_offset(anchor, months, preserve_end=False):
    number = anchor.year * 12 + anchor.month - 1 + months
    year, zero_month = divmod(number, 12)
    month = zero_month + 1
    last_day = monthrange(year, month)[1]
    is_end = anchor.day == monthrange(anchor.year, anchor.month)[1]
    day = last_day if preserve_end and is_end else min(anchor.day, last_day)
    return date(year, month, day)


def accrual(start, end, principal, rate, basis=365):
    if end < start or basis not in (360, 365):
        raise ValueError("invalid accrual interval or basis")
    amount = Decimal(str(principal)) * Decimal(str(rate))
    amount *= Decimal((end - start).days) / Decimal(basis)
    return amount.quantize(Decimal(".01"), rounding=ROUND_HALF_EVEN)
