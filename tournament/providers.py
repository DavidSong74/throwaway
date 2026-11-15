"""Nosana hosted inference and Daytona v2; imported without cloud dependencies."""
import json
import os
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class Nosana:
    def __init__(self):
        self.key = os.environ.get("NOSANA_API_KEY", "")
        self.base = os.environ.get("NOSANA_API_BASE", "https://inference.nosana.com/v1").rstrip("/")
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
            with urlopen(req, timeout=90) as response:
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
        response = self._request("/chat/completions", {
            "model": model, "messages": messages, "max_tokens": max_tokens, "stream": False})
        choice = response["choices"][0]
        if choice.get("finish_reason") == "length":
            raise ValueError("Model output was truncated; reduce task scope or increase output budget")
        content = choice["message"].get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Model returned no final answer")
        return content, response.get("usage")


class DaytonaWorkspace:
    """One client and one isolated sandbox per candidate; no keys sent to the sandbox."""
    def __init__(self, name):
        from daytona import Daytona
        self.client = Daytona()
        self.sandbox = None
        self.name = name

    def create(self):
        self.sandbox = self.client.v2.create(name=self.name, wait_seconds=60)
        return self.sandbox.id

    def exec(self, command, timeout=90):
        result = self.sandbox.exec(command, timeout=timeout + 10, execution_timeout=timeout)
        return result.exit_code, result.output or ""

    def close(self):
        try:
            if self.sandbox is not None:
                self.client.v2.delete(self.sandbox)
                self.sandbox.wait_for_state(["destroyed"], timeout=60)
        finally:
            self.client.close()
