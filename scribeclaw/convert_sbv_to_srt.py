#!/usr/bin/env python3
"""Convert SBV → SRT and apply comprehensive Romanian corrections for C0072."""
from __future__ import annotations
import re
import sys
from pathlib import Path

# ── Timestamp conversion ──────────────────────────────────────────────────────

def sbv_ts_to_srt(ts: str) -> str:
    """Convert H:MM:SS.mmm → HH:MM:SS,mmm"""
    ts = ts.strip()
    # Split into seconds part and milliseconds
    if "." in ts:
        main, ms = ts.rsplit(".", 1)
    else:
        main, ms = ts, "000"
    ms = ms.ljust(3, "0")[:3]
    parts = main.split(":")
    if len(parts) == 2:
        h, m, s = "00", parts[0], parts[1]
    else:
        h, m, s = parts[0].zfill(2), parts[1], parts[2]
    return f"{h.zfill(2)}:{m.zfill(2)}:{s.zfill(2)},{ms}"


def parse_sbv(text: str) -> list[dict]:
    """Parse SBV into list of {start, end, text}."""
    blocks = re.split(r"\n{2,}", text.strip())
    entries = []
    for block in blocks:
        lines = block.strip().splitlines()
        if not lines:
            continue
        # First line should be timestamp
        m = re.match(r"(\d+:\d+:\d+\.\d+),(\d+:\d+:\d+\.\d+)", lines[0].strip())
        if not m:
            continue
        start = sbv_ts_to_srt(m.group(1))
        end = sbv_ts_to_srt(m.group(2))
        body = " ".join(l.strip() for l in lines[1:] if l.strip())
        entries.append({"start": start, "end": end, "text": body})
    return entries


def render_srt(entries: list[dict]) -> str:
    parts = []
    for i, e in enumerate(entries, 1):
        parts.append(f"{i}\n{e['start']} --> {e['end']}\n{e['text']}")
    return "\n\n".join(parts) + "\n"


# ── Corrections ───────────────────────────────────────────────────────────────

# Noise markers to remove completely (with surrounding whitespace)
NOISE_PATTERNS = [
    r"\[sforăit\]",
    r"\[voce dreasă\]",
    r"\[Applause\]",
    r"\[Music\]",
    r"\[Laughter\]",
]

# Filler sound cleanup: isolated ă/ăă/â particles used as verbal fillers
FILLER_RE = re.compile(
    r"(?<!\w)(?:ă{1,3}|âî|ăă+)\s*"  # standalone ă fillers mid-sentence
    r"(?=[a-zA-ZăâîșțĂÂÎȘȚ\"]|$)",
)

