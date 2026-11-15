import os
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from tournament.providers import DaytonaWorkspace


class ProviderTests(unittest.TestCase):
    def fake_modules(self, client):
        daytona = ModuleType("daytona")
        daytona.Daytona = lambda: client
        v0 = ModuleType("daytona.v0")
        v0.CreateSandboxFromSnapshotParams = lambda **kwargs: SimpleNamespace(**kwargs)
        return {"daytona": daytona, "daytona.v0": v0}

    def test_feature_disabled_uses_standard_api_and_waits_for_deletion(self):
        error = RuntimeError("feature disabled")
        error.code = "FEATURE_NOT_ENABLED"
        client = Mock()
        client.v2.create.side_effect = error
        sandbox = client.v0.create.return_value
        sandbox.id = "fixture-sandbox"
        sandbox.process.exec.return_value = SimpleNamespace(exit_code=0, result="5\n")
        with patch.dict("sys.modules", self.fake_modules(client)), patch.dict(os.environ, {}, clear=True):
            workspace = DaytonaWorkspace("fixture")
            self.assertEqual(workspace.create(), "fixture-sandbox")
            self.assertEqual(workspace.api_version, "v0")
            self.assertEqual(workspace.exec("printf '5\\n'", 30), (0, "5\n"))
            command = sandbox.process.exec.call_args.args[0]
            self.assertTrue(command.startswith("timeout -k 5 30s sh -c "))
            workspace.close()
            client.v0.delete.assert_called_once_with(sandbox, timeout=60, wait=True)
            client.close.assert_called_once()

    def test_authentication_failures_do_not_create_second_sandbox(self):
        error = RuntimeError("not authorized")
        error.code = "UNAUTHORIZED"
        client = Mock()
        client.v2.create.side_effect = error
        with patch.dict("sys.modules", self.fake_modules(client)), patch.dict(os.environ, {}, clear=True):
            workspace = DaytonaWorkspace("fixture")
            with self.assertRaises(RuntimeError):
                workspace.create()
            client.v0.create.assert_not_called()
            workspace.close()
