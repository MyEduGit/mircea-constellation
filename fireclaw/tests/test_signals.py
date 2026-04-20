"""Tests for fireclaw/signals.py — all collectors, no live network required."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from fireclaw import signals


class TestHttpSignal(unittest.TestCase):
    def _mock_response(self, status: int):
        resp = MagicMock()
        resp.status = status
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    def test_ok_when_status_matches(self):
        with patch("urllib.request.urlopen",
                   return_value=self._mock_response(200)):
            r = signals.http("http://localhost/health", expect_status=200)
        self.assertTrue(r["ok"])
        self.assertEqual(r["kind"], "http")

    def test_not_ok_when_status_differs(self):
        with patch("urllib.request.urlopen",
                   return_value=self._mock_response(503)):
            r = signals.http("http://localhost/health", expect_status=200)
        self.assertFalse(r["ok"])

    def test_not_ok_on_connection_error(self):
        import urllib.error
        with patch("urllib.request.urlopen",
                   side_effect=urllib.error.URLError("refused")):
            r = signals.http("http://localhost/health")
        self.assertFalse(r["ok"])
        self.assertIn("unreachable", r["detail"])

    def test_http_error_matching_expect(self):
        import urllib.error
        err = urllib.error.HTTPError(
            "http://x", 404, "Not Found", {}, None)
        with patch("urllib.request.urlopen", side_effect=err):
            r = signals.http("http://x", expect_status=404)
        self.assertTrue(r["ok"])


class TestTcpSignal(unittest.TestCase):
    def test_ok_when_port_open(self):
        with patch("socket.create_connection", return_value=MagicMock(
                __enter__=lambda s: s, __exit__=MagicMock(return_value=False))):
            r = signals.tcp("localhost", 8080)
        self.assertTrue(r["ok"])
        self.assertEqual(r["kind"], "tcp")

    def test_not_ok_when_port_closed(self):
        with patch("socket.create_connection",
                   side_effect=OSError("connection refused")):
            r = signals.tcp("localhost", 9999)
        self.assertFalse(r["ok"])
        self.assertIn("9999", r["detail"])


class TestFileFieldSignal(unittest.TestCase):
    def _write_json(self, data: dict, path: str) -> None:
        with open(path, "w") as f:
            json.dump(data, f)

    def test_ok_when_field_matches(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w",
                                        delete=False) as f:
            json.dump({"fleet": {"status": "ok"}}, f)
            fname = f.name
        try:
            r = signals.file_field(fname, "fleet.status", "ok")
            self.assertTrue(r["ok"])
        finally:
            os.unlink(fname)

    def test_not_ok_when_field_mismatches(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w",
                                        delete=False) as f:
            json.dump({"fleet": {"status": "error"}}, f)
            fname = f.name
        try:
            r = signals.file_field(fname, "fleet.status", "ok")
            self.assertFalse(r["ok"])
        finally:
            os.unlink(fname)

    def test_not_ok_when_file_missing(self):
        r = signals.file_field("/nonexistent/path.json", "x", "ok")
        self.assertFalse(r["ok"])
        self.assertIn("missing", r["detail"])

    def test_not_ok_when_field_absent(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w",
                                        delete=False) as f:
            json.dump({"other": "value"}, f)
            fname = f.name
        try:
            r = signals.file_field(fname, "fleet.status", "ok")
            self.assertFalse(r["ok"])
            self.assertIn("missing field", r["detail"])
        finally:
            os.unlink(fname)

    def test_not_ok_on_invalid_json(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w",
                                        delete=False) as f:
            f.write("not json {{{")
            fname = f.name
        try:
            r = signals.file_field(fname, "x", "ok")
            self.assertFalse(r["ok"])
        finally:
            os.unlink(fname)


class TestProcessSignal(unittest.TestCase):
    def test_ok_when_process_found(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "1234\n"
        with patch("subprocess.run", return_value=mock_result):
            r = signals.process(name="python3")
        self.assertTrue(r["ok"])
        self.assertIn("1234", r["detail"])

    def test_not_ok_when_process_missing(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result):
            r = signals.process(name="nonexistent_daemon_xyz")
        self.assertFalse(r["ok"])

    def test_ok_with_live_pid_file(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False,
                                         suffix=".pid") as f:
            f.write(str(os.getpid()))
            fname = f.name
        try:
            r = signals.process(pid_file=fname)
            self.assertTrue(r["ok"])
            self.assertIn(str(os.getpid()), r["detail"])
        finally:
            os.unlink(fname)

    def test_not_ok_with_missing_pid_file(self):
        r = signals.process(pid_file="/tmp/fireclaw_no_such.pid")
        self.assertFalse(r["ok"])
        self.assertIn("missing", r["detail"])

    def test_not_ok_with_stale_pid_in_file(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False,
                                         suffix=".pid") as f:
            f.write("999999999")  # almost certainly not a real PID
            fname = f.name
        try:
            r = signals.process(pid_file=fname)
            self.assertFalse(r["ok"])
        finally:
            os.unlink(fname)

    def test_not_ok_when_neither_name_nor_pid_file(self):
        r = signals.process()
        self.assertFalse(r["ok"])
        self.assertIn("neither", r["detail"])


class TestCollectDispatch(unittest.TestCase):
    def test_unknown_kind_returns_not_ok(self):
        r = signals.collect({"kind": "bogus"})
        self.assertFalse(r["ok"])
        self.assertIn("unknown signal kind", r["detail"])

    def test_missing_kind_returns_not_ok(self):
        r = signals.collect({})
        self.assertFalse(r["ok"])

    def test_dispatches_file(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w",
                                        delete=False) as f:
            json.dump({"s": "ok"}, f)
            fname = f.name
        try:
            r = signals.collect({"kind": "file", "path": fname,
                                  "field": "s", "expect": "ok"})
            self.assertTrue(r["ok"])
        finally:
            os.unlink(fname)

    def test_dispatches_process(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "42\n"
        with patch("subprocess.run", return_value=mock_result):
            r = signals.collect({"kind": "process", "name": "python3"})
        self.assertTrue(r["ok"])


if __name__ == "__main__":
    unittest.main()
