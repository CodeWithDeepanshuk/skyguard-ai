"""Centralized Configuration Loader for SkyGuard AI.

Loads versioned, auditable YAML configurations from the config/ directory.
Provides structured access to:
- spatial_qc.yaml: Concentric multi-radius thresholds, tolerances, lapse rates
- model_fusion.yaml: Ensemble weights, decision thresholds, calibration constants
- health.yaml: Sensor health degradation thresholds and penalty factors
- regional_qc.yaml: 8 Indian climate zones physical possibility envelopes
"""
from __future__ import annotations

import functools
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"

try:
    import yaml
    HAS_YAML = True
except (ImportError, ModuleNotFoundError):
    yaml = None
    HAS_YAML = False


def _load_yaml_file(filename: str, default: Dict[str, Any]) -> Dict[str, Any]:
    file_path = CONFIG_DIR / filename
    if not file_path.exists():
        return default
    if not HAS_YAML or yaml is None:
        return default
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)
            return content if isinstance(content, dict) else default
    except Exception:
        return default


@functools.lru_cache(maxsize=1)
def get_spatial_qc_config() -> Dict[str, Any]:
    """Retrieve centralized spatial QC configuration with concentric ring specifications."""
    default = {
        "version": "1.2.0",
        "tier1": {
            "radius_km": {"value": 20.0},
            "temperature_tolerance_c": {"value": 2.0},
        },
        "tier2": {
            "radius_km": {"value": 50.0},
            "temperature_tolerance_c": {"value": 3.5},
        },
        "tier3": {
            "radius_km": {"value": 100.0},
            "temperature_tolerance_c": {"value": 5.0},
        },
        "elevation_lapse_rate": {
            "lapse_rate_c_per_m": {"value": -0.0065},
        },
        "coastal": {
            "tolerance_buffer_c": {"value": 1.5},
            "cross_boundary_weight_penalty": {"value": 0.6},
        },
        "synoptic_weather": {
            "coherence_ratio_threshold": {"value": 0.50},
            "min_drop_magnitude_c": {"value": 3.0},
            "min_peer_count": {"value": 2},
        },
    }
    return _load_yaml_file("spatial_qc.yaml", default)


@functools.lru_cache(maxsize=1)
def get_model_fusion_config() -> Dict[str, Any]:
    """Retrieve centralized model fusion weights and decision thresholds."""
    default = {
        "version": "1.2.0",
        "fusion_weights": {
            "neural_reconstruction": {"value": 0.40},
            "drift_heuristic": {"value": 0.35},
            "spatial_consensus": {"value": 0.25},
        },
        "thresholds": {
            "operational_anomaly_threshold": {"value": 0.6845},
            "neural_effective_loss_offset": {"value": 1.80},
            "neural_sigmoid_scale": {"value": 2.50},
            "drift_metric_threshold": {"value": 0.95},
            "drift_sigmoid_scale": {"value": 3.00},
            "freeze_consecutive_count": {"value": 5},
            "cusum_drift_statistic_limit": {"value": 2.50},
        },
    }
    return _load_yaml_file("model_fusion.yaml", default)


@functools.lru_cache(maxsize=1)
def get_health_config() -> Dict[str, Any]:
    """Retrieve centralized sensor health scoring thresholds."""
    default = {
        "version": "1.2.0",
        "health_index": {
            "healthy_threshold": {"value": 85.0},
            "degraded_threshold": {"value": 60.0},
            "critical_threshold": {"value": 60.0},
            "rolling_window_days": {"value": 7},
            "penalties": {
                "drift_penalty_per_sigma": {"value": 12.0},
                "missing_packet_penalty_per_pct": {"value": 1.5},
                "residual_variance_penalty_per_deg": {"value": 8.0},
            },
        },
    }
    return _load_yaml_file("health.yaml", default)


@functools.lru_cache(maxsize=1)
def get_regional_qc_config() -> Dict[str, Any]:
    """Retrieve centralized regional meteorological physical possibility boundaries."""
    return _load_yaml_file("regional_qc.yaml", {})
