"""Build the standalone SkyGuard GPU iteration notebook."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks" / "SkyGuard_AI_GPU_Iterative_Improvement_Colab.ipynb"


def md(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(keepends=True)}


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


cells = [
md(r"""# SkyGuard AI — GPU Iterative Improvement Lab

**SIH 26073 | Colab notebook adapted to the real Phase 10 project data**

This notebook preserves the compliant LightGBM baseline and tests controlled GPU improvements: deterministic communication rules, specialist fault scores, a five-seed CatBoost ensemble, an optional causal TCN, calibrated fusion, hysteresis, strict incident metrics, weather-source separation, confidence intervals, and saved experiment artifacts.

### Scientific status of our labels

- The meteorological observations are genuine NOAA/NCEI station data.
- The fault and regional-weather evaluation labels are reproducibly injected scenarios, as permitted by SIH 26073.
- We do **not** possess confirmed maintenance fault logs. Therefore, this notebook never calls the injected labels “real hardware faults.”
- No final 2024 test file is opened during normal iterations.
"""),
md(r"""## Iteration protocol — read before running

1. Upload `SkyGuard_GPU_Data_Bundle.zip` to `MyDrive/SkyGuard_AI_GPU/`.
2. Use a Colab GPU runtime.
3. Run the notebook from top to bottom with `UNLOCK_FINAL_TESTS = False`.
4. Send back `iteration_result_block.json`, `development_ablation.csv`, and the displayed result block.
5. We will improve one controlled component at a time.
6. The two 2024 tests are opened only after the configuration and thresholds are frozen.

The uploaded generic prompt is treated as methodology advice. Its placeholder schemas, 15-minute cadence assumption, unfinished Phase 10 adapter, and unfinished TCN loader have been replaced with the actual SkyGuard data contract.
"""),
md("## 0. Install packages and mount Google Drive"),
code(r"""# Colab setup. Restarting the runtime is normally not required.
!pip -q install catboost==1.2.10 lightgbm==4.6.0 scikit-learn==1.7.2 pyarrow==21.0.0 psutil==7.0.0

from google.colab import drive
drive.mount('/content/drive')
"""),
code(r"""from pathlib import Path

DRIVE_ROOT = Path('/content/drive/MyDrive/SkyGuard_AI_GPU')
BUNDLE_ZIP = DRIVE_ROOT / 'SkyGuard_GPU_Data_Bundle.zip'
DATA_ROOT = DRIVE_ROOT / 'SkyGuard_GPU_Data_Bundle'
ARTIFACT_ROOT = DRIVE_ROOT / 'experiments' / 'iteration_01_detection'

# Keep false while we iterate. Change only after the complete candidate is frozen.
UNLOCK_FINAL_TESTS = False

# GPU experiment controls.
RUN_CATBOOST = True
RUN_TCN = True
REUSE_SAVED_MODELS = True
SEEDS = [17, 29, 41, 53, 67]

ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
print('Bundle:', BUNDLE_ZIP)
print('Artifacts:', ARTIFACT_ROOT)
"""),
code(r"""import os, json, time, math, random, hashlib, shutil, zipfile, warnings, platform
from dataclasses import dataclass

import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import psutil

from sklearn.metrics import (
    average_precision_score, precision_score, recall_score, f1_score,
    confusion_matrix, brier_score_loss, log_loss
)
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression
from catboost import CatBoostClassifier

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from IPython.display import display

warnings.filterwarnings('ignore')
pd.set_option('display.max_columns', 50)
pd.set_option('display.float_format', lambda x: f'{x:,.5f}')
plt.style.use('seaborn-v0_8-whitegrid')

DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
print({
    'python': platform.python_version(), 'device': DEVICE,
    'gpu': torch.cuda.get_device_name(0) if DEVICE == 'cuda' else None,
    'cpu_count': os.cpu_count(),
    'ram_gb': round(psutil.virtual_memory().total / 2**30, 2)
})
assert DEVICE == 'cuda', 'Select Runtime > Change runtime type > GPU before training.'
"""),
md("## 1. Extract and validate the exact project bundle"),
code(r"""if not DATA_ROOT.exists():
    assert BUNDLE_ZIP.exists(), f'Upload the bundle first: {BUNDLE_ZIP}'
    print('Extracting bundle once...')
    with zipfile.ZipFile(BUNDLE_ZIP) as zf:
        zf.extractall(DRIVE_ROOT)

REQUIRED_FILES = [
    'data/features_phase10/train_features.csv.gz',
    'data/features_phase10/validation_features.csv.gz',
    'data/features_phase10/time_test_features.csv.gz',
    'data/features_phase10/station_test_features.csv.gz',
    'data/features_phase10/feature_spec.json',
    'models/phase10_final.joblib',
    'models/phase10_tcn.pt',
    'reports/phase10_final.json',
    'reports/data_validation.json',
    'reports/fault_injection.json',
    'data/labelled/episodes.csv',
    'bundle_manifest.json',
]
missing = [name for name in REQUIRED_FILES if not (DATA_ROOT / name).exists()]
assert not missing, f'Missing bundle files: {missing}'

def sha256_file(path, chunk_size=4 << 20):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b''):
            digest.update(chunk)
    return digest.hexdigest()

bundle_manifest = json.loads((DATA_ROOT / 'bundle_manifest.json').read_text())
hash_errors = []
for item in bundle_manifest['files']:
    path = DATA_ROOT / item['path']
    if not path.exists() or sha256_file(path) != item['sha256']:
        hash_errors.append(item['path'])
assert not hash_errors, f'Integrity failures: {hash_errors}'
print(f"PASS: {len(bundle_manifest['files'])} files matched their SHA-256 hashes.")
"""),
md(r"""## 2. Load development data only

The immutable protocol is:

