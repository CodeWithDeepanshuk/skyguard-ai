"""Check exact details of 8783 vs 8784."""
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(r"c:\Users\deepa\OneDrive\Desktop\Sih 73")
sys.path.insert(0, str(ROOT / "src"))
from data.run_phase10_models import load_split

val = load_split("validation")
r83 = val.iloc[8783].to_dict()
r84 = val.iloc[8784].to_dict()
print("8783:", r83["emitted_timestamp_utc"], r83["is_anomaly"], r83["anomaly_type"], r83["time_since_previous_minutes"], r83["temperature_value"], r83["pressure_value"], r83["humidity_value"])
print("8784:", r84["emitted_timestamp_utc"], r84["is_anomaly"], r84["anomaly_type"], r84["time_since_previous_minutes"], r84["temperature_value"], r84["pressure_value"], r84["humidity_value"])
