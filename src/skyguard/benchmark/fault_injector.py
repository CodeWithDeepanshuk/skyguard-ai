"""Controlled fault injection into copies of genuine observations only."""
from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import numpy as np
import pandas as pd

SENSORS = ("temperature_c", "pressure_hpa", "relative_humidity_pct")
FAULT_TYPES = ("spike", "frozen_sensor", "missing_block", "calibration_drift",
               "step_bias", "noise_burst_or_power_related_signature", "data_corruption",
               "multisensor_inconsistency", "slow_sensor_degradation")
SEVERITIES = ("subtle", "moderate", "severe")
BASE_SCALES = {"temperature_c": .5, "pressure_hpa": .8, "relative_humidity_pct": 3.0}


@dataclass(frozen=True)
class InjectionConfig:
    events_per_type: int = 3
    seed: int = 42
    minimum_event_steps: int = 4
    maximum_event_steps: int = 96


def _local_scale(group, sensor, start):
    history = pd.to_numeric(group.loc[:max(start-1, 0), sensor], errors="coerce").tail(168)
    med = history.median()
    mad = (history-med).abs().median()
    iqr = history.quantile(.75)-history.quantile(.25)
    return max(BASE_SCALES[sensor], float(1.4826*mad) if pd.notna(mad) else 0,
               float(iqr/1.349) if pd.notna(iqr) else 0)


