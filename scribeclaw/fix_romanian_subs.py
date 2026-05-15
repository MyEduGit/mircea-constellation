#!/usr/bin/env python3
"""fix_romanian_subs.py — One-command Romanian subtitle correction pipeline.

Usage (on Mac, from any directory):
    python3 fix_romanian_subs.py <YOUTUBE_VIDEO_ID_OR_URL> [--out OUTPUT.srt]

What it does automatically:
  1. Downloads auto-generated Romanian subtitles via yt-dlp
  2. Falls back to AssemblyAI transcription if no subtitles found
  3. Applies deterministic orthography fixes (cedilla → comma-below, spacing)
  4. Sends to Claude API for professor-grade Romanian linguistic correction
     (capitalisation, punctuation, theological terminology, diacritics)
  5. Writes corrected .srt ready for upload to YouTube Studio

Requirements:
    pip install yt-dlp anthropic assemblyai
    export ANTHROPIC_API_KEY=<your key>
    export ASSEMBLYAI_API_KEY=<your key>   # optional fallback

Proven pipeline for Dr. Emanoil Geaboc — JabbokRiver Productions.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# ── Theological Romanian dictionary ─────────────────────────────────────────
# Deterministic replacements that must survive LLM rewriting.
# Keys are exact (lowercased for matching); values are canonical forms.
THEOLOGICAL_CORRECTIONS: dict[str, str] = {
    # Diacritics that Whisper/YouTube often miss
    "hristos": "Hristos",
    "isus": "Isus",
    "iisus": "Iisus",
    "dumnezeu": "Dumnezeu",
    "duhul sfant": "Duhul Sfânt",
    "duhul sfânt": "Duhul Sfânt",
    "spiritul sfant": "Spiritul Sfânt",
    "spiritul sfânt": "Spiritul Sfânt",
    "biblia": "Biblia",
    "scriptura": "Scriptura",
    "scripturile": "Scripturile",
    "evanghelia": "Evanghelia",
    "apocalipsa": "Apocalipsa",
    "geneza": "Geneza",
    "exodul": "Exodul",
    "psalmii": "Psalmii",
    "proverbele": "Proverbele",
    "isaia": "Isaia",
    "ieremia": "Ieremia",
    "daniel": "Daniel",
    "matei": "Matei",
    "marcu": "Marcu",
    "luca": "Luca",
    "ioan": "Ioan",
    "faptele apostolilor": "Faptele Apostolilor",
    "romani": "Romani",
    "corinteni": "Corinteni",
    "galateni": "Galateni",
    "efeseni": "Efeseni",
    "filipeni": "Filipeni",
    "coloseni": "Coloseni",
    "tesaloniceni": "Tesaloniceni",
    "timotei": "Timotei",
    "tit": "Tit",
    "filimon": "Filimon",
    "evrei": "Evrei",
    "iacov": "Iacov",
    "petru": "Petru",
    "iuda": "Iuda",
    # Adventist / theological terms
    "neprihănire": "neprihănire",
    "neprihanitre": "neprihănire",
    "neprihânire": "neprihănire",
    "sabat": "Sabat",
    "sabatul": "Sabatul",
    "advent": "Advent",
    "adventist": "adventist",
    "adventistă": "adventistă",
    "adventism": "adventism",
    "teologia ultimei generatii": "Teologia Ultimei Generații",
    "teologia ultimei generații": "Teologia Ultimei Generații",
    "sora white": "Sora White",
    "ellen white": "Ellen White",
    "ellen g. white": "Ellen G. White",
    "spiritul profetic": "Spiritul Profetic",
    "cartea neamurilor": "Cartea Neamurilor",
    "cartea urantia": "Cartea Urantia",
    "apostolul pavel": "Apostolul Pavel",
    "apostolul petru": "Apostolul Petru",
    "apostolul ioan": "Apostolul Ioan",
    # C0072 — Spiritism / Modern Spiritualism specific terms
    # ASR garbles these heavily in Romanian theological speech
    "spiritism": "spiritism",
    "spiritismul": "spiritismul",
    "spiritismului": "spiritismului",
    "spiritist": "spiritist",
    "spiritistă": "spiritistă",
    "mediumship": "mediumship",
    "medium": "medium",
    "mediumul": "mediumul",
    "surorile fox": "surorile Fox",
    "fratii fox": "frații Fox",
    "frații fox": "frații Fox",
    "fox": "Fox",
    "hydesville": "Hydesville",
    "new york": "New York",
    "emanuel swedenborg": "Emanuel Swedenborg",
    "swedenborg": "Swedenborg",
    "allan kardec": "Allan Kardec",
    "kardec": "Kardec",
    "arthur conan doyle": "Arthur Conan Doyle",
    "conan doyle": "Conan Doyle",
    "marea lupta": "Marea Luptă",
    "marea luptă": "Marea Luptă",
    "marele conflict": "Marele Conflict",
    "starea mortilor": "Starea Morților",
    "starea morților": "Starea Morților",
    "nemurirea sufletului": "nemurirea sufletului",
    "nemuritorul suflet": "nemuritorul suflet",
    "mortii nu stiu nimic": "Morții nu știu nimic",
    "morții nu știu nimic": "Morții nu știu nimic",
    "sedinta spiritista": "ședință spiritistă",
    "ședință spiritistă": "ședință spiritistă",
    "invocare": "invocare",
    "invocarea mortilor": "invocarea morților",
    "new age": "New Age",
    "mișcarea new age": "Mișcarea New Age",
    "miscarea new age": "Mișcarea New Age",
    "val": "val",
    "cele trei valuri": "Cele Trei Valuri",
    "primul val": "Primul Val",
    "al doilea val": "Al Doilea Val",
    "al treilea val": "Al Treilea Val",
    "spiritismul modern": "Spiritismul Modern",
    "marturiile lui ellen white": "Mărturiile lui Ellen White",
    "patimi și moarte": "Patimi și Moarte",
    "dorința veacurilor": "Dorința Veacurilor",
    "dorinta veacurilor": "Dorința Veacurilor",
    "tragedia veacurilor": "Tragedia Veacurilor",
    "profeti si regi": "Profeți și Regi",
    "profeți și regi": "Profeți și Regi",
    "solii alese": "Solii Alese",
    "evenimentele ultimelor zile": "Evenimentele Ultimelor Zile",
    "conferinta generala": "Conferința Generală",
    "conferința generală": "Conferința Generală",
    "adventistii de ziua a saptea": "Adventiștii de Ziua a Șaptea",
    "adventiștii de ziua a șaptea": "Adventiștii de Ziua a Șaptea",
    # Common ASR errors for Romanian
    "şi": "și",
    "ş": "ș",
    "ţ": "ț",
    "ţara": "țara",
    "ţările": "țările",
}

# Cedilla → comma-below (Whisper / YouTube auto-sub often emit cedilla)
_CEDILLA_MAP = str.maketrans({
    "ş": "ș",  # ş → ș
    "Ş": "Ș",  # Ş → Ș
    "ţ": "ț",  # ţ → ț
    "Ţ": "Ț",  # Ţ → Ț
})

_MULTISPACE = re.compile(r"[ \t]+")
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([,.;:!?»])")
_SPACE_AFTER_OPEN = re.compile(r"([«(])\s+")


def _fix_deterministic(text: str) -> str:
    """Apply rule-based fixes that must not be delegated to LLM."""
    text = text.translate(_CEDILLA_MAP)
    text = _MULTISPACE.sub(" ", text)
    text = _SPACE_BEFORE_PUNCT.sub(r"\1", text)
    text = _SPACE_AFTER_OPEN.sub(r"\1", text)
    # Theological proper-noun enforcement (case-insensitive match)
    for wrong, right in THEOLOGICAL_CORRECTIONS.items():
        text = re.sub(re.escape(wrong), right, text, flags=re.IGNORECASE)
    return text.strip()


# ── SRT parsing / rendering ─────────────────────────────────────────────────

def parse_srt(raw: str) -> list[dict]:
    """Return list of {index, start, end, text} dicts."""
    blocks = re.split(r"\n{2,}", raw.strip())
    entries = []
    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 3:
            continue
        try:
            index = int(lines[0].strip())
        except ValueError:
            continue
        timecode = lines[1].strip()
        text = " ".join(l.strip() for l in lines[2:])
        m = re.match(
            r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})", timecode
        )
        if not m:
            continue
        entries.append({"index": index, "start": m.group(1), "end": m.group(2), "text": text})
    return entries


def render_srt(entries: list[dict]) -> str:
    """Render entries back to SRT format."""
    parts = []
    for i, e in enumerate(entries, 1):
        parts.append(f"{i}\n{e['start']} --> {e['end']}\n{e['text']}")
    return "\n\n".join(parts) + "\n"


# ── Step 1: Download subtitles ───────────────────────────────────────────────

def download_subtitles(video_id: str, tmp_dir: Path) -> str | None:
    """Try yt-dlp to get Romanian subtitles. Returns raw SRT string or None."""
    url = f"https://youtu.be/{video_id}"
    out_tmpl = str(tmp_dir / "%(id)s.%(ext)s")

    for lang in ("ro", "ro-RO"):
        cmd = [
            "yt-dlp",
            "--write-sub", "--write-auto-sub",
            "--sub-lang", lang,
            "--sub-format", "srt",
            "--skip-download",
            "--no-playlist",
            "--output", out_tmpl,
            url,
        ]
        print(f"[yt-dlp] Trying language: {lang}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            for f in tmp_dir.glob("*.srt"):
                print(f"[yt-dlp] Found: {f}")
                return f.read_text(encoding="utf-8")
            # Also look for .vtt
            for f in tmp_dir.glob("*.vtt"):
                print(f"[yt-dlp] Found VTT (converting): {f}")
                return _vtt_to_srt(f.read_text(encoding="utf-8"))
        else:
            print(f"[yt-dlp] {lang} failed: {result.stderr[:200]}")

    return None


def _vtt_to_srt(vtt: str) -> str:
    """Minimal VTT → SRT conversion."""
    lines = vtt.splitlines()
    entries, block, idx = [], [], 1
    for line in lines:
        if re.match(r"\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*", line):
            if block:
                entries.append((idx, "\n".join(block)))
                idx += 1
                block = []
            tc = line.replace(".", ",", 1).replace(".", ",", 1)
            # Ensure HH:MM:SS,mmm format
            parts = re.match(r"(\d+:\d+:\d+,\d+)\s*-->\s*(\d+:\d+:\d+,\d+)", tc)
            if parts:
                block.append(f"{parts.group(1)} --> {parts.group(2)}")
        elif line.strip() and not line.startswith("WEBVTT") and not line.startswith("Kind:"):
            # Strip VTT tags
            clean = re.sub(r"<[^>]+>", "", line).strip()
            if clean:
                block.append(clean)
    if block:
        entries.append((idx, "\n".join(block)))

    result = []
    for i, (n, content) in enumerate(entries, 1):
        result.append(f"{i}\n{content}")
    return "\n\n".join(result) + "\n"


# ── Step 2: AssemblyAI fallback ──────────────────────────────────────────────

def transcribe_assemblyai(video_id: str, tmp_dir: Path) -> str | None:
    """Download audio and transcribe via AssemblyAI. Returns SRT or None."""
    api_key = os.environ.get("ASSEMBLYAI_API_KEY")
    if not api_key:
        print("[AssemblyAI] No ASSEMBLYAI_API_KEY — skipping")
        return None

    # Download audio only
    audio_path = tmp_dir / f"{video_id}.mp3"
    url = f"https://youtu.be/{video_id}"
    cmd = [
        "yt-dlp", "-x", "--audio-format", "mp3",
        "--output", str(audio_path.with_suffix("")),
        "--no-playlist", url,
    ]
    print("[AssemblyAI] Downloading audio...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not audio_path.exists():
        print(f"[AssemblyAI] Audio download failed: {result.stderr[:200]}")
        return None

    try:
        import assemblyai as aai
        aai.settings.api_key = api_key
        config = aai.TranscriptionConfig(language_code="ro", punctuate=True, format_text=True)
        transcriber = aai.Transcriber()
        print("[AssemblyAI] Uploading and transcribing (this takes a few minutes)...")
        transcript = transcriber.transcribe(str(audio_path), config=config)
        if transcript.status == aai.TranscriptStatus.error:
            print(f"[AssemblyAI] Error: {transcript.error}")
            return None
        return transcript.export_subtitles_srt()
    except ImportError:
        print("[AssemblyAI] 'assemblyai' package not installed. Run: pip install assemblyai")
        return None
    except Exception as e:
        print(f"[AssemblyAI] Exception: {e}")
        return None


# ── Step 3: Claude API correction ────────────────────────────────────────────

SYSTEM_PROMPT = """Ești un lingvist român de elită cu expertiză în teologie adventistă și limba română literară.
Sarcina ta: corectează subtitrările românești la un standard de excepție — cel pe care un profesor universitar de limba română l-ar considera PERFECT.

