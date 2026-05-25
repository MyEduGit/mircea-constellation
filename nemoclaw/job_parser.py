from pathlib import Path
import re

def parse(job_path: Path) -> dict:
    text = job_path.read_text(encoding="utf-8")
    job: dict = {"path": job_path, "stem": job_path.stem, "raw": text}
    for line in text.splitlines():
        m = re.match(r"^[-*]?\s*\*?\*?(\w[\w\s]*):\*?\*?\s*(.+)$", line)
        if m:
            job[m.group(1).strip().lower().replace(" ","_")] = m.group(2).strip()
    return job
