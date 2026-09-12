"""Generate the standalone corrected Iteration 11 data-rebuild Colab artifact.

Does not overwrite the older catalogue-only Iteration 11 notebook/results.
Embeds reviewed source modules so no starter ZIP, GitHub checkout or hidden
earlier-notebook globals are required. Run again after changing either module.
"""
from pathlib import Path
import ast
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
NAME = "SkyGuard_AI_Iteration_11_Data_Rebuild_Colab.ipynb"


def build():
    cells = []
    def md(s):
        cells.append({"cell_type": "markdown", "metadata": {}, "source": s.strip().splitlines(keepends=True)})
    def code(s):
        ast.parse(s.strip())
        cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": s.strip().splitlines(keepends=True)})
    md("""
# SkyGuard AI — Iteration 11 Data Rebuild

**Run this corrected notebook, not the older `SkyGuard_AI_GPU_Iteration_11_Colab.ipynb`.**
The old ZIP named “545 stations” contained 24-station observations plus a larger station catalog.
This version actually downloads new Indian-station observations and builds fresh training tables.

Verified discovery on 11 September 2026: **545 Indian ISD station IDs; 543 have coordinates;
441 have at least one listed 2020–2023 file (1,596 station-year files).** These are availability
counts, not quality-passing counts. Discovery rechecks official metadata in a new experiment.
IMD's 1008 AWS network is a different network, not a percentage denominator for this archive.

Data: official NOAA/NCEI historical Indian surface/airport station observations, **not direct IMD AWS telemetry**.
Temperature and pressure are reported; RH here is derived from T/dew point. Dew point never enters model features.
Only T/P/RH, time, and station metadata for causal context are used. No rain/wind/forecast predictors.

This is a research baseline rebuild, not a completed production/maintenance system or guaranteed accuracy increase.
Original project datasets, old results and deployed models remain untouched.
""")
    md("""
## 1. Run instructions — pehle yeh padhein

1. Upload **only this notebook** to Google Colab. No old data ZIP is needed.
2. Run setup and connect your Google Drive. Data is downloaded automatically from official NOAA URLs.
3. Default `RUN_MODE='all_available'` processes the full discovered Indian candidate network.
   A first run may require multiple sessions: downloads and station features resume from checked files.
   Runtime is not promised to be 6–8 minutes. Keep enough free Drive space (several GB; actual size depends on files).
4. CPU runtime is sufficient for data download/features and LightGBM. For optional CatBoost select **T4 GPU**.
5. Use **Runtime → Run all**. If Colab disconnects, reconnect, run setup, then Run all again.
   Completed files are reused only when their checksums/contracts match.
6. Send back the small result ZIP from the last cell. Do not send model files unless requested.

`pilot` mode downloads six new stations for troubleshooting and deliberately does not claim national training.
At least 50 eligible stations, including 25 outside the original24, are required for the expanded training path.
This is a pragmatic readiness guard, not an SIH-prescribed threshold.
""")
    code("""
import sys, subprocess
subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q',
    'numpy>=1.26,<3', 'pandas>=2.2,<3', 'pyarrow>=16,<24',
    'scikit-learn>=1.5,<1.9', 'lightgbm==4.6.0', 'catboost>=1.2.7,<1.3',
    'joblib>=1.4,<2', 'requests>=2.31,<3'])
print('Dependencies installed. If Colab explicitly requests a restart, restart once and rerun setup.')
""")
    code("""
from pathlib import Path
import json, os, sys, shutil, gc, importlib.metadata
import numpy as np
import pandas as pd
from IPython.display import display
from google.colab import drive
drive.mount('/content/drive')

RUN_MODE = 'all_available'  # 'pilot' for six NEW stations; it does not run national training
RUN_TRAINING = True
USE_CATBOOST = True
RUN_EXTRA_SEEDS = False  # True runs two additional complete scenarios after the first run
SEED = 111
EXPERIMENT_NAME = 'iteration11_data_rebuild_v1'
I11_ROOT = Path('/content/drive/MyDrive/SkyGuard_AI_GPU/experiments') / EXPERIMENT_NAME
I11_ROOT.mkdir(parents=True, exist_ok=True)
assert RUN_MODE in {'all_available', 'pilot'}
print('Persistent experiment:', I11_ROOT)
print('Drive available GB (Colab mount may not reflect account quota):', round(shutil.disk_usage(I11_ROOT).free/1024**3, 1))
GPU_AVAILABLE = shutil.which('nvidia-smi') is not None and subprocess.run(['nvidia-smi'], capture_output=True).returncode == 0
print('GPU available:', GPU_AVAILABLE, '| CatBoost enabled:', USE_CATBOOST)
print('LightGBM and data preparation use CPU. Unused GPU memory during these steps is normal.')
""")
    md("""
## 2. Self-contained, checksummed implementation

The next cell installs the two embedded Python modules in the temporary Colab runtime.
All experiment data stays on Drive. There are no hidden `train`, `dev`, or previous-iteration variables.
Changing embedded source changes cache contracts; use a new experiment name after substantive changes.
""")
    modules = {n: (ROOT / "tools" / (n + ".py")).read_text(encoding="utf-8") for n in ["iteration11_data", "iteration11_training"]}
    hashes = {n: hashlib.sha256(s.encode()).hexdigest() for n, s in modules.items()}
    code("MODULE_SOURCES = " + repr(modules) + "\nEXPECTED_MODULE_SHA256 = " + repr(hashes) + """
import hashlib, importlib
MODULE_ROOT = Path('/content/skyguard_iteration11_rebuild_code')
MODULE_ROOT.mkdir(exist_ok=True)
for name, text in MODULE_SOURCES.items():
    assert hashlib.sha256(text.encode()).hexdigest() == EXPECTED_MODULE_SHA256[name]
    (MODULE_ROOT / (name + '.py')).write_text(text, encoding='utf-8')
sys.path.insert(0, str(MODULE_ROOT)) if str(MODULE_ROOT) not in sys.path else None
import iteration11_data as i11d
import iteration11_training as i11t
importlib.reload(i11d)
importlib.reload(i11t)
print('Code loaded:', i11d.VERSION, '| explicit feature count:', len(i11t.FEATURES))
""")
    md("""
## 3. Source discovery — metadata is not observation coverage

All Indian ISD IDs are considered, not a hardcoded24-station selection. Annual directory listings verify
which historical CSVs exist. File downloads then verify schema and hashes. Missing/incompatible files
are reported instead of replaced with synthetic observations. NOAA is transitioning from ISD to GHCNh;
this notebook deliberately supports the verified **historical ISD CSV schema only**, with no silent format fallback.

Sources:
- [NOAA station histories](https://www.ncei.noaa.gov/products/land-based-station/station-histories)
- [ISD data and limitations](https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database)
- [GHCNh transition](https://www.ncei.noaa.gov/products/global-historical-climatology-network-hourly)
- [IMD AWS API](https://api.imd.gov.in/public/api_reference.html)
- [Official 1008 IMD AWS count](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2241702)
""")
    legacy = []
    import csv
    with (ROOT / "config/stations.csv").open(encoding="utf-8") as f:
        legacy = [r["station_id"] for r in csv.DictReader(f)]
    code("LEGACY_24_IDS = " + repr(legacy) + """
catalog, download_plan, discovery = i11d.discover(I11_ROOT, LEGACY_24_IDS)
display(pd.Series(discovery))
display(catalog[['station_id','station_name','latitude','longitude','station_role',
                 'inventory_reports_2020','inventory_reports_2021','legacy_24_station']].head(15))
print('Eligible station count will be computed AFTER downloading and inspecting actual observations.')
""")
    md("""
## 4. Download real observations, 2020–2023

Requests are limited to three simultaneous downloads with retries, disk checks and per-file receipts.
No IMD credentials are required for this public proxy source. This does **not** obtain authorized IMD AWS data.
Do not count map/catalog entries as downloaded stations. No 2024/2025 labelled test files are opened.
""")
    code("""
PILOT_IDS = ['42369099999','42372099999','42273099999','42492099999','42591099999','42391099999']
selected_ids = None if RUN_MODE == 'all_available' else PILOT_IDS
download_status = i11d.acquire(I11_ROOT, selected_ids, workers=3)
display(download_status.status.value_counts())
failed_downloads = download_status.loc[download_status.status.ne('complete')]
if len(failed_downloads):
    display(failed_downloads[['station_id','year','error']])
    print('Rerun this cell to retry. Incomplete acquisition cannot silently become a full-network experiment.')
print('Completed unique stations in this requested run:', download_status.loc[download_status.status.eq('complete'),'station_id'].nunique())
""")
    md("""
## 5. Normalize and profile — no pressure-type mixing

Each station preserves station pressure, mean-sea-level pressure and altimeter pressure separately.
One pressure type is selected from usable **2020–2021 data only** and kept fixed; absent values stay missing.
RH is calculated from reported T/dew point without silently clipping invalid results. Source quality flags
remain audit fields, **never model predictors or verified fault labels**. Duplicates use deterministic quality/completeness ordering.

Training eligibility: >=1,000 QC-screened triples across >=180 distinct 2020–2021 days.
QC-screened means **presumed normal, not confirmed healthy**; other rows stay unknown and are not negative labels.
Pressure datum and sensor-resolution differences can cause spurious alarms even with many stations.
""")
    code("""
station_quality, graph, readiness = i11d.prepare(I11_ROOT)
display(pd.Series(readiness))
display(station_quality[['station_id','station_name','training_eligible','pressure_datum',
                        'fit_rows','fit_screened_proxy_rows','fit_screened_days','fit_median_cadence_minutes','exclusion_reason']])
display(pd.read_csv(I11_ROOT/'spatial_support.csv', dtype={'station_id':str}).head(30))
""")
    md("""
## 6. Data gate and split contract

| Purpose | Observations | Station scope |
|---|---|---|
| Fit models | 2020–2021 | Development geographic blocks |
| Early stopping | January–April 2022 | Development blocks |
| Probability calibration | May–August 2022 | Development blocks, unsampled prevalence |
| Threshold selection | September–December 2022 | Development blocks, unsampled prevalence |
| Temporal confirmation | 2023 | Development blocks |
| Spatial confirmation | 2023 | Held-out geographic blocks |

Spatial holdouts supply no training examples and no pre-2023 training buddies. Their historical unlabelled
data selects their own pressure type/eligibility: this is **label-held-out station transfer with historical context**,
not zero-history cold-start performance. 2023 has been inspected elsewhere in this project; do not call it blind.
No failed false-alarm gate is turned into an operational promotion.

Small pilots stop here for data review. They can export a report in the last cell without training.
""")
    code("""
all_files_complete = download_status.status.eq('complete').all()
CAN_TRAIN = bool(RUN_MODE == 'all_available' and all_files_complete and readiness['ready_for_expanded_training'])
split_manifest = {'version':i11d.VERSION,'run_mode':RUN_MODE,'can_train':CAN_TRAIN,
    'data_hash':readiness['all_data_hash'],'feature_names':i11t.FEATURES,
    'seed':SEED,'all_requested_files_complete':bool(all_files_complete),
    'real_fault_labels_available':False,'old_model_replaced':False}
i11d.write_json(I11_ROOT/'run_contract.json', split_manifest)
print('Expanded training enabled:', CAN_TRAIN)
if not CAN_TRAIN:
    print('Data-only result: inspect failed downloads/exclusions or switch from pilot to all_available and rerun.')
""")
    md("""
## 7. Causal features and controlled challenge labels

We use time gaps, missing-value counts, lag/rate changes, previous24-hour robust residuals,
elapsed flatline duration, previous3/6/24-hour slopes, seasonal time encodings, and buddy residuals.
No future data or raw labels enter features. Neighbours must be <=150km away, <=300m elevation difference,
independent (not <1km co-located aliases), and <=90 minutes old. Pressure buddies also require the same datum.
At least two usable buddies are required for a spatial residual; otherwise the feature is unavailable.
These are conservative engineering defaults, not universal meteorological standards.

Synthetic tests cover spikes, bias, drift, flatlines, noise, missing values and coherent regional perturbations.
Faults are injected **before feature building in target AND neighbour streams**; neighbours are not clean oracles.
Regional perturbations are synthetic weather challenges, not labelled real storms. Packet loss is distinct from
a missing sensor value: without a verified heartbeat contract, real archive gaps cannot establish communication faults.
""")
    code("""
FEATURE_DIR = None
if CAN_TRAIN and RUN_TRAINING:
    FEATURE_DIR = i11t.build_features(I11_ROOT, seed=SEED)
    print('Checksummed per-station features:', FEATURE_DIR)
else:
    print('Feature/training stage skipped; data reports remain available.')
""")
    md("""
## 8. Fit and compare models

- Robust temporal QC comparator (non-learning score, separately calibrated).
- LightGBM without spatial features.
- LightGBM with causal spatial features.
- Original24-only **retrained** comparator, when enough old stations qualify. Same splits/features; not the old deployed binary.
- Optional CatBoost with spatial features, on T4 if available.

Per-station training mass is balanced and long episodes are downweighted. Training negatives are capped per station
for Colab memory; calibration and evaluation retain the full observed class prevalence. L1/L2 regularization and early stopping
control overfitting. New networks are not added without evidence they improve weak faults and weather false alarms.

Models/calibrators/policies are saved under this experiment only. A policy needs precision>=80% and <=0.05 false-positive
rows per observed station-day on the policy block. These are development targets, not official SIH score thresholds.
If none pass, the best descriptive F1 comparator is saved **with a failed gate**, never promoted.
""")
    code("""
MODEL_OUTPUT = None
if FEATURE_DIR is not None:
    MODEL_OUTPUT = i11t.train_research(I11_ROOT, seed=SEED, use_catboost=USE_CATBOOST, gpu=GPU_AVAILABLE)
    policies = json.loads((MODEL_OUTPUT/'frozen_policies.json').read_text())
    display(pd.DataFrame(policies['policies'])[['model','threshold','precision','recall','f1','meets_development_budget']])
    gc.collect()
""")
    md("""
## 9. Frozen-policy confirmation (not a fresh blind test)

Reports point precision/recall/F1, average precision (PR-AUC), accuracy, Brier score, episode recall,
per-fault recall, per-station results and false alarms on synthetic weather challenges.
High accuracy alone is misleading because most rows are normal. Episode recall is any-point detection,
not onset accuracy. False-positive rows/day is not an incident-alert metric.

Do not retune against this report. Improvement is a measured comparison, not a promise.
""")
    code("""
RESULT = None
if MODEL_OUTPUT is not None:
    RESULT = i11t.confirm_research(I11_ROOT, seed=SEED)
    display(pd.DataFrame(RESULT['comparison']))
    display(pd.read_csv(MODEL_OUTPUT/'iteration11_fault_recall.csv'))
else:
    print('No training results yet. Send the data-readiness report first.')
""")
    md("""
## 10. Optional repeatability checks

Extra seeds change synthetic challenge realizations and retrain models. They use the same station/time split.
Variation across seeds is not an independent real-world confidence interval. No automatic winning-seed selection.
""")
    code("""
if RUN_EXTRA_SEEDS and CAN_TRAIN and RUN_TRAINING:
    repeated = []
    for extra_seed in [211, 311]:
        i11t.build_features(I11_ROOT, seed=extra_seed)
        i11t.train_research(I11_ROOT, seed=extra_seed, use_catboost=USE_CATBOOST, gpu=GPU_AVAILABLE)
        r = i11t.confirm_research(I11_ROOT, seed=extra_seed)
        repeated.extend([{'seed':extra_seed,**x} for x in r['comparison']])
        gc.collect()
    pd.DataFrame(repeated).to_csv(I11_ROOT/'repeat_seed_comparison.csv',index=False)
    display(pd.DataFrame(repeated))
""")
    md("""
## 11. Export reports to return for review

The report ZIP includes station eligibility/exclusions, acquisition status, spatial support,
split/feature contracts and results if training ran. Raw downloads and model binaries stay on Drive.
**Send this ZIP back.** Review must determine whether wider data improves station/fault recall without
excessive false alarms. No model is uploaded to the website by this notebook.

Before operational deployment: obtain compatible IMD AWS or owned-sensor T/P/RH streams, validate pressure/RH provenance,
collect independently verified fault/maintenance labels, test real weather extremes and packet SLAs, benchmark inference
resources, and explicitly promote a versioned model only after acceptance. Vercel website hosting alone does none of this.
""")
    code("""
import zipfile
from google.colab import files
REPORT_ZIP = I11_ROOT/'SkyGuard_Iteration11_Data_Rebuild_Reports.zip'
with zipfile.ZipFile(REPORT_ZIP,'w',zipfile.ZIP_DEFLATED) as z:
    for name in ['discovery_receipt.json','station_catalog.csv','download_status.csv','station_quality.csv',
                 'neighbor_graph.csv','spatial_support.csv','data_readiness.json','run_contract.json','repeat_seed_comparison.csv']:
        p = I11_ROOT/name
        if p.exists(): z.write(p,name)
    for directory in sorted(I11_ROOT.glob('research_seed*')):
        for p in sorted(directory.iterdir()):
            if p.suffix in {'.csv','.json'}: z.write(p,p.relative_to(I11_ROOT))
print('Send back:',REPORT_ZIP)
files.download(str(REPORT_ZIP))
""")
    notebook = {"cells":cells,"metadata":{"colab":{"name":NAME},"accelerator":"GPU",
                  "kernelspec":{"display_name":"Python 3","language":"python","name":"python3"},
                  "language_info":{"name":"python","version":"3.12"}},"nbformat":4,"nbformat_minor":5}
    for i, cell in enumerate(cells):
        cell["id"] = f"i11-rebuild-{i:02d}"
    content = json.dumps(notebook, ensure_ascii=False, indent=1) + "\n"
    for folder in ["notebooks", "deliverables"]:
        (ROOT/folder/NAME).write_text(content, encoding="utf-8")
    print(f"Generated {NAME}: {len(cells)} cells; source hashes {hashes}")


if __name__ == "__main__":
    build()
