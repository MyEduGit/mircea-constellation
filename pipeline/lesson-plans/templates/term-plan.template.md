{# Term Unit Session Plan — Jinja2 template (v2.0, mapping-first)            #}
{# Strictly renders government-mandated + audit-indexed content:             #}
{#   • Header strip (course identity, stream, trainer, class, term)          #}
{#   • Units threaded through the term                                       #}
{#   • ACSF indicator grid for the course level (verbatim from DEWR)         #}
{#   • Per unit: Elements + PCs + RK&S + PE + FS (VRQA verbatim)             #}
{#   • Per unit: Mapping rows (CommunityPlus LWA Mapping document)           #}
{#   • Per unit: Assessor Guide tasks (CommunityPlus Assessor Guide)         #}
{#   • Term calendar (vic.gov.au authoritative)                              #}
{#   • Compliance frame                                                      #}
{# Trainer-specific narrative is explicitly NOT rendered here.               #}
<!-- colophon: {{ header.left_colophon }}   |   {{ header.right_colophon }} -->

# {{ header.title }}: {{ header.term_label }} — Year {{ header.year }}

> **Generated:** {{ doc.generated_at }} — **Input hash:** `{{ doc.input_sha256 }}`
> **Template:** term-plan v{{ template.version }} (mapping-first)

## Header strip

|                          |                                                       |
|--------------------------|-------------------------------------------------------|
| **Stream**               | {{ course.stream }}{% if course.stream_substream %} — {{ course.stream_substream }}{% endif %} |
| **Framework**            | {{ course.framework_code }} — {{ course.framework_level_label }} ({{ course.framework_title }}) |
| **Accreditation period** | {{ course.accreditation_period }}                     |
| **ACSF level**           | {{ course.acsf_level }} (DEWR Australian Core Skills Framework) |
| **Trainer/Assessor**     | {{ trainer.name or "—" }}{% if trainer.credential %} — {{ trainer.credential }}{% endif %} |
| **Class code**           | {{ class.code }}{% if class.campus %} — {{ class.campus }}{% endif %} |

## Units threaded through this term

| Code | Role | Title |
|---|---|---|
{% for u in units %}| `{{ u.code }}` | {{ u.role }} | {{ u.title }} |
{% endfor %}

---

## ACSF indicator grid — Level {{ acsf.level }}

*Source: {{ acsf.framework.custodian }} — {{ acsf.framework.name }}.*
*Progress against these indicators is the SEE / AMEP progress-reporting instrument.*

| Indicator | Core skill | Title | Heading |
|---|---|---|---|
{% for ind in acsf.indicators %}| **{{ ind.id }}** | {{ acsf.core_skills[ind.core_skill] }}{% if 'domain' in ind %} — {{ ind['domain'] }}{% endif %} | {{ ind.indicator_title }} | {{ ind.heading }} |
{% endfor %}

---

# Per-unit audit surface

{% for u in units %}
## {{ u.code }} — {{ u.title }}  *({{ u.role }} unit)*

### Elements and Performance Criteria *(VRQA verbatim)*

| Element | Performance Criteria |
|---|---|
{% for e in unit_index[u.code].elements %}| **{{ e.id }}. {{ e.title }}** | {% for pc in e.performance_criteria %}{{ pc.id }} {{ pc.text }}{% if not loop.last %}<br>{% endif %}{% endfor %} |
{% endfor %}

### Required Knowledge and Skills *(VRQA verbatim)*

{% if unit_index[u.code].required_knowledge_skills %}| ID | Description |
|---|---|
{% for ks in unit_index[u.code].required_knowledge_skills %}| {{ ks.id }} | {{ ks.text | trim | replace('\n', '<br>') }} |
{% endfor %}{% else %}*Not supplied for this unit — re-verify from training.gov.au unit PDF.*{% endif %}

{% if unit_index[u.code].performance_evidence %}
### Performance Evidence *(VRQA verbatim)*

{% for pe in unit_index[u.code].performance_evidence %}- **{{ pe.id }}** — {{ pe.text | trim | replace('\n', '<br>  ') }}
{% endfor %}
{% endif %}

{% if unit_index[u.code].foundation_skills_block %}
### Foundation Skills *(VRQA verbatim)*

{% for fs in unit_index[u.code].foundation_skills_block %}- **{{ fs.id }}** — {{ fs.text | trim | replace('\n', '<br>  ') }}
{% endfor %}
{% endif %}

{% if unit_index[u.code].foundation_skills %}
### Foundation Skills — ACSF alignment

| Domain | Level | Indicator |
|---|---|---|
{% for fs in unit_index[u.code].foundation_skills %}| {{ fs.domain }} | {{ fs.level }} | {{ fs.indicator }} |
{% endfor %}
{% endif %}

### Mapping — assessments to Elements / PCs / Knowledge / Foundation Skills

*Source: CommunityPlus LWA Mapping document (internal, SharePoint).*
*This table is the audit-grade link from delivery to assessment evidence.*

{% set mapping = unit_index[u.code].mapping or {} %}
{% if mapping.rows %}Mapping version: **{{ mapping.version }}** — issued **{{ mapping.issued }}**

| Map row | Assessment task | PCs covered | Knowledge & Skills | Foundation Skills | Evidence type | Description |
|---|---|---|---|---|---|---|
{% for r in mapping.rows %}| `{{ r.id }}` | `{{ r.assessment_task }}` | {{ r.performance_criteria | join(', ') if r.performance_criteria else '—' }} | {{ r.required_skills_knowledge | join(', ') if r.required_skills_knowledge else '—' }} | {{ r.foundation_skills | join(', ') if r.foundation_skills else '—' }} | {{ r.evidence_type }} | {{ r.description | trim | replace('\n', '<br>') }} |
{% endfor %}{% else %}*Mapping rows not supplied — paste from the CP LWA Mapping document.*{% endif %}

### Assessor Guide — tasks

*Source: CommunityPlus Assessor Guide (internal, SharePoint).*

{% set ag = unit_index[u.code].assessor_guide or {} %}
{% if ag.tasks %}Assessor Guide version: **{{ ag.version }}** — issued **{{ ag.issued }}**

| Task | Title | Mode | Benchmark | Reasonable adjustment | Reassessment rule |
|---|---|---|---|---|---|
{% for t in ag.tasks %}| `{{ t.id }}` | {{ t.title }} | {{ t.mode }} | {{ t.benchmark_summary | trim | replace('\n', '<br>') }} | {{ t.reasonable_adjustment | trim | replace('\n', '<br>') }} | {{ t.reassessment_rule | trim | replace('\n', '<br>') }} |
{% endfor %}{% else %}*Assessor Guide tasks not supplied — paste from the CP Assessor Guide.*{% endif %}

---

{% endfor %}

## Term calendar

- **Term start:** {{ calendar.term_start }}
- **Term end:** {{ calendar.term_end }}
- **Weeks:** {{ calendar.weeks }}
- **Sessions per week:** {{ calendar.sessions_per_week }}
{% if calendar.public_holidays_impacting %}
- **Public holidays impacting delivery:**
{% for h in calendar.public_holidays_impacting %}  - {{ h.date }} — {{ h.name }}
{% endfor %}{% endif %}

*Calendar source: Victorian Government school term dates and holidays*
*(https://www.vic.gov.au/school-term-dates-and-holidays-victoria) —*
*statutory basis: Education and Training Reform Regulations 2017, Reg 13.*

---

## Compliance frame applied to this term plan

- **VRQA** — *Education and Training Reform Act 2006* (Vic), accredited course **{{ course.framework_code }}**
- **ASQA** — Revised Standards for RTOs 2025 (in effect 1 July 2025)
{% if course.stream == "AMEP" %}- **Home Affairs** — AMEP Deed of Standing Offer / Business Rules
{% elif course.stream == "SEE" %}- **DEWR** — Skills for Education and Employment (SEE) programme contract
{% endif %}- **DEWR** — Australian Core Skills Framework (ACSF) — progress-reporting instrument
- **CommunityPlus** — LWA Mapping document + Assessor Guide (internal sources)

_Generator: `pipeline/lesson-plans/generate.py --mode term`  •  Input SHA-256: `{{ doc.input_sha256 }}`_
