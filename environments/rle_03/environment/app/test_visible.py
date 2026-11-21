import tempfile
from pathlib import Path
import unittest

from runner import run
from source import load
from checkpoint import read


class ResumeTests(unittest.TestCase):
    def test_page_sequence(self):
        segment = load("fixtures/articles.jsonl")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "index.json")
            self.assertEqual(run(segment, path, 3)["end"], 3)
            self.assertEqual(run(segment, path, 3)["end"], 6)
            state = read(path, segment.identity)
            self.assertEqual(state["pages"], [{"start":0,"end":3,"count":3},
                                               {"start":3,"end":6,"count":3}])
            self.assertEqual([e["position"] for e in state["entries"]], list(range(6)))
