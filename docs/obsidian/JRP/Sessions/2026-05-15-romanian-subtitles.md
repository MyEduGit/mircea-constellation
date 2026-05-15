# Session Journal — 2026-05-15 — Romanian Subtitle Pipeline

**Sesiune:** `fix-romanian-subtitles-Hg00H`
**Branch:** `claude/fix-romanian-subtitles-Hg00H`
**PR:** https://github.com/MyEduGit/mircea-constellation/pull/72

---

## Ce s-a făcut

### 1. Script automat creat — `fix_romanian_subs.py`

Locație: `scribeclaw/fix_romanian_subs.py`

Pipeline complet în un singur script:
- yt-dlp descarcă subtitrări auto-generate (ro/ro-RO)
- Fallback AssemblyAI dacă nu există subtitrări
- Corecție deterministă: cedilla→virgulă-jos, dicționar 50+ termeni teologici
- Corecție Claude Opus: capitalizare, punctuație, diacritice, referințe biblice
- Chunk processing: 150 segmente/apel API

### 2. Separarea conturilor — documentată permanent

- `/ACCOUNTS.md` creat în repo root
- `channels/jabbokriver/channel.json` actualizat cu `account_email` + `account_rule`
- Notion Command Control actualizat cu tabelul de separare
- Obsidian: [[SOPs/Account-Separation]]

**Regula:**
- `messagetostephanos@gmail.com` → Dr. Geaboc EXCLUSIV
- `mirceamatthews@gmail.com` → Mircea / Urantia / Educație / 9 Necesități

### 3. Notion actualizat

- [📦 C0072 — Transcriere & Subtitrări Română](https://www.notion.so/3618525ab5a081e59c48ee0dbe0e791f) — creat
- Command Control dashboard — actualizat cu regula conturilor + C0072 în coada
- Hub principal — C0072 adăugat în lista de pagini metadata

### 4. Obsidian vault files create

```
docs/obsidian/JRP/
├── Command-Control.md
├── Videos/
│   └── C0072.md
├── SOPs/
│   ├── Romanian-Subtitle-Pipeline.md
│   └── Account-Separation.md
└── Sessions/
    └── 2026-05-15-romanian-subtitles.md  ← acest fișier
```

---

## Status C0072

- ✅ Script creat și în repo
- ✅ Notion page creată
- ✅ Obsidian documentat
- 🔄 **Pending:** Rulare script pe Mac (YouTube blocat de pe server cloud)

### Comandă exactă pentru Mac

```bash
# Pas 1 — găsește repo-ul
find ~ -name "fix_romanian_subs.py" 2>/dev/null

# Pas 2 — instalează dependențele (o singură dată)
pip install yt-dlp anthropic assemblyai

# Pas 3 — setează cheia API
export ANTHROPIC_API_KEY=sk-ant-...   # din Keychain

# Pas 4 — rulează din directorul repo-ului
cd /calea/catre/mircea-constellation
python3 scribeclaw/fix_romanian_subs.py GFttc7f5zEo

# Rezultat: GFttc7f5zEo_RO_corrected.srt
```

### Dacă repo-ul nu e clonat local

```bash
# Descarcă doar scriptul
curl -L -o fix_romanian_subs.py \
  "https://raw.githubusercontent.com/myedugit/mircea-constellation/claude/fix-romanian-subtitles-Hg00H/scribeclaw/fix_romanian_subs.py"
python3 fix_romanian_subs.py GFttc7f5zEo
```

---

## Probleme întâlnite

| Problemă | Cauză | Soluție |
|---|---|---|
| YouTube 403 pe server cloud | IP datacenter blocat de YouTube | Rulare pe Mac local |
| `zsh: parse error near \n` | Comenzi multiple lipite ca un bloc | Rulare linie cu linie |
| `cd: no such file or directory: path/to/mircea-constellation` | Placeholder literal | `find ~ -name fix_romanian_subs.py` pentru localizare |

---

## Arhitectura pipeline-ului (descoperit în această sesiune)

Pipeline existent în repo (ScribeClaw):
```
audio_extract → transcribe_ro (faster-whisper large-v3) → postprocess_transcript → youtube_metadata
```

Pipeline adoptat pentru Dr. Geaboc (cloud, pe Mac):
```
yt-dlp/AssemblyAI → fix_romanian_subs.py → Claude Opus → YouTube Studio upload
```

---

*Governed by COVENANT.md · Truth · Beauty · Goodness*
