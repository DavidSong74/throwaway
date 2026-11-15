import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tournament.html_source import validate_html
from tournament.prepare import prepare
from tournament.runner import run, source_from_reply
from tournament.spec import Task


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "examples/day_planner/Day Planner.html"


def filtered_fixture(source):
    """Deterministic test fixture, never presented as an AI result or product baseline."""
    changes = {
        '<div id="tl"></div>': '<label for="search">Search tasks</label><input id="search">'
        '<label for="status">Status</label><select id="status"><option value="all">All</option>'
        '<option value="open">Open</option><option value="done">Done</option></select>'
        '<div id="filter-empty" hidden>No matching tasks.</div><div id="tl"></div>',
        'var P=plan(),tl=$("tl");tl.textContent="";': 'var P=plan(),tl=$("tl");tl.textContent="";'
        'function matches(t){var q=$("search").value.toLowerCase(),s=$("status").value;'
        'return t.title.toLowerCase().includes(q)&&(s==="all"||(s==="done"?t.done:!t.done))}'
        '$("filter-empty").hidden=!tasks.length||tasks.some(matches);',
        'P.out.forEach(function(o){': 'P.out.filter(function(o){return matches(o.t)}).forEach(function(o){',
        'tasks.filter(function(t){return t.done})': 'tasks.filter(function(t){return t.done&&matches(t)})',
        'load();$("s").value': '$("search").addEventListener("input",render);'
        '$("status").addEventListener("change",render);load();$("s").value',
    }
    for before, after in changes.items():
        assert source.count(before) == 1, before
        source = source.replace(before, after)
    return source


class HtmlTests(unittest.TestCase):
    def test_source_validation_accepts_complete_html_and_rejects_truncation(self):
        source = SOURCE.read_text()
        self.assertEqual(source_from_reply(json.dumps({"source": source}), ".html"), source)
        for invalid in (source.replace("</html>", ""), source.replace("</script>", ""),
                        source.replace('id="tl"', 'id="t"'), "<div>Fragment</div>"):
            with self.subTest(invalid=invalid[:30]), self.assertRaises(ValueError):
                validate_html(invalid)

    def test_html_requires_independent_verification_profile(self):
        with self.assertRaises(ValueError):
            Task("https://github.com/example/demo.git", "a" * 40, "Day Planner.html", "Improve", "true")

    def test_prepare_creates_minimal_pinned_baseline_without_touching_input(self):
        before = SOURCE.read_bytes()
        with tempfile.TemporaryDirectory() as temp:
            config, task = prepare(SOURCE, Path(temp))
            self.assertEqual(Task(**json.loads(config.read_text())), task)
            files = subprocess.check_output(["git", "ls-files"], cwd=task.repository, text=True)
            self.assertEqual(files.strip(), "Day Planner.html")
            self.assertEqual(SOURCE.read_bytes(), before)


@unittest.skipUnless(importlib.util.find_spec("playwright"), "Install .[browser] and Chromium for browser checks")
class BrowserTests(unittest.TestCase):
    def test_baseline_regressions_and_required_feature_failure_are_distinct(self):
        from tournament.verification.day_planner import verify
        with tempfile.TemporaryDirectory() as temp:
            baseline = verify(SOURCE, Path(temp) / "baseline", baseline=True)
            self.assertTrue(all(c["status"] == "passed" for c in baseline["checks"].values()), baseline)
            feature = verify(SOURCE, Path(temp) / "features")
            self.assertEqual(feature["checks"]["search"]["status"], "failed")
            self.assertEqual(feature["checks"]["combined_status_filters"]["status"], "not_run")

    def test_local_snapshot_to_parallel_html_artifacts_and_patch(self):
        from tournament.demo import FixtureWorkspace

        class HtmlFixtureModel:
            def complete(self, model, messages, max_tokens):
                source = json.loads(messages[1]["content"])["source"]
                if model == "fixture-correct":
                    source = filtered_fixture(source)
                return json.dumps({"source": source}), None

        class BrowserWorkspace(FixtureWorkspace):
            def exec(self, command, timeout=90):
                # These tests run only fixed trusted fixtures, never live model output.
                if "pip install" in command or "playwright install" in command:
                    return 0, "Using already-installed local test browser"
                command = command.replace("/tmp/tournament-", self.temp.name + "/tournament-")
                import os
                browser_path = os.environ["PLAYWRIGHT_BROWSERS_PATH"]
                command = command.replace(self.temp.name + "/tournament-browsers", browser_path)
                import shlex
                command = command.replace("python3 ", shlex.quote(sys.executable) + " ")
                return super().exec(command, timeout)

        with tempfile.TemporaryDirectory() as temp:
            _, task = prepare(SOURCE, Path(temp))
            from dataclasses import replace
            task = replace(task, max_repairs=0)
            directory, records = run(task, ["fixture-correct", "fixture-incorrect"],
                                     Path(temp) / "runs", BrowserWorkspace, HtmlFixtureModel)
            self.assertEqual([r["status"] for r in records], ["passed", "failed"], records)
            self.assertTrue(all(r["cleanup"] == "confirmed" for r in records))
            winner = directory / "candidate-1"
            self.assertTrue((winner / "proposed_file.html").exists())
            self.assertTrue((winner / "desktop.png").exists())
            self.assertTrue((winner / "mobile.png").exists())
            self.assertTrue((directory / "candidate-2/failure.png").exists())
            report = json.loads((winner / "checks.json").read_text())
            self.assertTrue(all(c["status"] == "passed" for c in report["checks"].values()), report)
            clean = Path(temp) / "clean"
            subprocess.run(["git", "clone", "--", str(directory / "baseline.bundle"), str(clean)],
                           check=True, capture_output=True)
            subprocess.run(["git", "checkout", "--detach", task.base_sha], cwd=clean, check=True, capture_output=True)
            subprocess.run(["git", "apply", "--check", str(winner / "changes.diff")], cwd=clean, check=True)
            subprocess.run(["git", "apply", str(winner / "changes.diff")], cwd=clean, check=True)
            self.assertEqual((clean / "Day Planner.html").read_text(), (winner / "proposed_file.html").read_text())
