import json,subprocess
from datetime import datetime
from pathlib import Path
REPO=Path(__file__).parent.parent
JOBS=Path.home()/"Obsidian/UrantiPedia/System/NemoClaw/Jobs"
STAGES=[("00_INBOX","Inbox"),("10_CREWAI_DISPATCH","Dispatch"),("20_CLAUDE_CODE_EXECUTE","Execute"),("40_RESULTS","Results"),("90_ARCHIVE","Archive")]
def _n(root,f): d=root/f; return len(list(d.glob("*.md"))) if d.exists() else 0
def _ev(root,n=10):
    p=root/"50_PROOF/proof.log"
    return p.read_text().strip().splitlines()[-n:] if p.exists() else []
def update(jobs_root=JOBS,push=False):
    p=REPO/"status.json"
    if p.exists():
        d=json.loads(p.read_text())
        d["nemoclaw"]={"status":"ok","version":"1.0.0","inbox":_n(jobs_root,"00_INBOX"),"dispatched":_n(jobs_root,"10_CREWAI_DISPATCH"),"executing":_n(jobs_root,"20_CLAUDE_CODE_EXECUTE"),"results":_n(jobs_root,"40_RESULTS"),"archived":_n(jobs_root,"90_ARCHIVE"),"proof_events":len(_ev(jobs_root,9999)),"recent_events":_ev(jobs_root,10)}
        d["updated"]=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
        p.write_text(json.dumps(d,indent=2)+"
")
    out=jobs_root/"DASHBOARD.md"
    jobs_root.mkdir(parents=True,exist_ok=True)
    lines=["# NemoClaw Dashboard",f"*{datetime.now().strftime(chr(37)+chr(89)+"-"+chr(37)+"m-"+chr(37)+"d "+chr(37)+"H:"+chr(37)+"M:"+chr(37)+"S")}*","","## Pipeline",""]
    for f,l in STAGES: n=_n(jobs_root,f); lines.append(f"| {l} | {n} |")
    ev=_ev(jobs_root,10)
    lines+=["
## Last Events
"]+([f"- `{e}`" for e in ev] or ["*none yet*"])
    out.write_text("
".join(lines)+"
")
    if push:
        subprocess.run(["git","-C",str(REPO),"add",str(REPO/"status.json")],check=True)
        subprocess.run(["git","-C",str(REPO),"commit","-m","chore: nemoclaw status"],check=True,capture_output=True)
        subprocess.run(["git","-C",str(REPO),"push"],check=True)
