"""Build the self-contained Iteration 12 genuine IMD AWS Colab notebook."""
from pathlib import Path
import ast
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
NAME = "SkyGuard_AI_Iteration_12_Genuine_IMD_AWS_Data_Colab.ipynb"


def build():
    cells = []

    def md(value):
        cells.append({"cell_type":"markdown", "metadata":{}, "source":value.strip().splitlines(keepends=True)})

    def code(value):
        value = value.strip()
        ast.parse(value)
        cells.append({"cell_type":"code", "metadata":{}, "execution_count":None, "outputs":[],
                      "source":value.splitlines(keepends=True)})

    md("""
# SkyGuard AI — Iteration 12: Genuine IMD AWS Data Foundation

Yeh notebook **official, authenticated IMD AWS observations** collect karta hai. Isme generated weather,
METAR substitution, DWD substitution ya 24-station starter data use nahi hota. Official endpoint se directly
reported temperature, MSLP pressure aur RH preserve hote hain. Har raw response immutable JSON, SHA-256 receipt
aur normalized Parquet ke roop mein Google Drive par save hota hai.

Important: IMD ka documented endpoint current snapshots deta hai, historical training archive nahi. Isliye ek run
sirf ek time-slice hai. Temporal/seasonal model ko honest tarike se train karne ke liye snapshots ko time ke saath
collect karna hoga. Notebook 30-day pilot, 90-day robust temporal aur 365-day seasonal readiness separately batata hai.
""")
    md("""
## Credentials — API key ko notebook mein paste mat karein

1. IMD API portal mein AWS Data aur AWS Data Mapping access approve karayein.
2. Colab ke left sidebar mein **Secrets (key icon)** kholein.
3. `IMD_API_KEY` aur `IMD_JWT_TOKEN` naam ke do secrets banayein aur notebook access enable karein.
4. JWT expire ho sakta hai; `401 Invalid or expired JWT token` aaye to official portal se renew karein.

Gateway contract independently checked on 12 September 2026: `x-api-key` header plus
`Authorization: Bearer <JWT>`. Secrets kisi output, receipt ya ZIP mein save nahi hote.

Official references: [IMD AWS API](https://api.imd.gov.in/public/api_reference.html),
[IMD API portal](https://api.imd.gov.in/public/index.php).
""")
    code("""
import sys, subprocess
subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q',
                       'pandas>=2.2,<3', 'numpy>=1.26,<3', 'pyarrow>=16,<24', 'requests>=2.31,<3'])
print('Dependencies ready')
""")
    code("""
from pathlib import Path
import json, os, sys, time, shutil
import pandas as pd
from IPython.display import display
from google.colab import drive, userdata

drive.mount('/content/drive')
I12_ROOT = Path('/content/drive/MyDrive/SkyGuard_AI_GPU/experiments/iteration12_genuine_imd_aws_v1')
I12_ROOT.mkdir(parents=True, exist_ok=True)

# 0 = one snapshot. Set e.g. 6 to collect every 15 minutes for six hours in this Colab session.
COLLECT_HOURS = 0
INTERVAL_MINUTES = 15
STATE_ID = None       # None = national endpoint; e.g. 7 = Delhi only
SOURCE_TIMEZONE = 'UTC'  # IMD sample timing is handled under this explicit, auditable contract.
TIMESTAMP_TIMEZONE_CONFIRMED = False  # Set True only after IMD/portal confirms AWS DATE+TIME convention.

IMD_API_KEY = userdata.get('IMD_API_KEY')
IMD_JWT_TOKEN = userdata.get('IMD_JWT_TOKEN')
assert IMD_API_KEY and IMD_JWT_TOKEN, 'Add IMD_API_KEY and IMD_JWT_TOKEN in Colab Secrets first.'
print('Experiment:', I12_ROOT)
print('Secrets loaded in memory; they will not be printed or saved.')
""")
    source = (ROOT / "tools" / "iteration12_imd_aws.py").read_text(encoding="utf-8")
    digest = hashlib.sha256(source.encode()).hexdigest()
    code("MODULE_SOURCE = " + repr(source) + "\nEXPECTED_SHA256 = " + repr(digest) + "\n" + """
import hashlib, importlib
assert hashlib.sha256(MODULE_SOURCE.encode()).hexdigest() == EXPECTED_SHA256
module_path = Path('/content/iteration12_imd_aws.py')
module_path.write_text(MODULE_SOURCE, encoding='utf-8')
sys.path.insert(0, '/content') if '/content' not in sys.path else None
import iteration12_imd_aws as i12
importlib.reload(i12)
print('Loaded', i12.VERSION, '| model inputs:', i12.MODEL_INPUTS)
""")
    md("""
## 1. Mapping and authenticated source verification

Mapping station identity/coverage ke liye hai; observation rows nahi hai. HTTP/schema mismatch fail-closed hota hai.
Notebook unauthorized response ko public data samajhkar continue nahi karega.
""")
    code("""
mapping, mapping_receipt = i12.collect_mapping(I12_ROOT, IMD_API_KEY, IMD_JWT_TOKEN)
print('Official mapping saved; SHA-256:', mapping_receipt['saved_sha256'])
print('Credential values saved:', mapping_receipt['credentials_recorded'])
""")
    md("""
## 2. Collect official AWS snapshots

Raw API response unchanged store hota hai. Normalized table mein model ke inputs exactly T/P/RH hain.
Wind, rain, dew point aur forecast model features nahi bante. Source ke impossible values overwrite nahi hote;
unhe QC flags ke through training baseline se exclude kiya jata hai.
""")
    code("""
def collect_and_show():
    frame, receipt = i12.collect_once(I12_ROOT, IMD_API_KEY, IMD_JWT_TOKEN,
                                      state_id=STATE_ID, source_timezone=SOURCE_TIMEZONE)
    print('Saved:', receipt['raw_path'], '| stations:', receipt['stations'], '| rows:', receipt['records'])
    display(frame[['timestamp_utc','station_id','station_name','state','temperature_c',
                   'pressure_hpa','relative_humidity_pct','primary_complete',
                   'broad_physical_range_ok']].head(20))
    return receipt

receipts = [collect_and_show()]
if COLLECT_HOURS > 0:
    runs = max(1, int(COLLECT_HOURS * 60 / INTERVAL_MINUTES))
    for _ in range(1, runs):
        time.sleep(INTERVAL_MINUTES * 60)
        receipts.append(collect_and_show())
print('Snapshots collected this run:', len(receipts))
""")
    md("""
## 3. Assemble deduplicated training foundation and readiness gates

Official observation ka matlab verified healthy sensor label nahi hota. Isliye `ground_truth_fault=-1` rahega.
Future evaluation mein controlled faults copy par inject kiye ja sakte hain; raw IMD data kabhi modify nahi hoga.

- 30 days / 50 stations: pilot temporal model allowed.
- 90 days: stronger temporal validation target (reported separately below).
- 365 days / 50 stations: seasonal-pattern claim allowed.
- Real fault accuracy ke liye IMD maintenance/fault labels ya independently adjudicated injected benchmark zaroori hai.
""")
    code("""
dataset = i12.assemble(I12_ROOT)
station_quality, readiness = i12.readiness(
    dataset, timestamp_timezone_confirmed=TIMESTAMP_TIMEZONE_CONFIRMED)
processed = I12_ROOT / 'processed'
processed.mkdir(exist_ok=True)
dataset_path = processed / 'imd_aws_observations_deduplicated.parquet'
dataset.to_parquet(dataset_path, index=False)
station_quality.to_csv(I12_ROOT / 'iteration12_station_readiness.csv', index=False)
(I12_ROOT / 'iteration12_data_readiness.json').write_text(json.dumps(readiness, indent=2), encoding='utf-8')
display(pd.Series(readiness))
display(station_quality.sort_values(['distinct_days','rows'], ascending=False).head(30))
print('90-day stations:', int(station_quality.distinct_days.ge(90).sum()))
assert not dataset.generated_or_simulated.astype(bool).any()
assert dataset.source.eq('IMD_AUTHORIZED_AWS_API').all()
""")
    md("""
## 4. Honest training decision

`ready_for_pilot_training=False` ho to model train karna scientific shortcut hoga. Existing retained Phase 10 model
replace nahi hoga. Data accumulate hone ke baad next training stage station-blocked aur time-blocked splits,
causal temporal features, neighbour age/elevation guards, synthetic fault challenge copies, calibration and incident
false-alarm gates use karega. Accuracy class imbalance se hide na ho, isliye point accuracy primary metric nahi hogi.
""")
    code("""
decision = {
    'iteration': 12,
    'data_source': 'authorized IMD AWS API',
    'promote_or_train_now': bool(readiness['ready_for_pilot_training']),
    'seasonal_claim_allowed': bool(readiness['ready_for_seasonal_claims']),
    'retained_production_model_changed': False,
    'reason': ('Data readiness gate passed; create a separately evaluated Iteration 12 model challenger.'
               if readiness['ready_for_pilot_training'] else
               'Continue genuine snapshot collection; insufficient history for honest temporal training.'),
    'required_metrics_next': ['fault incident precision','fault episode recall','false incidents per station-day',
                              'weather-event preservation F1','unseen-station F1','detection latency'],
}
(I12_ROOT / 'iteration12_decision.json').write_text(json.dumps(decision, indent=2), encoding='utf-8')
display(pd.Series(decision))
""")
    md("""
## 5. Download the small audit package

Raw data Drive par hi rahega. ZIP mein credentials ya huge raw observations nahi honge. Team/Codex ko yahi ZIP
return karein; uske basis par next training notebook freeze hoga.
""")
    code("""
import zipfile
report_files = [I12_ROOT/'iteration12_data_readiness.json', I12_ROOT/'iteration12_station_readiness.csv',
                I12_ROOT/'iteration12_decision.json', I12_ROOT/'metadata/imd_aws_mapping.receipt.json']
zip_path = I12_ROOT / 'SkyGuard_Iteration12_Genuine_IMD_AWS_Reports.zip'
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
    for path in report_files:
        if path.exists():
            z.write(path, path.relative_to(I12_ROOT))
print('Return this file:', zip_path)
from google.colab import files
files.download(str(zip_path))
""")
    notebook = {"cells":cells, "metadata":{"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"},
                 "language_info":{"name":"python","version":"3.x"}, "accelerator":"GPU"},
                "nbformat":4, "nbformat_minor":5}
    for folder in (ROOT / "notebooks", ROOT / "deliverables"):
        folder.mkdir(exist_ok=True)
        (folder / NAME).write_text(json.dumps(notebook, indent=1), encoding="utf-8")
    return ROOT / "notebooks" / NAME


if __name__ == "__main__":
    print(build())
