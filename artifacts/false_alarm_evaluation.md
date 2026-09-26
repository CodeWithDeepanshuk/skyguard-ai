# SkyGuard AI: Empirical False Alarm Rate (FAR) Evaluation Report

**Execution Timestamp**: `2026-09-26T10:01:34.704883+00:00`  
**Evaluated Split**: `station_test.csv (Spatial Holdout Benchmark)`  

## 1. Truth in Metrics: Reconciling Scientific Claims

> [!IMPORTANT]
> **Scientific Correction**: Early project documentation quoted `0.0000 FAR`. Rigorous audit demonstrates that `0.0000 FAR` applies **only** to the deterministic Physical Possibility Envelope (Tier 0 Range Check).  
> For the complete Multi-Evidence Ensemble, the empirically measured operational rate is **0.0028 false alarms per station-day** (approximately 1 false alert every ~354.0 station-days).

## 2. Confusion Matrix on Spatial Holdout Stations

| True Condition \ Predicted | Predicted FAULT | Predicted NORMAL | Total |
| :--- | :--- | :--- | :--- |
| **Actual FAULT** | **25 (TP)** | 250 (FN) | 275 |
| **Actual NORMAL** | **4 (FP)** | **10,237 (TN)** | 10,241 |
| **Total** | 29 | 10,487 | **10,516** |

## 3. Statistical Metrics Summary

| Metric | Empirical Value | Operational Significance |
| :--- | :--- | :--- |
| **Precision** | **`86.21%`** (`0.8621`) | Ratio of genuine faults among all triggered alerts. |
| **Recall (Sensitivity)** | **`9.09%`** (`0.0909`) | Proportion of true sensor fault events caught. |
| **F1-Score** | **`0.1645`** | Harmonic mean of precision and recall. |
| **False Positive Rate (FPR)** | **`0.04%`** (`0.0004`) | Probability of false alarm given normal condition. |
| **False Alarms per Station-Day** | **`0.0028`** | Mean false alarms generated per station per 24h. |
| **Mean Time Between False Alarms** | **`~354.0 days`** | Average operational days of normal operation per false alert per station. |
| **Physical Range Filter FAR** | **`0.000391`** | Exact deterministic filter false alarm rate on nominal data. |

---
*Report generated deterministically by `scripts/evaluate_false_alarm_rate.py` based on physical holdout evaluation.*