- **Train:** 2022, all 20 development stations.
- **Model tuning:** January–April 2023.
- **Fusion fitting:** May–June 2023.
- **Probability calibration:** July–September 2023.
- **Policy selection:** October–December 2023.
- **Frozen time test:** 2024 development stations — not loaded now.
- **Frozen station test:** 2024 four unseen stations — not loaded now.

Injected episodes that touch a development boundary are assigned wholly to the partition in which the episode starts.
"""),
code(r"""FEATURE_DIR = DATA_ROOT / 'data' / 'features_phase10'
BASELINE_FILE = DATA_ROOT / 'models' / 'phase10_final.joblib'

def load_feature_table(name):
    frame = pd.read_csv(FEATURE_DIR / f'{name}_features.csv.gz', low_memory=False)
    frame['station_id'] = frame['station_id'].astype(str)
    frame['emitted_timestamp_utc'] = pd.to_datetime(frame['emitted_timestamp_utc'], utc=True)
    frame['episode_id'] = frame['episode_id'].fillna('').astype(str)
    return frame.sort_values(['station_id', 'emitted_timestamp_utc', 'row_id']).reset_index(drop=True)

train = load_feature_table('train')
validation = load_feature_table('validation')

train['dev_split'] = 'train'
ts = validation['emitted_timestamp_utc']
validation['dev_split'] = np.select(
    [ts < '2023-05-01', ts < '2023-07-01', ts < '2023-10-01'],
    ['tune_model', 'fusion_fit', 'calibrate'],
    default='policy_select'
)

# Prevent the same injected episode from crossing development partitions.
episodes = validation.loc[validation['episode_id'].ne('')]
episode_partition = (episodes.sort_values('emitted_timestamp_utc')
                      .groupby('episode_id', sort=False)['dev_split'].first())
mask = validation['episode_id'].ne('')
validation.loc[mask, 'dev_split'] = validation.loc[mask, 'episode_id'].map(episode_partition)

dev = pd.concat([train, validation], ignore_index=True)
del train, validation

# Models score emitted readings. Dropout is evaluated by the communication-event channel.
model_dev = dev.loc[dev['available_to_detector'].eq(1)].copy().reset_index(drop=True)
print('Development rows:', f'{len(dev):,}', '| model-visible rows:', f'{len(model_dev):,}')
display(model_dev.groupby('dev_split').agg(
    rows=('row_id','size'), stations=('station_id','nunique'),
    faults=('is_anomaly','sum'), weather=('is_weather_event','sum'),
    start=('emitted_timestamp_utc','min'), end=('emitted_timestamp_utc','max')
))
"""),
code(r"""# Leakage and schema audit.
baseline_bundle = joblib.load(BASELINE_FILE)
FEATURES = list(baseline_bundle['event_features'])
FORBIDDEN = {'hour_sin','hour_cos','day_of_year_sin','day_of_year_cos','temperature_dewpoint_spread_c'}
LABEL_COLUMNS = {
    'is_anomaly','is_weather_event','anomaly_type','anomaly_sensor','anomaly_severity',
    'episode_id','label_category','label_source','injection_seed','stream_action',
    'original_temperature_c','original_pressure_hpa','original_relative_humidity_pct'
}

assert len(FEATURES) == 108
assert not (set(FEATURES) & FORBIDDEN)
assert not (set(FEATURES) & LABEL_COLUMNS)
assert all(name in model_dev.columns for name in FEATURES)
assert len(baseline_bundle['training_stations']) == 20

episode_leak = (model_dev.loc[model_dev['episode_id'].ne('')]
                .groupby('episode_id')['dev_split'].nunique().gt(1).sum())
assert episode_leak == 0, f'{episode_leak} episodes cross development partitions.'

audit = {
    'rows': int(len(model_dev)),
    'stations': int(model_dev.station_id.nunique()),
    'feature_count': len(FEATURES),
    'forbidden_features_used': sorted(set(FEATURES) & FORBIDDEN),
    'episode_partition_leaks': int(episode_leak),
    'missing_fraction_top10': model_dev[FEATURES].isna().mean().sort_values(ascending=False).head(10).to_dict(),
    'baseline_classes': baseline_bundle['event_model'].classes_.tolist(),
}
(ARTIFACT_ROOT / 'development_audit.json').write_text(json.dumps(audit, indent=2))
display(pd.Series(audit, name='value').to_frame())
print('PASS: compliant feature and development-partition checks succeeded.')
"""),
md("## 3. Strict point and incident metrics"),
code(r"""def point_metrics(y_true, y_pred, score):
    y_true = np.asarray(y_true, int); y_pred = np.asarray(y_pred, int); score = np.asarray(score, float)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0,1]).ravel()
    return {
        'tp': int(tp), 'fp': int(fp), 'fn': int(fn), 'tn': int(tn),
        'precision': precision_score(y_true, y_pred, zero_division=0),
        'recall': recall_score(y_true, y_pred, zero_division=0),
        'f1': f1_score(y_true, y_pred, zero_division=0),
        'auprc': average_precision_score(y_true, score),
    }

def contiguous_predicted_events(group, pred_col, merge_factor=2.5):
    g = group.sort_values('emitted_timestamp_utc')
    dt = g['emitted_timestamp_utc'].diff().dt.total_seconds().div(60)
    cadence = float(dt[dt.gt(0)].median()) if dt.gt(0).any() else 60.0
    gap_limit = max(60.0, merge_factor * cadence)
    times=g.emitted_timestamp_utc.tolist(); pred=g[pred_col].to_numpy(bool)
    events=[]; start=None; previous=None
    for position in np.flatnonzero(pred):
        current=times[position]
        separated=(previous is None or position!=previous+1 or
                   (current-times[previous]).total_seconds()/60>gap_limit)
        if separated:
            if start is not None: events.append({'start':times[start],'end':times[previous]})
            start=position
        previous=position
    if start is not None: events.append({'start':times[start],'end':times[previous]})
    return events

