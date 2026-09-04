#!/usr/bin/env python3
"""sermon_transcribe — one-command AssemblyAI sermon transcription package.

Truthful label: real, but only two of the three transcript layers are
machine-producible. Layer 1 (RAW) and Layer 2 (CORRECTED) are generated
deterministically. Layer 3 (CANONICAL) is emitted as a *candidate* built
from Layer 2 by paragraph reflow only; promoting it to authoritative
requires a human or a reviewing pass against the audio. The file says so
in its own header — nothing here silently claims editorial sign-off.

Why this exists alongside the HTTP handlers: `transcribe_assemblyai`
requires the file to be staged inside the Docker bind mount at
/data/media/audio/. A sermon sitting on an external SSD is not there, and
copying an authoritative source just to transcribe it violates the
"never move the original" rule. This module reuses the same AssemblyAI
client functions against an arbitrary absolute path, read-only.

Usage:

    export ASSEMBLYAI_API_KEY=...        # or put it in scribeclaw/.env
    python3 -m scribeclaw.sermon_transcribe \\
        --input "/Volumes/SSD_Adobe:FCP/.../C0089_Audio.mp3" \\
        --code C0089 \\
        --out-dir "/Volumes/SSD_Adobe:FCP/.../C0089_Transcription"

The source file is opened read-only and never written, moved, or renamed.

UrantiOS governed — Truth, Beauty, Goodness.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .assemblyai import (
    _API_BASE,
    _fetch_sentences,
    _fmt_ts,
    _poll,
    _start_job,
    _upload_file,
)
from .postprocess import _fix_text

# A run of this many consecutive words at or below _LOW_CONF is marked
# [NECLAR — HH:MM:SS] rather than silently presented as certain.
_LOW_CONF = 0.50
_LOW_CONF_RUN = 3
# Silence longer than this between consecutive words is reported as a gap.
_GAP_SEC = 20.0
_ROMANIAN_DIACRITICS = set("ăâîșțĂÂÎȘȚ")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-ZĂÂÎȘȚ])")


# ---------------------------------------------------------------- helpers

def _hhmmss(sec: float) -> str:
    total = int(sec)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _load_env_file(path: Path) -> None:
    """Populate os.environ from a KEY=VALUE file without echoing values."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _ffprobe(path: Path) -> dict[str, Any]:
    """Best-effort container/stream facts. Absent ffprobe is not an error."""
    if not shutil.which("ffprobe"):
        return {"ffprobe": "not_on_path"}
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-print_format", "json",
             "-show_format", "-show_streams", str(path)],
            capture_output=True, text=True, timeout=120, check=True,
        ).stdout
        data = json.loads(out)
    except Exception as exc:
        return {"ffprobe": "failed", "detail": str(exc)}
    audio = next(
        (s for s in data.get("streams", []) if s.get("codec_type") == "audio"), {}
    )
    fmt = data.get("format", {})
    return {
        "ffprobe": "ok",
        "format_name": fmt.get("format_name"),
        "duration_sec": float(fmt["duration"]) if fmt.get("duration") else None,
        "bit_rate": fmt.get("bit_rate"),
        "codec_name": audio.get("codec_name"),
        "sample_rate": audio.get("sample_rate"),
        "channels": audio.get("channels"),
    }


def _words(raw: dict) -> list[dict]:
    """AssemblyAI word list, ms → s, keeping confidence and speaker."""
    out = []
    for w in raw.get("words") or []:
        out.append({
            "text": w.get("text", ""),
            "start": float(w.get("start", 0)) / 1000.0,
            "end": float(w.get("end", 0)) / 1000.0,
            "confidence": float(w.get("confidence", 0.0)),
            "speaker": w.get("speaker"),
        })
    return out


def _utterances(raw: dict) -> list[dict]:
    out = []
    for u in raw.get("utterances") or []:
        out.append({
            "speaker": u.get("speaker"),
            "start": float(u.get("start", 0)) / 1000.0,
            "end": float(u.get("end", 0)) / 1000.0,
            "text": (u.get("text") or "").strip(),
            "confidence": float(u.get("confidence", 0.0)),
        })
    return out


