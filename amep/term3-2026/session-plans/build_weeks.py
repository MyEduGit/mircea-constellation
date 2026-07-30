#!/usr/bin/env python3
"""Pour Codex Term 3 content into the exact AMEP evening-class template.

For each week: copy template/unpacked -> build/Week_NN, fill cells from
weeks/Week_NN source docx, remap hyperlinks, zip to out/.
"""
import copy, os, re, shutil, subprocess, sys
from lxml import etree

BASE = os.path.dirname(os.path.abspath(__file__))
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
REL = 'http://schemas.openxmlformats.org/package/2006/relationships'


def q(tag, ns=W):
    return f'{{{ns}}}{tag}'


def para_text(p):
    return ''.join(t.text or '' for t in p.iter(q('t')))


def is_bold(rpr):
    if rpr is None:
        return False
    b = rpr.find(q('b'))
    if b is None:
        return False
    return b.get(q('val')) not in ('0', 'false', 'none')


def extract_paragraphs(tc, rels):
    """Cell -> list of paragraphs; each is a list of (text, bold, href|None)."""
    paras = []
    for p in tc.findall(q('p')):
        segs = []
        for child in p:
            if child.tag == q('r'):
                txt = ''.join(t.text or '' for t in child.findall(q('t')))
                if txt:
                    segs.append((txt, is_bold(child.find(q('rPr'))), None))
            elif child.tag == q('hyperlink'):
                rid = child.get(q('id', R))
                href = rels.get(rid)
                for r_ in child.findall(q('r')):
                    txt = ''.join(t.text or '' for t in r_.findall(q('t')))
                    if txt:
                        segs.append((txt, is_bold(r_.find(q('rPr'))), href))
        if segs:
            paras.append(segs)
    return paras


def load_source(week_dir):
    rels_tree = etree.parse(os.path.join(week_dir, 'word/_rels/document.xml.rels'))
    rels = {rel.get('Id'): rel.get('Target')
            for rel in rels_tree.getroot()
            if rel.get('TargetMode') == 'External'}
    doc = etree.parse(os.path.join(week_dir, 'word/document.xml'))
    body = doc.getroot().find(q('body'))
    tbls = body.findall(q('tbl'))
    t_hdr, t_units, t_mon, t_wed = tbls[0], tbls[1], tbls[2], tbls[3]

    hdr_cells = t_hdr.findall(q('tr'))[0].findall(q('tc'))
    left = para_text(hdr_cells[0])
    right = para_text(hdr_cells[1])
    theme = left.split('Theme(s):')[-1].strip()
    week_no = re.search(r'Week\s*(\d+)', right).group(1)
    dates = right.split('Dates:')[-1].strip()

    units_rows = t_units.findall(q('tr'))
    units = [p for p in extract_paragraphs(units_rows[0].findall(q('tc'))[0], rels)
             if ''.join(s[0] for s in p).strip() != 'EAL units']
    priorities = extract_paragraphs(units_rows[1].findall(q('tc'))[0], rels)
    routine = extract_paragraphs(units_rows[2].findall(q('tc'))[0], rels)

    def day(tbl):
        rows = tbl.findall(q('tr'))
        date = para_text(rows[0].findall(q('tc'))[0])
        date = date.split('Date:')[-1].split('Teacher:')[0].strip()
        s1 = [extract_paragraphs(tc, rels) for tc in rows[2].findall(q('tc'))]
        s2 = [extract_paragraphs(tc, rels) for tc in rows[3].findall(q('tc'))]
        return {'date': date, 's1': s1, 's2': s2}

    return {'theme': theme, 'week': week_no, 'dates': dates, 'units': units,
            'priorities': priorities, 'routine': routine,
            'mon': day(t_mon), 'wed': day(t_wed)}


# ---------- target-side helpers ----------

def make_rpr(bold, link):
    rpr = etree.SubElement(etree.Element(q('r')), q('rPr'))  # detached parent ok
    rf = etree.SubElement(rpr, q('rFonts'))
    for a in ('ascii', 'hAnsi', 'cs'):
        rf.set(q(a), 'Arial')
    if bold:
        etree.SubElement(rpr, q('b'))
    if link:
        etree.SubElement(rpr, q('color')).set(q('val'), '0563C1')
        etree.SubElement(rpr, q('u')).set(q('val'), 'single')
    etree.SubElement(rpr, q('sz')).set(q('val'), '18')
    etree.SubElement(rpr, q('szCs')).set(q('val'), '18')
    return rpr


def make_para(segs, link_ids):
    """segs: [(text, bold, href|None)]; link_ids: dict href->rId (pre-registered)."""
    p = etree.Element(q('p'))
    ppr = etree.SubElement(p, q('pPr'))
    sp = etree.SubElement(ppr, q('spacing'))
    sp.set(q('after'), '0')
    sp.set(q('line'), '240')
    sp.set(q('lineRule'), 'auto')
    for txt, bold, href in segs:
        r_ = etree.Element(q('r'))
        r_.append(make_rpr(bold, href))
        t = etree.SubElement(r_, q('t'))
        t.text = txt
        t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        if href:
            h = etree.SubElement(p, q('hyperlink'))
            h.set(q('id', R), link_ids[href])
            h.append(r_)
        else:
            p.append(r_)
    return p


def append_to_run(p, extra):
    """Append text to the last non-empty run of paragraph p."""
    runs = [r_ for r_ in p.findall(q('r')) if r_.findall(q('t'))]
    if not runs:
        return False
    t = runs[-1].findall(q('t'))[-1]
    t.text = (t.text or '') + extra
    t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    return True


def fill_label(tc, label, value):
    """Find paragraph starting with label and append value to it."""
    for p in tc.findall(q('p')):
        if para_text(p).strip().startswith(label):
            return append_to_run(p, value)
    return False


