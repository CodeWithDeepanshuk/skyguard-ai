"""Combine temporal, multivariate, and neighbour features into one row."""

from __future__ import annotations

import hashlib

from .contracts import AUDIT_COLUMNS, IDENTITY_COLUMNS, LABEL_COLUMNS, MODEL_FEATURE_COLUMNS
from .neighbors import NeighborIndex
from .temporal import TemporalFeatureBuilder


class FeatureBuilder:
    def __init__(self, temporal: TemporalFeatureBuilder, neighbors: NeighborIndex) -> None:
        self.temporal = temporal
        self.neighbors = neighbors

    def transform(self, row: dict[str, str]) -> dict[str, object]:
        identity = f"{row['split']}|{row['station_id']}|{row['timestamp_utc']}"
        temporal_features = self.temporal.transform(row)
        neighbor_features = self.neighbors.features(row)
        emitted_timestamp = temporal_features.pop("emitted_timestamp_utc")
        available_to_detector = temporal_features.pop("available_to_detector")
        output: dict[str, object] = {
            "row_id": hashlib.sha1(identity.encode("utf-8")).hexdigest()[:20],
            "station_id": row["station_id"],
            "timestamp_utc": row["timestamp_utc"],
            "emitted_timestamp_utc": emitted_timestamp,
            "split": row["split"],
            "cluster": row["cluster"],
            "evaluation_role": row["evaluation_role"],
        }
        output.update(temporal_features)
        output.update(neighbor_features)
        for column in LABEL_COLUMNS:
            output[column] = row.get(column, "")
        for column in AUDIT_COLUMNS:
            if column == "available_to_detector":
                output[column] = available_to_detector
            else:
                output[column] = row.get(column, "")

        expected = set(IDENTITY_COLUMNS + MODEL_FEATURE_COLUMNS + LABEL_COLUMNS + AUDIT_COLUMNS)
        missing = expected - set(output)
        if missing:
            raise RuntimeError(f"Feature row is missing columns: {sorted(missing)}")
        return output
