"""Explainable causal hybrid detector used by the Iteration 13 benchmark."""
from __future__ import annotations

import math
import numpy as np
import pandas as pd

SENSORS = ("temperature", "pressure", "humidity")
COLUMNS = {"temperature":"temperature_c", "pressure":"pressure_hpa", "humidity":"relative_humidity_pct"}
LIMITS = {"temperature":(-60,65), "pressure":(850,1100), "humidity":(0,100)}
MIN_SCALE = {"temperature":.3, "pressure":.5, "humidity":2.0}


def _haversine(lat1, lon1, lat2, lon2):
    a, b, c, d = map(np.radians, [lat1, lon1, lat2, lon2])
    q = np.sin((c-a)/2)**2 + np.cos(a)*np.cos(c)*np.sin((d-b)/2)**2
    return 6371*2*np.arcsin(np.sqrt(np.clip(q, 0, 1)))


def add_spatial_context(frame: pd.DataFrame, radius_km=150, min_neighbors=2, max_neighbors=8):
    """Exact-timestamp robust neighbour deltas; no future/asynchronous interpolation."""
    data = frame.copy()
    data["timestamp_utc"] = pd.to_datetime(data.timestamp_utc, utc=True, errors="coerce")
    meta = data.groupby("station_id", sort=True)[["latitude","longitude"]].median().dropna()
    graph = {}
    for station, row in meta.iterrows():
        options=[]
        for other, candidate in meta.iterrows():
            if other == station: continue
            km=float(_haversine(row.latitude,row.longitude,candidate.latitude,candidate.longitude))
            if km <= radius_km: options.append((str(other),km))
        graph[str(station)] = [s for s,_ in sorted(options,key=lambda x:x[1])[:max_neighbors]]
    indexed={(str(r.station_id),r.timestamp_utc):r for r in data.itertuples()}
    coherence=[]; disagreement=[]; available=[]; counts=[]
    for row in data.itertuples():
        peers=[indexed[(s,row.timestamp_utc)] for s in graph.get(str(row.station_id),[]) if (s,row.timestamp_utc) in indexed]
        counts.append(len(peers)); available.append(len(peers)>=min_neighbors)
        support=[]; residuals=[]
        for sensor,col in COLUMNS.items():
            target=getattr(row,f"{sensor}_delta",np.nan)
            vals=np.array([getattr(p,f"{sensor}_delta",np.nan) for p in peers],float)
            vals=vals[np.isfinite(vals)]
            if len(vals)>=min_neighbors and np.isfinite(target):
                center=float(np.median(vals)); mad=float(np.median(np.abs(vals-center)))
                scale=max(1.4826*mad,MIN_SCALE[sensor])
                z=abs(target-center)/scale
                residuals.append(min(1,z/6)); support.append(float(np.mean(np.abs(vals-target)<=2.5*scale)))
        coherence.append(float(np.mean(support)) if support else np.nan)
        disagreement.append(float(max(residuals)) if residuals else 0.0)
    data["neighbor_count"] = counts
    data["spatial_context_available"] = available
    data["spatial_coherence_score"] = coherence
    data["spatial_disagreement_score"] = disagreement
    return data


def _run_lengths(values, tolerance):
    result = np.ones(len(values), dtype=int)
    for i in range(1, len(values)):
        a, b = values[i-1], values[i]
        result[i] = result[i-1]+1 if np.isfinite(a) and np.isfinite(b) and abs(a-b) <= tolerance else 1
    return result


def add_causal_features(frame: pd.DataFrame, window=24):
    data = frame.copy()
    data["timestamp_utc"] = pd.to_datetime(data.timestamp_utc, utc=True, errors="coerce")
    data = data.sort_values(["station_id","timestamp_utc"], kind="stable").reset_index(drop=True)
    pieces = []
    for _, group in data.groupby("station_id", sort=False):
        g = group.copy()
        for sensor, col in COLUMNS.items():
            x = pd.to_numeric(g[col], errors="coerce")
            prior = x.shift(1)
            history = prior.rolling(window, min_periods=4)
            med = history.median()
            mad = prior.rolling(window, min_periods=4).apply(lambda a: np.nanmedian(np.abs(a-np.nanmedian(a))), raw=True)
            q75, q25 = history.quantile(.75), history.quantile(.25)
            scale = np.maximum(1.4826*mad, MIN_SCALE[sensor])
            g[f"{sensor}_lag1"] = prior
            g[f"{sensor}_delta"] = x-prior
            g[f"{sensor}_second_difference"] = (x-prior)-(prior-prior.shift(1))
            g[f"{sensor}_rolling_median"] = med
            g[f"{sensor}_rolling_mad"] = mad
            g[f"{sensor}_rolling_iqr"] = q75-q25
            g[f"{sensor}_rolling_variance"] = history.var()
            g[f"{sensor}_robust_z"] = (x-med)/scale
            g[f"{sensor}_rolling_slope"] = (prior-prior.shift(min(window-1, 6)))/min(window-1, 6)
            g[f"{sensor}_frozen_run"] = _run_lengths(x.to_numpy(float), MIN_SCALE[sensor]/5)
            g[f"{sensor}_past_variability"] = history.std()
            residual = (x-med).fillna(0)
            g[f"{sensor}_cusum"] = residual.ewm(alpha=.08, adjust=False).mean()/scale
        pieces.append(g)
    data = pd.concat(pieces, ignore_index=True)
    hour = data.timestamp_utc.dt.hour + data.timestamp_utc.dt.minute/60
    doy = data.timestamp_utc.dt.dayofyear
    data["hour_sin"], data["hour_cos"] = np.sin(2*np.pi*hour/24), np.cos(2*np.pi*hour/24)
    data["day_sin"], data["day_cos"] = np.sin(2*np.pi*doy/365.25), np.cos(2*np.pi*doy/365.25)
    return data


