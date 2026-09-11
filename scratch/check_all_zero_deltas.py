"""Check how many rows have all 3 deltas == 0.0."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(r"c:\Users\deepa\OneDrive\Desktop\Sih 73")
sys.path.insert(0, str(ROOT / "src"))
from data.run_phase10_models import load_split

val = load_split("validation")
t_d = val["temperature_delta1"].abs() < 1e-5
p_d = val["pressure_delta1"].abs() < 1e-5
h_d = val["humidity_delta1"].abs() < 1e-5

all_zero = t_d & p_d & h_d
print(f"Total rows in validation: {len(val)}")
print(f"Rows with all 3 deltas == 0: {all_zero.sum()}")
print("Breakdown of anomaly types for all 3 deltas == 0:")
print(val.loc[all_zero, "anomaly_type"].value_counts(dropna=False))
