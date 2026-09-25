# SkyGuard AI — Data Integrity & Unsupported Results Audit
**Document Version:** 1.0.0-INTEGRITY  
**Date:** 2026-09-24  
**Audit Scope:** Full codebase scan for hard-coded accuracy, fabricated confidence values, synthetic time-series generators, silent fallbacks, uncalibrated probabilities, and simulated data presented as real IMD observations.

---

## 1. Executive Summary

This audit catalog documents every confirmed instance of:
- **Hard-Coded Metrics & Accuracy**: Fabricated model benchmarks (e.g., `accuracy: 0.984`, `precision: 0.9955`) returned directly in JSON endpoints.
- **Synthetic Time-Series Generation**: Programmatic sine-wave generators manufacturing 24 hours of fake hourly observations (`tempDiurnal`, `pressTide`, `rhDiurnal`) for station history.
- **Hard-Coded Fallback Scores**: Repeated arbitrary magic numbers (`0.884`, `0.024`, `0.95`, `0.439`) injected into the UI when backend models fail or abstain.
- **Silent Data Substitution**: Substituting Open-Meteo numerical weather forecasts into observation fields when genuine AWS observations are missing.
- **Fabricated Explanations & Evidence**: Synthetic strings and default bullet points rendered when true diagnostic evidence is absent.
- **Synthetic Fault Injections Presented as Labeled Datasets**: Synthetic faults on NOAA ISD data treated as validated ground-truth anomaly datasets.

---

## 2. Granular Inventory of Integrity Violations

### Category A: Hard-Coded Metrics & Model Accuracy

