# 🎮 COMMAND CONTROL — JRP Pipeline Dashboard

> **Jabbok River Productions** | Dr. Emanoil Geaboc | Mircea Matthews
> Canal YouTube RO: [Libertatea Religioasă](https://youtube.com/channel/UC79EWkQRlP0wGLFMfVpzzRg) | WhatsApp: [Canal JRP](https://whatsapp.com/channel/0029VbCnJ22BPzjgQ0o6La43)
> Notion master: https://www.notion.so/3458525ab5a08166b778d40e2bca463f

---

## ⚠️ REGULĂ PERMANENTĂ — SEPARAREA CONTURILOR

| Cont | Proprietar | Conținut |
|---|---|---|
| `messagetostephanos@gmail.com` | Dr. Emanoil Geaboc | **EXCLUSIV: predici + Shorts bazate pe predici** |
| `mirceamatthews@gmail.com` | Mircea G. Matthews | **Cartea Urantia · Educație · Cele 9 Necesități · Toate cele 7 audiențe** |

**Regula de aur:** Cine vorbește în video?
- Dr. Geaboc → `messagetostephanos@gmail.com`
- Mircea / conținut educațional / Cartea Urantia → `mirceamatthews@gmail.com`

Documentat în repo: [[ACCOUNTS]]

---

## 🔗 Quick Links

- [▶ Canal RO — Dr. Emanoil Geaboc](https://youtube.com/channel/UC79EWkQRlP0wGLFMfVpzzRg)
- [🎬 YouTube Studio](https://studio.youtube.com/channel/UC79EWkQRlP0wGLFMfVpzzRg/videos)
- [📲 WhatsApp Channel JRP](https://whatsapp.com/channel/0029VbCnJ22BPzjgQ0o6La43)
- [🗂️ Notion Hub](https://www.notion.so/29e8525ab5a081619084f31301c6cf2e)
- [🏗️ Full Pipeline Architecture](https://www.notion.so/3458525ab5a08147ab82ffdd1238b781)

---

## 📹 Video Catalog

### ✅ Published

| Cod | Titlu | YouTube | Studio |
|---|---|---|---|
| C0067 | Habemus Magisterium — Ep. 01 | [▶](https://youtu.be/S4STdKnmsec) | [✏️](https://studio.youtube.com/video/S4STdKnmsec/edit) |
| C0063 | Este Iisus Dumnezeu? | [▶](https://youtu.be/9eWI0xAlqGw) | [✏️](https://studio.youtube.com/video/9eWI0xAlqGw/edit) |
| C0069 | Iisus A Coborât Până La Noi | [▶](https://youtu.be/NiKO1J5KBMo) | [✏️](https://studio.youtube.com/video/NiKO1J5KBMo/edit) |

### 🔄 În lucru

| Cod | YouTube ID | Status |
|---|---|---|
| C0072 | GFttc7f5zEo | 🔄 SRT în lucru — rulează `fix_romanian_subs.py` pe Mac |

---

## 🔄 Pipeline per Video

1. **Înregistrare** → export FCP via Compressor (H.264, 1080p, 25fps)
2. **Lower Third** → Motion 5: WhatsApp link în ultimele 45–60 sec
3. **Transcriere** → AssemblyAI (Romanian) → export SRT
4. **Corecție SRT** → `fix_romanian_subs.py` (Claude Opus API)
5. **Metadata Package** → Claude: titlu RO+EN, descriere, tags, timestamps
6. **Upload YouTube** → Unlisted → WhatsApp early access → Public (duminică 15:00 RO)
7. **Notion + Obsidian** → pagină metadata + jurnal sesiune
8. **Google Drive** → backup manual (SSD + Drive)
9. **WhatsApp** → 3 posturi: zi lansare → miercuri → vineri

---

## ⚙️ Reguli Tehnice Permanente

- ❌ **NICIODATĂ** export direct din FCP → **ÎNTOTDEAUNA** File → Send to Compressor
- ✅ Lower third WhatsApp: ultimele 45–60 secunde din fiecare video
- 🎯 Punct critic drop-off: **31 secunde** — hook înainte de acest moment
- 🎵 Target audio: **-14 LUFS**
- 📐 Export: H.264 Multi-pass, 1920×1080, 25fps, 48kHz/160kbps AAC stereo
- 📅 Publicare: evită Sâmbăta (Sabat). Optim: **Duminică 15:00 ora României**

---

*Sync: Notion → Obsidian. Sursa de adevăr: Notion.*
*Ultima actualizare: 2026-05-15*