def inject_partition(frame: pd.DataFrame, partition: str, config=InjectionConfig()):
    required = {"station_id", "timestamp_utc", "source_row_id", "source_snapshot_hash",
                "source_is_genuine", *SENSORS}
    missing = required - set(frame)
    if missing:
        raise ValueError(f"Injection input missing: {sorted(missing)}")
    if not frame.source_is_genuine.astype(bool).all():
        raise ValueError("Faults may be injected only into copies of genuine source rows")
    out = frame.sort_values(["station_id", "timestamp_utc"], kind="stable").reset_index(drop=True).copy(deep=True)
    for sensor in SENSORS:
        out[f"original_{sensor}"] = out[sensor]
    out["observation_modified"] = False
    out["injection_applied"] = False
    out["fault_type"] = "none"
    out["fault_parameters"] = "{}"
    out["original_value"] = "{}"
    out["modified_value"] = "{}"
    out["injection_seed"] = pd.Series([pd.NA]*len(out), dtype="Int64")
    out["fault_severity"] = "none"
    out["episode_id"] = ""
    out["stream_action"] = "emit"
    rng = np.random.default_rng(config.seed)
    reserved = np.zeros(len(out), dtype=bool)
    groups = {str(s): idx.to_numpy() for s, idx in out.groupby("station_id", sort=True).groups.items() if len(idx) >= config.minimum_event_steps+8}
    if not groups:
        raise ValueError("NOT ENOUGH GENUINE TEMPORAL DATA FOR THIS EXPERIMENT")
    events = []
    counter = 0
    severity_factor = {"subtle": 2.0, "moderate": 4.0, "severe": 8.0}
    for fault in FAULT_TYPES:
        for event_number in range(config.events_per_type):
            severity = SEVERITIES[(event_number + list(FAULT_TYPES).index(fault)) % 3]
            selected = None
            for _ in range(500):
                station = rng.choice(sorted(groups))
                indices = groups[station]
                if fault in {"spike", "data_corruption", "multisensor_inconsistency"}:
                    duration = 1
                else:
                    severity_duration = {"subtle":8, "moderate":24, "severe":72}[severity]
                    upper = min(config.maximum_event_steps, len(indices)//3, severity_duration)
                    lower = min(config.minimum_event_steps, upper)
                    duration = int(rng.integers(lower, upper+1))
                start_pos = int(rng.integers(4, len(indices)-duration+1))
                candidate = indices[start_pos:start_pos+duration]
                if not reserved[candidate].any() and out.loc[candidate, list(SENSORS)].notna().all(axis=None):
                    selected = (station, candidate, start_pos)
                    break
            if selected is None:
                continue
            station, indices, start_pos = selected
            sensor = SENSORS[int(rng.integers(0, len(SENSORS)))]
            group = out.loc[groups[station]].reset_index(drop=True)
            scale = _local_scale(group, sensor, start_pos)
            sign = int(rng.choice([-1, 1]))
            factor = severity_factor[severity]
            params = {"parameter": sensor, "severity": severity, "duration_steps": len(indices),
                      "local_scale": scale, "direction": sign}
            original = pd.to_numeric(out.loc[indices, sensor], errors="coerce").to_numpy(float)
            if fault == "spike":
                out.loc[indices, sensor] = original + sign*factor*scale
            elif fault == "frozen_sensor":
                out.loc[indices, sensor] = original[0]
            elif fault == "missing_block":
                out.loc[indices, list(SENSORS)] = np.nan
                out.loc[indices, "stream_action"] = "missing"
            elif fault in {"calibration_drift", "slow_sensor_degradation"}:
                end = factor*scale*(.5 if fault.startswith("slow") else 1.0)
                out.loc[indices, sensor] = original + sign*np.linspace(0, end, len(indices))
                if fault.startswith("slow"):
                    out.loc[indices, sensor] += rng.normal(0, np.linspace(0, scale, len(indices)))
            elif fault == "step_bias":
                out.loc[indices, sensor] = original + sign*factor*scale
            elif fault == "noise_burst_or_power_related_signature":
                out.loc[indices, sensor] = original + rng.normal(0, factor*scale, len(indices))
            elif fault == "data_corruption":
                bad = {"temperature_c": 9999.0, "pressure_hpa": -999.0, "relative_humidity_pct": 180.0}[sensor]
                out.loc[indices, sensor] = bad
            elif fault == "multisensor_inconsistency":
                # Values can remain individually plausible while their joint movement is unusual.
                out.loc[indices, "temperature_c"] = np.clip(pd.to_numeric(out.loc[indices,"temperature_c"])+factor, -50, 60)
                out.loc[indices, "relative_humidity_pct"] = np.clip(pd.to_numeric(out.loc[indices,"relative_humidity_pct"])+factor*4, 0, 100)
                out.loc[indices, "pressure_hpa"] = np.clip(pd.to_numeric(out.loc[indices,"pressure_hpa"])-factor*2, 850, 1100)
                params["parameter"] = "temperature_c,pressure_hpa,relative_humidity_pct"
            counter += 1
            episode_id = f"{partition}-I13-{counter:04d}"
            out.loc[indices, "observation_modified"] = True
            out.loc[indices, "injection_applied"] = True
            out.loc[indices, "fault_type"] = fault
            out.loc[indices, "fault_parameters"] = json.dumps(params, sort_keys=True)
            changed_sensors = list(SENSORS) if fault in {"missing_block","multisensor_inconsistency"} else [sensor]
            for index in indices:
                out.at[index,"original_value"] = json.dumps({s:None if pd.isna(out.at[index,f"original_{s}"]) else float(out.at[index,f"original_{s}"]) for s in changed_sensors},sort_keys=True)
                out.at[index,"modified_value"] = json.dumps({s:None if pd.isna(out.at[index,s]) else float(out.at[index,s]) for s in changed_sensors},sort_keys=True)
            out.loc[indices, "injection_seed"] = config.seed
            out.loc[indices, "fault_severity"] = severity
            out.loc[indices, "episode_id"] = episode_id
            reserved[indices] = True
            events.append({"partition":partition, "episode_id":episode_id, "fault_type":fault,
                           "severity":severity, "station_id":station, "start_utc":str(out.loc[indices[0],"timestamp_utc"]),
                           "end_utc":str(out.loc[indices[-1],"timestamp_utc"]), "affected_rows":len(indices),
                           "injection_seed":config.seed, "fault_parameters":json.dumps(params, sort_keys=True),
                           "source_row_ids":",".join(out.loc[indices,"source_row_id"].astype(str))})
    out["benchmark_label"] = out.injection_applied.astype(int)
    assert out.loc[~out.injection_applied, list(SENSORS)].equals(out.loc[~out.injection_applied, [f"original_{s}" for s in SENSORS]].set_axis(SENSORS, axis=1))
    return out, pd.DataFrame(events), asdict(config)