def _segments(sentences_payload: dict, raw: dict) -> list[dict]:
    """Prefer AssemblyAI sentences; fall back to utterances, then whole text."""
    out: list[dict] = []
    for i, s in enumerate(sentences_payload.get("sentences", []) or []):
        out.append({
            "id": i,
            "start": float(s["start"]) / 1000.0,
            "end": float(s["end"]) / 1000.0,
            "text": (s.get("text") or "").strip(),
            "confidence": s.get("confidence"),
        })
    if out:
        return out
    for i, u in enumerate(_utterances(raw)):
        out.append({"id": i, "start": u["start"], "end": u["end"],
                    "text": u["text"], "confidence": u["confidence"]})
    if out:
        return out
    text = (raw.get("text") or "").strip()
    if text:
        out.append({"id": 0, "start": 0.0,
                    "end": float(raw.get("audio_duration") or 0.0),
                    "text": text, "confidence": raw.get("confidence")})
    return out


def _low_conf_spans(words: list[dict]) -> list[dict]:
    """Consecutive runs of low-confidence words — candidates for [NECLAR]."""
    spans, run = [], []
    for w in words:
        if w["confidence"] <= _LOW_CONF:
            run.append(w)
            continue
        if len(run) >= _LOW_CONF_RUN:
            spans.append({"start": run[0]["start"], "end": run[-1]["end"],
                          "text": " ".join(x["text"] for x in run),
                          "min_confidence": min(x["confidence"] for x in run)})
        run = []
    if len(run) >= _LOW_CONF_RUN:
        spans.append({"start": run[0]["start"], "end": run[-1]["end"],
                      "text": " ".join(x["text"] for x in run),
                      "min_confidence": min(x["confidence"] for x in run)})
    return spans


def _gaps(words: list[dict]) -> list[dict]:
    out = []
    for a, b in zip(words, words[1:]):
        if b["start"] - a["end"] >= _GAP_SEC:
            out.append({"after": _hhmmss(a["end"]), "until": _hhmmss(b["start"]),
                        "seconds": round(b["start"] - a["end"], 2)})
    return out


def _continuity_faults(words: list[dict]) -> list[dict]:
    out = []
    for i, w in enumerate(words):
        if w["end"] < w["start"]:
            out.append({"index": i, "fault": "end_before_start",
                        "at": _hhmmss(w["start"])})
    for i, (a, b) in enumerate(zip(words, words[1:])):
        if b["start"] < a["start"]:
            out.append({"index": i + 1, "fault": "non_monotonic_start",
                        "at": _hhmmss(b["start"])})
    return out


# ---------------------------------------------------------------- writers

def _srt(segments: list[dict]) -> str:
    lines = []
    for i, seg in enumerate(segments, start=1):
        lines += [str(i),
                  f"{_fmt_ts(seg['start'], ',')} --> {_fmt_ts(seg['end'], ',')}",
                  seg["text"].strip(), ""]
    return "\n".join(lines)


def _vtt(segments: list[dict]) -> str:
    lines = ["WEBVTT", ""]
    for seg in segments:
        lines += [f"{_fmt_ts(seg['start'], '.')} --> {_fmt_ts(seg['end'], '.')}",
                  seg["text"].strip(), ""]
    return "\n".join(lines)


def _timestamped_md(code: str, segments: list[dict], utterances: list[dict],
                    interval: float) -> str:
    """HH:MM:SS + text at semantic intervals, for Final Cut / editorial use."""
    head = [f"# {code} — Transcript cu marcaje de timp (RO)", "",
            "Generat din raspunsul AssemblyAI. Marcajele sunt in HH:MM:SS de la",
            "inceputul fisierului sursa.", ""]
    if utterances:
        head.append("Sursa marcajelor: utterances (cu etichete de vorbitor).")
        head.append("")
        for u in utterances:
            spk = f" **[Vorbitor {u['speaker']}]**" if u.get("speaker") else ""
            head.append(f"**{_hhmmss(u['start'])}**{spk}  {u['text']}")
            head.append("")
        return "\n".join(head)

    head.append(f"Sursa marcajelor: propozitii, grupate la ~{int(interval)}s.")
    head.append("")
    block: list[str] = []
    block_start = segments[0]["start"] if segments else 0.0
    for seg in segments:
        if block and seg["start"] - block_start >= interval:
            head.append(f"**{_hhmmss(block_start)}**  {' '.join(block)}")
            head.append("")
            block, block_start = [], seg["start"]
        block.append(seg["text"].strip())
    if block:
        head.append(f"**{_hhmmss(block_start)}**  {' '.join(block)}")
        head.append("")
    return "\n".join(head)


