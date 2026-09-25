"""Provider-priority ingestion orchestration with receipts and backoff."""

from __future__ import annotations

import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Optional

from skyguard.ingestion.identity import StationIdentityResolver
from skyguard.providers.base import ObservationRecord, PressureType, SourceType
from skyguard.providers.imd_api import IMDAWSAPIProvider
from skyguard.providers.imd_fixture import IMDFixtureProvider
from skyguard.providers.imd_wis2 import IMDWIS2Provider
from skyguard.providers.metar import MetarWeatherProvider
from skyguard.storage import ObservationStore


ROOT = Path(__file__).resolve().parents[3]


class IngestionService:
    """Collect direct observations in priority order and persist idempotently."""

    def __init__(
        self,
        store: Optional[ObservationStore] = None,
        *,
        root: Path = ROOT,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.root = root
        self.store = store or ObservationStore(root=root)
        self.resolver = StationIdentityResolver(root)
        self.sleep = sleep
        self.imd_api = IMDAWSAPIProvider()
        self.imd_fixture = IMDFixtureProvider(root=root)
        self.wis2 = IMDWIS2Provider(timeout=int(os.getenv("WIS2_TIMEOUT_SECONDS", "30")))
        self.metar = MetarWeatherProvider(timeout_seconds=float(os.getenv("METAR_TIMEOUT_SECONDS", "15")))

    @staticmethod
    def _validate(record: ObservationRecord) -> None:
        if record.source_type != SourceType.OBSERVED.value or not record.is_direct_observation:
            raise ValueError("Only direct physical observations belong in the operational observation store")
        if record.is_model_field or record.is_interpolated:
            raise ValueError("Reference/model fields cannot be persisted as station observations")
        if not (5.0 <= record.latitude <= 40.0 and 65.0 <= record.longitude <= 100.0):
            raise ValueError("Observation coordinates fall outside the configured India domain")
        if all(value is None for value in (
            record.temperature_c, record.pressure_hpa, record.relative_humidity_pct
        )):
            raise ValueError("Observation contains none of the three allowed meteorological parameters")
        if record.pressure_hpa is not None and record.pressure_type == PressureType.UNKNOWN.value:
            # Unknown semantics are retained for audit/history, but downstream
            # spatial pressure QC must refuse them.
            record.source_quality_flags = (*record.source_quality_flags, "PRESSURE_SPATIAL_QC_DISABLED")

    def _fetch_with_retry(
        self, provider: str, fetch: Callable[[], list[ObservationRecord]], *, attempts: int = 3,
    ) -> list[ObservationRecord]:
        last_error: Optional[Exception] = None
        for attempt in range(attempts):
            try:
                return fetch()
            except Exception as exc:  # provider/network boundary
                last_error = exc
                if attempt + 1 < attempts:
                    delay = min(12.0, (2.0 ** attempt) + random.uniform(0.05, 0.45))
                    self.sleep(delay)
        raise RuntimeError(f"{provider} ingestion failed after {attempts} attempts: {last_error}")

    def _run_provider(
        self,
        provider: str,
        fetch: Callable[[], list[ObservationRecord]],
        *,
        minimum_interval_seconds: int,
    ) -> dict[str, object]:
        latest = self.store.latest_run(provider)
        if latest and latest.get("status") == "SUCCESS":
            started = datetime.fromisoformat(str(latest["started_at_utc"]).replace("Z", "+00:00"))
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - started.astimezone(timezone.utc)).total_seconds()
            if age < minimum_interval_seconds:
                return {
                    "provider": provider, "status": "SKIPPED_RATE_LIMIT",
                    "retry_after_seconds": int(minimum_interval_seconds - age),
                }

        run_id = self.store.begin_run(provider, {"minimum_interval_seconds": minimum_interval_seconds})
        try:
            fetched = self._fetch_with_retry(provider, fetch)
            accepted: list[ObservationRecord] = []
            dead_letters = 0
            for raw_record in fetched:
                try:
                    record = self.resolver.resolve(raw_record)
                    self._validate(record)
                    accepted.append(record)
                except Exception as exc:
                    dead_letters += 1
                    self.store.record_dead_letter(provider, str(exc), raw_record.to_dict(include_raw=True))
            receipt = self.store.append(accepted)
            watermark = max((row.timestamp_utc for row in accepted), default="")
            if watermark:
                self.store.set_watermark(provider, watermark, {
                    "fetched": len(fetched), "accepted": len(accepted),
                })
            self.store.finish_run(
                run_id, status="SUCCESS", fetched_count=len(fetched),
                inserted_count=receipt["inserted"], duplicate_count=receipt["duplicates"],
                dead_letter_count=dead_letters,
                metadata={"watermark_utc": watermark},
            )
            if latest and latest.get("status") == "FAILED":
                self.store.record_source_event(provider, "SOURCE_RECOVERED", {"run_id": run_id})
            return {
                "provider": provider, "status": "SUCCESS", "run_id": run_id,
                **receipt, "dead_letters": dead_letters, "watermark_utc": watermark,
            }
        except Exception as exc:
            self.store.finish_run(run_id, status="FAILED", error_message=str(exc))
            self.store.record_source_event(provider, "SOURCE_OUTAGE", {"run_id": run_id, "error": str(exc)})
            return {"provider": provider, "status": "FAILED", "run_id": run_id, "error": str(exc)}

    def run_once(self, providers: Optional[Iterable[str]] = None) -> dict[str, object]:
        requested = {item.strip().upper() for item in (providers or ("IMD_API", "WIS2", "METAR"))}
        results: list[dict[str, object]] = []
        if "IMD_API" in requested or "IMD_AWS" in requested:
            if self.imd_api.configured:
                configured_interval = os.getenv("IMD_API_MIN_INTERVAL_SECONDS", "").strip()
                if not configured_interval:
                    results.append({
                        "provider": "IMD_AWS",
                        "status": "POLLING_DISABLED_PENDING_DOCUMENTED_REQUEST_LIMIT",
                    })
                else:
                    results.append(self._run_provider(
                        "IMD_AWS", self.imd_api.fetch_network,
                        minimum_interval_seconds=max(1, int(configured_interval)),
                    ))
            else:
                # Never substitute a fixture or another provider for failed IMD.
                results.append({
                    "provider": "IMD_AWS",
                    "status": "NORMALIZATION_DISABLED_PENDING_REAL_SCHEMA_REVIEW",
                })
        if "WIS2" in requested:
            lookback = max(1, min(24, int(os.getenv("WIS2_LOOKBACK_HOURS", "6"))))
            pages = max(1, min(50, int(os.getenv("WIS2_MAX_PAGES", "20"))))
            results.append(self._run_provider(
                "IMD_WIS2",
                lambda: self.wis2.fetch_network_history(lookback, pages)[0],
                minimum_interval_seconds=int(os.getenv("WIS2_MIN_INTERVAL_SECONDS", "1800")),
            ))
        if "METAR" in requested:
            results.append(self._run_provider(
                "METAR", lambda: self.metar.fetch_network_history(hours=6),
                minimum_interval_seconds=int(os.getenv("METAR_MIN_INTERVAL_SECONDS", "900")),
            ))
        return {
            "status": "COMPLETE",
            "results": results,
            "ingestion_health": self.store.ingestion_health(),
        }