def strict_event_metrics(frame, pred_col):
    true_events = []
    labelled = frame.loc[frame.is_anomaly.eq(1) & frame.episode_id.ne('')]
    for (station, episode), g in labelled.groupby(['station_id','episode_id']):
        true_events.append({
            'station': station, 'episode': episode,
            'start': g.emitted_timestamp_utc.min(), 'end': g.emitted_timestamp_utc.max(),
            'fault': g.anomaly_type.mode().iloc[0] if not g.anomaly_type.mode().empty else 'unknown'
        })

    predicted_events=[]; station_days=0.0
    for station,g in frame.groupby('station_id',sort=False):
        g=g.sort_values('emitted_timestamp_utc')
        span=max((g.emitted_timestamp_utc.iloc[-1]-g.emitted_timestamp_utc.iloc[0]).total_seconds()/86400,1/24)
        station_days += span
        for event in contiguous_predicted_events(g,pred_col):
            predicted_events.append({'station':station,'start':event['start'],'end':event['end']})

    matched_pred=set(); detected=[]; delays=[]; per_fault={}
    for ti,event in enumerate(true_events):
        candidates=[]
        for pi,pred in enumerate(predicted_events):
            if pi in matched_pred or pred['station']!=event['station']: continue
            if pred['start'] <= event['end'] and pred['end'] >= event['start']:
                candidates.append((pi,pred))
        hit=bool(candidates)
        if hit:
            pi,pred=min(candidates,key=lambda x:x[1]['start']); matched_pred.add(pi)
            first=max(pred['start'],event['start'])
            delays.append(max(0,(first-event['start']).total_seconds()/60))
        detected.append(hit)
        per_fault.setdefault(event['fault'],[]).append(hit)

    tp=sum(detected); fn=len(true_events)-tp; fp=len(predicted_events)-len(matched_pred)
    precision=tp/max(tp+fp,1); recall=tp/max(tp+fn,1)
    return {
        'true_episodes':len(true_events),'predicted_episodes':len(predicted_events),
        'event_precision':precision,'event_recall':recall,
        'event_f1':2*precision*recall/max(precision+recall,1e-12),
        'false_alarm_episodes_per_station_day':fp/max(station_days,1e-12),
        'delay_median_min':float(np.median(delays)) if delays else None,
        'delay_p90_min':float(np.quantile(delays,.90)) if delays else None,
        'delay_mean_min':float(np.mean(delays)) if delays else None,
        'per_fault_episode_recall':{k:float(np.mean(v)) for k,v in sorted(per_fault.items())},
    }

def apply_hysteresis(frame, score_col, start_threshold, continue_threshold):
    result=pd.Series(False,index=frame.index)
    for _,g in frame.groupby('station_id',sort=False):
        g=g.sort_values('emitted_timestamp_utc'); active=False; out=np.zeros(len(g),dtype=bool)
        for position,score in enumerate(g[score_col].fillna(0).to_numpy(float)):
            if not active and score >= start_threshold: active=True
            elif active and score < continue_threshold: active=False
            out[position]=active
        result.loc[g.index]=out
    return result

def evaluate(frame, score_col, pred_col):
    return {**point_metrics(frame.is_anomaly,frame[pred_col],frame[score_col]),
            **strict_event_metrics(frame,pred_col)}
"""),
md("## 4. Reproduce the compliant Phase 10 baseline on development blocks"),
code(r"""event_model = baseline_bundle['event_model']
fault_index = list(event_model.classes_).index('sensor_fault')
weather_index = list(event_model.classes_).index('genuine_weather')
X_all = model_dev[FEATURES].replace([np.inf,-np.inf],np.nan)
base_proba = event_model.predict_proba(X_all)
model_dev['baseline_fault_score'] = base_proba[:,fault_index]
model_dev['baseline_weather_score'] = base_proba[:,weather_index]
base_threshold = baseline_bundle['policy']['known_station']['threshold']
model_dev['baseline_pred'] = model_dev.baseline_fault_score.ge(base_threshold)

baseline_rows=[]
for split in ['tune_model','fusion_fit','calibrate','policy_select']:
    part=model_dev.loc[model_dev.dev_split.eq(split)].copy()
    baseline_rows.append({'variant':'phase10_compliant','split':split,**evaluate(part,'baseline_fault_score','baseline_pred')})
baseline_dev=pd.DataFrame(baseline_rows)
display(baseline_dev[['split','precision','recall','f1','auprc','event_precision','event_recall','event_f1',
                      'false_alarm_episodes_per_station_day','delay_median_min']])
"""),
md(r"""## 5. Unified deterministic rules and specialist evidence

Rules use operational fields only. `anomaly_type`, `stream_action`, clean/original values, and labels are never inputs. Dropout remains an incident-level stream event because no reading exists at a dropped timestamp; it must not be faked as a row prediction.
"""),
code(r"""def sigmoid(x): return 1/(1+np.exp(-np.clip(np.asarray(x,float),-30,30)))

def row_max(frame, columns, absolute=False):
    values=frame[columns].to_numpy(float)
    if absolute: values=np.abs(values)
    values=np.where(np.isfinite(values),values,np.nan)
    out=np.nanmax(values,axis=1)
    return np.nan_to_num(out,nan=0.0,posinf=1e6,neginf=0.0)

