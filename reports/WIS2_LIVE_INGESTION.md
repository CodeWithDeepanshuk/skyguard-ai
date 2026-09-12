# IMD WIS2 Live Ingestion Receipt

Run date: 2026-09-13 IST (source timestamps in UTC)

## Measured result

- Official IMD WIS2 OGC SYNOP collection
- Station: `0-20000-0-42798`
- Requested window: previous 24 hours
- Decoded reports: **8**
- Latest report: `2026-09-12T18:00:00Z`
- Temperature: **26.8 C**
- Pressure: **1010.3 hPa**
- Relative humidity: **93.7%**, derived from observed temperature and dew point
- Observation age at retrieval: **44.5 minutes**
- Provider health latency: **1899.1 ms**

This proves the decoder path, not national completeness. The metadata registry has 432 rows; reporting coverage must be measured independently per time window.

Safeguards: WIGOS/time filtering, report-level grouping, raw SHA-256 receipt, no missing-value invention, and no Open-Meteo substitution for observed rows.

