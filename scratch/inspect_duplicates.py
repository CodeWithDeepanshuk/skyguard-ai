"""Inspect duplicate_packet anomaly rows to understand their exact signatures."""
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(r"c:\Users\deepa\OneDrive\Desktop\Sih 73")
sys.path.insert(0, str(ROOT / "src"))
from data.run_phase10_models import load_split

val = load_split("validation")
dup_val = val.loc[val["anomaly_type"] == "duplicate_packet"]
print(f"Number of duplicate_packet rows in validation: {len(dup_val)}")

cols_to_check = [
    "station_id", "emitted_timestamp_utc", "time_since_previous_minutes", "gap_ratio",
    "out_of_order_indicator", "temperature_frozen_run_length", "temperature_delta1",
    "pressure_delta1", "humidity_delta1", "temperature_value", "pressure_value", "humidity_value"
]
print(dup_val[cols_to_check].head(10))