def add_operational_scores(frame):
    z=frame.copy()
    z['rule_duplicate'] = z.duplicated(['station_id','emitted_timestamp_utc'],keep=False).astype(float)
    z['rule_timestamp'] = z['out_of_order_indicator'].fillna(0).gt(0).astype(float)
    z['rule_physical'] = (
        (z.temperature_value.notna() & ~z.temperature_value.between(-60,60)) |
        (z.pressure_value.notna() & ~z.pressure_value.between(800,1100)) |
        (z.humidity_value.notna() & ~z.humidity_value.between(0,100))
    ).astype(float)
    z['rule_missing'] = z.primary_missing_count.fillna(0).gt(0).astype(float)
    z['rule_gap_soft'] = sigmoid((z.gap_ratio.fillna(1)-2.5)/0.5)
    z['hard_rule'] = z[['rule_duplicate','rule_timestamp','rule_physical']].max(axis=1)

    rz=['temperature_robust_z_24h','pressure_robust_z_24h','humidity_robust_z_24h']
    z['specialist_spike'] = sigmoid((row_max(z,rz,True)-3.0)/0.7)
    frozen=['temperature_frozen_run_length','pressure_frozen_run_length','humidity_frozen_run_length']
    z['specialist_frozen'] = sigmoid((row_max(z,frozen)-5.0)/1.5)
    slope=[f'{s}_neighbor_residual_slope_{w}h' for s in ['temperature','pressure','humidity'] for w in [6,12,24]]
    z['specialist_drift'] = sigmoid((row_max(z,slope,True)-0.8)/0.3)
    cusum=[f'{s}_cusum_{direction}' for s in ['temperature','pressure','humidity'] for direction in ['positive','negative']]
    z['specialist_bias'] = sigmoid((row_max(z,cusum,True)-5.0)/1.5)
    disagreement=['regional_standardized_disagreement_max','regional_trend_disagreement_mean']
    z['specialist_spatial'] = sigmoid((row_max(z,disagreement,True)-2.0)/0.6)
    z['rule_specialist_score'] = z[['hard_rule','rule_missing','rule_gap_soft','specialist_spike',
                                      'specialist_frozen','specialist_drift','specialist_bias','specialist_spatial']].max(axis=1)
    return z

model_dev=add_operational_scores(model_dev)
RULE_COLS=['hard_rule','rule_missing','rule_gap_soft','specialist_spike','specialist_frozen',
           'specialist_drift','specialist_bias','specialist_spatial','rule_specialist_score']
display(model_dev[RULE_COLS].describe().T)
"""),
md("## 6. Five-seed GPU CatBoost fault and weather models"),
code(r"""def fit_or_load_catboost(target, prefix):
    train_mask=model_dev.dev_split.eq('train')
    tune_mask=model_dev.dev_split.eq('tune_model')
    y_train=model_dev.loc[train_mask,target].astype(int)
    ratio=(len(y_train)-y_train.sum())/max(y_train.sum(),1)
    positive_weight=min(math.sqrt(ratio),15.0)
    models=[]; histories=[]
    for seed in SEEDS:
        path=ARTIFACT_ROOT/f'{prefix}_seed{seed}.cbm'
        model=CatBoostClassifier(
            iterations=1200,depth=8,learning_rate=0.035,loss_function='Logloss',eval_metric='PRAUC',
            scale_pos_weight=positive_weight,random_seed=seed,l2_leaf_reg=6.0,random_strength=0.5,
            task_type='GPU',devices='0',verbose=100,od_type='Iter',od_wait=100,
            allow_writing_files=False
        )
        if REUSE_SAVED_MODELS and path.exists():
            model.load_model(path)
        else:
            model.fit(model_dev.loc[train_mask,FEATURES],y_train,
                      eval_set=(model_dev.loc[tune_mask,FEATURES],model_dev.loc[tune_mask,target].astype(int)),
                      use_best_model=True)
            model.save_model(path)
        models.append(model)
        histories.append({'seed':seed,'best_iteration':int(model.get_best_iteration())})
    return models,histories

if RUN_CATBOOST:
    fault_models,fault_history=fit_or_load_catboost('is_anomaly','cat_fault')
    weather_models,weather_history=fit_or_load_catboost('is_weather_event','cat_weather')
    model_dev['cat_fault_score']=np.mean([m.predict_proba(model_dev[FEATURES])[:,1] for m in fault_models],axis=0)
    model_dev['cat_weather_score']=np.mean([m.predict_proba(model_dev[FEATURES])[:,1] for m in weather_models],axis=0)
else:
    fault_models=weather_models=[]; fault_history=weather_history=[]
    model_dev['cat_fault_score']=model_dev.baseline_fault_score
    model_dev['cat_weather_score']=model_dev.baseline_weather_score

print('Fault models:',fault_history)
print('Weather models:',weather_history)
"""),
md(r"""## 7. Optional causal TCN ablation

The TCN uses fixed-length sequences within one station and one development partition. It never crosses station/split boundaries. It is advisory until calibrated fusion proves a benefit without violating false-alarm constraints.
"""),
code(r"""TCN_FEATURES=[
 'temperature_value','pressure_value','humidity_value',
 'temperature_robust_z_24h','pressure_robust_z_24h','humidity_robust_z_24h',
 'neighbor_temperature_residual','neighbor_pressure_residual','neighbor_humidity_residual',
 'temperature_slope_6h','pressure_slope_6h','humidity_slope_6h',
 'temperature_slope_24h','pressure_slope_24h','humidity_slope_24h',
 'temperature_neighbor_residual_slope_12h','pressure_neighbor_residual_slope_12h','humidity_neighbor_residual_slope_12h',
 'temperature_cusum_positive','temperature_cusum_negative',
 'pressure_cusum_positive','pressure_cusum_negative',
 'humidity_cusum_positive','humidity_cusum_negative',
 'regional_agreement_mean','regional_standardized_disagreement_max'
]
assert all(c in model_dev for c in TCN_FEATURES)
SEQ_LEN=48

train_mask=model_dev.dev_split.eq('train')
median=model_dev.loc[train_mask,TCN_FEATURES].median()
iqr=(model_dev.loc[train_mask,TCN_FEATURES].quantile(.75)-model_dev.loc[train_mask,TCN_FEATURES].quantile(.25)).replace(0,1)

