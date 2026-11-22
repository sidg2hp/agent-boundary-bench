from pathlib import Path
import tempfile
import unittest
from catalog import collect
from markdown import parse
from publishing import fingerprint, publish


class DigestTests(unittest.TestCase):
    def test_vendored_release(self):
        self.assertEqual([str(r.version) for r in collect("workspace.toml", ["loom"])], ["1.4.0"])

    def test_fenced_headings(self):
        text = "## 1.0.0\n- one\n```md\n## 9.0.0\n```\n"
        self.assertEqual([r.sections for r in parse("x", text)], [{"Changes": ["one"]}])

    def test_tools_channel_waits_for_desk_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "w.toml").write_text('[[package]]\nname = "kit"\nchangelog = "kit.md"\nchannel = "tools"\n')
            (root / "kit.md").write_text("## 1.0.0\n- one\n")
            ledger = root / "desk.sqlite3"
            self.assertEqual(collect(root / "w.toml", ledger=ledger), [])
            publish("kit-1.0-preview", journal=fingerprint(root / "kit.md"), path=ledger)
            self.assertEqual([str(r.version) for r in collect(root / "w.toml", ledger=ledger)], ["1.0.0"])
            (root / "kit.md").write_text("## 1.0.0\n- one\n- two\n")
            self.assertEqual(collect(root / "w.toml", ledger=ledger), [])
