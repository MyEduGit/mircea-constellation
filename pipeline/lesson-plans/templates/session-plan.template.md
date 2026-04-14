# Session Plan — {{ unit.code }} {{ unit.title }}

> **Template:** CommunityPlus AMEP Session Plan — superset v{{ template.version }}
> **Generated:** {{ doc.generated_at }} — **Input hash:** `{{ doc.input_sha256 }}`

## 1. Document control

| Field                         | Value                                      |
|-------------------------------|--------------------------------------------|
| RTO                           | CommunityPlus                              |
| RTO code                      | {{ rto.code }}                             |
| Campus / site                 | {{ delivery.campus }}                      |
| Class code                    | {{ delivery.class_code }}                  |
| Funding stream                | {{ delivery.funding_stream }}              |
| Session number / of           | {{ session.number }} of {{ session.total }} |
| Delivery date                 | {{ session.date }}                         |
| Session duration (hours)      | {{ session.duration_hours }}               |
| Trainer                       | {{ trainer.name }}                         |
| Trainer TAE / credential      | {{ trainer.credential }}                   |
| Trainer vocational competency | {{ trainer.vocational_competency }}        |
| Trainer industry currency     | {{ trainer.industry_currency }}            |
| Coordinator                   | {{ coordinator.name }}                     |
| Template version              | v{{ template.version }}                    |
| Mapping version               | v{{ unit.mapping.version }} ({{ unit.mapping.issued }}) |
| Assessor Guide version        | v{{ unit.assessor_guide.version }} ({{ unit.assessor_guide.issued }}) |
| Course doc (VRQA)             | {{ unit.parent_courses[0].code }} — accredited {{ unit.parent_courses[0].accreditation_period }} |

## 2. Unit alignment (VRQA accredited course document)

- **Unit code:** {{ unit.code }}
- **Unit title:** {{ unit.title }}
- **Parent courses:** {% for c in unit.parent_courses %}{{ c.code }} {{ c.title_verified_from_vrqa }}{% if not loop.last %}, {% endif %}{% endfor %}
- **Total nominal hours:** {{ unit.nominal_hours_total }}
- **Hours consumed prior to this session:** {{ session.nominal_hours_used_prior }}
- **Hours consumed this session:** {{ session.duration_hours }}
- **Pre-requisites:** {{ unit.prerequisites }}
- **Assessment conditions (verbatim from course doc):**
  > {{ unit.assessment_conditions }}

### Elements & Performance Criteria addressed this session

{% for e in session.elements_addressed %}
- **{{ e.element_id }} — {{ e.element_title }}**
  {% for pc in e.performance_criteria %}  - {{ pc.id }}: {{ pc.text }}
  {% endfor %}
{% endfor %}

### Required Skills & Knowledge targeted

{% for rsk in session.required_skills_knowledge %}- [{{ rsk.id }}] {{ rsk.text }}
{% endfor %}

### Foundation Skills — ACSF (AMEP-mandated framework since 1 July 2017)

AMEP progress is reported against 8 ACSF indicators (two each for Reading,
Writing, Learning, Oral Communication). Numeracy is tracked for the
Victorian EAL Framework unit but is not used for AMEP progress reporting.
Pre Level 1A / 1B from the ACSF Pre Level 1 Supplement applies where the
learner is below ACSF Level 1.

{% for fs in session.foundation_skills %}- {{ fs.domain }} — ACSF Level {{ fs.level }}{% if fs.pre_level %} ({{ fs.pre_level }}){% endif %}: {{ fs.indicator }}
{% endfor %}

## 3. Cohort & Individual Learning Plan linkage (AMEP)

