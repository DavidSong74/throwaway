"""Operator-authored configuration, never model-authored commands."""
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re


@dataclass(frozen=True)
class Task:
    repository: str
    base_sha: str
    target_file: str
    request: str
    test_command: str
    candidates: int = 2
    max_repairs: int = 1
    max_output_tokens: int = 2400
    command_timeout: int = 90
    verification: str = "command"

    def __post_init__(self):
        is_github = re.fullmatch(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?", self.repository)
        is_local = Path(self.repository).is_absolute() and (Path(self.repository) / ".git").is_dir()
        if not is_github and not is_local:
            raise ValueError("Use a public HTTPS GitHub URL or an absolute path to an explicit local Git repository")
        if not re.fullmatch(r"[0-9a-fA-F]{40}", self.base_sha):
            raise ValueError("base_sha must be a full 40-character commit SHA")
        path = PurePosixPath(self.target_file)
        if (path.is_absolute() or ".." in path.parts or "\\" in self.target_file
                or not path.parts or any(p.startswith(".") for p in path.parts)
                or path.suffix.lower() not in {".py", ".html"} or path.name.startswith("test")
                or any(p in {"tests", "verification"} for p in path.parts)):
            raise ValueError("target_file must be a relative non-test Python or HTML source path")
        if self.verification not in {"command", "day_planner"}:
            raise ValueError("Unknown verification profile")
        if path.suffix.lower() == ".html" and self.verification != "day_planner":
            raise ValueError("HTML tasks require the trusted day_planner browser verification profile")
        if self.verification == "day_planner" and path.suffix.lower() != ".html":
            raise ValueError("day_planner verification requires an HTML target")
        if not self.request.strip() or not self.test_command.strip():
            raise ValueError("request and test_command are required")
        for name, lo, hi in [("candidates", 1, 4), ("max_repairs", 0, 2),
                             ("max_output_tokens", 64, 16384), ("command_timeout", 1, 300)]:
            value = getattr(self, name)
            if type(value) is not int or not lo <= value <= hi:
                raise ValueError(f"{name} must be an integer from {lo} to {hi}")
