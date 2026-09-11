# SkyGuard AI data readiness

## Final benchmark scope

- Provider: NOAA/NCEI
- Product: Global Hourly / Integrated Surface Database (ISD)
- Years: 2022, 2023, 2024
- Regional clusters: Delhi, Hyderabad, Bengaluru, Chennai
- Stations: 24, six per cluster
- Observation files: 72
- Supporting official files: station inventory and ISD format documentation
- Files in SHA-256 manifest: 74
- Raw bytes covered by manifest: 257,260,122
- Processed rows: 578,448
- Clean candidate rows: 569,633 (98.4761%)

## Validation results

- Official NCEI source URLs only: pass
- Every expected file present: pass
- SHA-256 integrity checks: pass
- Station IDs and coordinates match official inventory: pass
- Raw and processed schemas: pass
- All 24 stations and three years present: pass
- At least 1,500 rows for every station-year: pass
- Duplicate processed station/timestamps: zero
- Missing temperature: 0.0180%
- Missing derived humidity: 0.0425%
- Missing pressure: 1.4900%
- Physical-bound violations in the final cohort: zero

The generated details are in `reports/data_validation.md` and `reports/data_validation.json`.

## Variables

- Temperature is decoded from NOAA `TMP` and converted from tenths of °C.
- Dew point is decoded from `DEW` and used to calculate relative humidity with the Magnus approximation.
- Pressure prefers NOAA sea-level pressure `SLP`; when unavailable, it uses the first `MA1` altimeter-pressure value. `pressure_source` records which one was used.
- NOAA quality codes are preserved for temperature, dew point, and pressure.

Relative humidity is derived rather than directly observed in this corpus. This must be stated in the SIH report and dashboard.

## Fixed modelling split

| Purpose | Data |
|---|---|
| Train | Development stations, 2022 |
| Tune/validate | Development stations, 2023 |
| Time generalization test | Development stations, 2024 |
| Station generalization test | Hisar, Ramagundam, Chitradurga, Pondicherry across all years, with 2024 as final reporting period |

## What is still generated rather than downloaded

The official observations do not include trustworthy confirmed sensor-fault labels. The next phase must create controlled synthetic faults on clean real observations. This is methodologically valid when the original value, injected value, episode boundaries, and random seed are preserved, but the final presentation must not describe synthetic faults as real historical failures.

No IMD-private data, ERA5 credentials, field surveys, or commercial feeds are required for the planned benchmark and offline demonstration.