- Learner count: {{ cohort.count }}
- **ACSF profile range** (R / W / L / OC): {{ cohort.acsf_range }}
- Pre Level 1 learners in cohort (1A / 1B): {{ cohort.pre_level_1_count }}
- ISLPR secondary benchmark (optional triangulation): {{ cohort.islpr_range }}
- ILP themes this session addresses: {{ cohort.ilp_themes }}
- Settlement content integrated: {{ cohort.settlement_content }}
- Pathway alignment: {{ cohort.pathway }}  <!-- Social English / Pre-Employment English / Further Study -->

## 4. Session learning outcomes (SMART)

{% for lo in session.learning_outcomes %}{{ loop.index }}. {{ lo.text }}  _(PCs: {{ lo.pc_refs | join(', ') }})_
{% endfor %}

## 5. Session sequence

| # | Stage                 | Time  | Activity                               | Differentiation                         | Maps to (Mapping row) |
|---|-----------------------|-------|-----------------------------------------|------------------------------------------|------------------------|
{% for a in session.activities %}| {{ loop.index }} | {{ a.stage }} | {{ a.minutes }} min | {{ a.description }} | {{ a.differentiation }} | {{ a.maps_to | join(', ') }} |
{% endfor %}

**Total time allocated:** {{ session.activities | sum(attribute='minutes') }} minutes

## 6. Differentiation & reasonable adjustment

- **Below level:** {{ session.differentiation.below }}
- **At level:**    {{ session.differentiation.at }}
- **Above level:** {{ session.differentiation.above }}
- **Pre-literacy adaptation:** {{ session.differentiation.pre_literacy }}
- **Reasonable adjustment available:** {{ session.differentiation.reasonable_adjustment }}
- **Cultural / gender-sensitive considerations:** {{ session.differentiation.cultural }}

## 7. Resources

| Artefact              | Role            | Source / version                           | Licence / copyright            |
|-----------------------|-----------------|--------------------------------------------|--------------------------------|
{% for r in session.resources %}| {{ r.title }} | {{ r.role }} | {{ r.source }} | {{ r.licence }} |
{% endfor %}

Room setup: {{ session.room_setup }}
Digital platforms: {{ session.digital_platforms }}

## 8. Formative assessment → summative evidence chain

{% for f in session.formative_checks %}- **{{ f.id }}** — {{ f.description }}
  - Mapping row: `{{ f.mapping_row }}`
  - Summative task it feeds: `{{ f.assessor_guide_task }}`
  - Evidence captured: {{ f.evidence_artefact }}
  - Recorded in: {{ f.evidence_location }}
{% endfor %}

## 9. WHS, wellbeing & trauma-informed practice

- WHS considerations this session: {{ session.whs }}
- Trauma-informed practice notes: {{ session.trauma_informed }}
- Referral pathways (wellbeing / settlement / legal / health): {{ session.referrals }}

## 10. Between-session learning

- Homework / self-directed task: {{ session.homework }}
- Time expected (hours): {{ session.homework_hours }}
- Link to next session: {{ session.next_session_link }}

## 11. Post-session reflection (completed after delivery)

- What worked:
- What didn't:
- Amendments for next cycle:
- Learner-voice summary (method: {{ cohort.feedback_method }}):
- Moderation / validation note (last validation: {{ unit.last_validation_date }}):

## 12. Signoff

| Role          | Name                   | Signature | Date |
|---------------|------------------------|-----------|------|
| Trainer       | {{ trainer.name }}     |           |      |
| Coordinator   | {{ coordinator.name }} |           |      |

---

**Compliance frame applied to this plan:**
- VRQA — *Education and Training Reform Act 2006* (Vic), accredited course {{ unit.parent_courses[0].code }}
- ASQA — Revised Standards for RTOs 2025 (in effect from 1 July 2025)
- Department of Home Affairs — AMEP Deed / Business Rules
- CommunityPlus TAS for {{ unit.parent_courses[0].code }} (TAS v{{ delivery.tas_version }})

_Generator: `pipeline/lesson-plans/generate.py`  •  Input SHA-256: `{{ doc.input_sha256 }}`_