CONTEXT PREDICĂ (C0072): Această predică se numește „Spiritismul Modern: Cele Trei Valuri ale Spiritismului" de Dr. Emanoil Geaboc. Conține referințe la: surorile Fox, Hydesville, Emanuel Swedenborg, Allan Kardec, Arthur Conan Doyle, Marea Luptă (Ellen White), starea morților, nemurirea sufletului, Mișcarea New Age. ASR-ul garblează frecvent aceste nume — reconstruiește-le corect din context.

REGULI ABSOLUTE:
1. CAPITALIZARE: Prima literă a fiecărui enunț sau propoziție principală se scrie cu majusculă. Substantivele proprii (nume de persoane, locuri, cărți biblice, denumiri teologice) se scriu cu majusculă.
2. PUNCTUAȚIE: Pune virgulă acolo unde există o pauză naturală sau o propoziție subordonată. Pune punct acolo unde enunțul se termină. Nu lăsa niciun segment fără punctuație finală dacă contextul o cere.
3. DIACRITICE: Folosește ÎNTOTDEAUNA diacriticele corecte românești: ă, â, î, ș (nu ş), ț (nu ţ). Niciodată literă fără diacritic acolo unde limba o cere.
4. TERMINOLOGIE TEOLOGICĂ: Respectă ortografia canonică: Iisus Hristos, Dumnezeu, Duhul Sfânt, Sabat, neprihănire, Spiritul Profetic, Ellen White / Sora White, Apostolul Pavel, etc.
5. REFERINȚE BIBLICE: Cărțile Bibliei se scriu cu majusculă și complet: Evanghelia după Ioan, Epistola către Romani, Faptele Apostolilor, etc.
6. COEZIUNE: Dacă un enunț este tăiat între două segmente de subtitrare, asigură-te că textul curge natural.
7. NU SCHIMBA CONȚINUTUL: Nu adăuga, nu elimina, nu reformula ideile. Corectează DOAR ortografia, punctuația și capitalizarea.
8. PĂSTREAZĂ TIMECODE-URILE: Returnează EXACT același format SRT, cu aceleași timecode-uri.

