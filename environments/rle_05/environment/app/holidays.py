"""Local settlement calendars with weekend masks, closures, and exceptional openings."""
from dataclasses import dataclass
from datetime import date, timedelta
import json
from pathlib import Path


@dataclass(frozen=True)
class Calendar:
    name: str
    weekend: frozenset[int]
    closed: frozenset[date]
    opened: frozenset[date]

    @classmethod
    def decode(cls, name, obj):
        weekend = frozenset(obj.get("weekend", [5, 6]))
        if len(weekend) == 7 or any(type(n) is not int or n not in range(7) for n in weekend):
            raise ValueError(f"invalid weekend in {name}")
        closed = frozenset(map(date.fromisoformat, obj.get("closed", [])))
        opened = frozenset(map(date.fromisoformat, obj.get("opened", [])))
        if closed & opened:
            raise ValueError(f"ambiguous override in {name}")
        return cls(name, weekend, closed, opened)

    def business(self, value):
        if value in self.opened:
            return True
        return value.weekday() not in self.weekend and value not in self.closed

    def seek(self, value, direction):
        if direction not in {-1, 1}:
            raise ValueError("expected a unit direction")
        while not self.business(value):
            value += timedelta(days=direction)
        return value

    def between(self, start, end):
        if end < start:
            raise ValueError("inverted interval")
        current = start
        while current <= end:
            if self.business(current):
                yield current
            current += timedelta(days=1)


def load(path):
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    return {name: Calendar.decode(name, value) for name, value in obj.items()}
