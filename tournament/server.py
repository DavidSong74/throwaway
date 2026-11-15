"""Local demo coordinator and static React host; credentials remain server-side."""
from datetime import datetime, timezone
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading
import time
from urllib.parse import urlsplit, unquote
from uuid import uuid4

from .config import load_local_env
from .prepare import prepare, REQUEST
from .runner import run, save_json

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
LOCK = threading.Lock()
ACTIVE = set()
ARTIFACTS = {"changes.diff", "selected.patch", "proposed_file.html", "checks.json", "desktop.png", "mobile.png",
             "failure.png", "attempt-1.log", "attempt-2.log", "baseline.log", "result.json", "infrastructure.log"}


def location(run_id):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,90}", run_id):
        raise ValueError("Invalid run ID")
    path = RESULTS / run_id
    if not path.is_dir():
        raise ValueError("Run not found")
    return path


def snapshot(path):
    task = json.loads((path / "task.json").read_text()) if (path / "task.json").exists() else {}
    candidates = []
    for i in (1, 2):
        file = path / f"candidate-{i}" / "result.json"
        d = json.loads(file.read_text()) if file.exists() else {"candidate": f"candidate-{i}", "stage": "queued", "status": "queued"}
        d["artifacts"] = [name for name in ARTIFACTS if (file.parent / name).is_file()]
        d["feature_check"] = d.get("verification", "not_run")
        candidates.append(d)
    selection = path / "selection.json"
    return {"id": path.name, "base_sha": task.get("base_sha"), "request": task.get("request", ""),
            "active": path.name in ACTIVE, "candidates": candidates,
            "selection": json.loads(selection.read_text()) if selection.exists() else None}


