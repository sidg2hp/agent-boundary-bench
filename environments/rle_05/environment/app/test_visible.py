import subprocess
import sys
import unittest


class SettlementTests(unittest.TestCase):
    def test_desk_examples(self):
        run = subprocess.run([sys.executable, "settle.py", "check"], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout)