def clear_cell_keep_first(tc):
    """Remove all paragraphs except the first (label) one."""
    paras = tc.findall(q('p'))
    for p in paras[1:]:
        tc.remove(p)


def append_paras(tc, paras, link_ids):
    for segs in paras:
        tc.append(make_para(segs, link_ids))


def strip_session_prefix(paras):
    """Return (title_segs, rest). First para is 'Session N (...) — Title'."""
    if not paras:
        return None, []
    first = paras[0]
    joined = ''.join(s[0] for s in first)
    m = re.search(r'—\s*(.+)$', joined)
    title = [(m.group(1).strip(), True, None)] if m else None
    return title, paras[1:]


def collect_links(week):
    links = set()
    def scan(paras):
        for p in paras:
            for _, _, href in p:
                if href:
                    links.add(href)
    scan(week['units']); scan(week['priorities']); scan(week['routine'])
    for d in (week['mon'], week['wed']):
        for cell in d['s1'] + d['s2']:
            scan(cell)
    return sorted(links)


def build_week(n, teacher='Mircea Matthews', class_code='CP123E3 & CP123E4'):
    nn = f'{int(n):02d}'
    src_dir = os.path.join(BASE, 'weeks', f'Week_{nn}')
    wk = load_source(src_dir)
    out_dir = os.path.join(BASE, 'build', f'Week_{nn}')
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    shutil.copytree(os.path.join(BASE, 'template', 'unpacked'), out_dir)

    # --- relationships: add external hyperlinks ---
    rels_path = os.path.join(out_dir, 'word/_rels/document.xml.rels')
    rels_tree = etree.parse(rels_path)
    rroot = rels_tree.getroot()
    max_id = max(int(rel.get('Id')[3:]) for rel in rroot
                 if rel.get('Id', '').startswith('rId'))
    link_ids = {}
    for i, href in enumerate(collect_links(wk), start=1):
        rid = f'rId{max_id + i}'
        rel = etree.SubElement(rroot, f'{{{REL}}}Relationship')
        rel.set('Id', rid)
        rel.set('Type', f'{R}/hyperlink')
        rel.set('Target', href)
        rel.set('TargetMode', 'External')
        link_ids[href] = rid
    rels_tree.write(rels_path, xml_declaration=True, encoding='UTF-8', standalone=True)

    # --- document ---
    doc_path = os.path.join(out_dir, 'word/document.xml')
    tree = etree.parse(doc_path)
    body = tree.getroot().find(q('body'))
    t1, t2 = body.findall(q('tbl'))[:2]
    rows1 = t1.findall(q('tr'))
    rows2 = t2.findall(q('tr'))

    # T1 R0 header
    hc = rows1[0].findall(q('tc'))
    assert fill_label(hc[0], 'Class code:', f' {class_code}')
    assert fill_label(hc[0], 'Skill set/qualification:',
                      ' Mixed 22638VIC Cert I / 22639VIC Cert II / 22640VIC Cert III EAL (evening)')
    assert fill_label(hc[0], 'Theme(s):', f' {wk["theme"]}')
    assert fill_label(hc[1], 'Teacher/s:', f' {teacher}')
    assert fill_label(hc[1], 'Term/week:', f' Term 3 / Week {int(wk["week"])}')
    assert fill_label(hc[1], 'Dates:', f' {wk["dates"]}')

    # T1 R1 EAL units
    uc = rows1[1].findall(q('tc'))[0]
    clear_cell_keep_first(uc)
    append_paras(uc, wk['units'], link_ids)

    # T1 R2 themes -> Term 3 weekly focus
    thc = rows1[2].findall(q('tc'))[0]
    first = thc.findall(q('p'))[0]
    for t in first.iter(q('t')):
        t.text = ''
    ok = append_to_run(first, f'Themes – term 3, week {int(wk["week"])}: {wk["theme"]}')
    assert ok
    clear_cell_keep_first(thc)
    append_paras(thc, wk['priorities'] + wk['routine'], link_ids)

    def fill_day(date_tc, s1_row, s2_row, day):
        assert fill_label(date_tc, 'Date:', f' {day["date"]}')
        assert fill_label(date_tc, 'Teacher:', f' {teacher}')
        for row, key in ((s1_row, 's1'), (s2_row, 's2')):
            tcs = row.findall(q('tc'))
            title, rest0 = strip_session_prefix(day[key][0])
            if title:
                tcs[0].append(make_para(title, link_ids))
            append_paras(tcs[0], rest0, link_ids)
            for ci in (1, 2):
                _, rest = strip_session_prefix(day[key][ci])
                append_paras(tcs[ci], rest, link_ids)

    # Monday: T1 rows 3 (date), 7 (S1), 8 (S2)
    fill_day(rows1[3].findall(q('tc'))[0], rows1[7], rows1[8], wk['mon'])
    # Wednesday: T2 rows 0 (date), 4 (S1), 5 (S2)
    fill_day(rows2[0].findall(q('tc'))[0], rows2[4], rows2[5], wk['wed'])

    tree.write(doc_path, xml_declaration=True, encoding='UTF-8', standalone=True)

    # --- zip ---
    out_docx = os.path.join(BASE, 'out', f'AMEP_Term3_2026_Week_{nn}_Lesson_Plan.docx')
    os.makedirs(os.path.dirname(out_docx), exist_ok=True)
    if os.path.exists(out_docx):
        os.remove(out_docx)
    subprocess.run(['zip', '-Xrq', out_docx, '.'], cwd=out_dir, check=True)
    return out_docx


if __name__ == '__main__':
    for n in range(1, 11):
        path = build_week(n)
        print('built', path)
