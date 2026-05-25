import subprocess, shutil
from pathlib import Path

def build_prompt(job: dict) -> str:
    lines = [f"Job: {job.get('stem','unknown')}", f"Task: {job.get('task',job.get('job_title','process this job'))}"]
    if job.get("source"): lines.append(f"Source URL: {job['source']}")
    lines += ["", job.get("raw",""), "", "Return only the deliverable content."]
    return "\n".join(lines)

def run(job: dict, results_dir: Path) -> Path:
    results_dir.mkdir(parents=True, exist_ok=True)
    out = results_dir / f"{job['stem']}.md"
    prompt = build_prompt(job)
    b = shutil.which("claude")
    if b:
        r = subprocess.run([b,"-p",prompt,"--output-format","text"], capture_output=True, text=True, timeout=120)
        content = r.stdout.strip() or r.stderr.strip() or "[no output]"
    else:
        content = f"# {job['stem']}\n\n`claude` not on PATH.\n\nPrompt:\n```\n{prompt}\n```"
    out.write_text(content, encoding="utf-8")
    return out
