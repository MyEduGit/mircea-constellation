# Session-plan compliance checklist

Every generated plan must pass this checklist before classroom use. The
pipeline's `generate.py --check` runs the mechanical items; the human-judgment
items are the coordinator's responsibility.

## A. VRQA accredited-course fidelity

- [ ] Unit code and **exact title** match the VRQA accredited course document.
- [ ] Parent course code + accreditation period cited (e.g. 22485VIC, accredited
      dd/mm/yyyy – dd/mm/yyyy).
- [ ] Every **Element of Competency** addressed this session is listed verbatim.
- [ ] Every **Performance Criterion (PC)** targeted this session is listed
      verbatim.
- [ ] **Required Skills & Knowledge** items targeted this session are listed
      verbatim.
- [ ] **Assessment Conditions** of the unit are respected by in-session
      formative activities (e.g. authentic text types, observation mode).
- [ ] Session duration contributes to the **nominal hours** ledger for the unit.
- [ ] Pre-requisites / co-requisites verified for the cohort.

## B. Standards for RTOs 2025 (ASQA)

- [ ] Session plan is derived from the **TAS** for the parent qualification.
- [ ] Session sits correctly in the **sequence** implied by the TAS.
- [ ] Differentiation for below/at/above level is documented.
- [ ] **Reasonable adjustment** options documented.
- [ ] Formative assessment links to a summative task in the **Assessor Guide**.
- [ ] Trainer holds current TAE credential + vocational competency + industry
      currency (captured in trainer profile; referenced in plan header).
- [ ] Continuous-improvement section present (post-session reflection fields).
- [ ] Validation / moderation reference present (last validation date + outcome
      link).

## C. AMEP Deed / Business Rules (Department of Home Affairs)

- [ ] Session content traceable to cohort **ILPs** (reference block in header).
- [ ] Initial Assessment results (ISLPR / ACSF) considered in differentiation.
- [ ] **Settlement content** integration named (topic + how woven into EAL
      outcomes).
- [ ] **Pre-Employment English** / Social English pathway alignment stated
      where applicable.
- [ ] Attendance capture method named.
- [ ] Learner voice / feedback capture method named.

## D. CommunityPlus internal audit trail

- [ ] Document header fields all populated (RTO, campus, class code, trainer,
      coordinator).
- [ ] Document control block present (template version, mapping version,
      assessor-guide version, generation date, content hash).
- [ ] Coordinator signoff row present.
- [ ] Trainer signoff row present.
- [ ] WHS + trauma-informed practice block present.
- [ ] Referral pathways named (wellbeing, settlement).
- [ ] Resources block lists every learner and trainer artefact by title +
      source + copyright / licensing note.

## E. Assessment-chain integrity

- [ ] Each formative check in the session cites the **Mapping row** it feeds.
- [ ] Each Mapping row cited sits within an Assessment Task present in the
      **Assessor Guide**.
- [ ] The Assessor Guide version referenced is the one currently approved for
      the delivery cohort (no superseded versions).
- [ ] Re-assessment / reasonable-adjustment triggers from the Assessor Guide
      are carried into the plan's differentiation section.

## F. Mechanical checks run by `generate.py --check`

The generator refuses to produce a non-draft plan if any of the following
fails:

1. No `TBD_FROM_*` placeholders remain anywhere in the resolved document.
2. Every `maps_to` reference in the session activities resolves to a real
   `mapping_row` id in the unit YAML.
3. Every `mapping_row.assessment_task` resolves to a real
   `assessor_guide.tasks[].id` in the unit YAML.
4. Template version declared in the unit YAML ≤ `TEMPLATE_VERSION` in the
   generator (prevents forward-dated regeneration against a template that
   didn't exist yet).
5. `nominal_hours_used_this_session + nominal_hours_used_prior ≤
   nominal_hours_total` (prevents over-allocation against VRQA nominal hours).
6. SHA-256 hash of inputs is stamped into the output footer.
