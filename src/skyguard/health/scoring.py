"""Transparent sensor-health score; no unsupported remaining-life claim."""
from __future__ import annotations


def sensor_health(*, history_rows, short_term_anomaly_rate=0, long_term_anomaly_rate=0,
                  drift_score=0, noise_score=0, missingness_rate=0, frozen_rate=0,
                  residual_bias=0, residual_variance=0):
    if history_rows < 24:
        return {"health_score":None, "state":"INSUFFICIENT_HISTORY", "components":{}}
    components = {
        "short_term_anomaly": min(25, 25*max(0, short_term_anomaly_rate)),
        "long_term_anomaly": min(15, 15*max(0, long_term_anomaly_rate)),
        "drift": min(20, 20*max(0, drift_score)),
        "noise": min(10, 10*max(0, noise_score)),
        "missingness": min(15, 15*max(0, missingness_rate)),
        "frozen": min(15, 15*max(0, frozen_rate)),
        "residual_bias": min(5, 5*max(0, residual_bias)),
        "residual_variance": min(5, 5*max(0, residual_variance)),
    }
    score = max(0, 100-sum(components.values()))
    state = "HEALTHY" if score >= 85 else "WATCH" if score >= 70 else "DEGRADING" if score >= 45 else "MAINTENANCE_RECOMMENDED"
    return {"health_score":round(score,2), "state":state, "components":components,
            "remaining_useful_life":None}
