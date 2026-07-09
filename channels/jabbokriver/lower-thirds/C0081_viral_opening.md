# C0081 — Viral opening treatment (retention past 0:35)

Goal: hold the viewer through the first 30–35 seconds of the C0081 sermon
(**Închiderea Harului**) and set up retention for the full video.

Everything here follows one guardrail from `COVENANT.md`: every hook line
is Dr. Geaboc's own material from this sermon — quoted, tightened, or
lightly corrected from the raw transcript. No manufactured claims.

---

## Why the current opening loses viewers

The recording opens with a liturgical greeting ("Vă rog tuturor ca de
obicei… har și pace…") followed by a slow topic announcement ("în lectura
de săptămâna aceasta o să vorbim despre…"). Research is unanimous that
this is the highest-cost pattern on YouTube: viewers decide in the first
5–10 seconds, up to 30% leave inside 30 seconds even with a good opening,
and "today we're going to talk about…" is the canonical drop-off trigger.
The greeting is not cut from the sermon — it is *relocated* to ~0:35,
after the hook has earned the viewer's stay.

## The retention structure applied (0:00 → 0:40)

Hook framework: 0–5s attention grab → 5–15s promise → 15–30s stakes/open
loops → pattern interrupt at ~0:30 → content begins.

| Time | Beat | Screen | Audio |
|------|------|--------|-------|
| 0:00–0:05 | **Cold open — bold claim** (flash-forward clip pulled from mid-sermon) | Dr. Geaboc mid-sermon, tight crop, captions ON | «Fără zgomot, nevăzută, va veni ora decisivă care marchează destinul oricărui om.» |
| 0:05–0:12 | **Stakes — the shock stat + the fear** | Cut to second mid-sermon clip; text overlay: „6 din 10"* | «În jur de 60% dintre adventiști nu mai cred această doctrină.* Un editor adventist spune că a fost terorizat de ea din copilărie.» |
| 0:12–0:20 | **The promise** (what this video delivers) | Clip or VO over B-roll (open Bible); overlay: „Ce spune Biblia — nu tradiția" | «Astăzi vedem ce se întâmplă de fapt la închiderea harului — și ce NU se întâmplă.» |
| 0:20–0:30 | **Three open loops** (tease later payoffs, in order of appearance) | Rapid 3-card montage, one overlay each | ① «De ce filmele *Left Behind* greșesc complet» ② «De ce nimeni — nimeni — nu poate ști data» ③ «Ce se întâmplă cu poporul lui Dumnezeu după ce ușa se închide» |
| 0:30–0:33 | **Pattern interrupt** | HARD CUT to black / door-closing B-roll (arca lui Noe motif), music stops, single SFX (heavy door) | Silence, then: «Și Domnul a închis ușa după el.» (Geneza 7:16) |
| 0:33–0:40 | **Sermon begins** | Wide shot, HostLowerThird card #1 (speaker ID), greeting *briefly* | Trimmed greeting → straight into «O să vorbim despre închiderea harului…» |

\* The 60% figure is garbled in the raw ASR («În jur de 60% advențizii
așatea care nu cred în doctrina santuarului») — **verify against the audio
before using it on screen**. If unclear, replace beat 2 with the
Adventist-Today-editor line alone, which is unambiguous in the recording.

## Techniques carried through the rest of the video

1. **Captions always on** — the majority of first-30s viewers are muted;
   word-level captions are already the house style (`Captions.tsx`).
2. **Silence removal + tight cuts for the first 60s** (cut every 10–20s),
   then relax to 25–40s spacing once the viewer is committed.
3. **Replay the hook in context** — when the sermon naturally reaches the
   «fără zgomot, nevăzută…» passage (*Marea Luptă* 490/613 section),
   let it play in full; viewers who came for the hook get the payoff.
4. **Scripture overlays as pattern interrupts** — every verse he cites
   (Apocalipsa 22:10–12, Luca 13:25, Matei 24–25, Geneza 7:16, Amos 8:12,
   Proverbe 1:24–28, Daniel 7:13–14) becomes a full-text card, ~every
   60–90s. This is both retention mechanics and study value.
5. **Mid-video re-hooks at section turns** — one line each, e.g. before
   the *Left Behind* section: overlay «Filmele au înțeles greșit» — this
   resolves open loop ① and re-arms attention.
6. **Chapters** (YouTube description) matching the open loops, so the
   progress bar shows structure: Închiderea harului – ce NU este / Left
   Behind / Cine poate ști data? / După închiderea ușii / Apelul final.
7. **End screen discipline** — the closing set of lower thirds
   (`C0081_lower_thirds.md` cards 5–7) plus CTA in the final ~15s only.

## Title + thumbnail (must match the hook, or retention dies at 0:05)

- Title A: **„Ușa se va închide — și nimeni nu va ști"**
- Title B: **„De ce «Left Behind» greșește complet — Închiderea Harului"**
- Thumbnail: heavy door almost closed, warm light through the gap;
  3–4 words max: **„NIMENI NU VA ȘTI"**. Dr. Geaboc inset if consent
  gate is green (see `OPERATOR.md` hard launch gate — still applies).

## Revised opening lower thirds (replaces the 0:00–0:36 set for this cut)

The v1 opening set in `C0081_lower_thirds.md` assumed the greeting-first
edit. With the cold open, cards move:

| In–Out | Main line | Secondary line |
|---|---|---|
| 0:05–0:12 | 6 din 10 nu mai cred* | Închiderea harului — doctrina evitată |
| 0:12–0:20 | Ce spune Biblia de fapt | Nu tradiția. Nu filmele. Nu frica. |
| 0:33–0:40 | Dr. Emanoil Geaboc | Jabbok River Productions |
| 0:40–0:48 | Închiderea Harului | Încheierea timpului de probă |

Closing set (cards 5–7) unchanged.

## Prior work this builds on (already in the repo)

- `remotion/CLAUDE.md` editorial rails: hook in first 1.5s, word-level
  captions, accent color discipline, evergreen rule, ProgressBar, CTA.
- `remotion/src/compositions/shorts/` — ShortClip/TitleCard/Captions/CTA
  components implementing those rails for Shorts.
- `docs/shorts/LAUNCH_TIMING.md` — researched publish windows (RO: Sun AM
  06:00 UTC, Wed/Sun PM 18:00 UTC winter).
- `council/` — Council of Seven ranks segment virality pre-cut.
- `channels/jabbokriver/geaboc-glossary.md` — translation layer for the
  EN/ES/PT image-driven variants of the same hooks.
- `C0081_lower_thirds.md` — v1 lower thirds (greeting-first edit).
