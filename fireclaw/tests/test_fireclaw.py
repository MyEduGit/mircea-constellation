"""Tests for fireclaw/fireclaw.py — evaluation loop, Lucifer test, state."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fireclaw import fireclaw as fc


def _bad_sig(detail: str = "probe failed") -> dict:
    return {"kind": "http", "ok": False, "detail": detail, "raw": {}}


def _good_sig() -> dict:
    return {"kind": "http", "ok": True, "detail": "status=200", "raw": {}}


def _ok_action_result() -> dict:
    return {"kind": "alert_only", "executed": True, "exit_code": 0,
            "duration_ms": 1, "stdout": "ok", "stderr": ""}


def _fail_action_result() -> dict:
    return {"kind": "alert_only", "executed": True, "exit_code": 1,
            "duration_ms": 1, "stdout": "", "stderr": "oops"}


MINIMAL_RULE = {
    "id": "test-rule",
    "description": "test",
    "signal": {"kind": "http", "url": "http://x"},
    "condition": {"consecutive_failures": 1, "cooldown_seconds": 0},
    "action": {"kind": "alert_only", "message": "test alert"},
}


class TestLuciferTest(unittest.TestCase):
    def test_passes_valid_rule_and_bad_signal(self):
        rule = dict(MINIMAL_RULE)
        allowed, reason = fc.lucifer_test(rule, _bad_sig())
        self.assertTrue(allowed)
        self.assertEqual(reason, "passed")

    def test_fails_when_action_missing(self):
        rule = {**MINIMAL_RULE, "action": None}
        allowed, reason = fc.lucifer_test(rule, _bad_sig())
        self.assertFalse(allowed)
        self.assertIn("no action", reason)

    def test_fails_when_action_kind_unknown(self):
        rule = {**MINIMAL_RULE, "action": {"kind": "bogus_action"}}
        allowed, reason = fc.lucifer_test(rule, _bad_sig())
        self.assertFalse(allowed)
        self.assertIn("not in DISPATCH", reason)

    def test_refuses_on_healthy_signal(self):
        allowed, reason = fc.lucifer_test(MINIMAL_RULE, _good_sig())
        self.assertFalse(allowed)
        self.assertIn("signal is ok", reason)


class TestEvaluateCycle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        fc.STATE_DIR = Path(self.tmp.name)
        fc.INCIDENTS_PATH = fc.STATE_DIR / "incidents.jsonl"
        fc.COUNTERS_PATH = fc.STATE_DIR / "counters.json"

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, rules, state=None, dry_run=True):
        if state is None:
            state = {}
        return fc.evaluate_cycle(rules, state, dry_run, lambda _: None)

    def test_no_action_when_signal_ok(self):
        with patch("fireclaw.signals.collect", return_value=_good_sig()):
            executed, failed = self._run([MINIMAL_RULE])
        self.assertEqual(executed, 0)
        self.assertEqual(failed, 0)

    def test_action_fires_on_bad_signal(self):
        with patch("fireclaw.signals.collect", return_value=_bad_sig()), \
             patch("fireclaw.actions.execute", return_value=_ok_action_result()):
            executed, failed = self._run([MINIMAL_RULE], dry_run=False)
        self.assertEqual(executed, 1)
        self.assertEqual(failed, 0)

    def test_threshold_prevents_early_action(self):
        rule = {**MINIMAL_RULE,
                "condition": {"consecutive_failures": 3, "cooldown_seconds": 0}}
        state = {}
        with patch("fireclaw.signals.collect", return_value=_bad_sig()), \
             patch("fireclaw.actions.execute", return_value=_ok_action_result()):
            # cycle 1: count=1, threshold=3 → no action
            executed, failed = self._run([rule], state, dry_run=False)
            self.assertEqual(executed, 0)
            # cycle 2: count=2 → still no action
            executed, failed = self._run([rule], state, dry_run=False)
            self.assertEqual(executed, 0)
            # cycle 3: count=3 → fires
            executed, failed = self._run([rule], state, dry_run=False)
            self.assertEqual(executed, 1)

    def test_cooldown_suppresses_repeated_action(self):
        rule = {**MINIMAL_RULE,
                "condition": {"consecutive_failures": 1,
                               "cooldown_seconds": 9999}}
        state = {}
        with patch("fireclaw.signals.collect", return_value=_bad_sig()), \
             patch("fireclaw.actions.execute", return_value=_ok_action_result()):
            executed1, _ = self._run([rule], state, dry_run=False)
            executed2, _ = self._run([rule], state, dry_run=False)
        self.assertEqual(executed1, 1)
        self.assertEqual(executed2, 0)  # suppressed by cooldown

    def test_failure_count_resets_on_recovery(self):
        state = {}
        rule = {**MINIMAL_RULE,
                "condition": {"consecutive_failures": 1, "cooldown_seconds": 0}}
        with patch("fireclaw.signals.collect", return_value=_bad_sig()), \
             patch("fireclaw.actions.execute", return_value=_ok_action_result()):
            self._run([rule], state, dry_run=False)
        # Now signal is ok — failure count must reset
        with patch("fireclaw.signals.collect", return_value=_good_sig()):
            self._run([rule], state, dry_run=False)
        self.assertEqual(state["test-rule"]["consecutive_failures"], 0)

    def test_skips_rule_missing_id(self):
        rule = {k: v for k, v in MINIMAL_RULE.items() if k != "id"}
        with patch("fireclaw.signals.collect", return_value=_bad_sig()):
            executed, failed = self._run([rule])
        self.assertEqual(executed, 0)
        self.assertEqual(failed, 0)

    def test_refused_action_recorded_as_failed(self):
        rule = {**MINIMAL_RULE, "action": {"kind": "not_a_real_kind"}}
        with patch("fireclaw.signals.collect", return_value=_bad_sig()):
            executed, failed = self._run([rule], dry_run=False)
        self.assertEqual(failed, 1)
        incident = fc.INCIDENTS_PATH.read_text().strip()
        data = json.loads(incident)
        self.assertIn("refused", data["action"]["stderr"])

    def test_incident_appended_on_action(self):
        with patch("fireclaw.signals.collect", return_value=_bad_sig()), \
             patch("fireclaw.actions.execute", return_value=_ok_action_result()):
            self._run([MINIMAL_RULE], dry_run=False)
        lines = fc.INCIDENTS_PATH.read_text().strip().splitlines()
        self.assertEqual(len(lines), 1)
        record = json.loads(lines[0])
        self.assertEqual(record["rule"], "test-rule")


class TestStateIO(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        fc.STATE_DIR = Path(self.tmp.name)
        fc.COUNTERS_PATH = fc.STATE_DIR / "counters.json"
        fc.INCIDENTS_PATH = fc.STATE_DIR / "incidents.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def test_round_trip(self):
        state = {"r1": {"consecutive_failures": 3, "last_action_ts": 0.0}}
        fc.save_state(state)
        loaded = fc.load_state()
        self.assertEqual(loaded, state)

    def test_load_returns_empty_when_missing(self):
        loaded = fc.load_state()
        self.assertEqual(loaded, {})

    def test_append_incident(self):
        fc.append_incident({"ts": "2026-04-20T00:00:00+00:00", "rule": "x"})
        fc.append_incident({"ts": "2026-04-20T00:01:00+00:00", "rule": "y"})
        lines = fc.INCIDENTS_PATH.read_text().strip().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(json.loads(lines[0])["rule"], "x")
        self.assertEqual(json.loads(lines[1])["rule"], "y")


if __name__ == "__main__":
    unittest.main()
