# Launch Timing — Researched Defaults

When to publish each clip, by language, platform, and audience archetype.
These are **starting defaults**. The Phase 2B scheduler treats them as a
prior; per-clip A/B and per-channel analytics overwrite them as data accrues.

## Audience archetype: theological / Christian-teaching short-form

Across platforms the generalized peaks for *religious & spiritual teaching*
content (distinct from generic creator content) cluster at three windows
in **viewer local time**:

| Window | Why it works                                                   |
|--------|----------------------------------------------------------------|
| **Sunday 06:00–09:00** | Pre-church browse; people seeking devotionals.       |
| **Wednesday 19:00–21:00** | Mid-week prayer / small-group night, traditional.  |
| **Sunday 19:00–21:30** | Post-church reflection; sermon-recap habit.          |

Layer on platform-general peaks (any vertical):

| Platform | Best windows (local time)                          |
|----------|----------------------------------------------------|
| YouTube Shorts | 07:00–10:00 and 19:00–23:00; Sat/Sun heavier. |
| Instagram Reels | 09:00, 12:00, 17:00–20:00; Tue/Wed peaks.    |
| TikTok | 06:00–10:00 and 19:00–23:00; Tue/Thu peaks; Sun PM bump. |

## Per-language defaults

Optimize for each language's largest viewership pool. Times are **UTC** —
the scheduler converts at publish time.

### Romanian (ro-RO)

Largest audience: Romania (Europe/Bucharest, UTC+2 / +3 DST).
Secondary: Moldova, Romanian diaspora in Italy / Spain / Germany.

| Slot                      | UTC (winter) | UTC (DST) |
|---------------------------|--------------|-----------|
| Sun AM (08:00 RO local)   | 06:00        | 05:00     |
| Wed PM (20:00 RO local)   | 18:00        | 17:00     |
| Sun PM (20:00 RO local)   | 18:00        | 17:00     |

### English (en-US)

Largest audience: US Eastern + Central. Anchor on US Eastern; UK / AU pick
up secondary sweeps.

| Slot                       | UTC (EST) | UTC (EDT) |
|----------------------------|-----------|-----------|
| Sun AM (08:00 ET local)    | 13:00     | 12:00     |
| Wed PM (20:00 ET local)    | 01:00 Thu | 00:00 Thu |
| Sun PM (20:00 ET local)    | 01:00 Mon | 00:00 Mon |

### Spanish (es-MX)

Largest single audience: Mexico (America/Mexico_City, UTC-6). Brazil-style
fork — additional pass at 19:00 Madrid (UTC+1/+2) catches Spain + LatAm
South Cone.

| Slot                       | UTC (CST) | UTC (CDT) |
|----------------------------|-----------|-----------|
| Sun AM (08:00 MX local)    | 14:00     | 13:00     |
| Wed PM (20:00 MX local)    | 02:00 Thu | 01:00 Thu |
| Sun PM (20:00 MX local)    | 02:00 Mon | 01:00 Mon |
| Sun PM (19:00 ES local)    | 18:00     | 17:00     |

### Portuguese (pt-BR)

Largest audience by far: Brazil (America/Sao_Paulo, UTC-3 year-round
since 2019 — Brazil no longer observes DST).

| Slot                       | UTC       |
|----------------------------|-----------|
| Sun AM (08:00 BR local)    | 11:00     |
| Wed PM (20:00 BR local)    | 23:00     |
| Sun PM (20:00 BR local)    | 23:00     |

## Cross-platform staggering

Don't publish all four locales × three platforms simultaneously — the
recommendation algorithms penalize identical assets posted at the same
instant from the same metadata neighborhood. Stagger:

```
T+0    : Romanian master    → YouTube Shorts (ro-RO)
T+15m  : Romanian master    → Instagram Reels (ro-RO)
T+30m  : Romanian master    → TikTok (ro-RO)
T+1d   : EN clip            → YT Shorts → IG Reels → TikTok (15m gaps)
T+2d   : ES clip            → same staircase
T+3d   : PT clip            → same staircase
T+7d   : Weekly compilation → YouTube long-form (ro-RO + multilingual subs)
```

The day-gap also creates four discrete promotional moments per teaching
instead of one — better for the channel's per-day publish cadence.

## Frequency caps

- **Per channel per platform: ≤2 shorts / day.** More than this and the
  algorithm starts under-distributing the second post.
- **Per topic: ≤1 short / day across platforms.** Same idea posted twice
  in 24h cannibalizes itself.
- **Compilation: weekly, not more.** Long-form is a different rhythm.

## What the scheduler actually does (Phase 2B preview)

```python
# scribeclaw/shorts/launch.py — sketch
def schedule(manifest_path: Path, locale: Locale) -> ScheduledPost:
    slots = LOCALE_SLOTS[locale]                  # the windows in this doc
    next_slot = pick_next_slot(slots, after=now_utc(),
                               respect_caps=channel_history(locale))
    return ScheduledPost(
        manifest=manifest_path,
        publish_at_utc=next_slot,
        platforms=staircase(["youtube", "instagram", "tiktok"]),
    )
```

## Updating these defaults

When you have ≥30 published clips per locale, run
`scribeclaw/shorts/learn_timing.py` (Phase 2C) to refit the slot table from
your own analytics. Until then, these are the priors.

## Source notes

- General platform peaks: Sprout Social, Later, Hootsuite recurring
  benchmarks (2023–2025).
- Religious-content windows: Pew, Barna Group "digital faith engagement"
  studies (2022–2024) plus YouTube creator analytics aggregations.
- Brazil DST: official record — STF / Decree 9772/2019.

These are starting points, not gospel. Replace with your own analytics
once you have them.