# Exact-phrase substitutions (order matters — longer phrases first)
PHRASE_FIXES: list[tuple[str, str]] = [
    # Bible verse garbles
    ("am stut pe nisipul mării", "am stat pe nisipul mării"),
    ("o fiare cu 10 coane", "o fiară cu 10 coarne"),
    ("șapte coane și cap cu 10 coane și șapte capete", "șapte coarne și șapte capete"),
    ("10 coane și șapte capete", "10 coarne și șapte capete"),
    ("cu 10 coane", "cu 10 coarne"),
    ("pe coarne avea 10 cununi", "pe coarne avea zece cununi"),
    ("Fiara semăna cu un leopard. Avea labă de urți", "Fiara semăna cu un leopard, avea labă de urs"),
    ("o gură de leu. Balaur i a dat", "o gură de leu. Balaurul i-a dat"),
    ("Balaur i a dat puterea lui scaunului de domnie", "Balaurul i-a dat puterea lui, scaunul de domnie"),
    # Papal / papacy
    ("biser romanocatolică", "Biserica Romano-Católică"),
    ("romanocatolică", "Romano-Católică"),
    ("Romano-Católică", "Romano-Catholică"),  # normalize spelling
    ("propalității", "papalității"),
    ("papalitată", "papalității"),
    ("Balaurul în Apocalips, în diferite contexte se referă la care este în spatele puterii politice Satana",
     "Balaurul în Apocalips, în diferite contexte, se referă la Satana, care este în spatele puterii politice."),
    # Eschatology
    ("escotologia", "escatologia"),
    ("escotologie", "escatologie"),
    # Trumpets
    ("trândițe", "trâmbițe"),
    ("trânditze", "trâmbițe"),
    # Proper names — ASR garbles
    ("Peter Fagner", "C. Peter Wagner"),
    ("William Simon", "William Seymour"),
    ("Demnul Olson", "Sora White"),
    # Revelation garbles
    ("Cine a rex să audă", "Cine are urechi să audă"),
    ("Unul din cape părea rănit", "Unul din capete părea rănit"),
    ("Primește ran moarte 1798", "A primit rană de moarte în 1798"),
    ("Apocalipt Daniel", "Apocalipsa și Daniel"),
    ("teologi adentici", "teologi adventiști"),
    ("3 ani jumate", "trei ani și jumătate"),
    ("o dată profetică de șapte ori spus", "o dată profetică spusă de șapte ori"),
    # Spiritualism / NAR
    ("semnifiare", "semnul fiarei"),
    ("a propalității", "a papalității"),
    ("să poboare foc", "să coboare foc"),
    ("să facă să poboare foc", "să facă să coboare foc"),
    ("Peginismul", "Păgânismul"),
    ("peginismul", "păgânismul"),
    ("O fi manifeste supranare", "O să fie manifestări supranaturale"),
    ("supranare", "supranaturale"),
    ("a propalității", "a papalității"),
    # Small grammar fixes throughout
    ("o icoane fiarei", "o icoană a fiarei"),
    ("o image fiarei", "o imagine a fiarei"),
    ("facă o icoane", "facă o icoană"),
    ("asunt versele", "iată versetele"),
    ("vorbea ca un bala.", "vorbea ca un balaur."),
    ("în ea și de foc care i ar cu pucioasă", "în iazul de foc, care ardea cu pucioasă"),
    ("de foc care i ar cu pucioasă", "în iazul de foc cu pucioasă"),
    ("aduce aceeași idee importantă", "aduce aceeași idee importantă."),
    ("cumpăra și vindece", "cumpăra și vinde"),
    ("Fiara biser", "Fiara — Biserica"),
    ("Apostolul merge înainte, după", "Apostolul merge înainte, după aceea"),
    ("revine 1798", "revine la 1798"),
    ("Balaurul i a dat", "Balaurul i-a dat"),
    ("Balaurul i a", "Balaurul i-a"),
    ("i a dat", "i-a dat"),
    ("I s a dat", "I s-a dat"),
    ("i s a dat", "i s-a dat"),
    ("nu a avansat", "nu a avansat"),
    ("nu a crescut,", "nu a crescut,"),
    ("Sora White, din nou,", "Sora White, din nou:"),
    ("Sora mai spune când", "Sora White mai spune: când"),
    ("și sora spune:", "și Sora White spune:"),
    ("Sora White mai spune:", "Sora White mai spune:"),
    # Rezerred elsewhere
    ("a de prooroci", "a vorbit despre prooroci"),
    ("Cine duce pe alții în robie va merge și el în robie", "Cine duce în robie, va merge în robie."),
    ("legeală", "lege"),
    ("restelească", "restabilească"),
    ("restabilesca", "restabilească"),
    ("restabilesc", "restabilesc"),
    ("invedeze", "întemeieze"),
    ("substăpânirea", "sub stăpânirea"),
    ("ăra pământului", "întreaga a pământului"),
    ("pold de opinie", "sondaj de opinie"),
    ("a readus ăă importanța", "a readus importanța"),
    ("a readus ăă a readus ăă", "a readus"),
    ("săci", "și"),
    ("profeet", "profetă"),
    # Numbers
    ("Măr volumul 5", "Mărturii, volumul 5"),
    ("2014", "1014 d.Hr."),
    # Sentence cleanup
    ("N avem timp", "Nu avem timp"),
    ("n o să fie", "nu o să fie"),
    ("n a avansat", "nu a avansat"),
    ("n au", "nu au"),
    ("n am", "nu am"),
    ("protestant pastismul", "protestantismul"),
    ("protestantastismul", "protestantismul"),
    ("dracilor și spiritele rele îi dă putere locașul dracilor să facă",
     "dracilor. Spiritele rele dau putere să facă"),
    ("printre din terminologia", "folosind terminologia"),
    ("Ioan folosește din terminologia", "Ioan folosește terminologia"),
    ("la la spiritism", "la spiritism"),
    ("la la unele", "la unele"),
    ("de la la", "de la"),
    ("Să spune în mare obligă pagina 47", "Se spune în Marea Luptă, pagina 47,"),
    ("Romano-Catholică", "romano-catholică"),
    ("Romano-Catholică.", "romano-catholică."),
    ("vede la evenimentele finale", "privind evenimentele finale"),
    ("ca vez se întâmplă", "ca să vedem ce se întâmplă"),
    ("manifestările minuni extraordinare", "manifestările de minuni extraordinare"),
    ("gata pentru manifestările", "gata pentru"),
    # Additional fixes
    ("Oam oamenii", "Oamenii"),
    ("oam oamenii", "oamenii"),
    ("s a întâmplat", "s-a întâmplat"),
    ("s a rugau", "se rugau"),
    ("s a schimbat", "s-a schimbat"),
    ("s a unit", "s-a unit"),
    ("s au împlinit", "s-au împlinit"),
    ("s a împlinit", "s-a împlinit"),
    ("s au întâmplat", "s-au întâmplat"),
    ("l a ales", "l-a ales"),
    ("l a dat", "l-a dat"),
    ("l a chemat", "l-a chemat"),
    ("a ajuns un locaș", "a ajuns un lăcaș"),
    ("locașul dracilor", "lăcașul dracilor"),
    ("locaș al dracilor", "lăcaș al dracilor"),
    ("locaș al", "lăcaș al"),
    ("vorinde mâna asupra bisului", "vor întinde mâna deasupra abisului"),
    ("deasupra chiasmei", "deasupra prăpastiei"),
    ("proroco mincinos", "prooroc mincinos"),
    ("Fuller ă spunea:", "Fuller, spunea:"),
    ("Fuller ă spunea", "Fuller, spunea"),
    ("a care au furat", "care au furat"),
    ("a Dumnezeul celor apernic", "a Dumnezeului celui Atotputernic"),
    ("pedepsiverei", "pedepsirii"),
    ("bisului ca", "bisului ca"),  # handled by full-phrase fix above — don't double-apply
    ("specifică specifică", "specifică"),
    ("că cap întreg", "ca șef al întregii"),
    ("episcopolul", "episcopul"),
    ("protesta.", "protesteze."),
    ("să ăă devină", "să devină"),
    ("supranaturatul", "supranaturalul"),
    ("cunoștință. și", "cunoștință. Și"),
    ("Acceest adevăr", "Acest adevăr"),
    ("noi eri apostolice", "noii ere apostolice"),
    ("toți apostoliilor", "toți apostolii"),
    ("se potcăiesc", "se pocăiesc"),
    ("Paula White. Paul White,", "Paula White,"),
    ("am prut o predică", "am ținut o predică"),
    ("proiectul 2025", "Proiectul 2025"),
    ("melului", "Mielului"),
    ("a episcopolul din Roma", "Episcopul din Roma"),
    ("principiu a constituției", "principiile constituției"),
    ("principii a constituției", "principiile constituției"),
    ("cuerea pe apară continuai", ""),
    ("vor da mâna cuerea pe apară continuai", "vor da mâna"),
    ("Ei, spun eu, indirectă,", "ei, spun eu, indirectă,"),
    ("profeției Ei,", "profeției, ei,"),
    ("cum ar fi războaie și vești de războaie, cutremure uragane",
     "cum ar fi războaie și zvonuri de războaie, cutremure, uragane"),
    ("înainte a mergem", "înainte să mergem"),
    ("altor oficial altor", "altor — oficial altor"),
    ("să aducă vie împărăția ta", "să aducă: «Vie împărăția Ta»"),
    ("de a lungul pe lângă", "de-a lungul, pe lângă"),
    ("aducă la îndeplinirezatele dorite", "aducă la îndeplinire rezultatele dorite"),
    ("nesimbător", "nesimțitor"),
    ("Când fugau în cercuri,", "Când fugeau în cercuri,"),
    ("Lătau ca și câinii", "Lătrau ca și câinii"),
    ("Citează versetul că împărăția lui Dumnezeu se ia cu violență",
     "Citează versetul că «împărăția lui Dumnezeu se ia cu violență»"),
]

