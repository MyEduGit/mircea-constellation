# CommunityPlus AMEP — Session Plan Pipeline

Reproducible pipeline for producing audit-ready session plans for every
`VU22xxx` unit CommunityPlus delivers inside AMEP (and Skills First / fee-for-
service where the same units sit in Victorian accredited EAL courses).

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

| Unit     | Parent qualifications (from Mircea's catalogue)                              |
|----------|------------------------------------------------------------------------------|
| VU22098  | 22484VIC                                                                     |
| VU22358  | 22485VIC, 22476VIC, 22639VIC                                                 |
| VU22369  | 22485VIC, 22484VIC, 22476VIC, 22639VIC                                       |
| VU22384  | 22486VIC, 22489VIC, 22491VIC, 22640VIC, 22643VIC                             |
| VU22398  | 22251VIC, 22486VIC, 22643VIC                                                 |
| VU22590  | 22484VIC                                                                     |
| VU22591  | 22484VIC                                                                     |
| VU22592  | 22484VIC                                                                     |
| VU22593  | 22484VIC                                                                     |
| VU22594  | 22484VIC                                                                     |

All parent qualifications are Victorian accredited EAL courses (VRQA).

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
