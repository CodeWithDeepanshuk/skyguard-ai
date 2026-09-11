# Iteration 10R India-vs-DWD data feasibility audit

## Scope

This report uses genuine 2022–2023 observations only. DWD is sampled at exact hourly timestamps to match the GPU notebook. No 2024/2025 observation was opened.

## Direct comparison

| Property | India NOAA/ISD corpus | DWD CDC corpus used by model |
|---|---:|---:|
| Model rows | 385,656 | 279,400 |
| Original source rows | 385,656 | 1,676,433 |
| Stations / clusters | 24 / 4 | 16 / 4 |
| Rows/station range | 3,565–34,891 | 17,341–17,520 |
| Rows/station coefficient of variation | 0.803 | 0.003 |
| Median cadence regularity | 97.22% | 99.99% |
| Worst station-year cadence regularity | 59.83% | 99.86% |
| Median full-year slot coverage | 97.55% | 99.95% |
| Worst station-year slot coverage | 11.50% | 98.31% |
| Exact-time rows with at least two neighbours | 72.98% | 100.00% |
| Median 99.9th-percentile gap/cadence ratio | 4.00x | 1.00x |
| Complete T/P/RH rows | 99.93% | 100.00% |

## Why DWD transfers more cleanly

1. DWD originates as synchronized 10-minute station observations and remains nearly uniform after hourly sampling.
2. India is a mixed archive: station cadences differ, reporting schedules change, and station row counts are highly unequal.
3. DWD clusters provide more simultaneous neighbour evidence. India often needs tolerance-based neighbour matching, increasing uncertainty and latency.
4. DWD pressure is normalized through one documented pipeline. India uses genuine station-pressure/sea-level-pressure fallbacks, so absolute or instantaneous cross-station pressure is unsafe.
5. Uniform DWD cadence makes frozen, dropout, slope and CUSUM episode lengths consistent. The same point-count rule represents different elapsed times in India.

## What can and cannot be claimed

- Injected-fault performance can be measured because the injected event boundaries and original values are known.
- Real-world India accuracy cannot be claimed from this archive alone because it has no confirmed sensor-maintenance fault labels.
- On genuine unlabelled India rows, the defensible operational measurements are false-alert rate, stability, neighbour consistency and expert-reviewed incident yield.
- Any accuracy range proposed for India is therefore a development target, not a measured real-world accuracy guarantee.
