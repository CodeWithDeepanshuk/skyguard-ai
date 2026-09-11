# Phase 10 — Live/offline dashboard and SIH demonstration

## Correct address

Start the local service with:

```powershell
python src/data/run_api.py
```

Open `http://127.0.0.1:8000/` for the SkyGuard dashboard. The `/docs` route is intentionally retained as a developer API tester and is not the judge-facing website.

## Dashboard views

The dashboard provides:

- automatic pressure-drift preview with visible data on first load;
- controls for pressure drift, regional weather, dropout, and packet errors;
- all 24 stations positioned from genuine latitude and longitude metadata;
- temperature, pressure, humidity, fault probability, event decision, and root-cause values;
- health colours, scores, status, incident count, last incident, and maintenance action;
- model and transport alert queue;
- readable explanation, rule evidence, local feature contributions, confidence, corrected value, method, and 90% interval;
- compliant Phase 10 time and unseen-station benchmark metrics;
- point precision, recall, F1, AUCPR, false-alarm rate, episode recall, and latency;
- weather protection, calibration, root-cause, correction, uncertainty, and safe-repair metrics;
- all 12 fault-type episode recalls and complete frozen JSON evidence;
- genuine NOAA/NCEI provenance, ranges, missingness, checks and scientific limitation;
- complete-path throughput, scale projection and bounded energy evidence;
- health trend, seven-day projected health and estimated maintenance horizon;
- downloadable CSV containing all 1,069 compliant time-benchmark incidents.

## Recommended 3–5 minute judge flow

1. Begin on the automatically loaded pressure-drift preview. Point out the genuine station rows, fault probability, station disagreement, and sensor-fault decisions.
2. Open the alert/explanation section. Show confidence, evidence, local feature contributions, advisory corrected value, uncertainty interval, and maintenance action.
3. Select Regional Weather and load the preview. Explain that 117 of the first 220 rows are preserved as genuine weather while only two are fault decisions.
4. Select Dropout and run to the end to show a stateful communication-gap alert backed by the packaged simulator's verified heartbeat contract. Explain that an unknown-cadence live/archive source would show an advisory instead.
5. Open Model accuracy and safety. Switch between unseen time and unseen stations, then show compliant detection, weather, diagnosis, correction, uncertainty, automatic-repair gates and full inference speed.
6. Finish with data provenance and download the incident report.

## Safety interpretation

Correction is advisory. The automatic tier is a frozen evaluation result, not a default live replacement mechanism. Only high-precision temperature and pressure cases qualify; humidity remains review-only. The dashboard states this explicitly alongside uncertainty and coverage values.
