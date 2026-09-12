"""Split genuine observations before injection; never random-split derived copies."""
from __future__ import annotations

import hashlib
import pandas as pd


def _row_id(row) -> str:
    raw = f"{row.station_id}|{pd.Timestamp(row.timestamp_utc).isoformat()}|{row.source_snapshot_hash}"
    return hashlib.sha256(raw.encode()).hexdigest()


def split_genuine_observations(frame: pd.DataFrame, station_holdout_fraction=.2):
    required = {"station_id", "timestamp_utc", "source_snapshot_hash", "source_is_genuine"}
    missing = required - set(frame)
    if missing:
        raise ValueError(f"Split input missing provenance fields: {sorted(missing)}")
    if not frame.source_is_genuine.astype(bool).all():
        raise ValueError("Iteration 13 scientific benchmark accepts genuine source rows only")
    data = frame.copy()
    data["timestamp_utc"] = pd.to_datetime(data.timestamp_utc, utc=True, errors="raise")
    data["source_row_id"] = data.apply(_row_id, axis=1)
    if data.source_row_id.duplicated().any():
        raise ValueError("Duplicate genuine source rows must be resolved before splitting")
    stations = sorted(data.station_id.astype(str).unique())
    held = {s for s in stations if int(hashlib.sha256(("i13:" + s).encode()).hexdigest()[:8], 16) % 100 < round(100*station_holdout_fraction)}
    if len(stations) >= 2 and (not held or held == set(stations)):
        held = {stations[-1]}
    dev = data.loc[~data.station_id.astype(str).isin(held)].copy()
    unseen = data.loc[data.station_id.astype(str).isin(held)].copy()
    times = dev.timestamp_utc.sort_values()
    if times.empty:
        raise ValueError("No development stations after station split")
    q70, q85 = times.quantile(.70), times.quantile(.85)
    partitions = {
        "train": dev.loc[dev.timestamp_utc <= q70].copy(),
        "validation": dev.loc[(dev.timestamp_utc > q70) & (dev.timestamp_utc <= q85)].copy(),
        "future_test": dev.loc[dev.timestamp_utc > q85].copy(),
        "unseen_station_test": unseen.copy(),
    }
    for name, part in partitions.items():
        part["benchmark_partition"] = name
    verify_no_source_overlap(partitions)
    return partitions, {"time_train_end": q70.isoformat(), "time_validation_end": q85.isoformat(),
                        "held_out_stations": sorted(held), "split_before_injection": True}


def verify_no_source_overlap(partitions: dict[str, pd.DataFrame]):
    names = list(partitions)
    ids = {name: set(part.source_row_id.astype(str)) for name, part in partitions.items()}
    for i, left in enumerate(names):
        for right in names[i+1:]:
            overlap = ids[left] & ids[right]
            if overlap:
                raise ValueError(f"Source leakage between {left} and {right}: {len(overlap)} rows")
    return True