#### 1. Backend Dashboard Summary Hard-Coded Metrics
* **File:** [`src/skyguard/api/app.py`](file:///c:/Users/deepa/OneDrive/Desktop/Sih%2073/src/skyguard/api/app.py)
* **Line:** 120–145
* **Code:**
  ```python
  "event_decision": {
      "accuracy": 0.984,
      "weather_false_positive_rate": conf.get("weather_to_fault_rate", 0.0045),
      "genuine_weather_f1": conf.get("weather_f1", 0.88),
      "per_class": {
          "genuine_weather": {
              "precision": 0.9955,
              "recall": 0.88,
              "f1": conf.get("weather_f1", 0.88),
          }
      },
  }
  ```
* **Purpose:** Returns a fixed `accuracy: 0.984` (98.4%) and `precision: 0.9955` (99.55%) in the `/api/status` endpoint to make the model appear exceptionally accurate to judges.
* **Classification:** **UNSAFE** (Fabricated accuracy claims).
* **Action Required:** Remove hard-coded numbers completely. Only return empirical metrics computed from reproducible, logged experiment runs.

---

### Category B: Synthetic Time-Series Generation

#### 2. Programmatic Hourly Sine-Wave Generator for Station History
* **File:** [`src/app/api/stations/[id]/route.ts`](file:///c:/Users/deepa/OneDrive/Desktop/Sih%2073/src/app/api/stations/%5Bid%5D/route.ts)
* **Line:** 141–177
* **Code:**
  ```typescript
  for (let i = 23; i >= 0; i--) {
    const pointTime = new Date(baseTimestamp - i * 3600 * 1000);
    const hour = pointTime.getUTCHours();
    const solarPhase = ((hour - 9) / 24) * 2 * Math.PI;
    const tempDiurnal = Math.sin(solarPhase) * 3.5;
    const pressTide = Math.cos(((hour - 4) / 12) * 2 * Math.PI) * 1.2;
    const rhDiurnal = -Math.sin(solarPhase) * 12.0;

    const neighTemp = Math.round((baseTemp + tempDiurnal) * 10) / 10;
    const neighPress = Math.round((basePress + pressTide) * 10) / 10;
    const neighRh = Math.round(Math.min(99, Math.max(15, baseRh + rhDiurnal)));

    const obsTemp = isTempFault ? Math.round((baseTemp + 4.5 + tempDiurnal) * 10) / 10 : ...;
    const obsPress = isPressureFault ? Math.round((basePress + 6.2 + pressTide) * 10) / 10 : ...;
    ...
  }
  ```
* **Purpose:** When the backend does not have historical hourly readings for an AWS station, this Next.js API route manufactures 24 fake hourly points using sine and cosine waves to fill the chart!
* **Classification:** **CRITICALLY UNSAFE** (Inventing fake weather readings).
* **Action Required:** Completely delete this synthetic generator. If the observation store does not contain historical observations for the requested hours, return an empty array with status `NO_HISTORICAL_DATA` and display an honest empty state in the chart.

---

### Category C: Hard-Coded Fallback Anomaly Scores & Confidences

#### 3. Magic Fallback Anomaly Score `0.884` in Station Drawer
* **File:** [`src/components/station/StationDrawer.tsx`](file:///c:/Users/deepa/OneDrive/Desktop/Sih%2073/src/components/station/StationDrawer.tsx)
* **Line:** 93–99
* **Code:**
  ```typescript
  const anomalyScoreVal = assessment?.anomaly_score != null && Number(assessment.anomaly_score) > 0.001
    ? Number(assessment.anomaly_score)
    : (station.anomaly_score != null && Number(station.anomaly_score) > 0.001 
        ? Number(station.anomaly_score) 
        : (isAnomalous ? 0.884 : 0.024));
  ```
* **Purpose:** If the station does not have an evaluated anomaly score, it forces `0.884` for anomalous stations and `0.024` for normal stations.
* **Classification:** **UNSAFE** (Hard-coded anomaly scores).
* **Action Required:** Remove `0.884` and `0.024` fallbacks. If no score was produced by the engine, display `null` or `INSUFFICIENT_EVIDENCE`.

#### 4. Magic Fallback Anomaly Score `0.884` in Station Detail API Route
* **File:** [`src/app/api/stations/[id]/route.ts`](file:///c:/Users/deepa/OneDrive/Desktop/Sih%2073/src/app/api/stations/%5Bid%5D/route.ts)
* **Line:** 118–124
* **Code:**
  ```typescript
  const anomalyScore = typeof station.anomaly_score === 'number'
    ? station.anomaly_score
    : isAnomalous
    ? 0.884
    : isWeather
    ? 0.420
    : 0.032;
  ```
* **Purpose:** Forces `0.884` (fault), `0.420` (weather), or `0.032` (normal) as default anomaly scores.
* **Classification:** **UNSAFE** (Hard-coded anomaly scores).
* **Action Required:** Remove hard-coded values; report actual score from the backend operational store.

#### 5. Magic Fallback Anomaly Score `0.884` in Live Data Layer
* **File:** [`src/server/liveData.ts`](file:///c:/Users/deepa/OneDrive/Desktop/Sih%2073/src/server/liveData.ts)
* **Line:** 172 & 389
* **Code:**
  ```typescript
  : (decision === 'sensor_fault' ? 0.884 : 0.024);
  const scoreVal = Number(r.anomaly_score ?? r.fault_probability ?? (isFault ? 0.884 : 0.439));
  ```
* **Purpose:** Injects `0.884` into the incident list if the backend did not emit a score.
* **Classification:** **UNSAFE** (Hard-coded anomaly scores).
* **Action Required:** Eliminate fallback constants. Return only verified model outputs.

#### 6. Floor Threshold `0.8840` in Deep Ensemble Model
* **File:** [`src/skyguard/models/deep_ensemble.py`](file:///c:/Users/deepa/OneDrive/Desktop/Sih%2073/src/skyguard/models/deep_ensemble.py)
* **Line:** 394
* **Code:**
  ```python
  evidence_score = max(evidence_score, 0.8840)
  ```
* **Purpose:** Artificially bumps any detected fault evidence score up to at least `0.8840`.
* **Classification:** **UNSAFE** (Forcing model score magnitude).
* **Action Required:** Remove arbitrary floor clamping. Let the statistical or calibrated model produce its true score.

#### 7. Default 95% Confidence Fallback in Incidents Feed
* **File:** [`src/server/liveData.ts`](file:///c:/Users/deepa/OneDrive/Desktop/Sih%2073/src/server/liveData.ts)
* **Line:** 444–445
* **Code:**
  ```typescript
  confidence: typeof r.fault_probability === 'number' ? r.fault_probability : (r.confidence ?? 0.95),
  anomaly_score: typeof r.fault_probability === 'number' ? r.fault_probability : 0.95,
  ```
* **Purpose:** Injects a `0.95` (95% confidence) value if `fault_probability` is missing.
* **Classification:** **UNSAFE** (Manufactured 95% confidence).
* **Action Required:** Remove default `0.95`. Mark confidence as `null` when uncalibrated.

---

### Category D: Fabricated Evidence & Default UI Text

#### 8. Default 91% Confidence Badge & Fake Evidence Bullets
* **File:** [`src/components/station/ExplainabilityCard.tsx`](file:///c:/Users/deepa/OneDrive/Desktop/Sih%2073/src/components/station/ExplainabilityCard.tsx)
* **Line:** 19, 37–43, 60
* **Code:**
  ```typescript
  confidencePct = 91,
  const defaultEvidence = [
    'Temperature increased > 5.8°C within 10 min window without convective pressure plunge.',
    'Nearest neighbour cluster median changed only 0.4°C during identical temporal interval.',
    'Station pressure remained meteorologically coherent (ΔP < 0.2 hPa).',
    'Relative humidity response was physically inconsistent with local dew-point equilibrium.',
    'Temporal residual exceeded historical 99.2th empirical percentile for this climate zone.',
  ];
  <span ...>{confidencePct}% Confidence</span>
  ```
* **Purpose:** Renders a hard-coded "91% Confidence" badge and five plausible-sounding fake meteorological bullets if no real evidence is passed to the component!
* **Classification:** **CRITICALLY UNSAFE** (Fabricated evidence and uncalibrated confidence).
* **Action Required:** Remove `defaultEvidence` array and `91%` default. Render only actual evidence items returned from the detection engine. If empty, show "No anomaly evidence recorded."

#### 9. Synthetic Evidence Generation in StationDrawer
* **File:** [`src/components/station/StationDrawer.tsx`](file:///c:/Users/deepa/OneDrive/Desktop/Sih%2073/src/components/station/StationDrawer.tsx)
* **Line:** 128–154
* **Code:**
  ```typescript
  const evidence = rawEvidence.length > 0 ? rawEvidence : (
    isAnomalous
      ? [
          {
            code: 'PEER_RESIDUAL_OUTLIER',
            strength: anomalyScoreVal,
            message: `Elevation-adjusted residual exceeds 3.8-sigma peer tolerance relative to 5 nearest spatial neighbours (${rootCauseVal}).`,
          },
          {
            code: 'CUSUM_DRIFT_DETECTION',
            strength: 0.92,
            message: 'Cumulative sum sequential test confirms persistent systematic bias across consecutive observation windows.',
          },
        ]
      : ...
  );
  ```
* **Purpose:** If `rawEvidence` from the API is empty, it fabricates a `CUSUM_DRIFT_DETECTION` item with `strength: 0.92`.
* **Classification:** **UNSAFE** (Fabricating diagnostic signals).
* **Action Required:** Delete synthetic evidence branch. Render only true `rawEvidence` from the operational store.

#### 10. Fake Payload Hash Generation
* **File:** [`src/components/station/StationDrawer.tsx`](file:///c:/Users/deepa/OneDrive/Desktop/Sih%2073/src/components/station/StationDrawer.tsx)
* **Line:** 173
* **Code:**
  ```typescript
  raw payload hash {latest.raw_payload_hash || ('WIS2-SYNOP-SHA256-' + station.station_id.slice(-6))}
  ```
* **Purpose:** Injects a mock SHA-256 string if no raw payload hash exists.
* **Classification:** **UNSAFE** (Mock cryptographic provenance).
* **Action Required:** Show hash ONLY if present on a genuine received payload; otherwise display `No raw payload hash recorded`.

#### 11. Hardcoded Demonstration Case Study & "Zero False Alarms"
* **File:** [`src/components/station/WeatherVsFaultCard.tsx`](file:///c:/Users/deepa/OneDrive/Desktop/Sih%2073/src/components/station/WeatherVsFaultCard.tsx)
* **Line:** 47–57, 82–93, 108
* **Code:**
  ```typescript
  <span ...>37.8°C (↑ +5.7°C Residual)</span>
  <div ...>31.8°C</div><div ...>32.0°C</div>...
  <strong ...>Decision:</strong> ... Zero false alarms generated.
  ```
* **Purpose:** Interactive card displaying hardcoded weather front vs. sensor spike values without a visible `SAMPLE / DEMO DATA` badge, concluding with an unproven claim: *"Zero false alarms generated."*
* **Classification:** **UNSAFE** (Unlabeled demo data with exaggerated claims).
* **Action Required:** Add a visible `SAMPLE / DEMONSTRATION DATA` badge and remove unproven marketing assertions.

---

### Category E: Silent Weather Model Substitution

#### 12. Open-Meteo Silent Substitution in History & QC Endpoints
* **File:** [`src/skyguard/api/v1_router.py`](file:///c:/Users/deepa/OneDrive/Desktop/Sih%2073/src/skyguard/api/v1_router.py)
* **Line:** 347–348 & 418–422
* **Code:**
  ```python
  # Line 347:
  if not observed_recs and reference_recs:
      observed_recs = reference_recs

  # Line 418:
  if not obs:
      if ref:
          obs = ref
  ```
* **Purpose:** If physical station observations are not found in the database, the router silently copies the Open-Meteo numerical weather forecast into the `observed` field and runs detection on it!
* **Classification:** **CRITICALLY UNSAFE** (Presenting simulated data as sensor observations).
* **Action Required:** Remove this fallback completely. If direct physical observations are unavailable, the API must return `LIVE_IMD_DATA_UNAVAILABLE` or `null`.

#### 13. Simulated Provider Assignment in Master Station Registry
* **File:** [`data/stations/imd_aws_master.csv`](file:///c:/Users/deepa/OneDrive/Desktop/Sih%2073/data/stations/imd_aws_master.csv)
* **Line:** 2–20+
* **Code:**
  ```csv
  43900000997,Nubra Diskit AWS,Northern Himalayas,34.57,77.56,3144.0,0-20000-0-43900,43900,,IMD_AWS,OPEN_METEO_LIVE,False
  ```
* **Purpose:** Marks network type as `IMD_AWS`, but maps `primary_provider` to `OPEN_METEO_LIVE` so that requests fetch model data instead of real IMD data.
* **Classification:** **UNSAFE** (Misleading data provenance).
* **Action Required:** Update primary provider to `IMD_AWS`. If IMD API is not yet connected for a station, label provider as `NOT_CONFIGURED`.

---

### Category F: Manufactured Residual Math & Explanations

#### 14. Synthetic Residual & Expected Value Formula
* **File:** [`src/server/liveData.ts`](file:///c:/Users/deepa/OneDrive/Desktop/Sih%2073/src/server/liveData.ts)
* **Line:** 357–381
* **Code:**
  ```typescript
  if (param === 'pressure') {
    const obsP = Number(r.pressure_hpa ?? 850.0);
    const resP = Number((zScore * 2.8).toFixed(1));
    const expP = Number((obsP - resP).toFixed(1));
    ...
  } else if (param === 'relative_humidity') {
    const obsRh = Number(r.relative_humidity_pct ?? 70.0);
    const resRh = Number((zScore * 6.2).toFixed(1));
    ...
  } else {
    const obsT = Number(r.temperature_c ?? 25.0);
    const resT = Number((zScore * 1.7).toFixed(1));
    ...
  }
  ```
* **Purpose:** Fabricates expected and residual numbers by multiplying Z-scores by arbitrary constants (`2.8`, `6.2`, `1.7`) instead of querying true spatial neighbor medians.
* **Classification:** **UNSAFE** (Fabricating mathematical features).
* **Action Required:** Remove this formula. Fetch true spatial neighbor residuals computed directly by the Python spatial QC engine.

---

### Category G: Heuristic Probabilities & Automated Imputation

#### 15. Arbitrary Probability Formulas in Hybrid Detector
* **File:** [`src/skyguard/detection/hybrid.py`](file:///c:/Users/deepa/OneDrive/Desktop/Sih%2073/src/skyguard/detection/hybrid.py)
* **Line:** 121, 132, 135
* **Code:**
  ```python
  frozen_probability = min(.98, .45 + .05 * frozen)
  probability = min(base, max(.02, base * (1 - .65 * coherence)))
  probability = min(1, base + (.2 * isolated if spatial_available else 0))
  ```
* **Purpose:** Converts heuristic rule triggers into decimal numbers between 0 and 1, labeled as `anomaly_probability`.
* **Classification:** **UNSAFE** (Uncalibrated pseudo-probabilities).
* **Action Required:** Rename field to `anomaly_score`. Explicitly document that this is a rule-based index, NOT a statistically calibrated probability.

#### 16. Automated Sensor "Repair" / Imputation
* **File:** [`src/skyguard/correction/policy.py`](file:///c:/Users/deepa/OneDrive/Desktop/Sih%2073/src/skyguard/correction/policy.py)
* **Line:** 17–60
* **Code:**
  ```python
  def fit_correction_policy(rows: Iterable[Mapping[str, object]], ...):
      # Selects automated replacement methods (temporal_median, ewma_prior, neighbor_median)
  ```
* **Purpose:** Imputes and replaces faulty sensor readings automatically.
* **Classification:** **INVALID** (Corrupts meteorological truth).
* **Action Required:** Disable automated replacement. Keep output purely advisory as a diagnostic fault label.

---

## 3. Summary & Remediation Priority

| Violation Category | Occurrences Found | Risk Level | Target Phase for Removal |
| :--- | :--- | :--- | :--- |
| **Hard-coded Model Accuracy (98.4%)** | 1 file (`app.py:130`) | Critical | Phase 10 (Backend API Rebuild) |
| **Synthetic Time-Series Sine Generator** | 1 file (`api/stations/[id]/route.ts:141`) | Critical | Phase 10 / 11 (API & UI Rebuild) |
| **Silent Open-Meteo Model Substitution** | 2 files (`v1_router.py:347, 418`, `manager.py`) | Critical | Phase 4 / 10 (IMD API & Routing) |
| **Hardcoded Fallback Scores (`0.884`, `0.024`)** | 5 files (`StationDrawer`, `liveData`, etc.) | High | Phase 11 (Frontend Rebuild) |
| **Fabricated 91% Confidence & Default Evidence** | 2 files (`ExplainabilityCard`, `StationDrawer`) | High | Phase 11 (Frontend Rebuild) |
| **Fabricated Residual Math (`z * 2.8`)** | 1 file (`liveData.ts:357`) | High | Phase 10 (Backend API Rebuild) |
| **Automated Sensor "Repair" (Imputation)** | 2 files (`policy.py`, `estimators.py`) | Moderate | Phase 5 (Operational QC Rebuild) |
| **Synthetic Faults in Labeled Data** | 1 folder (`data/labelled/`) | Moderate | Phase 3 (Data Cleaning & Relabeling) |

---
