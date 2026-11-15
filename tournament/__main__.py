import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys

from .providers import Nosana
from .runner import run
from .spec import Task


def main():
    parser = argparse.ArgumentParser(description="Compare independent coding candidates")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("demo", help="Offline, deterministic fixtures; no cloud or AI calls")
    commands.add_parser("models", help="Read currently served Nosana models; requires API key")
    prepare_parser = commands.add_parser("prepare-day-planner", help="Snapshot local HTML and write a run configuration; no network")
    prepare_parser.add_argument("--file", type=Path, default=Path("examples/day_planner/Day Planner.html"))
    for name in ("plan", "run"):
        sub = commands.add_parser(name)
        sub.add_argument("task", type=Path)
        if name == "run":
            sub.add_argument("--live", action="store_true", help="Required to create paid cloud resources")
            sub.add_argument("--models", help="Comma-separated available IDs, one per candidate")
    args = parser.parse_args()
    try:
        if args.command == "prepare-day-planner":
            from .prepare import prepare
            config, task = prepare(args.file)
            print(f"Prepared: {config}")
            print(f"Exact baseline: {task.base_sha}")
            print("Next: python3 -m tournament plan task.day-planner.local.json")
            return 0
        elif args.command == "demo":
            from .demo import demo
            directory, results = demo()
            print("OFFLINE FIXTURES: deterministic code, not AI-generated candidates")
        elif args.command == "models":
            # Deliberately display only catalog fields, never credentials or headers.
            for model in Nosana().models():
                print(json.dumps({k: model.get(k) for k in
                    ("id", "available", "context_length", "max_output_tokens", "pricing")}))
            return 0
        else:
            task = Task(**json.loads(args.task.read_text()))
            if args.command == "plan":
                print(json.dumps({"task": asdict(task),
                    "max_inference_calls": task.candidates * (1 + task.max_repairs),
                    "cloud_resources_created": False,
                    "scope": ("One standalone HTML file, browser verification, exported HTML and screenshots"
                              if task.verification == "day_planner" else "One existing Python file"),
                    "verification_profile": task.verification,
                    "preview": "Exported HTML; sandbox deleted after capture, no hosted preview",
                    "dollar_spend_cap": "Not implemented; review provider account limits"}, indent=2))
                return 0
            if not args.live:
                raise ValueError("Use plan first; cloud execution requires --live")
            if not os.environ.get("DAYTONA_API_KEY"):
                raise ValueError("Set DAYTONA_API_KEY")
            model_ids = args.models
            if model_ids is None:
                model_ids = ",".join([os.environ.get("NOSANA_MODEL_ID", "")] * task.candidates)
            models = [model.strip() for model in model_ids.split(",")]
            if len(models) != task.candidates or any(not m for m in models):
                raise ValueError("Provide one model ID per candidate")
            available = {m["id"] for m in Nosana().models() if m.get("available", True)}
            if any(model not in available for model in models):
                raise ValueError("Requested model is unavailable; run models to inspect the live catalog")
            directory, results = run(task, models)
        print(f"Artifacts: {directory.resolve()}")
        for result in results:
            print(f"{result['candidate']}: {result['status']} | cleanup={result['cleanup']}")
        return 0 if all(r["status"] == "passed" and r["cleanup"] == "confirmed" for r in results) else 1
    except (ValueError, OSError, KeyError, TypeError, RuntimeError) as error:
        print(f"Cannot start: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
