---
title: Geaboc Glossary Tuning — ASR error catalog & correction policy
type: reference
status: living
updated_at: 2026-07-24
aliases:
  - glossary tuning
  - SAFE_CORRECTIONS
  - transcription corrections
  - ASR errors Geaboc
  - subtitle correction policy
  - Romanian ASR fixes
tags:
  - transcription
  - assemblyai
  - glossary
  - geaboc
  - quality
  - reference
tool: scribeclaw/geaboc/geaboc_subtitle_console.py
related:
  - "[[TRANSCRIBE]]"
  - "[[AssemblyAI_Console]]"
---

# Geaboc Glossary Tuning

How the console's `SAFE_CORRECTIONS` dictionary is grown safely. Read this
before adding entries — one wrong entry corrupts correct transcripts.

## The one rule that keeps it safe

`SAFE_CORRECTIONS` maps a **wrong** spelling → a **canonical** one, applied as
a case-insensitive, whole-word replacement. Therefore:

- ✅ **Add** a mapping only when the key is a **non-word** (something valid
  Romanian never spells) OR a clear un-accented form of a proper noun, and the
  target is **unambiguous**. Example: `"mala lupta" → "Marea Luptă"`.
- ❌ **Never** map one **valid word to another valid word.** The canonical
  trap: `"credințe" → "credință"`. `credințe` is the legitimate plural of
  `credință`; that rule would silently corrupt every correct plural. It is
  **deliberately excluded.** Agreement/diacritic *drift* (a valid word heard as
  another valid word) is a model problem, not a dictionary problem — fix it by
  using a better engine, not by find-and-replace.
- ⚠️ **Key to the engine you actually run.** The live pipeline is **AssemblyAI**
  (`universal-3-5-pro` → `universal-2`). Entries should be keyed to what
  *AssemblyAI* mishears. Junk produced only by the local whisper-`small` draft
  (below) is catalogued here but **not** added to the live dict — AssemblyAI
  won't emit those strings, so they'd be dead weight.

## Proof tiers

| Tier | Meaning |
|---|---|
| **VERIFIED** | Correct target confirmed; key is a non-word or safe un-accented form. In the dict. |
| **CANDIDATE** | Plausible; confirm against a real AssemblyAI transcript before adding. |
| **REJECTED** | Would corrupt correct text; must never be added. |

## Catalog — observed on C0083 (whisper-`small` draft, 2026-07-24)

Proper nouns & citation anchors (highest priority — these carry the sources):

| Heard | Correct | In dict? | Tier |
|---|---|---|---|
| Meral Domnie / Meral Domnile | Merle d'Aubigné | yes | VERIFIED |
| Mala Luptă | Marea Luptă | yes | VERIFIED |
| istoria reformatiu(nii) | Istoria Reformațiunii | yes | VERIFIED |
| valbenci / valdensi / waldensi | valdenzi | yes | VERIFIED |
| marță, luta | Martin Luther | no — phrase split across segments | CANDIDATE |

Whisper-`small` artifacts — **catalogued, NOT added** (AssemblyAI won't produce
these; listed so nobody "fixes" them into the live dict blindly):

| Heard | Correct | Why not added |
|---|---|---|
| trăturor | tuturor | whisper-only garble |
| prelerea de septemâna | predica de săptămâna | whisper-only garble |
| Lâgânezeu | lui Dumnezeu | whisper fusion of "lui Dumnezeu" |
| Coventul Săl | Cuvântul Său | whisper-only garble |
| niscribez | scrisă | whisper-only garble |
| Amine | Amin | low value; verify vs AssemblyAI first |
| Aspirii Lui Profetic | Spiritul Profetic | whisper-only; "spiritul profetic" already normalized |

REJECTED (never add):

| Heard | "Correct" | Reason |
|---|---|---|
| credințe | credință | `credințe` is the valid plural — rule would corrupt correct text |
| contradiții | contradicții | too close to valid inflections; fix via engine, not dict |

## Workflow to grow the dict

1. Run the episode through **AssemblyAI** (the console — `Transcribe.command`).
2. Read the QA file and skim the transcript for proper-noun / citation errors.
3. For each, apply the one rule above. Add VERIFIED entries; park CANDIDATEs
   here until a second episode confirms the pattern; log REJECTEDs so they stay
   out.
4. Re-run; the correction pass is deterministic, so fixes compound safely.

_Tool: `scribeclaw/geaboc/`. How-to: [[TRANSCRIBE]]. Background: [[AssemblyAI_Console]]._