def cleanup_run(path):
    from daytona import Daytona
    for record in path.glob("candidate-*/result.json"):
        d = json.loads(record.read_text())
        if d.get("cleanup") == "confirmed" or not d.get("sandbox_id"):
            continue
        if path.name in ACTIVE:
            raise ValueError("Wait for generation to finish before cleaning up this run")
        try:
            with Daytona() as client:
                if d.get("execution_api") == "v0":
                    box = client.v0.get(d["sandbox_id"])
                    client.v0.delete(box, timeout=60, wait=True)
                else:
                    box = client.v2.get(d["sandbox_id"])
                    client.v2.delete(box)
                    box.wait_for_state(["destroyed"], timeout=60)
            d.update(cleanup="confirmed", preview="expired", preview_url=None)
        except Exception as error:
            if "NotFound" in type(error).__name__:
                d.update(cleanup="confirmed", preview="expired", preview_url=None)
            else:
                d["cleanup"] = "needs_attention"
        save_json(record, d)
    return snapshot(path)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Never log signed preview URLs or user prompts.

    def json(self, data, status=200):
        raw = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def path_parts(self):
        path = unquote(urlsplit(self.path).path)
        if path.startswith("/api/"): path = path[4:]
        return [p for p in path.split("/") if p]

    def do_GET(self):
        try:
            parts = self.path_parts()
            if parts == ["config"]:
                return self.json({"request": REQUEST, "model": os.environ.get("NOSANA_MODEL_ID", "not configured"), "target": "Day Planner.html"})
            if parts == ["runs"]:
                return self.json([snapshot(p) for p in sorted(RESULTS.glob("*"), reverse=True) if (p / "task.json").exists()])
            if len(parts) == 2 and parts[0] == "runs":
                return self.json(snapshot(location(parts[1])))
            if len(parts) == 6 and parts[0] == "runs" and parts[2] == "candidates" and parts[4] == "artifacts":
                path = location(parts[1])
                if parts[3] not in {"candidate-1", "candidate-2"} or parts[5] not in ARTIFACTS:
                    raise ValueError("Unknown artifact")
                file = path / parts[3] / parts[5]
                return self.file(file, download=parts[5] in {"proposed_file.html", "changes.diff", "selected.patch"})
            dist = ROOT / "ui" / "dist"
            relative = urlsplit(self.path).path.lstrip("/") or "index.html"
            file = (dist / relative).resolve()
            if not file.is_relative_to(dist.resolve()): raise ValueError("Invalid static path")
            return self.file(file if file.is_file() else dist / "index.html")
        except (ValueError, OSError, json.JSONDecodeError):
            self.json({"error": "Requested resource is unavailable"}, 404)

    def file(self, file, download=False):
        raw = file.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream" if download else mimetypes.guess_type(file.name)[0] or "text/plain")
        if download: self.send_header("Content-Disposition", f'attachment; filename="{file.name}"')
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers(); self.wfile.write(raw)

    def do_POST(self):
        try:
            host = self.headers.get("Host", "")
            origin = self.headers.get("Origin")
            if host not in {"127.0.0.1:8787", "localhost:8787"} or origin not in {None, "http://127.0.0.1:8787", "http://localhost:8787"}:
                return self.json({"error": "Local requests only"}, 403)
            size = int(self.headers.get("Content-Length", "0"))
            if size > 20000: raise ValueError("Request too large")
            body = json.loads(self.rfile.read(size) or "{}")
            parts = self.path_parts()
            if parts == ["runs"]:
                with LOCK:
                    if ACTIVE: raise ValueError("A run is already active; review it before launching another")
                    request = body.get("request", REQUEST)
                    if not isinstance(request, str) or not 1 <= len(request.strip()) <= 12000:
                        raise ValueError("Enter a change request")
                    _, task = prepare(ROOT / "examples/day_planner/Day Planner.html", ROOT)
                    task = replace(task, request=request, max_repairs=1)
                    model = os.environ.get("NOSANA_MODEL_ID", "")
                    if not model or not os.environ.get("DAYTONA_API_KEY") or not os.environ.get("NOSANA_API_KEY"):
                        raise ValueError("Configure the provider keys and model in .env")
                    rid = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex[:8]
                    path = RESULTS / rid; path.mkdir(parents=True)
                    from dataclasses import asdict
                    save_json(path / "task.json", asdict(task)); ACTIVE.add(rid)
                def worker():
                    try:
                        run(task, [model, model], directory=path, retain_previews=True)
                    except Exception as error:
                        save_json(path / "error.json", {"error": type(error).__name__})
                    finally:
                        ACTIVE.discard(rid)
                threading.Thread(target=worker, daemon=True).start()
                return self.json({"id": rid}, 202)
            if len(parts) == 3 and parts[0] == "runs":
                path = location(parts[1])
                if parts[2] == "cleanup":
                    return self.json(cleanup_run(path))
                if parts[2] == "select":
                    if path.name in ACTIVE: raise ValueError("Wait for the run to finish")
                    name = body.get("candidate")
                    if name not in {"candidate-1", "candidate-2"}: raise ValueError("Invalid candidate")
                    selected = path / "selection.json"
                    if selected.exists():
                        prior = json.loads(selected.read_text())
                        if prior["candidate"] != name: raise ValueError("This run already has a frozen selection")
                        return self.json(prior)
                    record = json.loads((path / name / "result.json").read_text())
                    if record.get("verification") != "passed": raise ValueError("Required checks must pass before selection")
                    with tempfile.TemporaryDirectory(prefix="selected-check-") as td:
                        subprocess.run(["git", "clone", "--", str(path / "baseline.bundle"), td], check=True, capture_output=True)
                        task = json.loads((path / "task.json").read_text())
                        subprocess.run(["git", "checkout", "--detach", task["base_sha"]], cwd=td, check=True, capture_output=True)
                        patch = path / name / "changes.diff"
                        subprocess.run(["git", "apply", "--check", str(patch.resolve())], cwd=td, check=True, capture_output=True)
                        subprocess.run(["git", "apply", str(patch.resolve())], cwd=td, check=True, capture_output=True)
                        import hashlib
                        digest = hashlib.sha256((Path(td) / task["target_file"]).read_bytes()).hexdigest()
                        if digest != record["source_sha256"]: raise ValueError("Patch differs from verified source")
                    (path / name / "selected.patch").write_bytes(patch.read_bytes())
                    result = {"candidate": name, "source_sha256": digest, "patch_application": "passed",
                              "download": f"/api/runs/{path.name}/candidates/{name}/artifacts/selected.patch"}
                    save_json(selected, result)
                    return self.json(result)
            raise ValueError("Unknown action")
        except ValueError as error:
            self.json({"error": str(error)}, 400)
        except Exception as error:
            self.json({"error": "Action failed: " + type(error).__name__}, 500)


def serve():
    load_local_env(ROOT / ".env")
    RESULTS.mkdir(exist_ok=True)
    def reap():
        while True:
            time.sleep(30)
            for p in RESULTS.glob("*"):
                if p.name in ACTIVE: continue
                for f in p.glob("candidate-*/result.json"):
                    try:
                        d = json.loads(f.read_text())
                        if d.get("cleanup") == "pending_review" and d.get("preview_expires_at", 0) < time.time():
                            cleanup_run(p); break
                    except Exception: pass
    threading.Thread(target=reap, daemon=True).start()
    print("Comparison UI: http://127.0.0.1:8787", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8787), Handler).serve_forever()


if __name__ == "__main__":
    serve()
