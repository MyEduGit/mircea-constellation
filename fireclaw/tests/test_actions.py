"""Tests for fireclaw/actions.py — action primitives, dry-run, dispatch."""
from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from fireclaw import actions


class TestRestartSystemd(unittest.TestCase):
    def test_dry_run_no_execution(self):
        r = actions.restart_systemd("fake.service", dry_run=True)
        self.assertFalse(r["executed"])
        self.assertIn("DRY-RUN", r["stderr"])
        self.assertEqual(r["kind"], "restart_systemd")

    def test_executes_when_not_dry(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result):
            r = actions.restart_systemd("fake.service", dry_run=False)
        self.assertTrue(r["executed"])
        self.assertEqual(r["exit_code"], 0)

    def test_remote_uses_ssh(self):
        captured = {}

        def fake_run(cmd, **kw):
            captured["cmd"] = cmd
            m = MagicMock()
            m.returncode = 0
            m.stdout = ""
            m.stderr = ""
            return m

        with patch("subprocess.run", side_effect=fake_run):
            actions.restart_systemd("fake.service", host="myhost", dry_run=False)
        self.assertIn("ssh", captured["cmd"])
        self.assertIn("myhost", captured["cmd"])


class TestRestartDocker(unittest.TestCase):
    def test_dry_run(self):
        r = actions.restart_docker("mycontainer", dry_run=True)
        self.assertFalse(r["executed"])
        self.assertIn("DRY-RUN", r["stderr"])
        self.assertEqual(r["kind"], "restart_docker")

    def test_command_not_found_returns_not_executed(self):
        with patch("subprocess.run", side_effect=FileNotFoundError("docker")):
            r = actions.restart_docker("c", dry_run=False)
        self.assertFalse(r["executed"])
        self.assertIn("not found", r["stderr"])


class TestDisableN8nWorkflow(unittest.TestCase):
    def test_dry_run(self):
        r = actions.disable_n8n_workflow("wf-123", dry_run=True)
        self.assertFalse(r["executed"])
        self.assertIn("DRY-RUN", r["stderr"])

    def test_success_response(self):
        resp = MagicMock()
        resp.status = 200
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=resp):
            r = actions.disable_n8n_workflow("wf-1",
                                              base_url="http://localhost:5678",
                                              api_key="test-key",
                                              dry_run=False)
        self.assertTrue(r["executed"])
        self.assertEqual(r["exit_code"], 0)


class TestQuarantine(unittest.TestCase):
    def test_dry_run(self):
        r = actions.quarantine("botname", dry_run=True)
        self.assertFalse(r["executed"])
        self.assertIn("DRY-RUN", r["stderr"])

    def test_creates_marker_file(self):
        with tempfile.TemporaryDirectory() as d:
            r = actions.quarantine("mybot",
                                    marker_dir=d,
                                    dry_run=False)
        self.assertTrue(r["executed"])
        self.assertEqual(r["exit_code"], 0)
        self.assertIn("mybot", r["stdout"])


class TestAlertTelegram(unittest.TestCase):
    def test_dry_run(self):
        r = actions.alert_telegram("test message", dry_run=True)
        self.assertFalse(r["executed"])
        self.assertIn("DRY-RUN", r["stderr"])

    def test_skipped_when_no_credentials(self):
        env_backup = {k: os.environ.pop(k, None)
                      for k in ("FIRECLAW_TG_BOT_TOKEN", "FIRECLAW_TG_CHAT_ID")}
        try:
            r = actions.alert_telegram("msg", bot_token=None, chat_id=None,
                                        dry_run=False)
        finally:
            for k, v in env_backup.items():
                if v is not None:
                    os.environ[k] = v
        self.assertFalse(r["executed"])
        self.assertIn("skipped", r["stderr"])


class TestAlertOnly(unittest.TestCase):
    def test_always_succeeds(self):
        r = actions.alert_only("status.json stale")
        self.assertTrue(r["executed"])
        self.assertEqual(r["exit_code"], 0)
        self.assertIn("stale", r["stdout"])

    def test_dry_run_still_succeeds(self):
        r = actions.alert_only("msg", dry_run=True)
        self.assertEqual(r["exit_code"], 0)


class TestExecCommand(unittest.TestCase):
    def test_dry_run(self):
        r = actions.exec_command(["echo", "hello"], dry_run=True)
        self.assertFalse(r["executed"])
        self.assertIn("DRY-RUN", r["stderr"])
        self.assertEqual(r["kind"], "exec_command")

    def test_string_command_split(self):
        r = actions.exec_command("echo hello world", dry_run=True)
        self.assertIn("echo", r["stderr"])

    def test_empty_command_refused(self):
        r = actions.exec_command([], dry_run=False)
        self.assertFalse(r["executed"])
        self.assertIn("empty", r["stderr"])

    def test_runs_real_command(self):
        r = actions.exec_command(["true"], dry_run=False)
        self.assertTrue(r["executed"])
        self.assertEqual(r["exit_code"], 0)

    def test_failed_command_exit_nonzero(self):
        r = actions.exec_command(["false"], dry_run=False)
        self.assertTrue(r["executed"])
        self.assertNotEqual(r["exit_code"], 0)

    def test_command_not_found(self):
        r = actions.exec_command(["__no_such_binary__"], dry_run=False)
        self.assertFalse(r["executed"])
        self.assertIn("not found", r["stderr"])


class TestDispatch(unittest.TestCase):
    def test_all_kinds_in_dispatch(self):
        expected = {"restart_systemd", "restart_docker", "disable_n8n_workflow",
                    "quarantine", "alert_telegram", "alert_only", "exec_command"}
        self.assertEqual(set(actions.DISPATCH.keys()), expected)

    def test_execute_unknown_kind(self):
        r = actions.execute({"kind": "nonexistent"})
        self.assertFalse(r["executed"])
        self.assertIn("unknown action kind", r["stderr"])

    def test_execute_alert_only_via_dispatch(self):
        r = actions.execute({"kind": "alert_only", "message": "hi"})
        self.assertTrue(r["executed"])
        self.assertEqual(r["exit_code"], 0)

    def test_execute_exec_command_via_dispatch(self):
        r = actions.execute({"kind": "exec_command", "command": ["true"]})
        self.assertTrue(r["executed"])
        self.assertEqual(r["exit_code"], 0)


if __name__ == "__main__":
    unittest.main()
