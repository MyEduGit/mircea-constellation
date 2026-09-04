"""End-to-end test for scribeclaw.sermon_transcribe against a mock AssemblyAI.

No network: a local HTTP server stands in for api.assemblyai.com and the
module's _API_BASE is redirected at it. This exercises the real upload path
(chunked async streaming), job start, polling, sentence fetch, and every
output writer.
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from scribeclaw import assemblyai, sermon_transcribe

TRANSCRIPT_ID = "tid-c0089-test"
_TEXT = ("Fraților, deschideți la Ioan capitolul trei. "
         "Astăzi vorbim despre naşterea din nou. "
         "Mmm bâlbâit neclar aici. "
         "Domnul să vă binecuvânteze.")

_SENTENCES = [
    {"text": "Fraților, deschideți la Ioan capitolul trei.", "start": 1000, "end": 4000,
     "confidence": 0.95},
    {"text": "Astăzi vorbim despre naşterea din nou.", "start": 4000, "end": 7000,
     "confidence": 0.93},
    {"text": "Mmm bâlbâit neclar aici.", "start": 7000, "end": 9000,
     "confidence": 0.31},
    {"text": "Domnul să vă binecuvânteze.", "start": 40000, "end": 42000,
     "confidence": 0.97},
]


def _words_payload():
    words = []
    for s in _SENTENCES:
        toks = s["text"].split()
        span = (s["end"] - s["start"]) / max(len(toks), 1)
        for i, t in enumerate(toks):
            words.append({
                "text": t,
                "start": int(s["start"] + i * span),
                "end": int(s["start"] + (i + 1) * span),
                "confidence": s["confidence"],
                "speaker": "A",
            })
    return words


class _Handler(BaseHTTPRequestHandler):
    uploaded_bytes = 0

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path.endswith("/upload"):
            n = 0
            if self.headers.get("Transfer-Encoding") == "chunked":
                while True:
                    size = int(self.rfile.readline().strip() or b"0", 16)
                    if size == 0:
                        self.rfile.readline()
                        break
                    n += len(self.rfile.read(size))
                    self.rfile.readline()
            else:
                n = int(self.headers.get("Content-Length") or 0)
                self.rfile.read(n)
            type(self).uploaded_bytes = n
            return self._json({"upload_url": "https://cdn.test/audio"})
        if self.path.endswith("/transcript"):
            n = int(self.headers.get("Content-Length") or 0)
            type(self).last_body = json.loads(self.rfile.read(n) or b"{}")
            return self._json({"id": TRANSCRIPT_ID, "status": "queued"})
        return self._json({"error": "unexpected"}, 404)

    def do_GET(self):
        if self.path.endswith(f"/transcript/{TRANSCRIPT_ID}/sentences"):
            return self._json({"sentences": _SENTENCES})
        if self.path.endswith(f"/transcript/{TRANSCRIPT_ID}"):
            return self._json({
                "id": TRANSCRIPT_ID, "status": "completed",
                "text": _TEXT, "language_code": "ro",
                "audio_duration": 42.0, "confidence": 0.89,
                "speech_model": "best", "words": _words_payload(),
                "utterances": [{"speaker": "A", "start": 1000, "end": 42000,
                                "text": _TEXT, "confidence": 0.89}],
            })
        return self._json({"error": "unexpected"}, 404)

    def log_message(self, *a):
        pass


@pytest.fixture()
def mock_api(monkeypatch):
    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}/v2"
    monkeypatch.setattr(assemblyai, "_API_BASE", base)
    monkeypatch.setenv("ASSEMBLYAI_API_KEY", "test-key-not-real")
    yield srv
    srv.shutdown()


def _run(tmp_path, extra=None):
    src = tmp_path / "C0089_Audio.mp3"
    src.write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * (6 * 1024 * 1024))
    out = tmp_path / "pkg"
    argv = ["--input", str(src), "--code", "C0089", "--out-dir", str(out),
            "--speaker-labels", "--poll-sec", "1"]
    rc = sermon_transcribe.main_with_argv(argv + (extra or []))
    return rc, src, out


def test_full_package_written(tmp_path, mock_api):
    rc, src, out = _run(tmp_path)
    assert rc == 0

    expected = [
        "C0089_AssemblyAI_RAW.json", "C0089_AssemblyAI_RAW.txt",
        "C0089_Transcript_Corrected_RO.txt", "C0089_Transcript_Canonical_RO.md",
        "C0089_Transcript_Timestamped_RO.md", "C0089_Word_Timestamps.json",
        "C0089_Transcription_Metadata.json", "C0089_Transcription_QA.md",
        "C0089_RO.srt", "C0089_RO.vtt",
    ]
    for name in expected:
        assert (out / name).is_file(), f"missing {name}"
        assert (out / name).stat().st_size > 0, f"empty {name}"


def test_whole_file_uploaded(tmp_path, mock_api):
    """The sync-generator bug silently uploaded zero bytes; guard against it."""
    rc, src, out = _run(tmp_path)
    assert rc == 0
    assert _Handler.uploaded_bytes == src.stat().st_size


def test_raw_layer_is_verbatim(tmp_path, mock_api):
    rc, src, out = _run(tmp_path)
    raw = json.loads((out / "C0089_AssemblyAI_RAW.json").read_text("utf-8"))
    assert raw["text"] == _TEXT
    # Raw keeps the legacy cedilla exactly as AssemblyAI returned it.
    assert "naşterea" in (out / "C0089_AssemblyAI_RAW.txt").read_text("utf-8")


def test_corrected_layer_normalises_diacritics_only(tmp_path, mock_api):
    rc, src, out = _run(tmp_path)
    corrected = (out / "C0089_Transcript_Corrected_RO.txt").read_text("utf-8")
    # cedilla ş (U+015F) → comma-below ș (U+0219)
    assert "nașterea" in corrected
    assert "ş" not in corrected
    # wording is otherwise untouched
    assert "deschideți la Ioan capitolul trei" in corrected


def test_low_confidence_marked_unclear(tmp_path, mock_api):
    rc, src, out = _run(tmp_path)
    corrected = (out / "C0089_Transcript_Corrected_RO.txt").read_text("utf-8")
    assert "[NECLAR —" in corrected
    qa = (out / "C0089_Transcription_QA.md").read_text("utf-8")
    assert "Pasaje neclare" in qa


def test_word_timestamps_in_seconds(tmp_path, mock_api):
    rc, src, out = _run(tmp_path)
    wt = json.loads((out / "C0089_Word_Timestamps.json").read_text("utf-8"))
    assert wt["units"] == "seconds"
    assert wt["words"], "no words captured"
    assert wt["words"][0]["start"] == pytest.approx(1.0, abs=0.2)
    assert all("confidence" in w for w in wt["words"])
    assert wt["utterances"][0]["speaker"] == "A"


def test_gap_detected(tmp_path, mock_api):
    """9s → 40s is a 31s silence; QA must report it, not hide it."""
    rc, src, out = _run(tmp_path)
    qa = (out / "C0089_Transcription_QA.md").read_text("utf-8")
    assert "Pauze peste" in qa
    meta = json.loads((out / "C0089_Transcription_Metadata.json").read_text("utf-8"))
    assert meta["counts"]["gaps"] >= 1


def test_metadata_records_provenance_and_no_secret(tmp_path, mock_api):
    rc, src, out = _run(tmp_path)
    text = (out / "C0089_Transcription_Metadata.json").read_text("utf-8")
    assert "test-key-not-real" not in text, "API key leaked into metadata"
    meta = json.loads(text)
    assert meta["source"]["sha256"]
    assert meta["source"]["bytes"] == src.stat().st_size
    assert meta["transcription"]["transcript_id"] == TRANSCRIPT_ID
    assert meta["transcription"]["language"] == "ro"
    assert meta["provenance"]["source_untouched"] is True
    assert "CANDIDATE" in meta["provenance"]["layer_3_canonical"]


def test_source_file_untouched(tmp_path, mock_api):
    src = tmp_path / "C0089_Audio.mp3"
    src.write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * (1024 * 1024))
    before = (src.stat().st_mtime_ns, src.read_bytes())
    out = tmp_path / "pkg"
    rc = sermon_transcribe.main_with_argv(
        ["--input", str(src), "--code", "C0089", "--out-dir", str(out),
         "--poll-sec", "1"])
    assert rc == 0
    assert (src.stat().st_mtime_ns, src.read_bytes()) == before


def test_refuses_to_overwrite_existing_package(tmp_path, mock_api):
    rc, src, out = _run(tmp_path)
    assert rc == 0
    canonical = out / "C0089_Transcript_Canonical_RO.md"
    original = canonical.read_bytes()

    rc2 = sermon_transcribe.main_with_argv(
        ["--input", str(src), "--code", "C0089", "--out-dir", str(out),
         "--poll-sec", "1"])
    assert rc2 == 5, "should refuse without --overwrite"
    assert canonical.read_bytes() == original, "existing transcript was clobbered"
    assert (out / "C0089_EXISTING_PACKAGE_FOUND.json").is_file()

    rc3 = sermon_transcribe.main_with_argv(
        ["--input", str(src), "--code", "C0089", "--out-dir", str(out),
         "--poll-sec", "1", "--overwrite"])
    assert rc3 == 0


def test_custom_vocabulary_sent(tmp_path, mock_api):
    wb = tmp_path / "terms.txt"
    wb.write_text("# biblical names\nIoan\nGeaboc\n", encoding="utf-8")
    rc, src, out = _run(tmp_path, ["--word-boost-file", str(wb)])
    assert rc == 0
    assert _Handler.last_body["word_boost"] == ["Ioan", "Geaboc"]
    assert _Handler.last_body["boost_param"] == "high"
    assert _Handler.last_body["language_code"] == "ro"
    assert _Handler.last_body["speaker_labels"] is True


def test_missing_api_key_refuses(tmp_path, mock_api, monkeypatch):
    monkeypatch.delenv("ASSEMBLYAI_API_KEY", raising=False)
    monkeypatch.setattr(sermon_transcribe, "_load_env_file", lambda p: None)
    src = tmp_path / "C0089_Audio.mp3"
    src.write_bytes(b"\x00" * 1024)
    rc = sermon_transcribe.main_with_argv(
        ["--input", str(src), "--code", "C0089", "--out-dir", str(tmp_path / "o")])
    assert rc == 3


def test_missing_source_refuses(tmp_path, mock_api):
    rc = sermon_transcribe.main_with_argv(
        ["--input", str(tmp_path / "nope.mp3"), "--code", "C0089",
         "--out-dir", str(tmp_path / "o")])
    assert rc == 2


def test_repo_geaboc_vocabulary_is_loadable(tmp_path, mock_api):
    """The shipped Geaboc vocabulary must parse and reach AssemblyAI intact."""
    vocab = (Path(__file__).resolve().parents[2]
             / "channels" / "jabbokriver" / "geaboc-vocabulary-ro.txt")
    assert vocab.is_file(), f"missing {vocab}"

    rc, src, out = _run(tmp_path, ["--word-boost-file", str(vocab)])
    assert rc == 0

    sent = _Handler.last_body["word_boost"]
    assert len(sent) > 100, f"only {len(sent)} terms boosted"
    assert not any(t.startswith("#") for t in sent), "comment leaked into word_boost"
    assert not any(t != t.strip() for t in sent), "unstripped term"
    assert len(sent) == len(set(sent)), "duplicate terms"
    # Terminology and biblical names the generic Romanian model mis-hears.
    for term in ("Sanctuar", "Duhul Sfânt", "Apocalipsa", "Emanoil Geaboc"):
        assert term in sent, f"{term} missing from vocabulary"

    meta = json.loads((out / "C0089_Transcription_Metadata.json").read_text("utf-8"))
    assert meta["transcription"]["custom_vocabulary_terms"] == len(sent)
