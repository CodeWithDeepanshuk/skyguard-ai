"""Independent robust buddy evidence inspired by metno/titanlib.

Not a copy of Titanlib or its SCT. Uses causal existing neighbour features;
does not claim elevation-adjusted or pressure-convention-safe spatial QC.
"""
import numpy as np
import pandas as pd


SPATIAL_QC_FEATURES = (
    "qc_spatial_support",
    "qc_temperature_buddy_z",
    "qc_temperature_temporal_spatial",
    "qc_pressure_buddy_z",
    "qc_pressure_temporal_spatial",
    "qc_humidity_buddy_z",
    "qc_humidity_temporal_spatial",
)


def add_spatial_qc(frame):
    result = frame.copy()
    def col(name):
        if name not in frame.columns:
            return pd.Series(np.nan, index=frame.index, dtype=float)
        return pd.to_numeric(frame[name], errors='coerce').replace([np.inf, -np.inf], np.nan)
    # The nearest distance alone cannot guarantee all buddies are local. Do not
    # call these robust residuals a geographically validated buddy test.
    supported = (col('neighbor_station_count') >= 2) & (col('neighbor_max_age_minutes') <= 60)
    result['qc_spatial_support'] = supported.astype('int8')
    for sensor, floor in [('temperature', 1.0), ('pressure', 2.0), ('humidity', 5.0)]:
        count = col(f'neighbor_{sensor}_count')
        residual = col(f'neighbor_{sensor}_residual')
        scale = (1.4826 * col(f'neighbor_{sensor}_mad').abs()).clip(lower=floor)
        score = (residual / scale).where(supported & (count >= 2))
        result[f'qc_{sensor}_buddy_z'] = score.clip(-30, 30)
        result[f'qc_{sensor}_temporal_spatial'] = np.minimum(score.abs(), col(f'{sensor}_robust_z_24h').abs()).clip(0, 30)
    return result