class StationWindowDataset(Dataset):
    def __init__(self,frame,split_name):
        self.frame=frame.loc[frame.dev_split.eq(split_name)].copy().sort_values(['station_id','emitted_timestamp_utc'])
        values=((self.frame[TCN_FEATURES]-median)/iqr).replace([np.inf,-np.inf],np.nan).fillna(0)
        self.x=values.clip(-12,12).to_numpy(np.float32)
        self.y=self.frame.is_anomaly.to_numpy(np.float32)
        self.row_index=self.frame.index.to_numpy()
        self.ends=[]
        station=self.frame.station_id.to_numpy()
        timestamps=self.frame.emitted_timestamp_utc.to_numpy(dtype='datetime64[ns]')
        gaps=np.r_[np.nan,np.diff(timestamps)/np.timedelta64(1,'m')]
        for end in range(SEQ_LEN-1,len(self.frame)):
            if station[end]!=station[end-SEQ_LEN+1]: continue
            cadence=gaps[end-SEQ_LEN+2:end+1]
            positive=cadence[cadence>0]
            if len(positive)==0: continue
            # Reject windows containing a communication gap larger than three local cadences.
            if np.nanmax(cadence) <= 3.0*np.median(positive): self.ends.append(end)
        self.ends=np.asarray(self.ends,dtype=np.int64)
        self.labels=self.y[self.ends]
    def __len__(self): return len(self.ends)
    def __getitem__(self,i):
        end=self.ends[i]; start=end-SEQ_LEN+1
        return torch.from_numpy(self.x[start:end+1]),torch.tensor(self.y[end]),torch.tensor(self.row_index[end])

class Chomp1d(nn.Module):
    def __init__(self,n): super().__init__(); self.n=n
    def forward(self,x): return x[:,:,:-self.n] if self.n else x

class TCNBlock(nn.Module):
    def __init__(self,channels,dilation,dropout=.12):
        super().__init__(); pad=2*dilation
        self.net=nn.Sequential(
            nn.Conv1d(channels,channels,3,padding=pad,dilation=dilation),Chomp1d(pad),nn.GELU(),nn.Dropout(dropout),
            nn.Conv1d(channels,channels,3,padding=pad,dilation=dilation),Chomp1d(pad),nn.GELU(),nn.Dropout(dropout))
        self.norm=nn.BatchNorm1d(channels)
    def forward(self,x): return self.norm(x+self.net(x))

class CausalTCN(nn.Module):
    def __init__(self,n_features,channels=64):
        super().__init__(); self.input=nn.Conv1d(n_features,channels,1)
        self.blocks=nn.Sequential(*[TCNBlock(channels,d) for d in [1,2,4,8,16]])
        self.head=nn.Sequential(nn.Linear(channels,32),nn.GELU(),nn.Dropout(.1),nn.Linear(32,1))
    def forward(self,x):
        z=self.blocks(self.input(x.transpose(1,2)))
        return self.head(z[:,:,-1]).squeeze(1)
"""),
code(r"""def predict_tcn(model,dataset,batch_size=1024):
    loader=DataLoader(dataset,batch_size=batch_size,shuffle=False,num_workers=2,pin_memory=True)
    rows=[]; scores=[]; model.eval()
    with torch.no_grad():
        for xb,_,idx in loader:
            logits=model(xb.to(DEVICE,non_blocking=True))
            rows.extend(idx.numpy().tolist()); scores.extend(torch.sigmoid(logits).cpu().numpy().tolist())
    return pd.Series(scores,index=rows,dtype=float)

tcn_path=ARTIFACT_ROOT/'causal_tcn.pt'
tcn_history=[]
if RUN_TCN:
    ds_train=StationWindowDataset(model_dev,'train')
    ds_tune=StationWindowDataset(model_dev,'tune_model')
    positives=max(ds_train.labels.sum(),1); negatives=len(ds_train)-positives
    sample_weight=np.where(ds_train.labels==1,min(math.sqrt(negatives/positives),15),1.0)
    sampler=WeightedRandomSampler(sample_weight,num_samples=min(len(ds_train),240000),replacement=True)
    train_loader=DataLoader(ds_train,batch_size=512,sampler=sampler,num_workers=2,pin_memory=True)
    tune_loader=DataLoader(ds_tune,batch_size=1024,shuffle=False,num_workers=2,pin_memory=True)
    tcn=CausalTCN(len(TCN_FEATURES)).to(DEVICE)
    optimizer=torch.optim.AdamW(tcn.parameters(),lr=8e-4,weight_decay=2e-4)
    criterion=nn.BCEWithLogitsLoss(pos_weight=torch.tensor(min(math.sqrt(negatives/positives),15),device=DEVICE))
    scaler=torch.cuda.amp.GradScaler(enabled=DEVICE=='cuda')
    best=-1; patience=0
    if REUSE_SAVED_MODELS and tcn_path.exists():
        tcn.load_state_dict(torch.load(tcn_path,map_location=DEVICE))
    else:
        for epoch in range(1,13):
            tcn.train(); losses=[]
            for xb,yb,_ in train_loader:
                xb=xb.to(DEVICE,non_blocking=True); yb=yb.to(DEVICE,non_blocking=True)
                optimizer.zero_grad(set_to_none=True)
                with torch.cuda.amp.autocast(enabled=DEVICE=='cuda'):
                    logits=tcn(xb); loss=criterion(logits,yb)
                scaler.scale(loss).backward(); scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(tcn.parameters(),2.0)
                scaler.step(optimizer); scaler.update(); losses.append(loss.item())
            tune_score=predict_tcn(tcn,ds_tune)
            tune_y=model_dev.loc[tune_score.index,'is_anomaly']
            auprc=average_precision_score(tune_y,tune_score)
            tcn_history.append({'epoch':epoch,'loss':float(np.mean(losses)),'tune_auprc':float(auprc)})
            print(tcn_history[-1])
            if auprc>best+1e-4:
                best=auprc; patience=0; torch.save(tcn.state_dict(),tcn_path)
            else:
                patience+=1
                if patience>=3: break
        tcn.load_state_dict(torch.load(tcn_path,map_location=DEVICE))

    model_dev['tcn_score']=model_dev.cat_fault_score
    for split in model_dev.dev_split.unique():
        ds=StationWindowDataset(model_dev,split)
        score=predict_tcn(tcn,ds)
        model_dev.loc[score.index,'tcn_score']=score
