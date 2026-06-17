URANTIPEDIA PIPELINE — MASTER SPEC

OBJECTIVE:
Transform each section of the Urantia Book into:
1) Core concept (source-first)
2) Closest NKJV-aligned references
3) Biblical-language explanation of every component
4) Expansion links to 3 related concepts

INPUT:
- Source: Foreword → Paper 196 (sequential)
- Format: Markdown (.md)

PROCESS (PER CHUNK):
1. Extract concept (atomic, ≤1 paragraph)
2. Normalize language (remove internal jargon where possible)
3. Map to NKJV:
   - Minimum 3 references
   - Prefer doctrinal + narrative + poetic balance
4. Re-express concept entirely in Biblical language
5. Break down subcomponents (line-by-line theological mapping)
6. Link 3 related concepts (forward/back references)

OUTPUT FORMAT (STRICT):

---
CONCEPT:
[cleaned statement]

NKJV ALIGNMENT:
- Ref 1
- Ref 2
- Ref 3+

BIBLICAL EXPOSITION:
[rewrite in Scripture-consistent language]

BREAKDOWN:
- component → biblical meaning
- component → biblical meaning

RELATED:
- concept A
- concept B
- concept C
---

STORAGE:
Primary:
~/Obsidian/UrantiPedia/

Structure:
UrantiPedia/
 ├── Foreword/
 ├── Paper_001/
 ├── ...
 └── INDEX.md

Each concept = one note.

BACKUP:
1. iCloud Drive (auto)
2. External SSD (rsync mirror)
3. Secondary cloud (optional)

LOGGING:
~/Obsidian/UrantiPedia/_manifest_log.md

Each run appends:
- timestamp
- source range
- concepts created
- failures (if any)

FAIL CONDITIONS:
- Missing NKJV alignment
- Non-biblical phrasing
- Concept drift

COMPLETION CONDITION:
All Papers processed + indexed.