Returnează DOAR fișierul SRT corectat, fără explicații, fără comentarii."""

CORRECTION_PROMPT = """Corectează fișierul SRT următor conform regulilor de mai sus. Returnează DOAR SRT-ul corectat:

{srt_content}"""


def correct_with_claude(srt_content: str) -> str:
    """Send SRT to Claude API for professor-grade Romanian correction."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[Claude] No ANTHROPIC_API_KEY — skipping AI correction")
        return srt_content

    try:
        import anthropic
    except ImportError:
        print("[Claude] 'anthropic' package not installed. Run: pip install anthropic")
        return srt_content

    client = anthropic.Anthropic(api_key=api_key)

    # Process in chunks to respect context limits (max ~200 entries per call)
    entries = parse_srt(srt_content)
    CHUNK = 150
    corrected_entries = []

    total_chunks = (len(entries) + CHUNK - 1) // CHUNK
    print(f"[Claude] Correcting {len(entries)} segments in {total_chunks} chunk(s)...")

    for i in range(0, len(entries), CHUNK):
        chunk = entries[i:i + CHUNK]
        chunk_srt = render_srt(chunk)
        chunk_num = i // CHUNK + 1

        print(f"[Claude] Chunk {chunk_num}/{total_chunks} ({len(chunk)} segments)...")
        try:
            message = client.messages.create(
                model="claude-opus-4-7",
                max_tokens=8192,
                system=SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": CORRECTION_PROMPT.format(srt_content=chunk_srt)
                }]
            )
            corrected_chunk_srt = message.content[0].text.strip()
            corrected_chunk = parse_srt(corrected_chunk_srt)

            # Preserve original timecodes (Claude must not change them)
            for orig, corr in zip(chunk, corrected_chunk):
                corrected_entries.append({
                    "index": orig["index"],
                    "start": orig["start"],
                    "end": orig["end"],
                    "text": corr["text"] if corr else orig["text"],
                })
        except Exception as e:
            print(f"[Claude] Chunk {chunk_num} failed: {e} — keeping original")
            corrected_entries.extend(chunk)

    return render_srt(corrected_entries)