else:
    tcn=None; model_dev['tcn_score']=model_dev.cat_fault_score

print('TCN history:',tcn_history[-5:])
"""),
md(r"""## 8. Leakage-safe fusion and probability calibration

- Fusion weights are fitted only on May–June 2023.
- Platt and isotonic calibration are fitted only on July–September 2023.
- The calibration method is chosen by Brier score, then expected calibration error.
- Alert thresholds and hysteresis are selected only on October–December 2023.
"""),
code(r"""META_COLS=['baseline_fault_score','cat_fault_score','tcn_score','rule_missing','rule_gap_soft',
           'specialist_spike','specialist_frozen','specialist_drift','specialist_bias','specialist_spatial']

fusion_mask=model_dev.dev_split.eq('fusion_fit')
fusion=LogisticRegression(class_weight='balanced',max_iter=3000,C=.5,random_state=17)
fusion.fit(model_dev.loc[fusion_mask,META_COLS].fillna(0),model_dev.loc[fusion_mask,'is_anomaly'])
model_dev['fusion_raw']=fusion.predict_proba(model_dev[META_COLS].fillna(0))[:,1]

cal_mask=model_dev.dev_split.eq('calibrate')
y_cal=model_dev.loc[cal_mask,'is_anomaly'].astype(int)
raw_cal=np.clip(model_dev.loc[cal_mask,'fusion_raw'].to_numpy(),1e-6,1-1e-6)
logit_cal=np.log(raw_cal/(1-raw_cal)).reshape(-1,1)
platt=LogisticRegression(C=1.0,max_iter=2000).fit(logit_cal,y_cal)
isotonic=IsotonicRegression(out_of_bounds='clip').fit(raw_cal,y_cal)

def expected_calibration_error(y,p,bins=15):
    y=np.asarray(y); p=np.asarray(p); edges=np.linspace(0,1,bins+1); ece=0.0
    for lo,hi in zip(edges[:-1],edges[1:]):
        mask=(p>=lo)&(p<(hi if hi<1 else hi+1e-12))
        if mask.any(): ece+=mask.mean()*abs(y[mask].mean()-p[mask].mean())
    return float(ece)

cal_candidates={
    'platt':platt.predict_proba(logit_cal)[:,1],
    'isotonic':isotonic.transform(raw_cal)
}
calibration_table=[]
for name,p in cal_candidates.items():
    calibration_table.append({'method':name,'brier':brier_score_loss(y_cal,p),
                              'log_loss':log_loss(y_cal,np.clip(p,1e-6,1-1e-6)),
                              'ece':expected_calibration_error(y_cal,p)})
calibration_table=pd.DataFrame(calibration_table).sort_values(['brier','ece'])
CALIBRATION_METHOD=calibration_table.iloc[0].method

def calibrate_scores(raw):
    raw=np.clip(np.asarray(raw,float),1e-6,1-1e-6)
    if CALIBRATION_METHOD=='platt':
        return platt.predict_proba(np.log(raw/(1-raw)).reshape(-1,1))[:,1]
    return isotonic.transform(raw)

model_dev['fusion_calibrated']=calibrate_scores(model_dev.fusion_raw)
model_dev['hybrid_score']=np.maximum(model_dev.fusion_calibrated,model_dev.hard_rule)
display(calibration_table)
print('Selected:',CALIBRATION_METHOD)
"""),
md("## 9. Select alert threshold and hysteresis on the policy block only"),
code(r"""FALSE_ALARM_BUDGET=0.02
MIN_POINT_PRECISION=0.75

def select_policy(frame,score_col):
    rows=[]
    for start in np.linspace(.10,.95,15):
        for delta in [0,.08]:
            cont=max(0,start-delta)
            work=frame.copy(); work['candidate_pred']=apply_hysteresis(work,score_col,start,cont)
            metrics=evaluate(work,score_col,'candidate_pred')
            f2=5*metrics['event_precision']*metrics['event_recall']/max(4*metrics['event_precision']+metrics['event_recall'],1e-12)
            rows.append({'start_threshold':start,'continue_threshold':cont,'event_f2':f2,**metrics})
    frontier=pd.DataFrame(rows)
    feasible=frontier.loc[(frontier.precision>=MIN_POINT_PRECISION)&
                          (frontier.false_alarm_episodes_per_station_day<=FALSE_ALARM_BUDGET)]
    if len(feasible):
        selected=feasible.sort_values(['event_f2','f1','delay_median_min'],ascending=[False,False,True]).iloc[0]
        status='constraints_met'
    else:
        frontier['violation']=(np.maximum(0,MIN_POINT_PRECISION-frontier.precision)/MIN_POINT_PRECISION+
            np.maximum(0,frontier.false_alarm_episodes_per_station_day-FALSE_ALARM_BUDGET)/FALSE_ALARM_BUDGET)
        selected=frontier.sort_values(['violation','event_f2'],ascending=[True,False]).iloc[0]
        status='pareto_fallback'
    return selected,frontier,status

