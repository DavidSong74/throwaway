import json
from pathlib import Path
import tempfile
import unittest

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

    def test_timeout_keeps_failure_stage_and_cleans_up(self):
        class TimeoutWorkspace:
            def __init__(self, name): pass
            def create(self): return "fixture-timeout"
            def exec(self, command, timeout): raise TimeoutError()
            def close(self): pass

        with tempfile.TemporaryDirectory() as temp:
            record = candidate(self.task(), "unused", Path(temp) / "candidate-1", TimeoutWorkspace)
            self.assertEqual(record["status"], "timed_out")
            self.assertEqual(record["failed_stage"], "preparing_source")
            self.assertEqual(record["cleanup"], "confirmed")
