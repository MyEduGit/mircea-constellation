import argparse, time
from pathlib import Path
from .flow import JobFlow, JobState
from .proof import log
try:
    from . import dashboard as _db
except Exception:
    _db=None

ROOT = Path.home() / "Obsidian/UrantiPedia/System/NemoClaw/Jobs"
DONE = ".done"

def inbox_jobs(inbox):
    return sorted(p for p in inbox.glob("*.md") if not (inbox/(p.name+DONE)).exists())

def handle(job_path, jobs_root):
    print(f"[dispatcher] handling {job_path.name}")
    f = JobFlow(); f.state = JobState(jobs_root=str(jobs_root), job_path=str(job_path))
    f.kickoff(); (job_path.parent/(job_path.name+DONE)).touch()
    log(jobs_root, f"DISPATCHED {job_path.name}")
    if _db: _db.update(jobs_root)

def run_once(jobs_root):
    inbox = jobs_root/"00_INBOX"; inbox.mkdir(parents=True,exist_ok=True)
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
        while True: run_once(args.jobs_root); time.sleep(10)
    else:
        print(f"[dispatcher] done — {run_once(args.jobs_root)} job(s)")

if __name__ == "__main__": main()