def _corrected_text(segments: list[dict], spans: list[dict]) -> str:
    """Layer 2: deterministic orthography only, plus explicit [NECLAR] marks.

    No lexical guessing. `_fix_text` maps legacy cedilla forms to the correct
    comma-below Romanian letters and normalises spacing — nothing else. Where
    the ASR itself reported sustained low confidence, an explicit marker is
    inserted so uncertainty is visible instead of hidden.
    """
    marks = {round(s["start"], 1): s for s in spans}
    out: list[str] = []
    for seg in segments:
        text = _fix_text(seg["text"])
        hit = next((m for k, m in marks.items()
                    if seg["start"] <= k <= seg["end"]), None)
        if hit is not None:
            text = f"{text} [NECLAR — {_hhmmss(hit['start'])}]"
        out.append(text)
    return "\n\n".join(t for t in out if t.strip())


def _canonical_md(code: str, corrected: str, meta: dict) -> str:
    body = _SENTENCE_SPLIT.split(" ".join(corrected.split("\n\n")))
    paragraphs = "\n\n".join(p.strip() for p in body if p.strip())
    return "\n".join([
        f"# {code} — Transcript canonic (RO)", "",
        "> **Stare: CANDIDAT, nu autoritativ.** Acest strat este derivat",
        "> automat din Stratul 2 prin reflow de paragrafe. Nu a fost inca",
        "> verificat de un om fata de audio. Numele biblice, referintele si",
        "> terminologia teologica NU au fost corectate editorial.",
        "> Marcajele `[NECLAR — HH:MM:SS]` indica pasaje cu incredere ASR",
        "> scazuta care necesita ascultare.", "",
        f"- Cod predica: `{code}`",
        f"- Sursa: `{meta['source']['filename']}`",
        f"- Durata: {_hhmmss(meta['source']['duration_sec'] or 0)}",
        f"- Furnizor: AssemblyAI (`{meta['transcription']['model']}`)",
        f"- Limba: {meta['transcription']['language']}",
        f"- Vorbitor principal: {meta['sermon']['principal_speaker']}",
        "", "---", "", paragraphs, "",
    ])


