from datetime import datetime
from pathlib import Path

def log(jobs_root: Path, event: str) -> None:
    proof_dir = jobs_root / "50_PROOF"
    proof_dir.mkdir(parents=True, exist_ok=True)
    entry = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {event}\n"
    (proof_dir / "proof.log").open("a").write(entry)
    print(f"[proof] {entry.strip()}")
