# Provider Independence & Non-Circular Validation Architecture
**SkyGuard AI — Smart India Hackathon 2026 (Problem Statement SIH26073)**  
**Document Revision:** 2.0  
**Date:** September 12, 2026  

---

## 1. The Core Scientific Imperative: Preventing Circular Validation

In computational meteorology and machine learning, **circular data dependency** (or self-validation leakage) occurs when an observation under evaluation is used—directly or indirectly—to construct the baseline against which it is judged.

For example, if an AWS station reporting $+48^\circ\text{C}$ is included in the spatial averaging calculation for its own region, its own erroneous reading pulls the regional average upward, reducing the detected residual and masking the sensor failure:

$$\text{Circular Bias:} \quad \bar{x} = \frac{x_{\text{target}} + \sum_{i=1}^{N-1} x_i}{N} \implies \text{Residual} = x_{\text{target}} - \bar{x} = \left(1 - \frac{1}{N}\right)(x_{\text{target}} - \bar{x}_{\text{peers}})$$

For $N=3$ neighbours, the detected error is reduced by $33\%$, creating a severe risk of missed anomalies.

SkyGuard AI enforces **strict mathematical provider independence and non-circular validation across all pipeline layers**.

---

## 2. Three Levels of Independence Isolation

```
+-------------------------------------------------------------------------+
|                  STREAM 1: Direct In-Situ Physical Observation         |
|  (IMD WIS 2.0 Synoptic Node / AviationWeather METAR / Meteostat Archive)|
+-------------------------------------------------------------------------+
                                    │
                                    ▼ (Compared Against)
+-------------------------------------------------------------------------+
|             STREAM 2: Independent NOAA MADIS Spatial Consensus          |
|    - STRICT Leave-One-Out Exclusion: Target station NEVER in pool       |
|    - Robust Distance-Weighted Median across physical neighbours         |
+-------------------------------------------------------------------------+
                                    │
                                    ▼ (Corroborated By)
+-------------------------------------------------------------------------+
|            STREAM 3: Independent Numerical Weather Reference Field      |
|    - Open-Meteo Global NWP Reanalysis (ECMWF IFS / GFS Model Physics)   |
|    - Zero dependency on live in-situ AWS hardware transducers           |
+-------------------------------------------------------------------------+
```

### 2.1 Spatial Independence (Leave-One-Out Isolation)
In `SpatialNeighborGraph` and `SpatialBuddyCheck`:
- The target station's own telemetry is excluded before computing distance weights, robust medians, and scaled MAD dispersions.
- Corrupted neighbour sensors are bounded by the robust weighted median's $50\%$ breakdown threshold.

### 2.2 Model Independence (Decoupled Global NWP Physics)
The reference model stream uses Open-Meteo, which assimilates satellite infrared sounders, radiosondes, and global synoptic networks into primitive-equation atmospheric models (ECMWF IFS / NOAA GFS). It does **not** depend on the live micro-controller ADC or analog circuit of the specific Indian AWS under test.

---

## 3. Provider Failure Isolation & High Availability Matrix

To ensure zero single points of failure (SPOF) during hackathon demonstrations and national operations, SkyGuard AI implements isolated fallback boundaries:

| Provider Subsystem | Failure Scenario | Impact on SkyGuard | Automatic Fallback Action |
| :--- | :--- | :--- | :--- |
| **IMD WIS 2.0 (`wis2box`)** | Node maintenance / timeout | Zero direct SYNOP | Automatically falls back to AviationWeather METAR and Meteostat in-situ feeds. |
| **AviationWeather METAR** | Network outage | Zero airport reports | Falls back to cached latest telemetry and historical baseline reanalysis. |
| **Open-Meteo Reference API** | Rate-limit / HTTP 429 | Reference stream unavailable | Falls back to local disk cache (`data/reference_weather/{id}.json`); spatial buddy check operates autonomously. |
| **Complete Internet Blackout** | Offline demonstration | Online streams unavailable | Fully functional **checksummed offline replay engine** runs from local SQLite store (`data/runtime/replay.db`) with 100% frozen model fidelity. |

---

## 4. Cryptographic Provenance Auditing (SHA-256)

Every raw observation received by any provider is tagged with an immutable SHA-256 fingerprint:

$$\text{Hash} = \text{SHA256}\left(\text{Provider} \parallel \text{StationID} \parallel \text{Timestamp} \parallel T \parallel P \parallel \text{RH}\right)$$

This hash is stored in `ObservationRecord.raw_source_hash` and propagated through all API responses. Independent auditors can verify that the data displayed in the dashboard exactly matches the byte-for-byte record emitted by the source provider.

---

## 5. Conclusion

By enforcing strict leave-one-out spatial isolation, integrating decoupled numerical weather models, and implementing resilient fallback tiers with cryptographic hashing, SkyGuard AI establishes an airtight, publication-grade scientific standard for automated meteorological quality control.
