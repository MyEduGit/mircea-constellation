# SOP — Romanian Subtitle Correction Pipeline

**Versiune:** 1.1 | **Data:** 2026-06-06
**Script:** `scribeclaw/fix_romanian_subs.py`
**PR:** https://github.com/MyEduGit/mircea-constellation/pull/72

---

## Scopul

Produce subtitrări românești la un standard pe care un profesor universitar de limba română l-ar considera perfect — pentru toate videoclipurile Dr. Emanoil Geaboc pe canalul `messagetostephanos@gmail.com`.

---

## Dependențe (instalare o singură dată pe Mac)

```bash
pip install yt-dlp anthropic assemblyai
```

API keys necesare:
- `ANTHROPIC_API_KEY` — din Keychain Mac sau Obsidian `12_Credentials/SECRETS.md`
- `ASSEMBLYAI_API_KEY` — opțional, doar dacă subtitrările auto lipsesc

---

## Utilizare

### Cazul 1 — Video YouTube cu subtitrări auto-generate

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python3 scribeclaw/fix_romanian_subs.py <VIDEO_ID>
# Exemplu: python3 scribeclaw/fix_romanian_subs.py GFttc7f5zEo
```

### Cazul 2 — Fișier SRT existent (descărcat manual)

```bash
python3 scribeclaw/fix_romanian_subs.py --from-srt fisier.srt --out fisier_corectat.srt
```

### Cazul 2b — Fișier SBV (descărcat din YouTube Studio)

YouTube Studio exportă subtitrări în format `.sbv`, nu `.srt`.

```bash
# Pas 1: convertire + corecție deterministă → acesta este fișierul de upload
python3 scribeclaw/convert_sbv_to_srt.py fisier.sbv VIDEO_ID_RO_corrected.srt
```

**Fișierul `_RO_corrected.srt` este fișierul final de upload.** Păstrează timecode-urile originale YouTube și text pe o singură linie per card.

> ⚠️ **NU folosi `reformat_srt.py` pentru upload YouTube.** Scriptul redistribuie proporțional duratele cardurilor pe baza lungimii textului — ceea ce rupe sincronizarea cu vorbirea. De asemenea, inserează `\n` în textul cardurilor, ceea ce face ca YouTube să afișeze subtitrările pe 4 rânduri pe telefon (YouTube aplică propria sa împărțire pe linie PESTE `\n`-urile deja existente).

### Cazul 3 — AssemblyAI fallback (fără subtitrări auto)

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export ASSEMBLYAI_API_KEY=...
python3 scribeclaw/fix_romanian_subs.py <VIDEO_ID>
# Descarcă audio → transcrie via AssemblyAI → corectează via Claude
```

---

## Ce face scriptul

### Pasul 1 — Descărcare subtitrări
- `yt-dlp` încearcă `ro` apoi `ro-RO`
- Convertește VTT → SRT dacă e necesar

### Pasul 2 — Corecție deterministă (fără AI)
- Cedilla → virgulă-jos: `ş→ș`, `ţ→ț`
- Spații multiple eliminate
- Dicționar terminologic (50+ termeni): Iisus Hristos, Duhul Sfânt, neprihănire, Sabat, Ellen White, Apostolul Pavel, etc.

### Pasul 3 — Corecție Claude Opus (AI)
- Capitalizare corectă la începutul fiecărui enunț
- Punctuație completă (virgulă, punct, semnul întrebării)
- Diacritice perfecte
- Terminologie teologică adventistă canonică
- Referințe biblice complete cu majusculă
- Procesare în chunk-uri de 150 segmente

---

## Standardul de calitate

> Un profesor universitar de limba română să spună că acestea sunt cele mai bune subtitrări în română pe care le-a văzut vreodată.

Criterii:
- ✅ Zero erori de diacritice
- ✅ Capitalizare perfectă la începutul fiecărui enunț
- ✅ Punctuație care reflectă ritmul natural al vorbirii Dr. Geaboc
- ✅ Terminologie teologică adventistă corectă și consecventă
- ✅ Referințe biblice scrise complet și corect
- ✅ Nicio modificare a conținutului — doar formă, nu fond
- ✅ Timecode-uri identice cu originalul

---

## Upload YouTube Studio

1. `studio.youtube.com/video/<VIDEO_ID>/translations`
2. Click **Română** → iconiță creion → **Înlocuiește fișierul**
3. Upload fișierul `_RO_corrected.srt`
4. Selectează **Cu sincronizare** → **Publică**

---

## Notă arhitecturală

Serverul cloud (unde rulează Claude Code) are IP-ul blocat de YouTube (HTTP 403).
Scriptul trebuie rulat **pe Mac local** unde YouTube este accesibil.

Alternativă viitoare: rulare pe OpenClaw (46.225.51.30) cu cookie fișier YouTube.

---

## ESTRS — QC automat pentru toate predicile

`scribeclaw/estrs/` — pachet Python cu 11 module care rulează în fundal și verifică automat toate predicile viitoare.

```bash
pip install watchdog anthropic rich
python -m estrs --watch                # mod daemon — monitorizează /Volumes/*
python -m estrs --sermon C0072         # verificare one-shot
```

Generează 6 fișiere Markdown per predică în dosarul sermonic: raport comparare transcrieri, nume incerte, referințe biblice, terminologie, raport gate (PASS / PASS_WITH_AUDIO_CHECK / BLOCKED), index Obsidian.

---

## Jurnal sesiuni

| Data | Video | Status | Note |
|---|---|---|---|
| 2026-05-15 | C0072 / GFttc7f5zEo | ✅ SRT gata de upload | SBV→SRT convertit, corectat (468 seg). **Fișier corect: `GFttc7f5zEo_RO_corrected.srt`** |
| 2026-06-06 | — | ✅ ESTRS livrat | Pachet `scribeclaw/estrs/` (11 module) committed + pushed pe PR #72. SOP actualizat: `_corrected.srt` = fișier corect; `_final.srt` NU pentru upload (sincronizare ruptă + 4 rânduri pe mobil). |

---

*Parte din JRP Pipeline Architecture. Governed by COVENANT.md.*