def _qa_md(code: str, raw: dict, words: list[dict], segments: list[dict],
           spans: list[dict], gaps: list[dict], faults: list[dict],
           meta: dict) -> str:
    text = " ".join(s["text"] for s in segments)
    diacritics = sum(1 for ch in text if ch in _ROMANIAN_DIACRITICS)
    confs = [w["confidence"] for w in words]
    duration = meta["source"]["duration_sec"] or float(raw.get("audio_duration") or 0)
    covered = words[-1]["end"] if words else 0.0
    first = words[0]["start"] if words else 0.0

    lines = [
        f"# {code} — QA transcriere", "",
        "Verificari deterministe pe raspunsul AssemblyAI. Nicio corectura",
        "lexicala nu a fost inventata.", "",
        "## Acoperire", "",
        f"- Durata audio: **{_hhmmss(duration)}**",
        f"- Primul cuvant la: **{_hhmmss(first)}**",
        f"- Ultimul cuvant la: **{_hhmmss(covered)}**",
        f"- Acoperire: **{(covered / duration * 100) if duration else 0:.1f}%**",
        f"- Cuvinte: **{len(words)}**",
        f"- Segmente: **{len(segments)}**", "",
        "## Incredere", "",
        f"- Incredere medie: **{(sum(confs) / len(confs)) if confs else 0:.3f}**",
        f"- Incredere minima: **{min(confs) if confs else 0:.3f}**",
        f"- Cuvinte sub {_LOW_CONF}: **{sum(1 for c in confs if c <= _LOW_CONF)}**",
        f"- Pasaje neclare marcate: **{len(spans)}**", "",
        "## Limba romana", "",
        f"- Cod limba raportat: **{raw.get('language_code')}**",
        f"- Diacritice (ă â î ș ț): **{diacritics}**",
    ]
    if diacritics == 0:
        lines.append("- ⚠️ **ZERO diacritice.** Verificati limba ceruta si "
                     "`format_text`. Un transcript romanesc fara diacritice "
                     "indica aproape sigur o problema de configurare.")
    lines += ["", "## Inceput predica", "",
              "```", (segments[0]["text"] if segments else "(gol)")[:600], "```",
              "", "## Final predica", "",
              "```", (segments[-1]["text"] if segments else "(gol)")[:600], "```",
              "", "## Continuitate marcaje", ""]
    lines.append(f"- Erori de continuitate: **{len(faults)}**")
    for f in faults[:20]:
        lines.append(f"  - `{f['at']}` — {f['fault']}")
    lines += ["", f"## Pauze peste {int(_GAP_SEC)}s", ""]
    if not gaps:
        lines.append("- Niciuna.")
    for g in gaps[:40]:
        lines.append(f"- `{g['after']}` → `{g['until']}` ({g['seconds']}s)")
    lines += ["", "## Pasaje neclare (necesita ascultare)", ""]
    if not spans:
        lines.append("- Niciunul peste prag.")
    for s in spans[:100]:
        lines.append(f"- `[NECLAR — {_hhmmss(s['start'])}]` "
                     f"(min conf {s['min_confidence']:.2f}) — «{s['text']}»")
    lines += ["", "## De verificat manual fata de audio", "",
              "Aceste categorii NU pot fi validate automat:", "",
              "- nume biblice si nume proprii",
              "- referinte biblice (carte, capitol, verset)",
              "- terminologie teologica si adventista",
              "- citate scripturistice",
              "- numere folosite ca referinte", "",
              "## Stare", "",
              "- Stratul 1 (RAW): **pastrat neatins**",
              "- Stratul 2 (CORECTAT): **doar ortografie determinista**",
              "- Stratul 3 (CANONIC): **CANDIDAT — necesita verificare umana**",
              ""]
    return "\n".join(lines)


# ---------------------------------------------------------------- guard

def _existing_package(out_dir: Path, names: list[str]) -> list[dict]:
    found = []
    for n in names:
        p = out_dir / n
        if p.exists():
            found.append({"file": n, "bytes": p.stat().st_size,
                          "sha256": _sha256(p),
                          "modified": datetime.fromtimestamp(
                              p.stat().st_mtime, timezone.utc).isoformat()})
    return found


# ---------------------------------------------------------------- main run

