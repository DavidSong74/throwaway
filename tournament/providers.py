"""Nosana hosted inference and Daytona v2; imported without cloud dependencies."""
import json
import os
import shlex
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class Nosana:
    def __init__(self):
        self.key = os.environ.get("NOSANA_API_KEY", "")
        self.base = os.environ.get("NOSANA_API_BASE", "https://inference.nosana.com/v1").rstrip("/")
        self.timeout = int(os.environ.get("NOSANA_REQUEST_TIMEOUT", "300"))
        if not 10 <= self.timeout <= 600:
            raise ValueError("NOSANA_REQUEST_TIMEOUT must be between 10 and 600 seconds")
        if not self.key:
            raise ValueError("Set NOSANA_API_KEY")
        url = urlparse(self.base)
        if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError("NOSANA_API_BASE must be a trusted HTTPS endpoint without credentials or query")

    def _request(self, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        req = Request(self.base + path, data=data, headers={
            "Authorization": f"Bearer {self.key}", "Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=self.timeout if payload is not None else 30) as response:
                raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValueError("Inference response exceeds 2 MB")
            return json.loads(raw)
        except HTTPError as error:
            # Do not log raw provider bodies or request headers containing credentials.
            raise RuntimeError(f"Nosana HTTP {error.code}; check endpoint, credits, and model availability") from None

    def models(self):
        return self._request("/models").get("data", [])

    def complete(self, model, messages, max_tokens):
        payload = {"model": model, "messages": messages, "max_tokens": max_tokens, "stream": False}
        if model.startswith("qwen/"):
            payload["chat_template_kwargs"] = {"enable_thinking": False}
        response = self._request("/chat/completions", payload)
        choice = response["choices"][0]
        if choice.get("finish_reason") == "length":
            raise ValueError("Model output was truncated; reduce task scope or increase output budget")
        content = choice["message"].get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Model returned no final answer")
        return content, response.get("usage")


class DaytonaWorkspace:
    """Use v2 when enabled; fall back only on its explicit feature-disabled response."""
    def __init__(self, name):
        from daytona import Daytona
        self.client = Daytona()
        self.sandbox = None
        self.name = name
        self.api_version = os.environ.get("DAYTONA_API_VERSION", "auto")
        if self.api_version not in {"auto", "v0", "v2"}:
            raise ValueError("DAYTONA_API_VERSION must be auto, v0, or v2")

    def create(self):
        if self.api_version != "v0":
            try:
                self.sandbox = self.client.v2.create(name=self.name, wait_seconds=60)
                self.api_version = "v2"
                return self.sandbox.id
            except Exception as error:
                if self.api_version != "auto" or getattr(error, "code", None) != "FEATURE_NOT_ENABLED":
                    raise
        from daytona.v0 import CreateSandboxFromSnapshotParams
        self.api_version = "v0"
        self.sandbox = self.client.v0.create(CreateSandboxFromSnapshotParams(
            name=self.name, language="python", auto_stop_interval=15, auto_delete_interval=0), timeout=90)
        return self.sandbox.id

    def exec(self, command, timeout=90):
        if self.api_version == "v0":
            # A provider wait timeout alone may leave processes alive; use a remote deadline too.
            bounded = f"timeout -k 5 {int(timeout)}s sh -c " + shlex.quote(command)
            result = self.sandbox.process.exec(bounded, timeout=timeout + 20)
            return result.exit_code, result.result or ""
        result = self.sandbox.exec(command, timeout=timeout + 10, execution_timeout=timeout)
        return result.exit_code, result.output or ""

    def close(self):
        try:
            if self.sandbox is not None:
                if self.api_version == "v0":
                    self.client.v0.delete(self.sandbox, timeout=60, wait=True)
                else:
                    self.client.v2.delete(self.sandbox)
                    self.sandbox.wait_for_state(["destroyed"], timeout=60)
        finally:
            self.client.close()

    def start_preview(self, port=8080, lifetime=900):
        import time
        from urllib.parse import quote
        if self.api_version != "v0":
            raise RuntimeError("Hosted preview adapter currently requires the standard Daytona API")
        from daytona.v0 import SessionExecuteRequest
        session = "preview-" + str(port)
        self.sandbox.process.create_session(session)
        self.sandbox.process.execute_session_command(session, SessionExecuteRequest(
            command=f"cd /tmp/candidate-repo && python3 -m http.server {port} --bind 0.0.0.0", run_async=True))
        for _ in range(20):
            code, _ = self.exec(f"python3 -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:{port}/',timeout=2)\"", 5)
            if code == 0:
                break
            time.sleep(1)
        else:
            raise RuntimeError("Preview server did not become ready")
        signed = self.sandbox.create_signed_preview_url(port, expires_in_seconds=lifetime)
        return signed.url.rstrip("/") + "/" + quote("Day Planner.html"), time.time() + lifetime
