#!/usr/bin/env python3
"""
Build the KDP-ready manuscript from markdown chapters.
Outputs: manuscript.html (open in browser → Print → Save as PDF → upload to KDP)
"""
import os
import re

BOOK_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(BOOK_DIR, "manuscript.html")

CHAPTERS = [
    ("chapter_01.md", "1"),
    ("chapter_02.md", "2"),
    ("chapter_03.md", "3"),
    ("chapter_04.md", "4"),
    ("chapter_05.md", "5"),
    ("chapter_06.md", "6"),
    ("chapter_07.md", "7"),
    ("chapter_08.md", "8"),
    ("chapter_09.md", "9"),
    ("chapter_10.md", "10"),
]

def md_to_html(md_text):
    html = md_text
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    html = re.sub(r'`(.+?)`', r'<code>\1</code>', html)
    html = re.sub(r'^---$', '<hr>', html, flags=re.MULTILINE)
    html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    lines = html.split('\n')
    result = []
    in_table = False
    in_list = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('|') and '|' in stripped[1:]:
            if not in_table:
                result.append('<table>')
                in_table = True
            if re.match(r'^\|[\s\-|]+\|$', stripped):
                continue
            cells = [c.strip() for c in stripped.split('|')[1:-1]]
            tag = 'th' if not any('<table>' in r for r in result[-5:] if '<table>' in r) and result[-1] == '<table>' else 'td'
            row = '<tr>' + ''.join(f'<{tag}>{c}</{tag}>' for c in cells) + '</tr>'
            result.append(row)
        else:
            if in_table:
                result.append('</table>')
                in_table = False
            if stripped.startswith('<li>'):
                if not in_list:
                    result.append('<ul>')
                    in_list = True
                result.append(stripped)
            else:
                if in_list:
                    result.append('</ul>')
                    in_list = False
                if stripped.startswith('<h') or stripped.startswith('<hr') or stripped == '':
                    result.append(stripped)
                elif stripped:
                    result.append(f'<p>{stripped}</p>')
    if in_table:
        result.append('</table>')
    if in_list:
        result.append('</ul>')
    return '\n'.join(result)


CSS = """
@page { size: 6in 9in; margin: 0.75in 0.625in; }
body { font-family: Georgia, 'Times New Roman', serif; font-size: 11pt; line-height: 1.6; color: #1a1a1a; max-width: 5in; margin: 0 auto; }
h1 { font-size: 22pt; margin: 2em 0 0.5em; page-break-before: always; color: #0B1D3A; border-bottom: 2px solid #00BCD4; padding-bottom: 8px; }
h1:first-of-type { page-break-before: avoid; }
h2 { font-size: 15pt; margin: 1.5em 0 0.5em; color: #1A3A5C; }
h3 { font-size: 12pt; margin: 1.2em 0 0.4em; color: #2A5A7C; }
p { margin: 0.5em 0; text-align: justify; }
strong { color: #0B1D3A; }
em { font-style: italic; }
code { font-family: 'Courier New', monospace; background: #f0f4f8; padding: 2px 5px; border-radius: 3px; font-size: 10pt; }
hr { border: none; border-top: 1px solid #ccc; margin: 1.5em 0; }
table { width: 100%; border-collapse: collapse; margin: 1em 0; font-size: 10pt; }
th, td { border: 1px solid #ddd; padding: 6px 10px; text-align: left; }
th { background: #f0f4f8; font-weight: 600; }
ul { margin: 0.5em 0 0.5em 1.5em; }
li { margin: 0.3em 0; }
.title-page { text-align: center; padding-top: 3in; page-break-after: always; }
.title-page h1 { font-size: 32pt; border: none; color: #0B1D3A; page-break-before: avoid; }
.title-page .subtitle { font-size: 14pt; color: #555; margin-top: 0.5em; }
.title-page .author { font-size: 16pt; margin-top: 2em; color: #1A3A5C; }
.title-page .credentials { font-size: 11pt; color: #888; margin-top: 0.3em; }
.toc { page-break-after: always; }
.toc h2 { font-size: 18pt; text-align: center; border: none; }
.toc ul { list-style: none; padding: 0; }
.toc li { padding: 6px 0; border-bottom: 1px dotted #ccc; font-size: 12pt; }
.toc li span { color: #888; }
.copyright { font-size: 9pt; color: #888; text-align: center; page-break-after: always; margin-top: 4in; }
@media print { .no-print { display: none; } }
"""

title_page = """
<div class="title-page">
  <h1>AI Literacy<br>for ESL Students</h1>
  <div class="subtitle">A Practical Guide for Adult Migrant English Learners</div>
  <div class="author">Mircea Matthews</div>
  <div class="credentials">AMEP Teacher &middot; Melbourne, Australia</div>
</div>
"""

copyright_page = """
<div class="copyright">
  <p><strong>AI Literacy for ESL Students</strong></p>
  <p>A Practical Guide for Adult Migrant English Learners</p>
  <p>&copy; 2026 Mircea Matthews. All rights reserved.</p>
  <p>No part of this book may be reproduced without written permission from the author,<br>
  except for brief quotations in reviews and educational use.</p>
  <p>First edition, 2026</p>
  <p>Published via Amazon Kindle Direct Publishing</p>
  <p>Cover design by Mircea's Constellation AI</p>
  <p>ISBN: [assigned by KDP]</p>
</div>
"""

toc = """
<div class="toc">
  <h2>Table of Contents</h2>
  <ul>
    <li><strong>Part 1: Foundation</strong></li>
    <li>Chapter 1: What is AI?</li>
    <li>Chapter 2: AI Tools You Can Use Today</li>
    <li>Chapter 3: Staying Safe Online with AI</li>
    <li><strong>Part 2: AI for English Learning</strong></li>
    <li>Chapter 4: Using AI to Practice Speaking</li>
    <li>Chapter 5: Using AI to Practice Writing</li>
    <li>Chapter 6: Using AI to Build Vocabulary</li>
    <li>Chapter 7: AI for Reading Comprehension</li>
    <li><strong>Part 3: AI for Daily Life in Australia</strong></li>
    <li>Chapter 8: AI for Job Searching and Resumes</li>
    <li>Chapter 9: AI for Government Services and Forms</li>
    <li>Chapter 10: AI for Healthcare and Community</li>
  </ul>
</div>
"""

chapters_html = []
for fname, num in CHAPTERS:
    fpath = os.path.join(BOOK_DIR, fname)
    with open(fpath) as f:
        md = f.read()
    chapters_html.append(md_to_html(md))

full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>AI Literacy for ESL Students — Mircea Matthews</title>
<style>{CSS}</style>
</head>
<body>
{title_page}
{copyright_page}
{toc}
{''.join(chapters_html)}
</body>
</html>"""

with open(OUTPUT, 'w') as f:
    f.write(full_html)

print(f"Manuscript built: {OUTPUT}")
print(f"Size: {len(full_html):,} bytes")
print("Open in browser → File → Print → Save as PDF → Upload to KDP")
