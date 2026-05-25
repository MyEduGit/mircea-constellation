import argparse, shutil, time
from pathlib import Path
from .job_parser import parse
from .worker_claude import run as claude_run
from .job_parser import parse
from .worker_claude import run as claude_run
from .proof import log
try:
    from . import dashboard as _db
except Exception:
    _db = None

ROOT = Path.home() / "Obsidian/UrantiPedia/System/NemoClaw/Jobs"
DONE = ".done"

def _stage(job_path, jobs_root):
    for d in ["10_CREWAI_DISPATCH", "20_CLAUDE_CODE_EXECUTE"]:
        dest = jobs_root / d
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(job_path, dest / job_path.name)

def _archive(job_path, jobs_root):
    arc = jobs_root / "90_ARCHIVE"
    arc.mkdir(parents=True, exist_ok=True)
    shutil.copy2(job_path, arc / job_path.name)

def inbox_jobs(inbox):
    return sorted(p for p in inbox.glob("*.md") if not (inbox/(p.name+DONE)).exists())

def handle(job_path, jobs_root):
    print(f"[dispatcher] handling {job_path.name}")
    job = parse(job_path)
    log(jobs_root, f"LOADED {job_path.name}")
    _stage(job_path, jobs_root)
    log(jobs_root, f"STAGED {job_path.name}")
    try:
        out = claude_run(job, jobs_root/"40_RESULTS")
        log(jobs_root, f"EXECUTED {job['stem']} -> {out.name}")
    except Exception as e:
        log(jobs_root, f"ERROR: {e}")
    _archive(job_path, jobs_root)
    log(jobs_root, f"ARCHIVED {job_path.name}")
    (job_path.parent/(job_path.name+DONE)).touch()
    log(jobs_root, f"DISPATCHED {job_path.name}")
    if _db:
        try: _db.update(jobs_root)
        except Exception: pass

def run_once(jobs_root):
    inbox = jobs_root/"00_INBOX"
    inbox.mkdir(parents=True, exist_ok=True)
    jobs = inbox_jobs(inbox)
    if not jobs: print("[dispatcher] inbox empty")
    for j in jobs: handle(j, jobs_root)
    return len(jobs)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--watch", action="store_true")
    p.add_argument("--jobs-root", type=Path, default=ROOT)
    args = p.parse_args()
    if args.watch:
        print("[dispatcher] watching — Ctrl+C to stop")
        while True: run_once(args.jobs_root); time.sleep(10)
    else:
        print(f"[dispatcher] done — {run_once(args.jobs_root)} job(s)")

if __name__ == "__main__": main()
