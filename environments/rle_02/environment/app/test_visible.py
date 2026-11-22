from contextlib import closing
import unittest

from floorplan import connect, seed, works
from worker import process
from tickets import read_queue, read_roster


class FloorTests(unittest.TestCase):
    def test_bundle_members(self):
        queue = list(read_queue("fixtures/bundles.jsonl"))
        self.assertEqual([t.key for t in queue], ["first", "second"])
        self.assertEqual([t.submitter for t in queue], ["mira","visit-curator"])

    def test_staff_install_and_replay(self):
        with closing(connect(":memory:")) as db:
            seed(db, "fixtures/layout.json")
            queue = list(read_queue("fixtures/install.jsonl"))
            roster = read_roster("docs/roster.json")
            first = process(db, queue, roster)
            self.assertEqual(process(db, queue, roster), {"replayed": len(queue)})
            placement = next(row for row in works(db) if row["code"] == "ripple")
            self.assertEqual((placement["room"], placement["revision"]), ("north", 1), first)
