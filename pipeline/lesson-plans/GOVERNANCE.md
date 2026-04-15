# Governance — which bodies must a CommunityPlus EAL plan satisfy?

Answer up front: **four overlapping authorities** plus the **funding stream
overlay** (AMEP or SEE), and every term / session plan must demonstrably
align to all of them. The pipeline's template enforces that by making each
alignment a mandatory field.

## Funding stream overlay — AMEP, SEE, Skills First, FFS

The same VRQA-accredited EAL unit can be delivered under any of these
streams. The governance of the *unit* doesn't change, but the funding body
and its programme rules do:

| Stream | Funder | Rule set | Progress framework |
|---|---|---|---|
| **AMEP** | Dept of Home Affairs | AMEP Deed of Standing Offer + Business Rules | ACSF (8 indicators across R/W/L/OC) |
| **SEE** | DEWR | SEE Programme contract + Service Delivery Plan | ACSF (same instrument) |
| **Skills First** | Vic Dept of Jobs, Skills, Industry and Regions | Skills First Funding Contract | ACSF / EAL Framework |
| **FFS** | Learner | RTO policy | internal |

CommunityPlus delivers both **AMEP** and **SEE** — Denis's Cert III Term 1
2026 plan (`terms/22640VIC-cert3-term1-2026.yaml`) is a SEE-stream delivery
of the same 22640VIC course that other cohorts take under AMEP. The term-plan
schema captures the stream in `course.stream`.

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

## 3. Funding programme — AMEP (Home Affairs) or SEE (DEWR)

Whichever stream funds the delivery, the plan must satisfy that stream's
rules in addition to the unit-level accreditation requirements above.

### 3a. Department of Home Affairs — AMEP Programme

**What it governs:** funded delivery of EAL to eligible migrants through the
AMEP Deed of Standing Offer and the AMEP Business Rules / Performance
Framework.

**Plan-relevant expectations:**
- Session / term content traceable to each learner's **Individual Learning
  Plan (ILP)** and to the results of the Initial Assessment (ACSF; ISLPR
  as optional secondary benchmark).
- **Settlement content** (e.g. Life in Australia, services, civic
  participation) integrated contextually into EAL delivery.
- **Pre-Employment English (PEE)** or Social English pathway alignment where
  the learner is on that stream.
- Attendance and participation data captured per session.
- Learner voice / feedback captured and actioned.

### 3b. DEWR — Skills for Education and Employment (SEE)

**What it governs:** funded delivery of adult LLN to eligible job seekers
under the SEE Programme (DEWR contract). SEE co-exists with AMEP for adult
LLN learners; CommunityPlus's "Learning for Employment" colophon on the
term-plan masthead is the SEE-stream branding.

**Plan-relevant expectations:**
- Learner progress reported against **ACSF** (same framework as AMEP —
  the DEWR *SEE/AMEP alignment report* formally confirms the shared
  instrument).
- Delivery aligned to the employability focus — pre-employment English,
  workplace literacy, digital literacy for work.
- Provider Service Delivery Plan (SDP) is the SEE-equivalent of the AMEP
  Business Rules and sits alongside the CommunityPlus TAS.
- Employability Skills tagged explicitly on every macro-skill row in the
  term plan (the pattern source makes this explicit: every row lists
  "Employability Skills: …").

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
  AMEP Deed  or  SEE contract  performance reporting  +  RTO audit  +  VRQA course audit
```

If any layer above is amended, every layer below must be regenerated. The
pipeline supports this by keeping mapping + assessor-guide references as
versioned inputs and stamping the output plan with the resolved version set.