policy_frame=model_dev.loc[model_dev.dev_split.eq('policy_select')].copy()
selected_policy,frontier,POLICY_STATUS=select_policy(policy_frame,'hybrid_score')
frontier.to_csv(ARTIFACT_ROOT/'calibration_policy_frontier.csv',index=False)
display(selected_policy.to_frame('selected'))
print('Policy status:',POLICY_STATUS)
"""),
md("## 10. Development ablation and fault-level diagnosis"),
code(r"""def evaluate_variant(frame,name,score_col,start,cont=None):
    work=frame.copy(); cont=start if cont is None else cont
    work['pred']=apply_hysteresis(work,score_col,float(start),float(cont))
    return {'variant':name,'development_block':'policy_select',**evaluate(work,score_col,'pred')}

ablation=[]
ablation.append(evaluate_variant(policy_frame,'Phase10 fixed policy','baseline_fault_score',base_threshold,base_threshold))
for name,col in [
    ('Rules and specialists only','rule_specialist_score'),
    ('GPU CatBoost 5-seed','cat_fault_score'),
    ('Causal TCN only','tcn_score'),
    ('Calibrated hybrid','hybrid_score')]:
    chosen,_,status=select_policy(policy_frame,col)
    row=evaluate_variant(policy_frame,name,col,chosen.start_threshold,chosen.continue_threshold)
    row['policy_status']=status; ablation.append(row)

ablation=pd.DataFrame(ablation)
ablation.to_csv(ARTIFACT_ROOT/'development_ablation.csv',index=False)
display(ablation[['variant','precision','recall','f1','auprc','event_precision','event_recall','event_f1',
                  'false_alarm_episodes_per_station_day','delay_median_min']])

winning=policy_frame.copy()
winning['pred']=apply_hysteresis(winning,'hybrid_score',selected_policy.start_threshold,selected_policy.continue_threshold)
event_detail=strict_event_metrics(winning,'pred')
fault_table=pd.Series(event_detail['per_fault_episode_recall'],name='episode_recall').sort_values().to_frame()
fault_table.to_csv(ARTIFACT_ROOT/'development_fault_episode_recall.csv')
display(fault_table)
"""),
code(r"""# Five-seed score stability and station-bootstrap interval on the development policy block.
seed_rows=[]
if fault_models:
    for seed,model in zip(SEEDS,fault_models):
        col=f'cat_seed_{seed}'
        policy_frame[col]=model.predict_proba(policy_frame[FEATURES])[:,1]
        # Use one fixed policy for seed stability; never optimize each reported seed independently.
        row=evaluate_variant(policy_frame,f'cat_seed_{seed}',col,
                             selected_policy.start_threshold,selected_policy.continue_threshold)
        seed_rows.append(row)
seed_table=pd.DataFrame(seed_rows)
seed_table.to_csv(ARTIFACT_ROOT/'seed_stability.csv',index=False)
display(seed_table[['variant','precision','recall','f1','auprc','event_recall','false_alarm_episodes_per_station_day']] if len(seed_table) else seed_table)

def station_bootstrap_event_recall(frame,n_boot=500,seed=26073):
    rng=np.random.default_rng(seed); stations=frame.station_id.unique(); values=[]
    for _ in range(n_boot):
        blocks=[]
        for k,station in enumerate(rng.choice(stations,len(stations),replace=True)):
            block=frame.loc[frame.station_id.eq(station)].copy(); block['station_id']=f'{station}_boot{k}'; blocks.append(block)
        values.append(strict_event_metrics(pd.concat(blocks,ignore_index=True),'pred')['event_recall'])
    return np.quantile(values,[.025,.5,.975]).tolist()

bootstrap_ci=station_bootstrap_event_recall(winning)
print('Development event-recall station-bootstrap [2.5%, median, 97.5%]:',bootstrap_ci)
"""),
md(r"""## 11. Weather-source hierarchy

Fault detection is decided first. A row not declared as a fault may be classified as genuine regional weather using the separately trained weather score. The weather model cannot erase a hard communication/physics fault.
"""),
code(r"""def best_f1_threshold(y,score):
    rows=[]
    for threshold in np.linspace(.02,.95,94):
        pred=np.asarray(score)>=threshold
        rows.append((f1_score(y,pred,zero_division=0),threshold,precision_score(y,pred,zero_division=0),recall_score(y,pred,zero_division=0)))
    return max(rows,key=lambda x:x[0])

weather_f1,WEATHER_THRESHOLD,weather_precision,weather_recall=best_f1_threshold(
    policy_frame.is_weather_event,policy_frame.cat_weather_score)
winning['source_prediction']=np.where(winning['pred'],'sensor_fault',
    np.where(winning.cat_weather_score.ge(WEATHER_THRESHOLD),'genuine_weather','normal'))
weather_metrics={
    'threshold':WEATHER_THRESHOLD,'precision':weather_precision,'recall':weather_recall,'f1':weather_f1,
    'weather_to_fault_rate':float(winning.loc[winning.is_weather_event.eq(1),'pred'].mean()),
    'fault_to_weather_rate':float(winning.loc[winning.is_anomaly.eq(1),'source_prediction'].eq('genuine_weather').mean())
}
display(pd.Series(weather_metrics,name='development_policy'))
"""),
md(r"""## 12. First-iteration scope: detection before correction

This iteration intentionally optimizes anomaly/incident recall, false alarms, latency, and weather separation. Root-cause and correction models must not be changed simultaneously because we would not know which change helped.

After this detector is accepted on development evidence, the next controlled notebooks will be:

1. Hierarchical root diagnosis with risk–coverage calibration and deterministic packet overrides.
2. Temperature/pressure/humidity correction with sensor-specific masked predictors and adaptive conformal intervals.
3. Full API/dashboard integration and end-to-end resource benchmark.

Existing corrections remain advisory; humidity remains review-only.
"""),
md(r"""## 13. Save the iteration result block

