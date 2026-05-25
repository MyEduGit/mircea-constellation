from pathlib import Path
from crewai.flow.flow import Flow, listen, start
from pydantic import BaseModel
from .job_parser import parse
from .worker_claude import run as claude_run
from .proof import log
import shutil

class JobState(BaseModel):
    jobs_root: str = ""; job_path: str = ""; stem: str = ""; result_path: str = ""; error: str = ""

class JobFlow(Flow[JobState]):
    @start()
    def load_job(self):
        job = parse(Path(self.state.job_path)); self.state.stem = job["stem"]; self._job = job
        log(Path(self.state.jobs_root), f"LOADED {Path(self.state.job_path).name}")
    @listen(load_job)
    def stage_job(self):
        r, p = Path(self.state.jobs_root), Path(self.state.job_path)
        for d in ["10_CREWAI_DISPATCH","20_CLAUDE_CODE_EXECUTE"]:
            (r/d).mkdir(parents=True,exist_ok=True); shutil.copy2(p, r/d/p.name)
        log(r, f"STAGED {p.name}")
    @listen(stage_job)
    def execute_job(self):
        r = Path(self.state.jobs_root)
        try:
            out = claude_run(self._job, r/"40_RESULTS"); self.state.result_path = str(out)
            log(r, f"EXECUTED {self.state.stem} -> {out.name}")
        except Exception as e:
            self.state.error = str(e); log(r, f"ERROR {self.state.stem}: {e}")
    @listen(execute_job)
    def archive_job(self):
        r, p = Path(self.state.jobs_root), Path(self.state.job_path)
        arc = r/"90_ARCHIVE"; arc.mkdir(parents=True,exist_ok=True); shutil.copy2(p, arc/p.name)
        log(r, f"ARCHIVED {p.name}")
