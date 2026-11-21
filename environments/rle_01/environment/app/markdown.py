"""Parse vendored Markdown with a small block tokenizer."""
from dataclasses import dataclass
import re

from releases import release_heading


@dataclass(frozen=True)
class Block:
    kind: str
    text: str
    level: int = 0


def blocks(source):
    lines = source.splitlines()
    fence = None
    pos = 0
    while pos < len(lines):
        line = lines[pos]
        pos += 1
        stripped = line.strip()
        marker = re.match(r"^(`{3,}|~{3,})", stripped)
        if marker:
            if fence is None:
                fence = marker[1]
            elif marker[1].startswith(fence):
                fence = None
            continue
        if fence is not None:
            continue
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if heading:
            yield Block("heading", heading[2], len(heading[1]))
            continue
        item = re.match(r"^\s*[-*+]\s+(.+)", line)
        if item:
            yield Block("item", item[1].strip())
        elif line.startswith(("    ", "\t")) and stripped:
            yield Block("continuation", stripped)
        else:
            yield Block("paragraph", stripped)


def parse(package, source):
    current = None
    group = "Changes"
    continued = False
    for block in blocks(source):
        if block.kind == "heading" and block.level <= 2:
            if current:
                yield current
            current = release_heading(package, block.text)
            group = "Changes"
            continued = False
        elif current and block.kind == "heading" and block.level == 3:
            group = block.text
            continued = False
        elif current and block.kind == "item":
            current.append(group, block.text)
            continued = True
        elif current and continued and block.kind == "continuation":
            current.sections[group][-1] += " " + block.text
        else:
            continued = False
    if current:
        yield current
