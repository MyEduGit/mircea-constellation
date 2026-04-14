# Governance — which bodies must a CommunityPlus AMEP session plan satisfy?

Answer up front: **four overlapping authorities**, and every session plan must
demonstrably align to all four. The pipeline's template enforces that by
making each alignment a mandatory field.

## 1. VRQA — Victorian Registration and Qualifications Authority

**What it governs:** the accredited course documents for every `VIC`-suffix
course CommunityPlus delivers, and the `VU` units inside them.

| Parent course | Stream                               |
|---------------|--------------------------------------|
| 22484VIC      | Course in Initial EAL                |
| 22485VIC      | Certificate I in EAL family          |
| 22476VIC      | Certificate I variant                 |
| 22486VIC      | Certificate II in EAL                |
| 22489VIC      | Certificate III in EAL               |
| 22491VIC      | Certificate IV in EAL                |
| 22251VIC      | earlier Cert II equivalent           |
| 22639VIC      | Certificate I in EAL (reaccredited)  |
| 22640VIC      | Certificate II in EAL (reaccredited) |
| 22643VIC      | Certificate IV in EAL (reaccredited) |

> Confirm exact course titles + current accreditation period against the VRQA
> accredited course register when populating each unit YAML — the pipeline
> stores the exact title in `parent_courses[].title_verified_from_vrqa`.

**Statutory basis:** *Education and Training Reform Act 2006* (Vic) —
VRQA accredits courses under Ch. 4, Pt 4.3.

**What it audits in a session plan:**
- Fidelity to the accredited Elements of Competency & Performance Criteria
- Required Skills & Knowledge coverage
- Assessment Conditions respected (e.g. authentic context, observation
  requirements, text-type coverage for EAL)
- Nominal hours are consistent with the session duration × number of sessions
- Pre-requisites and co-requisites observed

## 2. ASQA — Australian Skills Quality Authority

**What it governs:** CommunityPlus's registration as an RTO (if
ASQA-registered; dual-registered Victorian RTOs are regulated by VRQA for
Vic-only delivery).

**Current framework:** **Revised Standards for RTOs 2025**, in effect from
1 July 2025, replacing the Standards for RTOs 2015.

**Session-plan-relevant expectations** (paraphrased from the 2025 Outcome
Standards and Compliance Requirements):
- Training is planned and structured in line with the Training and Assessment
  Strategy (TAS) for the qualification.
- Learners are supported with appropriate resources and with differentiation
  / reasonable adjustment where required.
- Assessment is **valid, reliable, flexible, fair** — and formative assessment
  in the session plan feeds the summative evidence mapped in the Assessor
  Guide.
- Trainers hold the required credential (TAE40122 or Standards-2025
  equivalent) and maintain current vocational competency and industry
  currency.
- Continuous improvement — post-session reflection and validation outputs are
  recorded and fed back into the plan.

## 3. Department of Home Affairs — AMEP Programme

**What it governs:** funded delivery of EAL to eligible migrants through the
AMEP Deed of Standing Offer and the AMEP Business Rules / Performance
Framework.

**Session-plan-relevant expectations:**
- Session content traceable to each learner's **Individual Learning Plan
  (ILP)** and to the results of the Initial Assessment (ISLPR / ACSF).
- **Settlement content** (e.g. Life in Australia, services, civic
  participation) integrated contextually into EAL delivery.
- **Pre-Employment English (PEE)** or Social English pathway alignment where
  the learner is on that stream.
- Attendance and participation data captured per session.
- Learner voice / feedback captured and actioned.

## 4. Course Owner / Curriculum Maintenance Manager (CMM)

For the EAL suite the CMM has historically been AMES Australia (and
Victoria University for earlier versions). The course owner publishes:
- The **accredited course document** (the source of truth for LOs, PCs, RS&K,
  Assessment Conditions).
- Any endorsed sample assessments or moderation guidance.

The CommunityPlus **Mapping** and **Assessor Guide** are the RTO's contextualised
interpretation of the CMM's accredited document.

## Hierarchy of authority for a single session

```
  Education and Training Reform Act 2006 (Vic)
               │
               ▼
  VRQA accredited course document  ◀── source of PCs, RS&K, Assessment Conditions
               │
               ▼
  CommunityPlus TAS for the qualification (ASQA / Standards for RTOs 2025)
               │
               ▼
  Unit Mapping  +  Assessor Guide   ◀── RTO's contextualisation
               │
               ▼
  Session plan (this pipeline's output)
               │
               ▼
  Delivered session  →  formative evidence  →  summative evidence  →  competency
               │
               ▼
  AMEP Deed performance reporting  +  RTO audit  +  VRQA course audit
```

If any layer above is amended, every layer below must be regenerated. The
pipeline supports this by keeping mapping + assessor-guide references as
versioned inputs and stamping the output plan with the resolved version set.
