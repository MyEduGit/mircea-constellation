"""SeedanceClaw — AI video generation execution runtime.

Singular primary role: controlled execution of video generation via
ByteDance Seedance (text-to-video, image-to-video) through the fal.ai API.

Does not observe (NemoClaw), does not remediate (Fireclaw), does not
adjudicate (LuciferiClaw), does not explain (VisualUrantiClaw), does
not bundle evidence (Paperclip). Emits evidence records per handler call.

Truthful label: deployable scaffold. Real handlers:
  - text_to_video   (fal.ai Seedance; requires FAL_KEY)
  - image_to_video  (fal.ai Seedance; requires FAL_KEY)
  - download_video  (fetch a remote video URL to /data/videos/)

UrantiOS governed — Truth, Beauty, Goodness.
"""

__version__ = "0.1.0"
