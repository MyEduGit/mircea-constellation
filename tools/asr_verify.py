#!/usr/bin/env python3
"""Offline speech-to-text for verifying classroom audio against known scripts.

Built for Claude Code cloud sessions on this repo, where the egress policy
blocks the usual ASR model hosts (huggingface.co, alphacephei.com,
openaipublic.azureedge.net, download.pytorch.org) but allows PyPI directly.
PocketSphinx ships its English acoustic model inside the pip wheel, so the
whole pipeline works with no external model download:

    pip install pocketsphinx av numpy
    python3 tools/asr_verify.py <audio-file> [script.txt]

With just an audio file it prints the raw transcript. With a reference
script it also prints content-word recall — the discriminating metric:
matched audio/script pairs score far above mismatched ones (observed:
30-60% vs 4-7% on AMEP Cert III assessment recordings), so use relative
separation, not absolute accuracy, to judge a match. PocketSphinx is a
dated model; expect noisy raw output on accented or compressed speech.

Accepts anything PyAV can decode (mp3, mp4/m4a, wav, ...).
"""
import sys, re, wave, os, tempfile


def to_wav16k(src, dst):
    import av
    import numpy as np
    container = av.open(src)
    stream = next(s for s in container.streams if s.type == 'audio')
    resampler = av.AudioResampler(format='s16', layout='mono', rate=16000)
    frames = []
    for packet in container.demux(stream):
        for frame in packet.decode():
            for rf in resampler.resample(frame):
                frames.append(rf.to_ndarray())
    pcm = np.concatenate(frames, axis=1).astype(np.int16).tobytes()
    with wave.open(dst, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(pcm)
    return len(pcm) / 2 / 16000


def transcribe(wav):
    from pocketsphinx import Decoder
    d = Decoder(samprate=16000)
    d.start_utt()
    with open(wav, 'rb') as f:
        f.read(44)
        while True:
            buf = f.read(8192)
            if not buf:
                break
            d.process_raw(buf, False, False)
    d.end_utt()
    return d.hyp().hypstr if d.hyp() else ''


STOP = set('this that with your will have from they them then than were what '
           'when how the and for you are not can its it is a an of to in on '
           'at be or so do don as we i my me our us if all also'.split())


def content_words(text):
    return {w for w in re.findall(r"[a-z']+", text.lower())
            if len(w) >= 4 and w not in STOP}


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    audio = sys.argv[1]
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        wav = tmp.name
    try:
        dur = to_wav16k(audio, wav)
        print(f"decoded {os.path.basename(audio)}: {dur:.1f}s @16kHz mono")
        text = transcribe(wav)
        print(f"\n--- transcript ({len(text.split())} words) ---\n{text}\n")
        if len(sys.argv) > 2:
            script = open(sys.argv[2]).read()
            sw, aw = content_words(script), content_words(text)
            recall = len(aw & sw) / len(sw) if sw else 0.0
            print(f"content-word recall vs script: {recall:.0%} "
                  f"({len(aw & sw)}/{len(sw)} distinct words)")
            print("matched sample:", ', '.join(sorted(aw & sw)[:20]))
    finally:
        os.unlink(wav)


if __name__ == '__main__':
    main()
