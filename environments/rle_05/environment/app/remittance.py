"""Settlement register records and readers for the desk and custodian file formats."""
import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import json
from pathlib import Path


def label(row, field):
    value = row[field]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"empty {field}")
    return value.strip()


def minor_units(text):
    if not isinstance(text, str):
        raise ValueError("amounts must be decimal strings")
    number = Decimal(text)
    if not number.is_finite() or number.as_tuple().exponent < -2:
        raise ValueError(f"invalid settlement amount {text!r}")
    return int(number * 100)


@dataclass(frozen=True, order=True)
class Obligation:
    account: str
    contract: str
    installment: str
    payment: date
    currency: str

    @classmethod
    def from_row(cls, row):
        currency = label(row, "currency")
        if len(currency) != 3 or not currency.isalpha() or not currency.isupper():
            raise ValueError("expected three-letter currency code")
        return cls(label(row, "account"), label(row, "contract"),
                   label(row, "installment"), date.fromisoformat(label(row, "payment")), currency)

    def columns(self):
        return {"account": self.account, "contract": self.contract,
                "installment": self.installment, "payment": self.payment.isoformat(),
                "currency": self.currency}


@dataclass(frozen=True)
class Entry:
    obligation: Obligation
    cents: int
    advice_id: str

    @classmethod
    def from_row(cls, row):
        return cls(Obligation.from_row(row), minor_units(row["amount"]), label(row, "advice_id"))

    def columns(self):
        amount = Decimal(self.cents) / 100
        return {**self.obligation.columns(), "amount": format(amount, ".2f"), "advice_id": self.advice_id}


def custodian_rows(payload):
    for batch in payload["batches"]:
        header = {key: label(batch, key) for key in ("account","payment","currency")}
        for line in batch["lines"]:
            yield {**line, **header}


def read_entries(path):
    path = Path(path)
    with path.open(encoding="utf-8", newline="") as stream:
        if path.suffix.lower() == ".csv":
            return [Entry.from_row(row) for row in csv.DictReader(stream)]
        obj = json.load(stream)
        rows = obj["rows"] if obj["schema"] == "desk-register-v1" else None
        if rows is None:
            if obj["schema"] != "custodian-advice-v2":
                raise ValueError("unknown register format")
            rows = custodian_rows(obj)
        return [Entry.from_row(row) for row in rows]


def write_csv(entries, stream):
    fields = ["account", "contract", "installment", "payment", "currency", "amount", "advice_id"]
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for entry in entries:
        writer.writerow(entry.columns())


def replay_unique(entries):
    """A custodian may resend one advice verbatim after reconnecting."""
    observed = {}
    for entry in entries:
        key = (entry.obligation.account, entry.advice_id)
        previous = observed.get(key)
        if previous is None:
            observed[key] = entry
            yield entry
        elif previous != entry:
            raise ValueError(f"conflicting advice for {key[0]}/{key[1]}")


def trial_balance(entries):
    """The monthly desk statement, summed by currency and value month."""
    totals = {}
    for row in replay_unique(entries):
        key = row.obligation.currency, row.obligation.payment.strftime("%Y-%m")
        totals[key] = totals.get(key, 0) + row.cents
    return [{"currency": currency, "month": month, "cents": cents}
            for (currency, month), cents in sorted(totals.items())]
