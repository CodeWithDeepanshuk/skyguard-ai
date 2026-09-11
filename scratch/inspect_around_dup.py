"""Inspect around index 8784 in validation."""
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(r"c:\Users\deepa\OneDrive\Desktop\Sih 73")
sys.path.insert(0, str(ROOT / "src"))
from data.run_phase10_models import load_split

val = load_split("validation")
print(val.iloc[8780:8787][["row_id", "station_id", "emitted_timestamp_utc", "is_anomaly", "anomaly_type", "episode_id", "time_since_previous_minutes", "temperature_value", "pressure_value", "humidity_value"]])