async def run(args: argparse.Namespace) -> int:
    src = Path(args.input).expanduser()
    if not src.is_file():
        print(f"ERROR: source not found: {src}", file=sys.stderr)
        return 2

    _load_env_file(Path(__file__).resolve().parent / ".env")
    api_key = os.getenv("ASSEMBLYAI_API_KEY", "").strip()
    if not api_key:
        print("ERROR: ASSEMBLYAI_API_KEY is not set (env or scribeclaw/.env).",
              file=sys.stderr)
        return 3

    try:
        import httpx
    except ImportError:
        print("ERROR: httpx not installed — pip install httpx", file=sys.stderr)
        return 4

    code = args.code
    out_dir = Path(args.out_dir).expanduser() if args.out_dir else \
        src.parent / f"{code}_Transcription"
    names = [f"{code}_AssemblyAI_RAW.json", f"{code}_AssemblyAI_RAW.txt",
             f"{code}_Transcript_Corrected_RO.txt",
             f"{code}_Transcript_Canonical_RO.md",
             f"{code}_Transcript_Timestamped_RO.md",
             f"{code}_Word_Timestamps.json",
             f"{code}_Transcription_Metadata.json",
             f"{code}_Transcription_QA.md",
             f"{code}_RO.srt", f"{code}_RO.vtt"]

    prior = _existing_package(out_dir, names) if out_dir.exists() else []
    if prior and not args.overwrite:
        report = out_dir / f"{code}_EXISTING_PACKAGE_FOUND.json"
        report.write_text(json.dumps(
            {"refused": "existing package present; compare before overwriting",
             "out_dir": str(out_dir), "existing": prior,
             "hint": "re-run with --overwrite only after comparing"},
            ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"REFUSED: {len(prior)} existing file(s) in {out_dir}.")
        print(f"Comparison written to {report}. Nothing was overwritten.")
        for f in prior:
            print(f"  - {f['file']}  {f['bytes']} bytes  {f['sha256'][:16]}…")
        return 5

    print(f"[1/6] hashing source (read-only): {src}")
    probe = _ffprobe(src)
    source_meta = {
        "filename": src.name,
        "absolute_path": str(src.resolve()),
        "bytes": src.stat().st_size,
        "sha256": _sha256(src),
        "duration_sec": probe.get("duration_sec"),
        "container": probe.get("format_name"),
        "codec": probe.get("codec_name"),
        "sample_rate": probe.get("sample_rate"),
        "channels": probe.get("channels"),
        "probe": probe.get("ffprobe"),
    }
    print(f"      sha256={source_meta['sha256']}")
    print(f"      bytes={source_meta['bytes']}  "
          f"duration={_hhmmss(source_meta['duration_sec'] or 0)}")

    word_boost: list[str] = []
    if args.word_boost_file:
        wb = Path(args.word_boost_file).expanduser()
        if not wb.is_file():
            print(f"ERROR: --word-boost-file not found: {wb}", file=sys.stderr)
            return 2
        word_boost = [ln.strip() for ln in wb.read_text(encoding="utf-8").splitlines()
                      if ln.strip() and not ln.startswith("#")]
        print(f"      custom vocabulary: {len(word_boost)} term(s)")

    payload: dict[str, Any] = {
        "language": args.language,
        "punctuate": True,
        "format_text": True,
        "speaker_labels": args.speaker_labels,
        "speech_model": args.speech_model,
    }
    if word_boost:
        payload["word_boost"] = word_boost
        payload["boost_param"] = "high"

    started = datetime.now(timezone.utc)
    timeout = httpx.Timeout(connect=30.0, read=180.0, write=1800.0, pool=30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            print("[2/6] uploading to AssemblyAI …")
            audio_url = await _upload_file(client, api_key, src)
            print("[3/6] starting transcription job …")
            model_used = args.speech_model
            try:
                tid = await _start_job(client, api_key, audio_url, payload)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 400 or not args.speech_model:
                    raise
                # The account/API may not accept this speech_model. Retry once
                # on the account default rather than failing the whole run.
                print(f"      speech_model={args.speech_model} rejected "
                      f"(400); retrying on account default")
                payload.pop("speech_model", None)
                model_used = "account_default"
                tid = await _start_job(client, api_key, audio_url, payload)
            print(f"      transcript id: {tid}")
            print(f"[4/6] polling (every {args.poll_sec}s, "
                  f"timeout {args.poll_timeout_sec}s) …")
            raw = await _poll(client, api_key, tid,
                              poll_sec=float(args.poll_sec),
                              timeout_sec=float(args.poll_timeout_sec))
            sentences = await _fetch_sentences(client, api_key, tid)
        except httpx.HTTPStatusError as exc:
            print(f"ERROR: AssemblyAI HTTP {exc.response.status_code}: "
                  f"{exc.response.text[-800:]}", file=sys.stderr)
            return 6
        except Exception as exc:
            print(f"ERROR: {exc.__class__.__name__}: {exc}", file=sys.stderr)
            return 6

    finished = datetime.now(timezone.utc)
    print("[5/6] building transcript layers …")
    words = _words(raw)
    utts = _utterances(raw)
    segments = _segments(sentences, raw)
    spans = _low_conf_spans(words)
    gaps = _gaps(words)
    faults = _continuity_faults(words)

    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "sermon": {"code": code,
                   "principal_speaker": args.speaker,
                   "production": args.production},
        "source": source_meta,
        "transcription": {
            "provider": "AssemblyAI",
            "api_base": _API_BASE,
            "transcript_id": raw.get("id"),
            "model": model_used or "account_default",
            "speech_model_reported": raw.get("speech_model"),
            "language": raw.get("language_code"),
            "language_requested": args.language,
            "punctuate": True,
            "format_text": True,
            "speaker_labels": args.speaker_labels,
            "custom_vocabulary_terms": len(word_boost),
            "audio_duration_sec": raw.get("audio_duration"),
            "overall_confidence": raw.get("confidence"),
            "started_utc": started.isoformat(),
            "finished_utc": finished.isoformat(),
            "pipeline": "scribeclaw.sermon_transcribe",
            "api_key_source": "env/ASSEMBLYAI_API_KEY",
        },
        "outputs": {
            "raw_json": names[0], "raw_txt": names[1],
            "corrected": names[2], "canonical": names[3],
            "timestamped": names[4], "word_timestamps": names[5],
            "metadata": names[6], "qa": names[7],
            "srt": names[8], "vtt": names[9],
        },
        "counts": {"words": len(words), "segments": len(segments),
                   "utterances": len(utts), "unclear_spans": len(spans),
                   "gaps": len(gaps), "continuity_faults": len(faults)},
        "provenance": {
            "source_untouched": True,
            "raw_preserved_separately": True,
            "layer_1_raw": "AssemblyAI response, verbatim",
            "layer_2_corrected": "deterministic orthography only "
                                 "(cedilla→comma-below, spacing) + [NECLAR] marks",
            "layer_3_canonical": "CANDIDATE — paragraph reflow of layer 2; "
                                 "not human-verified",
            "qa_status": "automated_checks_only",
        },
    }

    raw_text = (raw.get("text") or "").strip()
    corrected = _corrected_text(segments, spans)

    (out_dir / names[0]).write_text(
        json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / names[1]).write_text(raw_text, encoding="utf-8")
    (out_dir / names[2]).write_text(corrected, encoding="utf-8")
    (out_dir / names[3]).write_text(
        _canonical_md(code, corrected, meta), encoding="utf-8")
    (out_dir / names[4]).write_text(
        _timestamped_md(code, segments, utts, args.timestamp_interval),
        encoding="utf-8")
    (out_dir / names[5]).write_text(
        json.dumps({"transcript_id": raw.get("id"), "source": src.name,
                    "units": "seconds", "words": words, "utterances": utts},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / names[6]).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / names[7]).write_text(
        _qa_md(code, raw, words, segments, spans, gaps, faults, meta),
        encoding="utf-8")
    (out_dir / names[8]).write_text(_srt(segments), encoding="utf-8")
    (out_dir / names[9]).write_text(_vtt(segments), encoding="utf-8")

    print(f"[6/6] wrote {len(names)} files to {out_dir}")
    for n in names:
        print(f"      {n}")
    print()
    print(f"transcript_id : {raw.get('id')}")
    print(f"language      : {raw.get('language_code')}")
    print(f"words         : {len(words)}")
    print(f"unclear spans : {len(spans)}")
    print(f"QA report     : {out_dir / names[7]}")
    return 0


def main_with_argv(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="scribeclaw.sermon_transcribe",
        description="Transcribe one sermon file with AssemblyAI and emit the "
                    "three-layer evidence package. Source is read-only.")
    p.add_argument("--input", required=True, help="absolute path to the audio file")
    p.add_argument("--code", required=True, help="sermon code, e.g. C0089")
    p.add_argument("--out-dir", help="output dir (default: <source dir>/<code>_Transcription)")
    p.add_argument("--language", default="ro", help="AssemblyAI language_code (default: ro)")
    p.add_argument("--speech-model", default="best",
                   help="AssemblyAI speech_model; falls back to the account "
                        "default if rejected (default: best)")
    p.add_argument("--speaker-labels", action="store_true",
                   help="request diarization (adds utterances + speaker tags)")
    p.add_argument("--word-boost-file",
                   help="newline-separated custom vocabulary (biblical names, "
                        "theological terms); '#' lines ignored")
    p.add_argument("--speaker", default="Dr Emanoil Geaboc",
                   help="principal speaker, recorded in metadata")
    p.add_argument("--production", default="Jabbok River Productions",
                   help="production, recorded in metadata")
    p.add_argument("--timestamp-interval", type=float, default=30.0,
                   help="seconds per block in the timestamped transcript")
    p.add_argument("--poll-sec", type=int, default=10)
    p.add_argument("--poll-timeout-sec", type=int, default=7200,
                   help="default 2h — long sermons transcribe slowly")
    p.add_argument("--overwrite", action="store_true",
                   help="allow replacing an existing package (compares first "
                        "and refuses without this flag)")
    return asyncio.run(run(p.parse_args(argv)))


def main() -> int:
    return main_with_argv(None)


if __name__ == "__main__":
    raise SystemExit(main())
