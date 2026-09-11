# GitHub-informed model challenger

Reference: https://github.com/metno/titanlib — spatial QC, minimum support and minimum dispersion. This project implements an independent robust residual feature experiment, not Titanlib's full algorithm. No third-party source code was copied. CrowdQCplus (https://github.com/dafenner/CrowdQCplus) remains a research comparator, not an imported model.

`tools/run_github_qc_challenger.py` trains a matched binary LightGBM baseline and an augmented challenger on 2022. Threshold selection uses January–June 2023; confirmation uses July–December with boundary-crossing episodes removed. These development periods were previously inspected and are not blind tests. No protected 2024/2025 files are loaded. Labels are injected-fault labels, not verified real hardware faults.

Seven added features: spatial support, three robust neighbour residuals, and three temporal/spatial agreement strengths. Use at least two neighbours and no more than 60-minute maximum neighbour age. Dispersion floors prevent dividing by near-zero MAD. Unsupported comparisons remain missing. Existing upstream neighbourhoods are reused: radius/elevation/pressure-convention controls are NOT newly solved. These features must not be described as physically validated buddy tests.

Artifacts are separate under reports/github_qc_challenger; deployed weights are not overwritten. Even passing the conservative development gate does not authorize automatic promotion: require multi-seed, unseen-station/domain comparison, calibration, root-cause integration and fresh held-out validation. This binary ablation is not a complete replacement for the deployed multiclass/incident system. No 'best possible model' or improved accuracy claim is justified until measured.
