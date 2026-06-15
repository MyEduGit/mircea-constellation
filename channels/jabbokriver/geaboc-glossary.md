# Geaboc Translation Glossary — Romanian → Spanish

Used as a fixed injection into every sermon translation prompt to ensure
terminology consistency across the entire JabbokRiverProductions catalog.

Paste the **GLOSSARY** block verbatim into the prompt template below.

---

## GLOSSARY

| Romanian (Cornilescu / SDA usage) | Spanish (Reina-Valera 1960 / SDA usage) |
|---|---|
| Sanctuar | Santuario |
| Neprihănirea prin credință | Justificación por la fe |
| Judecata de cercetare | Juicio Investigador |
| Marele Conflict | El Gran Conflicto |
| Sabat | Sábado |
| Duhul Sfânt | Espíritu Santo |
| Isus Hristos | Jesucristo |
| Mântuitorul | el Salvador |
| mântuire | salvación |
| har | gracia |
| credință | fe |
| pocăință | arrepentimiento |
| botez | bautismo |
| profeție | profecía |
| apocalipsă / Apocalipsa | el Apocalipsis |
| cartea Daniel | el libro de Daniel |
| a doua venire / revenirea lui Hristos | la segunda venida de Cristo |
| învierea morților | la resurrección de los muertos |
| starea morților | el estado de los muertos |
| somnul morții | el sueño de la muerte |
| suflet nemuritor | alma inmortal |
| îngeri | ángeles |
| Satana / Diavolul | Satanás / el Diablo |
| marea luptă | el gran conflicto |
| Spiritul Profetismului | el Espíritu de Profecía |
| reformă sanitară | reforma pro salud |
| zecime | diezmo |
| darul vorbirii în limbi | el don de lenguas |
| Împărăția lui Dumnezeu | el Reino de Dios |
| Tatăl ceresc | el Padre celestial |
| Sfânta Treime | la Santa Trinidad |
| legea lui Dumnezeu | la ley de Dios |
| Cele Zece Porunci | los Diez Mandamientos |
| ziua Domnului | el día del Señor |
| Sionul ceresc | el Sion celestial |
| promisiunea Duhului | la promesa del Espíritu |
| noua naștere | el nuevo nacimiento |
| sfințenie | santidad |
| desăvârșire | perfección |
| judecată | juicio |
| mânia lui Dumnezeu | la ira de Dios |
| iertare | perdón |
| ispășire | expiación |
| sângele lui Hristos | la sangre de Cristo |
| cruce | cruz |
| Golgota | el Calvario / Gólgota |
| înălțare | ascensión |
| mijlocire | intercesión |
| marea adunare | la gran asamblea |
| poporul lui Dumnezeu | el pueblo de Dios |
| rămășița | el remanente |
| timp de strâmtorare | tiempo de angustia |
| pecetea lui Dumnezeu | el sello de Dios |
| semnul fiarei | la marca de la bestia |
| cei 144.000 | los 144.000 |
| Babilonul mistic | la Babilonia mística |
| potir / cupa mâniei | la copa de la ira |
| judecata pre-adventă | el juicio pre-advenimiento |
| porțile perle | las puertas de perlas |
| Noul Pământ | la Tierra Nueva |
| veșnicie | eternidad |

---

## Prompt template

Copy this entire block and fill `[SERMON TEXT HERE]`:

```
Act as a professional theological translator for Seventh-day Adventist (SDA) content.

Translate the following sermon by Dr. Emanoil Geaboc from Romanian into Spanish.

GLOSSARY — always use these exact Spanish terms (never substitute equivalents):
[paste the table above]

Rules:
1. Tone: formal pulpit Spanish — not conversational, not academic. Match
   the oratorical register and preserve rhetorical repetition.
2. Bible verses: when Dr. Geaboc quotes Scripture, match the phrasing of
   Reina-Valera 1960 (RVR60) for that verse. Do not re-translate from
   Romanian — look up the RVR60 text for that reference.
3. If you are uncertain about a biblical reference's RVR60 form, translate
   the meaning accurately and flag it with [CHECK RVR60 <reference>].
4. Do not "clean up" the oratory. Preserve sentence rhythm, repeated
   phrases, and rhetorical questions exactly as spoken.
5. Speaker identification: Dr. Geaboc speaks in first-person throughout.
   Do not shift to third-person narration.

SERMON:
[SERMON TEXT HERE]
```

---

## Recommended models (as of June 2026)

| Use case | Model |
|---|---|
| Single sermon, best quality | `claude-opus-4-8` |
| Single sermon, fast/cost | `claude-sonnet-4-6` |
| Full series in one pass | `gemini-2.5-pro` (1M-token context) |
| Real-time YouTube subtitles | Immersive Translate → Claude backend |

---

## Bible version reference

- **Source:** Romanian *Cornilescu* (standard in Romanian SDA churches)
- **Target:** Spanish *Reina-Valera 1960* (RVR60) — standard in
  Spanish-speaking Protestant and SDA congregations
- When a Cornilescu verse diverges in wording from RVR60 (both are
  accurate translations from source languages), always prefer RVR60
  phrasing in the Spanish output. The theological meaning, not the
  Romanian wording, is what transfers.

---

## Maintenance

When Dr. Geaboc uses a term not in this glossary, add it here before
starting the next sermon. Keep the Romanian column in the *Cornilescu*
spelling; keep the Spanish column in *RVR60* / current SDA Spanish usage.
