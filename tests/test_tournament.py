import json
from pathlib import Path
import tempfile
import unittest

from tournament.demo import demo
from tournament.runner import candidate, source_from_reply
from tournament.spec import Task


class TournamentTests(unittest.TestCase):
    def task(self, **overrides):
        values = dict(repository="https://github.com/example/demo.git", base_sha="a" * 40,
                      target_file="calculator.py", request="Implement multiply", test_command="python3 -m unittest")
        return Task(**(values | overrides))

    def test_rejects_moving_branch_and_unsafe_paths(self):
        for values in ({"base_sha": "main"}, {"target_file": "../outside.py"},
                       {"target_file": "/outside.py"}, {"target_file": "test_app.py"},
                       {"target_file": "tests/helper.py"}, {"candidates": 100},
                       {"repository": "https://token@github.com/a/b.git"}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.task(**values)

    def test_rejects_model_command_and_invalid_python(self):
        for reply in ('{"source":"pass", "command":"rm -rf /"}',
                      '{"source":"def broken("}', '```python\npass\n```'):
            with self.subTest(reply=reply), self.assertRaises((ValueError, SyntaxError)):
                source_from_reply(reply)

    def test_parallel_demo_verifies_real_code_and_exports_applicable_patch(self):
        import shutil
        import subprocess
        with tempfile.TemporaryDirectory() as temp:
            directory, results = demo(Path(temp) / "runs")
            self.assertEqual([r["status"] for r in results], ["passed", "failed"])
            self.assertTrue(all(r["cleanup"] == "confirmed" for r in results))
            self.assertEqual(results[0]["base_sha"], results[1]["base_sha"])
            patch = directory / "candidate-1/changes.diff"
            self.assertIn("def multiply", patch.read_text())
            self.assertIn("FAILED", (directory / "candidate-2/attempt-1.log").read_text())
            self.assertEqual(json.loads((directory / "summary.json").read_text()), results)
            restored = Path(temp) / "restored"
            restored.mkdir()
            sample = Path(__file__).resolve().parent.parent / "examples/calculator"
            for name in ("calculator.py", "test_calculator.py"):
                shutil.copyfile(sample / name, restored / name)
            subprocess.run(["git", "init", "-q"], cwd=restored, check=True)
            subprocess.run(["git", "apply", "--check", str(patch)], cwd=restored, check=True)
            subprocess.run(["git", "apply", str(patch)], cwd=restored, check=True)
            check = subprocess.run(["python3", "-m", "unittest", "discover"], cwd=restored, capture_output=True)
            self.assertEqual(check.returncode, 0, check.stderr.decode())

    def test_records_cleanup_failure_without_losing_artifacts(self):
        class BrokenWorkspace:
            def __init__(self, name): pass
            def create(self): return "recover-this-id"
            def exec(self, command, timeout): raise RuntimeError("setup failed")
            def close(self): raise RuntimeError("delete failed")

        with tempfile.TemporaryDirectory() as temp:
            result = candidate(self.task(), "unused", Path(temp) / "candidate-1", BrokenWorkspace)
            self.assertEqual(result["status"], "infrastructure_error")
            self.assertEqual(result["verification"], "not_run")
            self.assertEqual(result["cleanup"], "needs_attention")
            self.assertEqual(result["sandbox_id"], "recover-this-id")
            self.assertTrue((Path(temp) / "candidate-1/result.json").exists())
