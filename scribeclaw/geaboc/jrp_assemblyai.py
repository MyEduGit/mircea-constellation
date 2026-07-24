#!/usr/bin/env python3
"""
jrp_assemblyai.py — Geaboc pipeline P2 transcription (lean CLI)
Host:   iMAC_M4 (hosts NemoClaw)
Rule:   The API key is NEVER stored in this file. It is read from the macOS
        Keychain at runtime. See SERVICES_REGISTER.md (NC-REG-SERVICES-001).

Outputs: <stem>_transcript.txt, <stem>_full.json, <stem>.srt, <stem>.vtt,
         and <stem>_lowconf.txt — every token under 0.60 confidence with its
         timestamp, so the correction pass targets exactly the shaky words.

Usage:  python3 jrp_assemblyai.py /path/to/C0083_AUDIO__.mp3
        python3 jrp_assemblyai.py file.mp3 --lang ro --outdir ./out --correct
        python3 jrp_assemblyai.py file.mp3 --model universal-3-5-pro

Relationship to geaboc_subtitle_console.py (same folder):
  - Console = one-click web UI, produces glossary-corrected SUBTITLES.
  - This    = lean CLI, produces RAW AssemblyAI output + the low-confidence
              audit file. Pass --correct to also emit a glossary-corrected
              plaintext transcript (reuses the console's SAFE_CORRECTIONS).
  Both read the SAME key from the Keychain (either service name below).
"""

import argparse, json, mimetypes, os, subprocess, sys, time, urllib.request, urllib.error

API = "https://api.assemblyai.com/v2"
# The one key has been filed under different Keychain service names by
# different tools. Accept all of them so they can never collide. See
# SERVICES_REGISTER.md — the secret itself lives only in the Keychain.
KEYCHAIN_SERVICES = ("assemblyai-api-key", "Geaboc AssemblyAI API Key")


def _keychain(service):
    """Return the key for a Keychain generic-password service, or None."""
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-a", os.environ.get("USER", ""),
             "-s", service, "-w"],
            capture_output=True, text=True, check=True)
        return out.stdout.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        # CalledProcessError: no such item. FileNotFoundError: not macOS.
        return None


def get_key():
    """Read the API key from env or the macOS Keychain. Never from a file/argv."""
    env = os.environ.get("ASSEMBLYAI_API_KEY")
    if env:
        return env.strip()
    for service in KEYCHAIN_SERVICES:
        key = _keychain(service)
        if key:
            return key
    services = " or ".join(f"'{s}'" for s in KEYCHAIN_SERVICES)
    sys.exit(
        f"\nERROR: no key found in Keychain under {services}.\n"
        f"Run the one-time setup first:\n"
        f"  security add-generic-password -a \"$USER\" -s {KEYCHAIN_SERVICES[0]} -w\n"
        f"(it will prompt for the key; paste it there, not into a terminal argument)\n")


def load_corrector():
    """Import SAFE_CORRECTIONS pass from the sibling console, if available."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import importlib
        return importlib.import_module("geaboc_subtitle_console").apply_safe_corrections
    except Exception:
        return None


def req(url, key, data=None, headers=None, method=None):
    h = {"authorization": key}
    if headers:
        h.update(headers)
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} on {url}\n{e.read().decode(errors='replace')[:800]}")


def upload(path, key):
    size = os.path.getsize(path)
    print(f"[1/4] uploading {os.path.basename(path)} ({size/1e6:.1f} MB) ...", flush=True)
    with open(path, "rb") as f:
        body = req(f"{API}/upload", key, data=f,
                   headers={"content-type": "application/octet-stream",
                            "content-length": str(size)})
    url = json.loads(body)["upload_url"]
    print("      upload ok", flush=True)
    return url


def submit(audio_url, key, lang, speakers, model):
    payload = {
        "audio_url": audio_url,
        "language_code": lang,
        "punctuate": True,
        "format_text": True,
    }
    if speakers:
        payload["speaker_labels"] = True
    if model:                      # omit -> account default (Universal)
        payload["speech_model"] = model
    print(f"[2/4] submitting job  lang={lang}  model={model or 'account default'}", flush=True)
    body = req(f"{API}/transcript", key,
               data=json.dumps(payload).encode(),
               headers={"content-type": "application/json"})
    tid = json.loads(body)["id"]
    print(f"      transcript id: {tid}", flush=True)
    return tid


def poll(tid, key):
    print("[3/4] processing (polling every 10s) ...", flush=True)
    t0 = time.time()
    while True:
        d = json.loads(req(f"{API}/transcript/{tid}", key))
        st = d.get("status")
        if st == "completed":
            print(f"      completed in {time.time()-t0:.0f}s", flush=True)
            return d
        if st == "error":
            sys.exit(f"TRANSCRIPTION FAILED: {d.get('error')}")
        print(f"      status={st}  elapsed={time.time()-t0:.0f}s", flush=True)
        time.sleep(10)


def export(tid, key, fmt):
    """Ask AssemblyAI for subtitle exports. Returns None if unsupported."""
    try:
        return req(f"{API}/transcript/{tid}/{fmt}", key).decode()
    except SystemExit:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--lang", default="ro", help="ISO code, default ro (Romanian)")
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--speakers", action="store_true", help="enable speaker diarization")
    ap.add_argument("--model", default="", help="speech_model; leave blank for account default")
    ap.add_argument("--correct", action="store_true",
                    help="also write a glossary-corrected plaintext transcript "
                         "(reuses geaboc_subtitle_console.py SAFE_CORRECTIONS)")
    a = ap.parse_args()

    if not os.path.isfile(a.audio):
        sys.exit(f"No such file: {a.audio}")
    os.makedirs(a.outdir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(a.audio))[0]
    key = get_key()

    d = poll(submit(upload(a.audio, key), key, a.lang, a.speakers, a.model), key)

    print("[4/4] writing outputs ...", flush=True)
    base = os.path.join(a.outdir, stem)

    text = d.get("text") or ""
    with open(base + "_transcript.txt", "w") as f:
        f.write(text)
    with open(base + "_full.json", "w") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)

    for fmt in ("srt", "vtt"):
        s = export(d["id"], key, fmt)
        if s:
            with open(f"{base}.{fmt}", "w") as f:
                f.write(s)

    words = d.get("words") or []
    low = [w for w in words if (w.get("confidence") or 1) < 0.60]
    with open(base + "_lowconf.txt", "w") as f:
        for w in low:
            f.write(f"{w['start']/1000:8.2f}s  {w.get('confidence',0):.2f}  {w['text']}\n")

    corrected_path = None
    if a.correct:
        corrector = load_corrector()
        if corrector:
            corrected_path = base + "_transcript_corrected.txt"
            with open(corrected_path, "w") as f:
                f.write(corrector(text))
        else:
            print("      --correct requested but geaboc_subtitle_console.py "
                  "not importable; skipped", flush=True)

    n = len(text.split())
    print(f"\nDONE  {n} words | {len(words)} tokens | {len(low)} below 0.60 confidence")
    print(f"      {base}_transcript.txt")
    print(f"      {base}.srt / .vtt")
    print(f"      {base}_lowconf.txt   <- start your correction pass here")
    if corrected_path:
        print(f"      {corrected_path}   <- glossary-corrected plaintext")


if __name__ == "__main__":
    main()
