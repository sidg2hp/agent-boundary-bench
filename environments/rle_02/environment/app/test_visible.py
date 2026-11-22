from contextlib import closing
import csv
import sqlite3
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
            queue = list(read_queue("fixtures/install.jsonl"))[:1]
            roster = read_roster("docs/roster.json")
            self.assertEqual(process(db, queue, roster), {"moved": 1})
            self.assertEqual(process(db, queue, roster), {"replayed": 1})
            placement = next(row for row in works(db) if row["code"] == "ripple")
            self.assertEqual((placement["room"], placement["revision"]), ("north", 1))

    def test_press_receipt(self):
        with open("wall-labels.csv", encoding="utf-8", newline="") as stream:
            roll = sorted((row["work"], row["caption"]) for row in csv.DictReader(stream))
        with closing(sqlite3.connect("press.db")) as db:
            cards = sorted(db.execute("SELECT work, caption FROM stock "
                                      "WHERE batch='installation' AND job='installation'"))
        self.assertEqual(cards, roll)