# Regex-based fixes (pattern, replacement)
REGEX_FIXES: list[tuple[str, str]] = [
    # Remove isolated filler ă sounds at word boundaries
    (r"\bă{1,3}\b", ""),
    (r"\băă+\b", ""),
    (r"\bă ă\b", ""),
    (r"\bă ăă\b", ""),
    (r"\băă ă\b", ""),
    # Clean up double spaces and double punctuation after removals
    (r"[ \t]{2,}", " "),
    (r"\.{2,}", "."),
    (r",{2,}", ","),
    # Fix broken hyphen-forms
    (r"(\w) a dat", r"\1 a dat"),  # keep intact
    # Clean up sentence-start lowercase after period+space
]

def apply_corrections(text: str) -> str:
    """Apply all corrections to a segment of text."""
    # 1. Remove noise markers
    for pat in NOISE_PATTERNS:
        text = re.sub(pat, "", text, flags=re.IGNORECASE)

    # 2. Phrase fixes (longest first, case-sensitive)
    for wrong, right in PHRASE_FIXES:
        text = text.replace(wrong, right)

    # 3. Cedilla → comma-below
    cedilla_map = str.maketrans({"ş": "ș", "Ş": "Ș", "ţ": "ț", "Ţ": "Ț"})
    text = text.translate(cedilla_map)

    # 4. Regex fixes
    for pat, rep in REGEX_FIXES:
        text = re.sub(pat, rep, text)

    # 5. Cleanup: strip leading/trailing spaces, collapse internal spaces
    text = re.sub(r"[ \t]+", " ", text).strip()

    # 6. If text is now empty or just punctuation, skip
    if re.match(r"^[.,;:!?\s]*$", text):
        return ""

    return text


