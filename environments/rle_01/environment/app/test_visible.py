import unittest
from catalog import collect
from markdown import parse


class DigestTests(unittest.TestCase):
    def test_vendored_release(self):
        self.assertEqual([str(r.version) for r in collect("workspace.toml", ["loom"])], ["1.4.0"])

    def test_fenced_headings(self):
        text = "## 1.0.0\n- one\n```md\n## 9.0.0\n```\n"
        self.assertEqual([r.sections for r in parse("x", text)], [{"Changes": ["one"]}])