Send the JSON and CSV files generated by this cell back with the Colab output. Do not unlock tests for ordinary iterations.
"""),
code(r"""best_hybrid=ablation.loc[ablation.variant.eq('Calibrated hybrid')].iloc[0].to_dict()
result_block={
    'iteration':'01_detection_gpu',
    'device':DEVICE,
    'gpu':torch.cuda.get_device_name(0),
    'data_bundle_sha256':sha256_file(BUNDLE_ZIP),
    'features':len(FEATURES),
    'seeds':SEEDS,
    'catboost_fault_history':fault_history,
    'catboost_weather_history':weather_history,
    'tcn_history':tcn_history,
    'calibration_method':CALIBRATION_METHOD,
    'calibration_table':calibration_table.to_dict('records'),
    'policy_status':POLICY_STATUS,
    'selected_policy':selected_policy.to_dict(),
    'development_hybrid':best_hybrid,
    'development_event_recall_ci95':bootstrap_ci,
    'development_fault_episode_recall':event_detail['per_fault_episode_recall'],
    'weather_metrics':weather_metrics,
    'final_tests_opened':bool(UNLOCK_FINAL_TESTS),
}
(ARTIFACT_ROOT/'iteration_result_block.json').write_text(json.dumps(result_block,indent=2,default=float))
joblib.dump({'fusion':fusion,'platt':platt,'isotonic':isotonic,'method':CALIBRATION_METHOD,
             'meta_cols':META_COLS,'features':FEATURES,'selected_policy':selected_policy.to_dict(),
             'weather_threshold':WEATHER_THRESHOLD},ARTIFACT_ROOT/'fusion_policy.joblib')
print(json.dumps(result_block,indent=2,default=float))
print('\nSEND BACK:')
print(ARTIFACT_ROOT/'iteration_result_block.json')
print(ARTIFACT_ROOT/'development_ablation.csv')
print(ARTIFACT_ROOT/'development_fault_episode_recall.csv')
"""),
md(r"""## 14. Frozen final-test gate — leave disabled during iterations

Only set `UNLOCK_FINAL_TESTS=True` after we have reviewed the development artifacts, selected one architecture, frozen all thresholds, and recorded model hashes. Opening tests and then changing the model invalidates the final-test claim.
"""),
code(r"""def score_new_frame(frame):
    frame=frame.loc[frame.available_to_detector.eq(1)].copy().reset_index(drop=True)
    frame=add_operational_scores(frame)
    X=frame[FEATURES].replace([np.inf,-np.inf],np.nan)
    prob=event_model.predict_proba(X)
    frame['baseline_fault_score']=prob[:,fault_index]
    frame['baseline_weather_score']=prob[:,weather_index]
    frame['cat_fault_score']=np.mean([m.predict_proba(X)[:,1] for m in fault_models],axis=0) if fault_models else frame.baseline_fault_score
    frame['cat_weather_score']=np.mean([m.predict_proba(X)[:,1] for m in weather_models],axis=0) if weather_models else frame.baseline_weather_score
    frame['dev_split']='inference'
    frame['tcn_score']=frame.cat_fault_score
    if RUN_TCN and tcn is not None:
        ds=StationWindowDataset(frame,'inference'); score=predict_tcn(tcn,ds); frame.loc[score.index,'tcn_score']=score
    frame['fusion_raw']=fusion.predict_proba(frame[META_COLS].fillna(0))[:,1]
    frame['fusion_calibrated']=calibrate_scores(frame.fusion_raw)
    frame['hybrid_score']=np.maximum(frame.fusion_calibrated,frame.hard_rule)
    frame['candidate_pred']=apply_hysteresis(frame,'hybrid_score',selected_policy.start_threshold,selected_policy.continue_threshold)
    frame['baseline_pred']=frame.baseline_fault_score.ge(base_threshold)
    frame['source_prediction']=np.where(frame.candidate_pred,'sensor_fault',
        np.where(frame.cat_weather_score.ge(WEATHER_THRESHOLD),'genuine_weather','normal'))
    return frame

if not UNLOCK_FINAL_TESTS:
    print('FINAL TESTS REMAIN SEALED. This is correct for an ordinary iteration.')
else:
    assert POLICY_STATUS=='constraints_met', 'Do not open final tests with an infeasible policy.'
    final_rows=[]; all_predictions=[]
    for split in ['time_test','station_test']:
        raw=load_feature_table(split)
        scored=score_new_frame(raw)
        candidate=evaluate(scored,'hybrid_score','candidate_pred')
        baseline=evaluate(scored,'baseline_fault_score','baseline_pred')
        final_rows.extend([
            {'split':split,'variant':'Phase10 fixed policy',**baseline},
            {'split':split,'variant':'Frozen GPU hybrid',**candidate},
        ])
        scored['final_split']=split; all_predictions.append(scored)
    final_report=pd.DataFrame(final_rows)
    display(final_report[['split','variant','precision','recall','f1','auprc','event_precision','event_recall','event_f1',
                          'false_alarm_episodes_per_station_day','delay_median_min']])
    final_report.to_csv(ARTIFACT_ROOT/'FINAL_TEST_REPORT.csv',index=False)
    pd.concat(all_predictions,ignore_index=True).to_parquet(ARTIFACT_ROOT/'FINAL_TEST_PREDICTIONS.parquet',index=False)
"""),
md(r"""## What to return after the first Colab run

Please send:

1. The complete printed `iteration_result_block.json`.
2. `development_ablation.csv`.
3. `development_fault_episode_recall.csv`.
4. Any red error message if a cell fails.
5. GPU model name and total runtime.

Keep `UNLOCK_FINAL_TESTS=False`. From those development results we will decide whether the gain comes from CatBoost, the TCN, the specialist rules, calibration, or hysteresis, and modify only the next highest-value component.
"""),
]


notebook = {
    "cells": cells,
    "metadata": {
        "accelerator": "GPU",
        "colab": {"name": OUTPUT.name, "provenance": []},
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(notebook, indent=1, ensure_ascii=False), encoding="utf-8")
print(OUTPUT)
