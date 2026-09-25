// Reproducible notebook generator; does not package private observations.
const fs = require('fs');
const path = require('path');
const cells = [];
function md(s) { cells.push({cell_type:'markdown', metadata:{}, source:s}); }
function code(s) { cells.push({cell_type:'code', metadata:{}, source:s, outputs:[], execution_count:null}); }
md(`# SkyGuard — IMD-first ML & GPU TCN research training

Configured for the user-selected **2022–2024 NOAA/ISD Indian historical station archive**. Run in Google Colab: Runtime → Change runtime type → T4 GPU → Run all.
Upload authorized CSV observations; this notebook never requests IMD credentials.
The current 1,172-row snapshot supports an audit, not temporal training. If history is insufficient, this notebook exports an audit ZIP and skips training without fabricating history.

**What is trained:** next-reading temperature/pressure/humidity forecasters (persistence, LightGBM and causal TCN), plus an Isolation Forest on historical features. Forecast disagreement is an anomaly evidence signal, not a calibrated hardware-fault probability.
No unlabelled observation is assumed to prove healthy hardware. No synthetic faults or generated weather are mixed into training. Official IMD and legacy NOAA runs are separate. Nothing automatically replaces the production model.

**Data contract:** station_id, timestamp_utc with explicit timezone, temperature_c, pressure_hpa, relative_humidity_pct. Optional provider/source_provider, pressure_type, is_synthetic. Units and pressure semantics must be verified by you from the provider contract. Different pressure types require separate runs. Keep raw source archives privately. Colab upload is a data transfer: only use it if your IMD permission permits this processing.
`);
code(String.raw`%pip -q install lightgbm==4.6.0 scikit-learn==1.6.1 pandas==2.2.3 joblib==1.4.2
import os, json, random, hashlib, platform, shutil, copy
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader
from sklearn.multioutput import MultiOutputRegressor
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler
from lightgbm import LGBMRegressor
import joblib
from google.colab import files
SEED = 26073
random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
print('Device:', DEVICE, torch.cuda.get_device_name(0) if DEVICE == 'cuda' else 'CPU fallback')
OUT = Path('/content/skyguard_imd_training_results'); OUT.mkdir(exist_ok=True)
`);
md(`## Configuration — verify before running
NOAA_ISD_RESEARCH is selected for this run. Upload aws_observations_2022_2024.csv from data/archive/legacy_noaa_aws, never Phase 10 feature/label files. Its known hash activates the reviewed historical configuration. This does not validate IMD deployment.
The 30-day/100-sequence minimum below is an engineering eligibility gate, not evidence of seasonal sufficiency. More seasons and verified fault labels are needed for operational validation.
Pressure type must be homogeneous. MSLP is not automatically interchangeable with station pressure or QNH. Do not set confirmation flags merely to bypass errors.`);
code(String.raw`SOURCE = 'NOAA_ISD_RESEARCH'  # user-selected historical 2022–2024 archive
UNITS_VERIFIED = False  # set True only after confirming deg C, hPa, %RH
PRESSURE_TYPE = 'UNVERIFIED'  # MEAN_SEA_LEVEL_PRESSURE / STATION_PRESSURE / ALTIMETER_QNH
SOURCE_CONFIRMED = False  # provenance checked against your private source receipts
SEQ = 24
MIN_HISTORY_DAYS = 30
MAX_GAP_HOURS = 3.0  # continuity policy, not an IMD polling interval
EPOCHS = 25
BATCH = 256
MAX_TRAIN_SEQUENCES = 100000  # reproducible memory/time limit
MIN_SPLIT_SEQUENCES = 100
uploaded = files.upload()  # upload one or more CSV/CSV.GZ observation files
receipts, frames = [], []
for name, blob in uploaded.items():
    if not (name.endswith('.csv') or name.endswith('.csv.gz')):
        raise ValueError('Only observation CSV or CSV.GZ files are supported')
    receipts.append({'file': Path(name).name, 'sha256': hashlib.sha256(blob).hexdigest(), 'bytes': len(blob)})
    frames.append(pd.read_csv(name, dtype={'station_id': str}))
assert frames, 'Upload observations first'
df = pd.concat(frames, ignore_index=True)
del uploaded, frames
KNOWN_ARCHIVE_SHA256 = '8d1bbfd21cb9032c2242b3215432d2c2490e745e9ea79fa07d27e329c5671d08'
if SOURCE == 'NOAA_ISD_RESEARCH' and len(receipts)==1 and receipts[0]['sha256']==KNOWN_ARCHIVE_SHA256:
    SOURCE_CONFIRMED = True
    UNITS_VERIFIED = True
    PRESSURE_TYPE = 'ALTIMETER_QNH'
    print('Known historical archive verified. This run uses QNH pressure only.')
if SOURCE == 'NOAA_ISD_RESEARCH':
    assert 'pressure_source' in df, 'Historical run requires pressure_source metadata'
    assert PRESSURE_TYPE == 'ALTIMETER_QNH', 'Historical configuration currently supports QNH only'
    # Mark incompatible pressure as missing rather than convert it without a verified contract.
    df.loc[~df.pressure_source.eq('ma1_altimeter'), 'pressure_hpa'] = np.nan
COLS = ['temperature_c', 'pressure_hpa', 'relative_humidity_pct']
assert set(['station_id', 'timestamp_utc'] + COLS) <= set(df), 'Missing required observation fields'
assert SOURCE in ['IMD_AWS', 'NOAA_ISD_RESEARCH']
assert not any(c in df for c in ['has_fault', 'event_label', 'fault_label']), 'Use original observations, not injected/labelled benchmark files'
for c in ['provider', 'source_provider']:
    if c in df and SOURCE == 'IMD_AWS':
        assert df[c].dropna().eq('IMD_AWS').all(), 'Mixed/unsupported provider in IMD run'
if 'is_synthetic' in df:
    assert not df.is_synthetic.astype(str).str.lower().isin(['true', '1', 'yes']).any(), 'Synthetic records rejected'
if 'pressure_type' in df:
    assert df.pressure_type.dropna().eq(PRESSURE_TYPE).all(), 'Mixed or unverified pressure types'
df['station_id'] = df.station_id.str.strip()
timestamp_text = df.timestamp_utc.astype(str)
explicit_zone = timestamp_text.str.contains(r'(?:Z|[+-]\d{2}:?\d{2})$', regex=True)
df['time'] = pd.to_datetime(timestamp_text.where(explicit_zone), utc=True, errors='coerce')
for c in COLS: df[c] = pd.to_numeric(df[c], errors='coerce').replace([np.inf, -np.inf], np.nan)
# Conflicting revisions cannot be resolved without arrival metadata: quarantine all versions.
key = ['station_id', 'time']
df = df.drop_duplicates(key + COLS)
conflict = df.duplicated(key, keep=False)
invalid = df.time.isna() | df.station_id.isna() | df.station_id.eq('') | (df.time > pd.Timestamp.now(tz='UTC'))
audit = {'source': SOURCE, 'input_rows_after_exact_dedup': len(df), 'conflicting_revision_rows': int(conflict.sum()),
         'invalid_identity_or_time_rows': int(invalid.sum()), 'input_receipts': receipts,
         'units_verified': UNITS_VERIFIED, 'pressure_type': PRESSURE_TYPE, 'source_confirmed': SOURCE_CONFIRMED}
df = df.loc[~conflict & ~invalid].sort_values(key).reset_index(drop=True)
# These are broad data sanity screens, not physical fault labels.
usable = df[COLS].notna().all(axis=1) & df.temperature_c.between(-100, 70) & df.pressure_hpa.between(100, 1200) & df.relative_humidity_pct.between(0, 100)
df['usable'] = usable
counts = df.groupby('station_id').size()
audit.update(rows=len(df), stations=len(counts), usable_rows=int(usable.sum()),
             readings_per_station_median=float(counts.median()) if len(counts) else 0,
             missing_counts=df[COLS].isna().sum().to_dict())
span = (df.time.max() - df.time.min()).total_seconds()/86400 if len(df) else 0
audit['span_days'] = span
READY = bool(UNITS_VERIFIED and SOURCE_CONFIRMED and PRESSURE_TYPE != 'UNVERIFIED'
             and span >= MIN_HISTORY_DAYS and len(counts) >= 5)
audit['training_eligible_initial'] = READY
(OUT/'data_audit.json').write_text(json.dumps(audit, indent=2))
print(json.dumps(audit, indent=2))
if not READY: print('AUDIT ONLY: verify semantics and collect repeated station history. Training cells will skip.')
`);
md(`## Leakage controls and sequences
Station IDs are split by a stable SHA-256 ordering. 20% are held out entirely (4 of 24 for this archive). Historical training uses 2022–June 2023; selection July–September 2023; threshold calibration October–December 2023; final test 2024. IMD mode uses chronological 60/15/10/15 percent periods. Every sequence must lie entirely within one partition; time gaps and invalid rows break sequences. No interpolation, shuffled station windows or future neighbour readings are used.
This first notebook deliberately omits spatial features until timestamp/elevation/pressure-compatible neighbours are verified. Evaluation uses the same eligible sequences for every candidate.`);
code(String.raw`def stable_order(s): return hashlib.sha256((str(SEED)+s).encode()).hexdigest()
def features(x):
    return np.concatenate([x[:, -1], x.mean(1), x.std(1), x[:, -1]-x[:, 0]], axis=1)
class Windows(Dataset):
    def __init__(self, values, ends): self.values, self.ends = values, np.asarray(ends)
    def __len__(self): return len(self.ends)
    def __getitem__(self, k):
        i = self.ends[k]
        return self.values[i-SEQ:i], self.values[i]
def materialize(values, ends):
    return np.stack([values[i-SEQ:i] for i in ends]), values[ends]
if READY:
    ids = sorted(df.station_id.unique(), key=stable_order)
    held = set(ids[:max(1, int(len(ids)*0.2))])
    start, finish = df.time.min(), df.time.max()
    cuts = ([pd.Timestamp(t) for t in ['2023-07-01T00:00:00Z','2023-10-01T00:00:00Z','2024-01-01T00:00:00Z']]
            if SOURCE == 'NOAA_ISD_RESEARCH' else [start + (finish-start)*f for f in [.60,.75,.85]])
    partition = np.searchsorted(np.array([t.value for t in cuts]), df.time.astype('int64'), side='right')
    df['partition'] = partition
    # Held-out stations are evaluated only in the final time period.
    df.loc[df.station_id.isin(held), 'partition'] = np.where(partition[df.station_id.isin(held)] == 3, 4, -1)
    ends = {k: [] for k in range(5)}
    for sid, group in df.groupby('station_id', sort=False):
        previous, run, previous_part = None, 0, None
        for i in group.index:
            part, t = int(df.at[i,'partition']), df.at[i,'time']
            continuous = previous is not None and 0 < (t-previous).total_seconds() <= MAX_GAP_HOURS*3600
            run = run+1 if continuous and previous_part == part else 1
            if not df.at[i,'usable'] or part < 0: run = 0
            if run >= SEQ+1 and part >= 0: ends[part].append(i)
            previous, previous_part = t, part
    split_info = {'counts': {str(k):len(v) for k,v in ends.items()}, 'held_out_stations':sorted(held),
                  'boundaries_utc':[t.isoformat() for t in cuts], 'sequence_length':SEQ}
    (OUT/'splits.json').write_text(json.dumps(split_info, indent=2))
    READY = all(len(v) >= MIN_SPLIT_SEQUENCES for v in ends.values())
    print(split_info)
    if not READY: print('AUDIT ONLY: too few continuous sequences in one or more partitions.')
if READY:
    rng = np.random.default_rng(SEED)
    if len(ends[0]) > MAX_TRAIN_SEQUENCES:
        ends[0] = sorted(rng.choice(ends[0], MAX_TRAIN_SEQUENCES, replace=False).tolist())
    scaler = RobustScaler().fit(df.loc[(df.partition==0)&df.usable, COLS])
    values = scaler.transform(df[COLS]).astype('float32')
    Xtr, Ytr = materialize(values, ends[0])
    Xval, Yval = materialize(values, ends[1])
    joblib.dump(scaler, OUT/'scaler.joblib')
`);
md(`## Train LightGBM, Isolation Forest and GPU causal TCN
LightGBM uses CPU; PyTorch uses the selected GPU. Selection uses normalized forecast MAE on the model-selection partition, with early stopping for TCN. This is forecasting performance, not hardware fault recall. Isolation Forest scores are supplementary uncalibrated evidence.`);
code(String.raw`class CausalBlock(nn.Module):
    def __init__(self, cin, cout, dilation):
        super().__init__(); self.pad=2*dilation
        self.conv=nn.Conv1d(cin, cout, 3, dilation=dilation)
    def forward(self, x): return torch.relu(self.conv(nn.functional.pad(x,(self.pad,0))))
class TCN(nn.Module):
    def __init__(self):
        super().__init__()
        self.net=nn.Sequential(CausalBlock(3,32,1),CausalBlock(32,32,2),CausalBlock(32,32,4),CausalBlock(32,32,8))
        self.head=nn.Linear(32,3)
    def forward(self,x): return self.head(self.net(x.transpose(1,2))[:,:,-1])
def neural_predict(model, x):
    model.eval(); chunks=[]
    with torch.no_grad():
        for i in range(0,len(x),BATCH): chunks.append(model(torch.as_tensor(x[i:i+BATCH],device=DEVICE)).cpu().numpy())
    return np.concatenate(chunks)
if READY:
    tree = MultiOutputRegressor(LGBMRegressor(n_estimators=300, learning_rate=.04, num_leaves=15,
                              min_child_samples=40, reg_lambda=2, random_state=SEED, verbosity=-1))
    tree.fit(features(Xtr), Ytr)
    isolation = IsolationForest(n_estimators=200, max_samples=2048, random_state=SEED, n_jobs=2)
    isolation.fit(features(Xtr))
    model=TCN().to(DEVICE); opt=torch.optim.AdamW(model.parameters(),lr=.001,weight_decay=.001)
    loader=DataLoader(Windows(values,ends[0]),batch_size=BATCH,shuffle=True,num_workers=0)
    best=float('inf'); wait=0; history=[]; best_state=None
    for epoch in range(EPOCHS):
        model.train(); total=0
        for x,y in loader:
            x,y=x.to(DEVICE),y.to(DEVICE); opt.zero_grad()
            loss=nn.functional.smooth_l1_loss(model(x),y); loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(),1); opt.step(); total+=loss.item()*len(x)
        val=float(np.abs(neural_predict(model,Xval)-Yval).mean())
        history.append({'epoch':epoch+1,'train_loss':total/len(ends[0]),'validation_mae_scaled':val})
        print(history[-1])
        if val < best: best=val; best_state=copy.deepcopy(model.state_dict()); wait=0
        else: wait+=1
        if wait>=5: break
    model.load_state_dict(best_state)
    predictions={'persistence':Xval[:,-1], 'lightgbm':tree.predict(features(Xval)), 'tcn':neural_predict(model,Xval)}
    selection={k:float(np.abs(v-Yval).mean()) for k,v in predictions.items()}
    winner=min(selection,key=selection.get)
    print('Validation comparison:',selection,'Selected:',winner)
    joblib.dump(tree,OUT/'lightgbm.joblib'); joblib.dump(isolation,OUT/'isolation_forest.joblib')
    torch.save({k:v.cpu() for k,v in model.state_dict().items()},OUT/'tcn_state.pt')
    pd.DataFrame(history).to_csv(OUT/'training_history.csv',index=False)
`);
md(`## Final evaluation and export
The separate calibration partition sets a residual reference threshold at its empirical 99th percentile. This is not a promised 1% false-alarm rate: calibration observations lack confirmed fault labels and time-series samples are dependent. Test sets are never used to select the model or threshold.
No accuracy, fault precision, fault recall or hardware-fault probability is reported without independently adjudicated labels. A lower prediction error alone cannot authorize production fault detection.

All three sensors receive separate empirical residual thresholds and error metrics. The multivariate model takes past temperature, pressure and humidity together, then predicts each channel separately. A spike may create a large forecast residual; persistent residuals may indicate drift. Neither proves a hardware failure. Freeze detection needs sensor resolution and persistence rules; spatial QC needs compatible neighbouring station history; communication gaps need reporting-cadence evidence. Those tasks are not validated by this forecasting experiment.`);
code(String.raw`def predict_candidate(name,x):
    if name=='persistence': return x[:,-1]
    if name=='lightgbm': return tree.predict(features(x))
    return neural_predict(model,x)
result={'source':SOURCE,'training_completed':False,'promoted':False,
        'fault_precision':None,'fault_recall':None,'fault_f1':None,'calibrated_fault_probability':False,
        'reason':'Insufficient verified history/semantics or sequences; see data audit and split counts.'}
if READY:
    Xcal,Ycal=materialize(values,ends[2])
    calibration_errors=np.abs(predict_candidate(winner,Xcal)-Ycal)
    residual=calibration_errors.mean(axis=1)
    channel_thresholds=np.quantile(calibration_errors,.99,axis=0)
    threshold=float(np.quantile(residual,.99))
    comparison={}
    for part,name in [(3,'future_seen_stations'),(4,'future_unseen_stations')]:
        x,y=materialize(values,ends[part]); comparison[name]={}
        for candidate in ['persistence','lightgbm','tcn']:
            p=predict_candidate(candidate,x); error=(p-y)*scaler.scale_
            comparison[name][candidate]={'rows':len(y),'mae':dict(zip(COLS,np.abs(error).mean(0).tolist())),
                'rmse':dict(zip(COLS,np.sqrt((error**2).mean(0)).tolist()))}
        channel_errors=np.abs(predict_candidate(winner,x)-y)
        evidence=channel_errors.mean(1)
        comparison[name]['selected_flagged_fraction']=float((evidence>threshold).mean())
        comparison[name]['per_sensor_flagged_fraction']=dict(zip(COLS,(channel_errors>channel_thresholds).mean(0).tolist()))
        comparison[name]['isolation_forest_score_quantiles']=dict(zip(['p50','p95','p99'],np.quantile(-isolation.score_samples(features(x)),[.5,.95,.99]).tolist()))
    result.update(training_completed=True, selected_model=winner, validation_selection=selection,
                  forecast_evaluation=comparison, residual_threshold=threshold,
                  per_sensor_residual_thresholds_scaled=dict(zip(COLS,channel_thresholds.tolist())),
                  per_sensor_residual_thresholds_native_units=dict(zip(COLS,(channel_thresholds*scaler.scale_).tolist())),
                  reason='Research candidate only: real fault labels, domain validation and runtime parity review required.')
manifest={'artifact_version':'imd-research-v1','source':SOURCE,'features':COLS,'sequence_length':SEQ,
          'max_gap_hours':MAX_GAP_HOURS,'pressure_type':PRESSURE_TYPE,'units':['degC','hPa','percent'],
          'seed':SEED,'python':platform.python_version(),'torch':torch.__version__,
          'promoted':False,'score_semantics':'uncalibrated mean absolute standardized forecast residual',
          'online_inputs':'24 past consecutive readings from one station; score the next actual observation',
          'spatial_features_enabled':False,'raw_observations_in_export':False,
          'predicted_parameters':COLS,
          'fault_types_validated':[],
          'unsupported_claims':['verified hardware diagnosis','drift recall','freeze recall','spatial fault recall','calibrated fault probability'],
          'parameter_contract':{'temperature_c':'air temperature, degC', 'pressure_hpa':PRESSURE_TYPE,
                                'relative_humidity_pct':'relative humidity, percent; historical derived RH is not a direct sensor reading'}}
(OUT/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False))
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
checksums={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file() and p.name!='checksums.json'}
(OUT/'checksums.json').write_text(json.dumps(checksums,indent=2))
shutil.make_archive('/content/SkyGuard_IMD_Training_Results','zip',OUT)
print(json.dumps(result,indent=2))
files.download('/content/SkyGuard_IMD_Training_Results.zip')
`);
md(`## Render handoff — after your Colab run
Return the result ZIP to this project. It contains hashes, data eligibility audit, split boundaries, forecast comparison and model files only when training ran. It contains no API keys or observation rows.
Before activation: review data lineage; measure actual fault precision/recall on adjudicated events; check forecasting/inference feature parity; configure durable station history; test model loading on Render CPU; verify latency/memory; run shadow mode; preserve rollback. Existing production loaders do not automatically understand this new research artifact format.
If audit-only: collect authorized station history or intentionally run a separately labelled NOAA research experiment. Do not lower the gates to make a single snapshot look like temporal training. Do not upload credentials with the ZIP.`);
const notebook={cells,metadata:{kernelspec:{display_name:'Python 3',language:'python',name:'python3'},language_info:{name:'python'},accelerator:'GPU',colab:{name:'SkyGuard_IMD_GPU_Training_Review.ipynb'}},nbformat:4,nbformat_minor:5};
const dest=path.join(__dirname,'..','notebooks','SkyGuard_IMD_GPU_Training_Review.ipynb');
fs.writeFileSync(dest,JSON.stringify(notebook,null,2));
console.log(dest);