# ── Main ─────────────────────────────────────────────────────────────────────

def extract_video_id(input_str: str) -> str:
    """Extract YouTube video ID from URL or return as-is."""
    patterns = [
        r"youtu\.be/([A-Za-z0-9_-]{11})",
        r"youtube\.com/watch\?v=([A-Za-z0-9_-]{11})",
        r"youtube\.com/video/([A-Za-z0-9_-]{11})",
        r"^([A-Za-z0-9_-]{11})$",
    ]
    for p in patterns:
        m = re.search(p, input_str)
        if m:
            return m.group(1)
    raise ValueError(f"Cannot extract video ID from: {input_str}")


def main():
    parser = argparse.ArgumentParser(description="Fix Romanian YouTube subtitles — professor-grade")
    parser.add_argument("video", help="YouTube video ID or URL")
    parser.add_argument("--out", help="Output SRT path (default: <video_id>_RO_corrected.srt)")
    parser.add_argument("--skip-ai", action="store_true", help="Skip Claude AI correction (deterministic only)")
    args = parser.parse_args()

    video_id = extract_video_id(args.video)
    out_path = Path(args.out) if args.out else Path(f"{video_id}_RO_corrected.srt")

    print(f"\n{'='*60}")
    print(f"  JRP Romanian Subtitle Pipeline")
    print(f"  Video: {video_id}")
    print(f"  Output: {out_path}")
    print(f"{'='*60}\n")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)

        # Step 1: Get subtitles
        print("── Step 1: Download Romanian subtitles ──")
        raw_srt = download_subtitles(video_id, tmp_dir)

        if not raw_srt:
            print("── Step 1b: AssemblyAI fallback ──")
            raw_srt = transcribe_assemblyai(video_id, tmp_dir)

        if not raw_srt:
            print("\n❌ Could not obtain subtitles or transcript.")
            print("   Options:")
            print("   1. Download manually from YouTube Studio → Subtitles → Download")
            print("   2. Set ASSEMBLYAI_API_KEY and retry")
            print(f"   3. Provide .srt file directly: python3 {sys.argv[0]} --from-srt file.srt")
            sys.exit(1)

        print(f"   ✓ Got raw subtitles ({len(raw_srt)} chars, {raw_srt.count(chr(10)*2)} blocks approx)")

        # Step 2: Deterministic fixes
        print("\n── Step 2: Deterministic orthography fixes ──")
        entries = parse_srt(raw_srt)
        for e in entries:
            e["text"] = _fix_deterministic(e["text"])
        deterministic_srt = render_srt(entries)
        print(f"   ✓ {len(entries)} segments processed")

        # Step 3: Claude AI correction
        if not args.skip_ai:
            print("\n── Step 3: Claude AI — professor-grade correction ──")
            final_srt = correct_with_claude(deterministic_srt)
        else:
            print("\n── Step 3: Skipped (--skip-ai) ──")
            final_srt = deterministic_srt

        # Write output
        out_path.write_text(final_srt, encoding="utf-8")
        final_entries = parse_srt(final_srt)
        print(f"\n{'='*60}")
        print(f"  ✅ Done! {len(final_entries)} corrected segments")
        print(f"  Output: {out_path}")
        print(f"{'='*60}")
        print(f"\nNext step — upload to YouTube Studio:")
        print(f"  1. Go to: https://studio.youtube.com/video/{video_id}/translations")
        print(f"  2. Click 'Română' → pencil icon → 'Înlocuiește fișierul'")
        print(f"  3. Upload: {out_path}")
        print(f"  4. Select 'Cu sincronizare' → Publică\n")


