"""Version ordering and release records for the team digest."""
from dataclasses import dataclass, field
import re


VERSION = re.compile(
    r"^\[?v?(\d+)\.(\d+)\.(\d+)(?:-([\w.-]+))?\]?"
    r"(?:\s+[-–]\s+(\d{4}-\d{2}-\d{2}))?$"
)


@dataclass(frozen=True)
class Version:
    major: int
    minor: int
    patch: int
    preview: str = ""

    def key(self):
        parts = tuple((0, int(value)) if value.isdigit() else (1, value)
                      for value in self.preview.split("."))
        return self.major, self.minor, self.patch, not self.preview, parts

    def __str__(self):
        number = f"{self.major}.{self.minor}.{self.patch}"
        return f"{number}-{self.preview}" if self.preview else number


@dataclass
class Release:
    package: str
    version: Version
    date: str
    sections: dict[str, list[str]] = field(default_factory=dict)

    def append(self, section, item):
        self.sections.setdefault(section, []).append(item)

    def as_dict(self):
        return dict(package=self.package, version=str(self.version),
                    date=self.date, sections=self.sections)


def release_heading(package, title):
    match = VERSION.fullmatch(title.strip())
    if not match:
        return None
    major, minor, patch, preview, date = match.groups()
    version = Version(int(major), int(minor), int(patch), preview or "")
    return Release(package, version, date or "")


def ordered(releases):
    return sorted(releases, key=lambda item: (item.package.casefold(),
                  tuple(-x for x in (item.version.major, item.version.minor,
                                     item.version.patch)), bool(item.version.preview),
                  item.version.preview))
