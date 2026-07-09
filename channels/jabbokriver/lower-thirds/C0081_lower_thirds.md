# C0081 — Lower thirds (Închiderea Harului)

Sermon: Dr. Emanoil Geaboc — **Închiderea Harului / Încheierea timpului de
probă** (Romanian, operator-held recording `C0081.mp3`).

Text below is corrected editorial Romanian (the raw AssemblyAI output has
ASR slips: „harmului" → „harului", „Hristoas" → „Hristos" etc.). Timecodes
for the opening set are relative to the start of the sermon audio; snap the
exact in-points to `C0081_subtitles_ro_raw.srt` if the edit trims the head.

Each card renders with the `HostLowerThird` composition (1920×1080, 30 fps,
4 s: slide-in 0–20 fr, fade-out 100–120 fr). To hold a card longer in FCP,
freeze it before frame 100 or stretch the clip — the fade only starts at
3 s 10 fr.

---

## Opening set — covers 0:00 → ~0:36

| # | In    | Out   | Main line (name)                    | Secondary line (credential)                              |
|---|-------|-------|-------------------------------------|----------------------------------------------------------|
| 1 | 0:00  | 0:08  | Dr. Emanoil Geaboc                  | Jabbok River Productions                                  |
| 2 | 0:08  | 0:16  | Închiderea Harului                  | Încheierea timpului de probă                              |
| 3 | 0:16  | 0:26  | Un subiect adesea prezentat greșit  | Interpretările eronate creează teamă și necredință        |
| 4 | 0:26  | 0:36  | Nu răpire secretă, nu o a doua șansă | Ce spune Biblia despre închiderea harului                |

## Closing set — final ~90 seconds (snap to SRT / final cut)

| # | In (relative)  | Out            | Main line                        | Secondary line                                            |
|---|----------------|----------------|----------------------------------|-----------------------------------------------------------|
| 5 | END − 1:30     | END − 1:20     | Marea Luptă, p. 622–623          | Ellen G. White — apelul final                              |
| 6 | END − 0:40     | END − 0:30     | Nădejdea noastră este Hristos    | „Dumnezeu să ne ajute și să ne mărească credința"          |
| 7 | END − 0:12     | END − 0:02     | Jabbok River Productions         | Predici și studii biblice în limba română                  |

Card 5 goes over the closing *Marea Luptă* quotation („Astăzi, acum, când
Marele nostru Preot face ispășire pentru noi…"); card 6 over the final
appeal; card 7 as the sign-off before/under the outro.

---

## Render commands (transparent overlays for FCP)

ProRes 4444 keeps the alpha channel so the cards drop straight onto the
timeline:

```bash
cd remotion

npx remotion render HostLowerThird out/C0081-lt1.mov \
  --codec=prores --prores-profile=4444 \
  --props='{"name":"Dr. Emanoil Geaboc","credential":"Jabbok River Productions"}'

npx remotion render HostLowerThird out/C0081-lt2.mov \
  --codec=prores --prores-profile=4444 \
  --props='{"name":"Închiderea Harului","credential":"Încheierea timpului de probă"}'

npx remotion render HostLowerThird out/C0081-lt3.mov \
  --codec=prores --prores-profile=4444 \
  --props='{"name":"Un subiect adesea prezentat greșit","credential":"Interpretările eronate creează teamă și necredință"}'

npx remotion render HostLowerThird out/C0081-lt4.mov \
  --codec=prores --prores-profile=4444 \
  --props='{"name":"Nu răpire secretă, nu o a doua șansă","credential":"Ce spune Biblia despre închiderea harului"}'

npx remotion render HostLowerThird out/C0081-lt5.mov \
  --codec=prores --prores-profile=4444 \
  --props='{"name":"Marea Luptă, p. 622–623","credential":"Ellen G. White — apelul final"}'

npx remotion render HostLowerThird out/C0081-lt6.mov \
  --codec=prores --prores-profile=4444 \
  --props='{"name":"Nădejdea noastră este Hristos","credential":"Dumnezeu să ne ajute și să ne mărească credința"}'

npx remotion render HostLowerThird out/C0081-lt7.mov \
  --codec=prores --prores-profile=4444 \
  --props='{"name":"Jabbok River Productions","credential":"Predici și studii biblice în limba română"}'
```

Diacritics (`ă â î ș ț`) must survive the shell — the JSON above is UTF-8;
paste as-is.
