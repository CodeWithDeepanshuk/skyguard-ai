"""Weather data providers package for SkyGuard AI."""

from skyguard.providers.base import (
    ObservationRecord,
    ProviderName,
    RHSource,
    SourceType,
    StalenessStatus,
    WeatherProvider,
)
from skyguard.providers.imd_wis2 import IMDWIS2Provider, IMDWIS2Provider as IMDWis2Provider
from skyguard.providers.manager import WeatherProviderManager
from skyguard.providers.metar import MetarWeatherProvider
from skyguard.providers.meteostat import MeteostatWeatherProvider
from skyguard.providers.reference_weather import ReferenceWeatherProvider

__all__ = [
    "ObservationRecord",
    "SourceType",
    "ProviderName",
    "RHSource",
    "StalenessStatus",
    "WeatherProvider",
    "IMDWis2Provider",
    "MetarWeatherProvider",
    "MeteostatWeatherProvider",
    "ReferenceWeatherProvider",
    "WeatherProviderManager",
]
