# GitHub weather QC review — 2026-09-10

- https://github.com/metno/titanlib — spatial checks and minimum buddy support; LGPL. No code copied or package installed.
- https://github.com/dafenner/CrowdQCplus — citizen weather QC comparator, not validated on our feed. No code imported.
- https://github.com/S-S-JHOTHEESHWAR/IMD-AWS-ARG-Quality-Control-Health-Monitoring-System — completeness and operational history reporting; repository name does not establish IMD endorsement. No code imported.

Implemented independently: live parameter completeness, observation age and temperature buddy-support eligibility. Buddies must be within 100 km, 200 m elevation and at or before the target time within 60 minutes. Fewer than two buddies produces insufficient support, never a fault. Missing elevation excludes a buddy. Thresholds are provisional display diagnostics, not calibrated anomaly thresholds. This is not Titanlib's actual buddy-check algorithm.

Models, correction policies and detection decisions are unchanged. No accuracy improvement claimed. Full spatial detection needs development-set comparison, weather false-alarm evaluation, pressure convention handling and genuinely unseen validation before promotion. Do not tune repeatedly on opened 2024/2025 tests.

Historical counts, health registry, training narrative, accuracy and provenance are offline-mode only. Raw data and reports are preserved. Live results are advisory, not measured live accuracy.
