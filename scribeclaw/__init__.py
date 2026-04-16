"""ScribeClaw — execution runtime (media transcription sub-role).

Singular primary role: controlled execution of a media pipeline —
edit (ffmpeg) → transcribe (faster-whisper, Romanian-first) →
post-process (diacritics, punctuation) → package YouTube metadata.

Does not observe (NemoClaw), does not remediate (Fireclaw), does not
adjudicate (LuciferiClaw), does not explain (VisualUrantiClaw), does
not bundle evidence (Paperclip). Emits evidence records per handler
call; Paperclip owns the bundling contract once it ships.

Truthful label: deployable scaffold. Real handlers:
  - media_edit         (ffmpeg; requires ffmpeg on PATH)
  - audio_extract      (ffmpeg)
  - transcribe_ro      (faster-whisper; requires model on disk / downloadable)
  - postprocess_transcript
  - youtube_metadata
Stub handler:
  - youtube_upload     (requires operator-supplied OAuth client secret)

UrantiOS governed — Truth, Beauty, Goodness.
"""

__version__ = "0.1.0"