def sbv_ts_to_srt(ts: str) -> str:
    """Convert SBV H:MM:SS.mmm → SRT HH:MM:SS,mmm"""
    ts = ts.strip()
    main, ms = ts.rsplit(".", 1) if "." in ts else (ts, "000")
    ms = ms.ljust(3, "0")[:3]
    parts = main.split(":")
    h, m, s = (parts[0].zfill(2), parts[1], parts[2]) if len(parts) == 3 else ("00", parts[0], parts[1])
    return f"{h}:{m.zfill(2)}:{s.zfill(2)},{ms}"


def parse_sbv(text: str) -> list[dict]:
    """Parse YouTube SBV format into SRT-compatible entry list."""
    blocks = re.split(r"\n{2,}", text.strip())
    entries = []
    for block in blocks:
        lines = block.strip().splitlines()
        if not lines:
            continue
        m = re.match(r"(\d+:\d+:\d+\.\d+),(\d+:\d+:\d+\.\d+)", lines[0].strip())
        if not m:
            continue
        start = sbv_ts_to_srt(m.group(1))
        end = sbv_ts_to_srt(m.group(2))
        body = " ".join(l.strip() for l in lines[1:] if l.strip())
        entries.append({"index": len(entries) + 1, "start": start, "end": end, "text": body})
    return entries


