# C0081 — Complete lower-thirds set with timing (cold-open edit)

Full package for the YouTube video: opening (0:00–0:48), mid-video
section cards, closing. Corrected: the ~60% statistic refers to the
**Sanctuary doctrine** (doctrina sanctuarului), not the closing of grace
itself — card 1 wording reflects that exactly.

Opening timecodes are fixed to the cold-open cut. Mid-video cards are
anchored to spoken cues — snap each in-point to that line in
`C0081_subtitles_ro_raw.srt` once the cut is locked; hold each card ~6–8 s.
Closing cards are relative to the final frame.

## Opening — 0:00 → 0:48

| # | In–Out | Main line | Secondary line |
|---|--------|-----------|----------------|
| — | 0:00–0:05 | *(no lower third — hook owns the frame)* | |
| 1 | 0:05–0:12 | 6 din 10 nu mai cred doctrina sanctuarului | temelia închiderii harului |
| 2 | 0:12–0:20 | Ce spune Biblia de fapt | Nu tradiția. Nu filmele. Nu frica. |
| — | 0:20–0:30 | *(no lower third — full-screen teaser cards ①②③)* | |
| — | 0:30–0:33 | *(no lower third — pattern interrupt, clean frame)* | |
| 3 | 0:33–0:40 | Dr. Emanoil Geaboc | Jabbok River Productions |
| 4 | 0:40–0:48 | Închiderea Harului | Încheierea timpului de probă |

## Mid-video — section cards (snap to SRT at the spoken cue)

| # | Spoken cue (his words) | Main line | Secondary line |
|---|------------------------|-----------|----------------|
| 5 | «Deschidem Bibliile, mai întâi la Apocalipsa capitolul 22» | Apocalipsa 22:10–12 | Cine este sfânt să se sfințească și mai departe |
| 6 | «În Luca capitolul 13… nevoiți-vă să intrați pe ușa cea strâmtă» | Luca 13:24–25 | Vor bate la ușă — și nu va mai fi răspuns |
| 7 | «…după cum a fost în zilele lui Noe» | Matei 24:37–39 | Mâncau, beau — și n-au știut nimic |
| 8 | «…pilda celor zece fecioare» | Matei 25:1–13 | Caracterul nu este transferabil |
| 9 | «Și Domnul a închis ușa după el» | Geneza 7:16 | Un act al lui Dumnezeu |
| 10 | «În Amos 8… foame după auzirea Cuvântului» | Amos 8:11–12 | Vor căuta — și nu vor mai găsi |
| 11 | «Același lucru în Proverbe 1» | Proverbe 1:24–28 | Mă vor chema — și nu voi răspunde |
| 12 | «Unul va fi luat și unul va fi lăsat» | Nimeni nu rămâne în urmă | «Left Behind» — interpretarea greșită |
| 13 | «Dacă deschideți cu mine în Daniel capitolul 7» | Daniel 7:13–14 | Venirea la Cel Îmbătrânit de zile |
| 14 | «Sunt adventiști care predică că ei știu când…» | Nimeni nu știe ziua și ceasul | Isus o spune de șapte ori |
| 15 | «…judecata să înceapă de la casa lui Dumnezeu» | 1 Petru 4:17 — corect înțeles | Judecata de cercetare, nu închiderea harului |
| 16 | «Ezechiel capitolul 9 este un pasaj…» | Ezechiel 9 — după sigilare | Plăgile vin după închiderea harului |
| 17 | «Duhul lui Dumnezeu nu se retrage de la poporul Lui» | Duhul Sfânt rămâne cu poporul Său | Ioan 14:16–17 · Matei 28:20 |
| 18 | «…îmbrăcați în neprihănirea Domnului Iisus Hristos» | Îmbrăcați în neprihănirea Lui | Zaharia 3 — haina de sărbătoare |
| 19 | «Cea mai bună pregătire… este pregătirea zilnică» | Pregătirea este astăzi | În pace cu Dumnezeu în fiecare zi |

## Closing — final ~90 seconds

| # | In–Out (relative) | Main line | Secondary line |
|---|-------------------|-----------|----------------|
| 20 | END−1:30 → END−1:20 | Marea Luptă, p. 622–623 | Ellen G. White — apelul final |
| 21 | END−0:40 → END−0:30 | Nădejdea noastră este Hristos | «Dumnezeu să ne ajute și să ne mărească credința» |
| 22 | END−0:12 → END−0:02 | Jabbok River Productions | Predici și studii biblice în limba română |

## Render

All cards render with `HostLowerThird` (transparent ProRes 4444 for FCP):

```bash
cd remotion
npx remotion render HostLowerThird out/C0081-lt<N>.mov \
  --codec=prores --prores-profile=4444 \
  --props='{"name":"<Main line>","credential":"<Secondary line>"}'
```

Each render is 4 s (fade-out starts at 3 s 10 fr); stretch or freeze in
FCP to hold 6–8 s. Diacritics are UTF-8 — paste props as-is.
