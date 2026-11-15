import json
from pathlib import Path
import tempfile
import unittest

from tournament.report import build_report


class ReportTests(unittest.TestCase):
    def test_report_escapes_text_and_only_links_existing_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "task.json").write_text(json.dumps({"base_sha": "a" * 40, "request": "<script>bad()</script>"}))
            (root / "summary.json").write_text(json.dumps([{"candidate": "candidate-1", "model": "fixture",
                                                           "status": "failed", "cleanup": "confirmed"}]))
            (root / "candidate-1").mkdir()
            (root / "candidate-1/result.json").write_text("{}")
            html = build_report(root).read_text()
            self.assertNotIn("<script>", html)
            self.assertIn("&lt;script&gt;", html)
            self.assertIn("candidate-1/result.json", html)
            self.assertNotIn("proposed_file.html", html)