if __name__ == "__main__":
    # Also support running directly on an existing SRT file
    if len(sys.argv) > 1 and sys.argv[1] == "--from-sbv":
        if len(sys.argv) < 3:
            print("Usage: fix_romanian_subs.py --from-sbv <file.sbv> [--out output.srt]")
            sys.exit(1)
        sbv_path = Path(sys.argv[2])
        raw = sbv_path.read_text(encoding="utf-8")
        entries = parse_sbv(raw)
        for e in entries:
            e["text"] = _fix_deterministic(e["text"])
        det_srt = render_srt(entries)
        out = Path(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[3] == "--out" else sbv_path.with_suffix("").with_stem(sbv_path.stem + "_corrected")
        out = out.with_suffix(".srt")
        skip_ai = "--skip-ai" in sys.argv
        final = det_srt if skip_ai else correct_with_claude(det_srt)
        out.write_text(final, encoding="utf-8")
        print(f"✅ Written: {out}")
    elif len(sys.argv) > 1 and sys.argv[1] == "--from-srt":
        if len(sys.argv) < 3:
            print("Usage: fix_romanian_subs.py --from-srt <file.srt> [--out output.srt]")
            sys.exit(1)
        srt_path = Path(sys.argv[2])
        raw = srt_path.read_text(encoding="utf-8")
        entries = parse_srt(raw)
        for e in entries:
            e["text"] = _fix_deterministic(e["text"])
        det_srt = render_srt(entries)
        out = Path(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[3] == "--out" else srt_path.with_stem(srt_path.stem + "_corrected")
        skip_ai = "--skip-ai" in sys.argv
        final = det_srt if skip_ai else correct_with_claude(det_srt)
        out.write_text(final, encoding="utf-8")
        print(f"✅ Written: {out}")
    else:
        main()
