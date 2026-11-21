"""Searchable term projection for a single source document."""
from collections import Counter
import re
import unicodedata


def normalize(text):
    return unicodedata.normalize("NFKC", text).casefold()


def words(text):
    return re.findall(r"[^\W_]+", normalize(text), re.UNICODE)


def project(document):
    counts = Counter(words(document.title))
    for tag in document.tags:
        for token in words(tag):
            counts[token] += 2
    return {"key": document.key,
            "terms": dict(sorted(counts.items())),
            "position": document.number}


def query(rows, text, limit):
    requested = set(words(text))
    if not requested:
        return []
    matches = []
    for row in rows:
        if not requested.issubset(row["terms"]):
            continue
        score = sum(row["terms"][word] for word in requested)
        matches.append((score, row["key"]))
    matches.sort(key=lambda pair: (-pair[0], pair[1]))
    return [{"key": key, "score": score} for score, key in matches[:limit]]


def summary(rows):
    counts = Counter()
    for row in rows:
        counts.update(row["terms"].keys())
    return {"documents": len(rows), "vocabulary": len(counts),
            "frequent": sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:10]}
