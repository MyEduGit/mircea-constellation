# CommunityPlus — EAL / AMEP / SEE Planning Pipeline

Reproducible pipeline for producing audit-ready **term plans** and
**session plans** for every VU unit CommunityPlus delivers across its
Victorian-accredited EAL courses, under whichever funding stream applies:

- **AMEP** — Adult Migrant English Program (Home Affairs)
- **SEE** — Skills for Education and Employment (DEWR)
- **Skills First** — Victorian state funding
- **Fee-for-service**

All four streams share the same VRQA-accredited EAL framework courses
and the same ACSF proficiency reporting, so a single pipeline can serve
all of them.

## Two artefact types

| Artefact | Scope | Schema | Template | Worked example |
|---|---|---|---|---|
| **Term plan** — "SEE/AMEP Unit Session Plan: Term N" | one 10-week term | `templates/term-plan.schema.yaml` | `templates/term-plan.template.md` | `terms/22640VIC-cert3-term1-2026.yaml` |
| **Session plan** — single 3-hour evening | one class session | `templates/mapping.schema.yaml` | `templates/session-plan.template.md` | *to be added* |

The **term plan is the primary artefact** trainers fill in (matrix of 7
macro skills × theme × 2–3 units × ACSF indicators, with verbatim unit
PCs appended). The session plan is an in-term drill-down when a specific
3-hour session needs its own documented sequence.

## What this solves

For any unit in the catalogue (see `units/units.yaml`), produce a session plan that:

1. Cites the **VRQA-accredited course document** (unit code + parent course).
2. Maps each session activity to **Elements / Performance Criteria / Required
   Skills & Knowledge / Foundation Skills** taken from the unit's **Mapping**.
3. References the **Assessor Guide** so formative checks in-session feed the
   summative evidence stream.
4. Satisfies the **Revised Standards for RTOs 2025** (Clauses on training
   strategies, assessment, and trainer competency).
5. Satisfies the **AMEP Deed / Business Rules** (ILP integration, settlement
   content, pre-employment pathway, attendance, learner voice).

See `GOVERNANCE.md` for the full regulatory stack and `COMPLIANCE.md` for the
audit checklist each generated plan is measured against.

## Pipeline shape

```
   ┌──────────────────────┐   ┌──────────────────┐   ┌─────────────────┐
   │ VRQA accredited      │   │ CommunityPlus    │   │ AMEP Deed /     │
   │ course doc (Unit     │──▶│ Mapping &        │──▶│ ILP & settlement│
   │ + Elements + PCs)    │   │ Assessor Guide   │   │ touchpoints     │
   └──────────────────────┘   └─────────┬────────┘   └────────┬────────┘
                                        ▼                     ▼
                              units/VU22xxx.yaml  ◀───────────┘
                                        │
                                        ▼
                              python generate.py VU22xxx
                                        │
                                        ▼
                   output/VU22xxx_session-plan_v<n>_<date>.md
```

## Units in scope (v1)

| Unit     | Status     | Parent qualifications                                         |
|----------|------------|---------------------------------------------------------------|
| VU22098  | stub       | 22484VIC                                                      |
| VU22358  | stub       | 22485VIC, 22476VIC, 22639VIC                                  |
| VU22369  | stub       | 22485VIC, 22484VIC, 22476VIC, 22639VIC                        |
| VU22384  | populated  | 22486VIC, 22489VIC, 22491VIC, 22640VIC, 22643VIC              |
| VU22398  | stub       | 22251VIC, 22486VIC, 22643VIC                                  |
| VU22590  | stub       | 22484VIC                                                      |
| VU22591  | stub       | 22484VIC                                                      |
| VU22592  | stub       | 22484VIC                                                      |
| VU22593  | stub       | 22484VIC                                                      |
| VU22594  | stub       | 22484VIC                                                      |
| VU23524  | populated  | 22640VIC                                                      |
| VU23560  | populated  | 22640VIC                                                      |

All parent qualifications are Victorian accredited EAL courses (VRQA).
`populated` units have their Elements / Performance Criteria / KS-KE /
PE / FS transcribed verbatim from the pattern source Denis's Cert3_Term1
2026 plan. Mapping + Assessor Guide blocks remain TBD until the
coordinator pastes the CommunityPlus internal LWA mapping and assessor
guide documents.

## Worked example: 22640VIC Cert III — SEE Term 1 — Year 2026

`terms/22640VIC-cert3-term1-2026.yaml` is the canonical populated term
plan (transcribed from Denis's 13-page Word doc). It demonstrates:

- Stream: **SEE — Basic**
- Framework: **22640VIC** Certificate III in EAL (Access) — reaccredited 2022/23
- Theme: "Education and Employment — Everyday English" (personal info,
  school, looking for work, celebrations)
- Units threaded: **VU22384** (ongoing portfolio unit) + **VU23524** (spoken
  conversations — Term 1) + **VU23560** (internet and email — Term 1)
- ACSF indicators claimed: 3.01–3.11 across 6 of 7 strands; Digital
  Literacy ACSF anchor marked "yet to confirm" (as in the source doc)
- LWA mapping + class-global document referenced (internal, not in repo)

## How to use

1. **Seed a unit file.** Copy `templates/mapping.schema.yaml` to
   `units/<UNIT>.yaml` and fill it from the authoritative sources:
   - VRQA course accreditation document (Elements, PCs, Required Skills &
     Knowledge, Assessment Conditions, Nominal Hours)
   - CommunityPlus **Mapping** document for that unit (assessment tasks ↔ PCs)
   - CommunityPlus **Assessor Guide** for that unit (benchmark answers, marking
     criteria, re-assessment rules)

   Fields left as `TBD_FROM_VRQA_COURSE_DOC`, `TBD_FROM_MAPPING`, or
   `TBD_FROM_ASSESSOR_GUIDE` must be replaced before generating — the pipeline
   refuses to generate an audit-ready plan with unresolved TBDs unless
   `--draft` is passed.

2. **Generate.**
   ```
   python3 generate.py VU22358 --session 3 --date 2026-04-22
   ```
   Output is written to `output/VU22358_S03_2026-04-22.md`.

3. **Review against the checklist** in `COMPLIANCE.md` before classroom use.

4. **Sign off.** Coordinator signs the generated plan; the version + hash are
   recorded in the document footer so ASQA / VRQA / AMEP auditors can trace
   which mapping version produced which delivered session.

## Template policy ("original / latest always")

`templates/session-plan.template.md` is a **superset** template: it contains
every field VRQA, Standards for RTOs 2025, and the AMEP Deed require, plus the
CommunityPlus-specific audit-trail fields (document control, coordinator
signoff, cohort class code). Any CommunityPlus internal template is a subset of
this one; when CommunityPlus issues a new internal version, bump the
`TEMPLATE_VERSION` constant in `generate.py` and record the new version in
`templates/CHANGELOG.md` so historical plans can be regenerated against the
template that was current at their delivery date.

## Governance

See `GOVERNANCE.md` for the full chain-of-authority from the
`Education and Training Reform Act 2006 (Vic)` through VRQA, ASQA, and the
Commonwealth AMEP programme.
