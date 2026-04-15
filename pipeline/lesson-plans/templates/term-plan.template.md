{# Term Unit Session Plan — Jinja2 template                                   #}
{# Mirrors the CommunityPlus "SEE Unit Session Plan: Term N — Year YYYY"      #}
{# Word-doc layout (co-branded "Learning for Employment" + "CommunityPlus").  #}
{# Pattern source: Denis's Cert3_Term1 2026 lesson planning (22640VIC).       #}
{# Unit verbatim blocks are injected from units/<CODE>.yaml.                  #}
<!-- colophon: {{ header.left_colophon }}   |   {{ header.right_colophon }} -->

# {{ header.title }}: {{ header.term_label }} — Year {{ header.year }}

> **Generated:** {{ doc.generated_at }} — **Input hash:** `{{ doc.input_sha256 }}`
> **Template:** term-plan v{{ template.version }}

## Header strip

|                          |                                                       |
|--------------------------|-------------------------------------------------------|
| **Stream**               | {{ course.stream }}{% if course.stream_substream %} — {{ course.stream_substream }}{% endif %} |
| **Unit Theme**           | {{ theme.title }}                                     |
| **ESL Framework Level**  | {{ course.framework_code }} — {{ course.framework_level_label }} ({{ course.framework_title }}) |
| **Accreditation period** | {{ course.accreditation_period }}                     |
| **Trainer/Assessor**     | {{ trainer.name }}{% if trainer.credential %} — {{ trainer.credential }}{% endif %} |
| **Class code**           | {{ class.code }}{% if class.campus %} — {{ class.campus }}{% endif %} |

### Top banner (reappears each term)

| Key topic | WHAT will students learn? | Teaching & Learning Resources / Incursions & Excursions | Assessment strategies (ACSF level / LWA mapping / class global) |
|---|---|---|---|
|  | {{ banner.what_students_learn | trim | replace('\n', ' ') }} | {{ banner.resources_statement | trim | replace('\n', ' ') }} | {{ banner.assessment_statement | trim | replace('\n', ' ') }} |

> *{{ banner.acknowledgement_note | trim | replace('\n', ' ') }}*
> *Mapping reference: {{ banner.mapping_reference }}*

## Units threaded through this term

| Code | Role | Title |
|---|---|---|
{% for u in units %}| `{{ u.code }}` | {{ u.role }} | {{ u.title }} |
{% endfor %}

## Macro-skill matrix

{% for row in macro_skills %}
### {{ row.strand }}  <!-- colour: {{ row.colour }} -->

| What will your learners know and be able to do? | Facilities used in the teaching and learning | What will you deliver, assess and evaluate? (Framework Units & ACSF Indicator) |
|---|---|---|
| {% for lp in row.learning_points %}• {{ lp }}<br>{% endfor %}{% if row.employability_skills %}**Employability Skills:** {{ row.employability_skills | join(', ') }}{% endif %} | {% for r in row.resources_and_facilities %}• {{ r }}<br>{% endfor %} | {% for code in row.framework_unit_refs %}**{{ code }}** — {{ unit_index[code].title }}<br>*Please refer to the Elements and Performance Criteria at the end of this document.*<br>{% endfor %}{% if row.acsf_indicators %}<br>ACSF: {{ row.acsf_indicators | join(' / ') }}{% else %}<br>*ACSF — yet to confirm*{% endif %} |

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

---

# Elements, Performance Criteria, Required Knowledge & Skills (verbatim)

{% for u in units %}
## {{ u.role | capitalize }} Unit — {{ u.code }} {{ u.title }}

### Elements and Performance Criteria

| Element | Performance Criteria |
|---|---|
{% for e in unit_index[u.code].elements %}| **{{ e.id }}. {{ e.title }}** | {% for pc in e.performance_criteria %}{{ pc.id }} {{ pc.text }}{% if not loop.last %}<br>{% endif %}{% endfor %} |
{% endfor %}

### Required Knowledge and Skills

{% if unit_index[u.code].required_knowledge_skills %}| ID | Description |
|---|---|
{% for ks in unit_index[u.code].required_knowledge_skills %}| {{ ks.id }} | {{ ks.text | trim | replace('\n', '<br>') }} |
{% endfor %}{% else %}*Not supplied for this unit.*{% endif %}

{% if unit_index[u.code].performance_evidence %}
### Performance Evidence

{% for pe in unit_index[u.code].performance_evidence %}- **{{ pe.id }}** — {{ pe.text | trim | replace('\n', '<br>  ') }}
{% endfor %}
{% endif %}

{% if unit_index[u.code].foundation_skills_block %}
### Foundation Skills

{% for fs in unit_index[u.code].foundation_skills_block %}- **{{ fs.id }}** — {{ fs.text | trim | replace('\n', '<br>  ') }}
{% endfor %}
{% endif %}

---

{% endfor %}

**Compliance frame applied to this term plan:**
- VRQA — *Education and Training Reform Act 2006* (Vic), accredited course **{{ course.framework_code }}**
- ASQA — Revised Standards for RTOs 2025 (in effect 1 July 2025)
{% if course.stream == "AMEP" %}- Department of Home Affairs — AMEP Deed of Standing Offer / Business Rules
{% elif course.stream == "SEE" %}- DEWR — Skills for Education and Employment (SEE) programme contract
{% endif %}- DEWR — Australian Core Skills Framework (ACSF) — progress reporting instrument
- CommunityPlus — LWA mapping document + class-global document (internal)

_Generator: `pipeline/lesson-plans/generate.py --mode term`  •  Input SHA-256: `{{ doc.input_sha256 }}`_
