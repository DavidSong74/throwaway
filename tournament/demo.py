"""Offline plumbing demonstration. Only fixed, trusted fixture code runs locally."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from .runner import run
from .spec import Task


class FixtureWorkspace:
    def __init__(self, name):
        self.temp = tempfile.TemporaryDirectory(prefix="tournament-fixture-")
        self.repo = Path(self.temp.name) / "repo"
        self.name = name

    def create(self):
        return "local-fixture-" + self.name

    def exec(self, command, timeout=90):
        command = command.replace("/tmp/candidate-repo", str(self.repo))
        result = subprocess.run(command, shell=True, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=timeout)
        return result.returncode, result.stdout

    def close(self):
        self.temp.cleanup()


class FixtureModel:
    def complete(self, model, messages, max_tokens):
        context = json.loads(messages[1]["content"])
        source = context["source"]
        if model == "fixture-correct":
            source += "\n\ndef multiply(a, b):\n    return a * b\n"
        elif model == "fixture-incorrect":
            source += "\n\ndef multiply(a, b):\n    return a + b\n"
        else:
            raise ValueError("Unknown fixture")
        return json.dumps({"source": source}), None


def demo(root=Path("results")):
    with tempfile.TemporaryDirectory(prefix="tournament-base-") as temp:
        base = Path(temp)
        sample = Path(__file__).resolve().parent.parent / "examples" / "calculator"
        for name in ("calculator.py", "test_calculator.py"):
            shutil.copyfile(sample / name, base / name)
        for args in (["git", "init", "-q"], ["git", "add", "calculator.py", "test_calculator.py"],
                     ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                      "commit", "-qm", "Trusted baseline"]):
            subprocess.run(args, cwd=base, check=True, capture_output=True)
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=base, text=True).strip()
        task = Task("https://github.com/fixture/calculator.git", sha, "calculator.py",
                    "Implement multiply, preserving existing operations", "python3 -m unittest discover -v",
                    candidates=2, max_repairs=0)

        class LocalFixture(FixtureWorkspace):
            def exec(self, command, timeout=90):
                if command.startswith("git clone -- "):
                    result = subprocess.run(["git", "clone", "--", str(base), str(self.repo)],
                                            capture_output=True, text=True, timeout=timeout)
                    return result.returncode, result.stdout + result.stderr
                return super().exec(command, timeout)

        return run(task, ["fixture-correct", "fixture-incorrect"], root, LocalFixture, FixtureModel)