def analyze_row(row):
    reasons, scores = [], []
    affected = []
    missing = []
    for sensor, col in COLUMNS.items():
        try: value = float(row.get(col, np.nan))
        except (TypeError, ValueError): value = np.nan
        low, high = LIMITS[sensor]
        if not np.isfinite(value):
            missing.append(sensor); scores.append(1.0); reasons.append(f"{sensor.upper()}_MISSING_OR_MALFORMED")
        elif not low <= value <= high:
            affected.append(sensor); scores.append(1.0); reasons.append(f"{sensor.upper()}_PHYSICAL_RANGE")
        z = abs(float(row.get(f"{sensor}_robust_z", 0) or 0))
        if np.isfinite(z) and z >= 3:
            affected.append(sensor); scores.append(min(1, z/8)); reasons.append(f"{sensor.upper()}_TEMPORAL_RESIDUAL_HIGH")
        frozen = float(row.get(f"{sensor}_frozen_run", 1) or 1)
        variability = float(row.get(f"{sensor}_past_variability", np.nan) or np.nan)
        frozen_probability = 0.0
        if frozen >= 8 and np.isfinite(variability) and variability > MIN_SCALE[sensor]:
            frozen_probability = min(.98, .45+.05*frozen)
            affected.append(sensor); scores.append(frozen_probability); reasons.append(f"{sensor.upper()}_FROZEN_WITH_EXPECTED_VARIABILITY")
        drift = abs(float(row.get(f"{sensor}_cusum", 0) or 0))
        if np.isfinite(drift) and drift >= 2:
            affected.append(sensor); scores.append(min(.95, drift/6)); reasons.append(f"{sensor.upper()}_CUSUM_DRIFT")
    spatial_available = bool(row.get("spatial_context_available", False))
    coherence = float(row.get("spatial_coherence_score", np.nan) or np.nan)
    isolated = float(row.get("spatial_disagreement_score", 0) or 0)
    base = max(scores, default=0.02)
    possible_event = bool(spatial_available and np.isfinite(coherence) and coherence >= .7 and not missing)
    if possible_event:
        probability = min(base, max(.02, base*(1-.65*coherence)))
        reasons.append("NEIGHBOURS_SUPPORT_COHERENT_CHANGE")
    else:
        probability = min(1, base + (.2*isolated if spatial_available else 0))
        if spatial_available and isolated >= .6: reasons.append("NEIGHBOR_DISAGREEMENT")
    if missing: root = "COMMUNICATION_OR_DATA_FIELD_ERROR"
    elif any("FROZEN" in r for r in reasons): root = "FROZEN_SENSOR_SIGNATURE"
    elif any("CUSUM" in r for r in reasons): root = "CALIBRATION_DRIFT_SIGNATURE"
    elif any("PHYSICAL_RANGE" in r for r in reasons): root = "DATA_CORRUPTION_OR_SENSOR_RANGE_ERROR"
    elif probability >= .5: root = "ROOT_CAUSE_UNCERTAIN"
    else: root = "NONE"
    persistence = max([float(row.get(f"{s}_frozen_run",1) or 1) for s in SENSORS])
    impact = probability + .06*len(set(affected)) + min(.15, persistence/100)
    severity = "CRITICAL" if impact >= 1.0 else "HIGH" if impact >= .8 else "MEDIUM" if impact >= .55 else "LOW" if impact >= .25 else "INFO"
    return {"is_anomaly":probability >= .5, "anomaly_probability":round(probability,6),
            "confidence_calibrated":False, "severity":severity, "root_cause":root,
            "affected_parameters":sorted(set(affected+missing)), "reason_codes":reasons,
            "spatial_context_available":spatial_available,
            "possible_genuine_meteorological_event":possible_event,
            "explanation":"; ".join(reasons) if reasons else "No validated anomaly trigger."}


def analyze_frame(frame):
    featured = add_spatial_context(add_causal_features(frame))
    decisions = pd.DataFrame([analyze_row(row) for row in featured.to_dict("records")])
    return pd.concat([featured.reset_index(drop=True), decisions], axis=1)
