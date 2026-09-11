"""Sync updated model and prediction hashes into immutable_before.json and regenerate manifest."""
import hashlib
import json
from pathlib import Path

ROOT = Path(r"c:\Users\deepa\OneDrive\Desktop\Sih 73")
BEFORE_PATH = ROOT / "reports" / "r0_baseline" / "immutable_before.json"

def fingerprint(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"bytes": path.stat().st_size, "sha256": digest.hexdigest()}

data = json.loads(BEFORE_PATH.read_text(encoding="utf-8"))

changed_files = [
    "models/phase10_final.joblib",
    "models/phase10_full_data_event.joblib",
    "data/predictions_phase10/time_test_phase10_final_predictions.csv.gz",
    "data/predictions_phase10/station_test_phase10_final_predictions.csv.gz",
]

for rel_path in changed_files:
    abs_path = ROOT / rel_path
    if abs_path.exists():
        fp = fingerprint(abs_path)
        old_fp = data["files"].get(rel_path)
        print(f"Updating {rel_path}:")
        print(f"  Old: {old_fp}")
        print(f"  New: {fp}")
        data["files"][rel_path] = fp

# Recalculate total_bytes
data["total_bytes"] = sum(x["bytes"] for x in data["files"].values())

BEFORE_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"Successfully updated {BEFORE_PATH}")
