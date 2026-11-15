"""Create an explicit, minimal Git baseline from the user's standalone HTML file."""
from dataclasses import asdict
import json
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

from .html_source import validate_html
from .spec import Task


REQUEST = """Improve Day Planner's layout and add case-insensitive task-title search and
All/Open/Done status filters. Combine search and status. Show a useful message when
no tasks match. Filters must only affect display: calculate the schedule from ALL
open tasks before hiding nonmatching tasks, so filtering never changes start times.
Preserve task creation, priority ordering, fixed start times, break settings, done,
undo, delete, clear-all confirmation, and localStorage persistence (dayplanner.v1).
Keep the existing element IDs t,d,p,f,add,s,e,g,sum,clr,tl,un,done and scheduled task
markup .blk with a b title and buttons labeled Mark done and Delete; keep completed
tasks in #done li with an Undo button. Add a labeled search input with id=search,
a labeled select with id=status and values all/open/done (default all), and a
non-empty message with id=filter-empty visible when existing tasks have no matches.
Keep filters working after rerender/reload and controls usable at 390px wide.
Return one complete standalone HTML file with inline CSS/JS, no build dependencies,
external scripts, new remote services, or markdown. Do not remove existing features.
"""


def prepare(source, root=Path.cwd()):
    source, root = Path(source).resolve(), Path(root).resolve()
    text = source.read_text(encoding="utf-8")
    validate_html(text)
    if len(text.encode()) > 64_000:
        raise ValueError("Day Planner source exceeds 64 KB")
    baseline = root / "work" / ("day-planner-base-" + uuid4().hex[:8])
    baseline.mkdir(parents=True)
    shutil.copyfile(source, baseline / "Day Planner.html")
    for args in (["git", "init", "-q"], ["git", "add", "--", "Day Planner.html"],
                 ["git", "-c", "user.name=Tournament baseline",
                  "-c", "user.email=baseline@example.invalid", "-c", "commit.gpgsign=false",
                  "commit", "-qm", "Snapshot Day Planner baseline"]):
        subprocess.run(args, cwd=baseline, check=True, capture_output=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=baseline, text=True).strip()
    task = Task(str(baseline), sha, "Day Planner.html", REQUEST,
                "coordinator-managed browser checks", max_output_tokens=12000,
                command_timeout=300, verification="day_planner")
    config = root / "task.day-planner.local.json"
    # Repeated prepares leave earlier snapshots intact and explicitly refresh this task.
    config.write_text(json.dumps(asdict(task), indent=2) + "\n")
    return config, task
