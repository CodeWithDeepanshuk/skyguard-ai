# Live observation mode

## Source

SkyGuard uses the official AviationWeather.gov/NWS Aviation Weather Center METAR API for a configured set of Indian airport stations. METAR provides genuine terminal weather observations. The adapter records source URL, provider, product, fetch time, latest observation time, station coverage and source age.

## Variable mapping

| SkyGuard variable | Live source |
|---|---|
| Temperature | Reported METAR air temperature |
| Pressure | Reported QNH/altimeter pressure in hPa |
| Relative humidity | Derived from reported temperature and dew point using the Magnus relationship |

The UI labels this distinction. A live METAR snapshot is not described as a direct IMD AWS feed.

## Processing path

1. Fetch up to 24 hours of observations for configured ICAO stations.
2. Validate timestamps and required meteorological fields.
3. Normalize station IDs, units and source metadata.
4. Build causal temporal, multivariate and neighbour features.
5. Apply the frozen `SkyGuard-P10-compliant` event/fault and root-cause policy.
6. Run stateful physical, frozen, rate and communication checks. A gap becomes an automatic dropout fault only when the adapter supplies verified expected cadence and heartbeat SLA; otherwise it is a low-severity `unverified_data_gap` advisory.
7. Cache the verified snapshot in `data/live/latest.json`.
8. Expose status, readings and alerts to the dashboard.

## API

- `GET /api/live/status`
- `POST /api/live/refresh?hours=24`
- `GET /api/live/readings?limit=400&latest_only=false`
- `GET /api/live/alerts?limit=200&include_quality=true`

## Failure behaviour

If the public feed is unavailable, the adapter returns the last verified cache and identifies it as cached. Offline Replay remains fully functional without internet.

## Accuracy interpretation

Live observations do not include confirmed fault labels. The dashboard can produce live alerts, but their accuracy cannot be calculated from the feed alone. The project’s reported accuracy comes from the frozen, labelled 2024 time and unseen-station tests.

The current cache records `model_version`, the exact three-input detector contract, and `dew_point_used_by_detector=false`. Dew point is used only by the source adapter to calculate relative humidity when RH is not reported directly.
