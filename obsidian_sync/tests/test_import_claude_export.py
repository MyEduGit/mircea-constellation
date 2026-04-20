import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "import_claude_export.py"


def _make_zip(zip_path: Path, conversations: list[dict]) -> None:
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("conversations.json", json.dumps(conversations))


class TestImportClaudeExport(unittest.TestCase):
    def test_writes_one_markdown_per_conversation_with_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            zp = tmp / "export.zip"
            target = tmp / "out"
            _make_zip(zp, [
                {
                    "uuid": "abcd1234-ef56-7890-abcd-ef1234567890",
                    "name": "A chat about clocks / timezones",
                    "created_at": "2026-04-13T13:18:00Z",
                    "updated_at": "2026-04-14T08:00:00Z",
                    "chat_messages": [
                        {"sender": "human", "created_at": "2026-04-13T13:18:00Z", "text": "hello"},
                        {"sender": "assistant", "created_at": "2026-04-13T13:18:05Z",
                         "content": [{"type": "text", "text": "world"}]},
                    ],
                },
                {
                    "uuid": "11111111-2222-3333-4444-555555555555",
                    "name": "",  # should fall back to untitled
                    "created_at": "",
                    "updated_at": "",
                    "chat_messages": [],
                },
            ])

            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(zp), str(target)],
                capture_output=True, text=True, check=True,
            )
            self.assertIn("2 written", result.stdout)

            files = sorted(p.name for p in target.iterdir())
            self.assertEqual(len(files), 2)
            chat = next(p for p in target.iterdir() if "clocks" in p.name)
            text = chat.read_text(encoding="utf-8")
            self.assertIn("source: claude-chat", text)
            self.assertIn("uuid: abcd1234-ef56-7890-abcd-ef1234567890", text)
            self.assertIn("message_count: 2", text)
            self.assertIn("### human", text)
            self.assertIn("### assistant", text)
            self.assertIn("world", text)

    def test_idempotent_rerun_skips_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            zp = tmp / "export.zip"
            target = tmp / "out"
            conv = [{
                "uuid": "deadbeef-0000-0000-0000-000000000000",
                "name": "Stable convo",
                "created_at": "2026-04-13T13:18:00Z",
                "updated_at": "2026-04-13T13:19:00Z",
                "chat_messages": [{"sender": "human", "text": "one"}],
            }]
            _make_zip(zp, conv)

            subprocess.run([sys.executable, str(SCRIPT), str(zp), str(target)], check=True, capture_output=True)
            second = subprocess.run(
                [sys.executable, str(SCRIPT), str(zp), str(target)],
                capture_output=True, text=True, check=True,
            )
            self.assertIn("0 written", second.stdout)
            self.assertIn("1 skipped", second.stdout)

    def test_rerun_rewrites_when_updated_at_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            zp = tmp / "export.zip"
            target = tmp / "out"
            conv = [{
                "uuid": "feedface-0000-0000-0000-000000000000",
                "name": "Evolving convo",
                "created_at": "2026-04-13T13:18:00Z",
                "updated_at": "2026-04-13T13:19:00Z",
                "chat_messages": [{"sender": "human", "text": "one"}],
            }]
            _make_zip(zp, conv)
            subprocess.run([sys.executable, str(SCRIPT), str(zp), str(target)], check=True, capture_output=True)

            conv[0]["updated_at"] = "2026-04-13T14:00:00Z"
            conv[0]["chat_messages"].append({"sender": "assistant", "text": "two"})
            _make_zip(zp, conv)

            second = subprocess.run(
                [sys.executable, str(SCRIPT), str(zp), str(target)],
                capture_output=True, text=True, check=True,
            )
            self.assertIn("1 written", second.stdout)


if __name__ == "__main__":
    unittest.main()
