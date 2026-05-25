import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "export_claude_code.py"


def _write_session(dir_path: Path, session_id: str, events: list[dict]) -> None:
    dir_path.mkdir(parents=True, exist_ok=True)
    with (dir_path / f"{session_id}.jsonl").open("w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")


class TestExportClaudeCode(unittest.TestCase):
    def test_harvests_jsonl_into_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            root = tmp / "projects"
            target = tmp / "out"
            _write_session(
                root / "-Users-you-repo",
                "aabbccdd-1111-2222-3333-444455556666",
                [
                    {"type": "summary", "summary": "Fix timezone clock on dashboard",
                     "timestamp": "2026-04-20T22:30:00Z"},
                    {"type": "user",
                     "timestamp": "2026-04-20T22:30:01Z",
                     "message": {"content": [{"type": "text", "text": "fix your clock"}]}},
                    {"type": "assistant",
                     "timestamp": "2026-04-20T22:30:05Z",
                     "message": {"content": [
                         {"type": "text", "text": "Reading index.html."},
                         {"type": "tool_use", "name": "Read"},
                     ]}},
                    {"type": "assistant",
                     "timestamp": "2026-04-20T22:31:00Z",
                     "message": {"content": [{"type": "text", "text": "Fixed line 514."}]}},
                ],
            )

            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(target), "--projects-root", str(root)],
                capture_output=True, text=True, check=True,
            )
            self.assertIn("1 written", result.stdout)
            files = list(target.iterdir())
            self.assertEqual(len(files), 1)
            text = files[0].read_text(encoding="utf-8")
            self.assertIn("source: claude-code", text)
            self.assertIn("session_id: aabbccdd-1111-2222-3333-444455556666", text)
            self.assertIn("last_timestamp: 2026-04-20T22:31:00Z", text)
            self.assertIn("Fix timezone clock on dashboard", text)
            self.assertIn("fix your clock", text)
            self.assertIn("*[tool call: Read]*", text)

    def test_idempotent_rerun_skips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            root = tmp / "projects"
            target = tmp / "out"
            _write_session(root / "-proj", "uuid", [
                {"type": "user", "timestamp": "2026-04-20T00:00:00Z",
                 "message": {"content": [{"type": "text", "text": "hello"}]}},
            ])
            subprocess.run(
                [sys.executable, str(SCRIPT), str(target), "--projects-root", str(root)],
                check=True, capture_output=True,
            )
            second = subprocess.run(
                [sys.executable, str(SCRIPT), str(target), "--projects-root", str(root)],
                capture_output=True, text=True, check=True,
            )
            self.assertIn("0 written", second.stdout)
            self.assertIn("1 skipped", second.stdout)

    def test_since_filter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            root = tmp / "projects"
            target = tmp / "out"
            _write_session(root / "-a", "old", [
                {"type": "user", "timestamp": "2025-01-01T00:00:00Z",
                 "message": {"content": [{"type": "text", "text": "old"}]}},
            ])
            _write_session(root / "-b", "new", [
                {"type": "user", "timestamp": "2026-04-20T00:00:00Z",
                 "message": {"content": [{"type": "text", "text": "new"}]}},
            ])
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(target),
                 "--projects-root", str(root), "--since", "2026-01-01"],
                capture_output=True, text=True, check=True,
            )
            self.assertIn("1 written", result.stdout)
            self.assertIn("1 skipped", result.stdout)
            files = list(target.iterdir())
            self.assertEqual(len(files), 1)
            self.assertIn("new", files[0].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
