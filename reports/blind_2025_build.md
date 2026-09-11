# SkyGuard Blind 2025 benchmark build

**Ready for one-time evaluation: YES**

- Official source: NOAA/NCEI Global Hourly legacy compatibility files
- Sealed interval: 2025-01-01 through 2025-08-24
- Normalized rows: 124,819
- Prior benchmark row overlap: 0
- Final models executed during build: no

## Checks

| Check | Result |
|---|---|
| all 24 stations present | PASS |
| minimum 900 rows per station | PASS |
| all stations start on january 1 | PASS |
| all stations reach august 24 | PASS |
| no normalized duplicate timestamps | PASS |
| temperature missing below 0 1 percent | PASS |
| humidity missing below 0 1 percent | PASS |
| pressure missing below 5 percent | PASS |
| episode ids unique | PASS |
| all fault types in both tests | PASS |
| weather cases in both tests | PASS |
| blind rows do not overlap prior benchmarks | PASS |
| phase10 input contract intact | PASS |
| final models not executed | PASS |

The benchmark must be opened once using the frozen comparison notebook. No policy or threshold may be changed after scoring.