def main():
    sbv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "/root/.claude/uploads/7dc8a767-fb8d-468a-98aa-575c52fc2c4d/2dc13e94-C0072_from_YouTube_captions.sbv"
    )
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(
        "/home/user/mircea-constellation/scribeclaw/GFttc7f5zEo_RO_corrected.srt"
    )

    print(f"Reading: {sbv_path}")
    raw = sbv_path.read_text(encoding="utf-8")

    print("Parsing SBV...")
    entries = parse_sbv(raw)
    print(f"  {len(entries)} segments parsed")

    print("Applying corrections...")
    corrected = []
    for e in entries:
        fixed = apply_corrections(e["text"])
        if fixed:  # drop empty segments
            corrected.append({"start": e["start"], "end": e["end"], "text": fixed})

    dropped = len(entries) - len(corrected)
    print(f"  {len(corrected)} segments kept, {dropped} dropped (noise-only)")

    srt = render_srt(corrected)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(srt, encoding="utf-8")
    print(f"\n✅ Written: {out_path}")
    print(f"   {len(corrected)} segments, {len(srt)} chars")

    # Preview first 5 segments
    print("\n── Preview (first 5 segments) ──")
    for i, e in enumerate(corrected[:5], 1):
        print(f"{i}\n{e['start']} --> {e['end']}\n{e['text']}\n")


if __name__ == "__main__":
    main()
