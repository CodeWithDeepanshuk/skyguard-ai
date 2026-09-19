"""Ingestion services for SkyGuard AI."""
from skyguard.ingestion.service import IngestionService
from skyguard.ingestion.open_meteo import OpenMeteoIngestionService

__all__ = ["IngestionService", "OpenMeteoIngestionService"]
