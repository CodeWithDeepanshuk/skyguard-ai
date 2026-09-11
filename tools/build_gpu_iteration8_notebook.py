"""Build GPU Iteration 8: multi-climate curriculum and leave-domain-out confirmation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "notebooks" / "SkyGuard_AI_GPU_Iteration_05_Weak_Fault_Consensus_Colab.ipynb"
OUTPUT = ROOT / "notebooks" / "SkyGuard_AI_GPU_Iteration_08_MultiClimate_Data_Curriculum_Colab.ipynb"
DATA_BUNDLE = ROOT / "deliverables" / "SkyGuard_Iteration8_Development_Data_Bundle.zip"


def md(text: str) -> dict[str, object]:
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text: str) -> dict[str, object]:
    return {
        "cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
        "source": text.splitlines(keepends=True),
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


NEW_BUNDLE_SHA = sha256(DATA_BUNDLE)
OLD_BUNDLE_SHA = sha256(ROOT / "deliverables" / "SkyGuard_GPU_Data_Bundle.zip")
notebook = json.loads(SOURCE.read_text(encoding="utf-8"))

for cell in notebook["cells"]:
    source = "".join(cell.get("source", [])).replace("\ufffd", "-")
    if cell.get("cell_type") == "code":
        cell["execution_count"] = None
        cell["outputs"] = []
        source = source.replace(
            "SEND BACK THESE FILES:",
            "HISTORICAL CHECKPOINT FILES - continue through Iteration 8; do not return these yet:",
        ).replace(
            "SEND BACK THESE ITERATION 7 FILES:",
            "HISTORICAL ITERATION 7 FILES - continue through Iteration 8; do not return these yet:",
        )
    elif cell.get("cell_type") == "markdown":
        source = source.replace(
            "## Return to Codex",
            "## Historical checkpoint - continue running",
        ).replace(
            "## Iteration 7 stop rule",
            "## Historical Iteration 7 stop rule - continue to the new-data phase",
        )
    cell["source"] = source.splitlines(keepends=True)

notebook["cells"][0] = md(r"""# SkyGuard AI — GPU Iteration 8

## Multi-climate data curriculum and leave-domain-out confirmation

Iteration 7 was a valid negative result: the causal TCN and weather calibrator did not transfer because the old curriculum contained only five training weather episodes and one narrow regional-temperature event family. This notebook starts directly from the frozen Iteration 5 development reference and fixes the data support; it does not rerun Iterations 6 or 7.

This notebook:

1. Reconstructs the frozen Iteration 5 India development reference without opening 2024 or 2025.
2. Loads 16 official DWD stations in four climate/neighbor groups at 10-minute cadence.
3. Uses hourly samples for model compatibility while retaining the full 10-minute source archive.
4. Creates 96 balanced training weather events across six physical families and 160 fault incidents across five families.
5. Creates independent 2023 tune, discovery and confirmation events with every climate and family represented in every scope.
6. Trains LightGBM/CatBoost supervised challengers plus clean-only Isolation Forest and a causal LSTM reconstruction autoencoder.
7. Selects among tree-only and unsupervised-consensus variants using tune data only.
8. Promotes nothing unless both domains pass precision, false-alarm, point-F1, event-F1, weather-transfer and weak-fault gates.

DWD 2024 and every 2025 benchmark remain sealed.
""")

notebook["cells"][1] = md(r"""## Run instructions

1. Keep both files in `/content/drive/MyDrive/SkyGuard_AI_GPU/`:
   - `SkyGuard_GPU_Data_Bundle.zip`
   - `SkyGuard_Iteration8_Development_Data_Bundle.zip`
2. Do **not** upload or extract `SkyGuard_Iteration8_Locked_2024_Confirmation.zip` in this run.
3. Select **Runtime → Change runtime type → T4 GPU**.
4. Run all cells in order. Historical cells reconstruct the frozen Iteration 5 development baseline; Iterations 6 and 7 are not rerun.
5. Leave `UNLOCK_FINAL_TESTS=False` and `REUSE_SAVED_MODELS=True`.
6. Expected first-run time is approximately 90–180 minutes with the LSTM autoencoder. Reusing saved DWD features/models is faster.
7. Return the Iteration 8 result files printed by the final cell.
""")

notebook["cells"].extend([
    md(r"""# Iteration 8 controlled new-data phase

The frozen Iteration 5 development reference and former blind benchmark are immutable. This section opens only the new DWD 2022–2023 development bundle. It does not load DWD 2024, NOAA 2024, or any 2025 observation/label file.
"""),
    code(f'''import sys,shutil

ITER8_ROOT=DRIVE_ROOT/'experiments'/'iteration_08_multiclimate_data_curriculum'
ITER8_ROOT.mkdir(parents=True,exist_ok=True)
ITER8_BUNDLE_ZIP=DRIVE_ROOT/'SkyGuard_Iteration8_Development_Data_Bundle.zip'
ITER8_EXTRACT_ROOT=Path('/content/skyguard_iteration8')
ITER8_DATA_ROOT=ITER8_EXTRACT_ROOT/'SkyGuard_Iteration8_Development_Data_Bundle'
ITER8_EXPECTED_SHA='{NEW_BUNDLE_SHA}'
OLD_EXPECTED_SHA='{OLD_BUNDLE_SHA}'

def sha256_file(path):
    digest=hashlib.sha256()
    with open(path,'rb') as handle:
        for block in iter(lambda:handle.read(1024*1024),b''): digest.update(block)
    return digest.hexdigest()

assert UNLOCK_FINAL_TESTS is False
assert ITER8_BUNDLE_ZIP.exists(),f'Missing {{ITER8_BUNDLE_ZIP}}'
assert sha256_file(ITER8_BUNDLE_ZIP)==ITER8_EXPECTED_SHA,'Iteration 8 development bundle hash mismatch.'
assert sha256_file(BUNDLE_ZIP)==OLD_EXPECTED_SHA,'Original GPU data bundle hash mismatch.'
ITER8_EXTRACT_ROOT.mkdir(parents=True,exist_ok=True)
if not ITER8_DATA_ROOT.exists():
    with zipfile.ZipFile(ITER8_BUNDLE_ZIP) as archive: archive.extractall(ITER8_EXTRACT_ROOT)
members=[str(path.relative_to(ITER8_DATA_ROOT)).lower() for path in ITER8_DATA_ROOT.rglob('*') if path.is_file()]
assert not any('2024' in name or '2025' in name for name in members),'Locked year leaked into development bundle.'
sys.path.insert(0,str(ITER8_DATA_ROOT/'src'))
print({{'iteration8_root':str(ITER8_ROOT),'bundle_sha256':ITER8_EXPECTED_SHA,'files':len(members)}})
'''),
    md(r"""## 32. Load and audit the new official DWD development corpus

The model sees temperature, sea-level-reduced pressure and relative humidity. Raw station pressure, source quality code, station elevation and transformation metadata remain audit fields and are not model features. Dew point is blanked before feature generation.
"""),
    code(r"""from skyguard.faults.curriculum import (
    FAULT_FAMILIES,WEATHER_FAMILIES,MultiClimateCurriculum)
from skyguard.features.builder import FeatureBuilder
from skyguard.features.contracts import FeatureConfig,OUTPUT_COLUMNS
from skyguard.features.neighbors import NeighborIndex
from skyguard.features.temporal import TemporalFeatureBuilder
from skyguard.features.phase10 import PHASE10_FEATURES,add_phase10_features,fit_climatology

I8_DATA=ITER8_DATA_ROOT/'data'
I8_CONFIG=ITER8_DATA_ROOT/'config'/'iteration8_dwd_stations.csv'
i8_source_report=json.loads((ITER8_DATA_ROOT/'reports'/'iteration8_dwd_data_validation.json').read_text())
assert i8_source_report['status']=='PASS'
assert i8_source_report['split_safety']['2025_loaded'] is False

def load_dwd(year):
    frame=pd.read_csv(I8_DATA/f'dwd_aws_10min_{year}.csv.gz',low_memory=False)
    frame['station_id']=frame.station_id.astype(str)
    timestamp=pd.to_datetime(frame.timestamp_utc,utc=True)
    frame=frame.loc[timestamp.dt.minute.eq(0)].copy().reset_index(drop=True)
    frame['timestamp_utc']=pd.to_datetime(frame.timestamp_utc,utc=True).dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    frame['dew_point_c']=''
    return frame

dwd22_raw=load_dwd(2022); dwd23_raw=load_dwd(2023)
assert dwd22_raw.station_id.nunique()==16 and dwd23_raw.station_id.nunique()==16
assert dwd22_raw.cluster.nunique()==4 and dwd23_raw.cluster.nunique()==4
assert dwd22_raw.year.eq(2022).all() and dwd23_raw.year.eq(2023).all()
assert not any('2024' in value or '2025' in value for value in dwd22_raw.source.astype(str).unique())
display(pd.DataFrame([
    {'year':2022,'rows_10min':i8_source_report['yearly'][0]['rows'],'hourly_rows':len(dwd22_raw),'stations':dwd22_raw.station_id.nunique()},
    {'year':2023,'rows_10min':i8_source_report['yearly'][1]['rows'],'hourly_rows':len(dwd23_raw),'stations':dwd23_raw.station_id.nunique()},
]))
"""),
    md(r"""## 33. Build balanced physical weather and fault curricula

Every 2023 scope contains all four climates, all six weather families and all five fault families. Events never cross scope boundaries or overlap. Genuine weather is a negative class for the fault detector.
"""),
    code(r"""i8_train_injector=MultiClimateCurriculum(dwd22_raw,'dwd_train',seed=8017)
i8_train_injector.build_training('2022-01-08','2022-12-22',weather_repetitions=4,fault_repetitions=8)
i8_validation_scopes={
    'tune':('2023-01-08','2023-04-24'),
    'discovery':('2023-05-05','2023-08-25'),
    'confirmation':('2023-09-05','2023-12-22'),
}
i8_val_injector=MultiClimateCurriculum(dwd23_raw,'dwd_validation',seed=8023)
i8_val_injector.build_validation(i8_validation_scopes)
i8_train_audit=i8_train_injector.validate(); i8_val_audit=i8_val_injector.validate()
assert i8_train_audit['status']=='PASS' and i8_val_audit['status']=='PASS'
assert i8_train_audit['weather_events']==96 and i8_train_audit['fault_events']==160
assert i8_val_audit['weather_events']==72 and i8_val_audit['fault_events']==60

i8_train_events=i8_train_injector.event_frame(); i8_val_events=i8_val_injector.event_frame()
coverage=(i8_val_events.groupby(['scope','cluster','label_category','anomaly_type']).size()
          .rename('events').reset_index())
assert coverage.events.min()>=1
i8_events=pd.concat([i8_train_events,i8_val_events],ignore_index=True)
i8_events.to_csv(ITER8_ROOT/'iteration8_curriculum_events.csv',index=False)
dwd22=i8_train_injector.frame; dwd23=i8_val_injector.frame
display(pd.DataFrame([i8_train_audit,i8_val_audit],index=['train','validation']))
display(coverage)
del dwd22_raw,dwd23_raw
"""),
    md(r"""## 34. Generate the exact 108-feature causal contract

The same production feature code is applied to the DWD domain. Neighbour lookup uses observations at or before the current timestamp only; station trends use current and prior observations only. The full feature tables are cached in Drive.
"""),
    code(r"""I8_DWD_TRAIN_FEATURES=ITER8_ROOT/'dwd_train_phase10_features.csv.gz'
I8_DWD_VAL_FEATURES=ITER8_ROOT/'dwd_validation_phase10_features.csv.gz'
I8_DWD_PROFILE=ITER8_ROOT/'dwd_phase10_climatology.joblib'
i8_station_frame=pd.read_csv(I8_CONFIG,dtype={'station_id':str,'dwd_numeric_id':str})
i8_stations={str(row['station_id']):{key:str(value) for key,value in row.items()}
              for row in i8_station_frame.to_dict('records')}
i8_intervals={station:60.0 for station in i8_stations}
i8_feature_config=FeatureConfig(max_neighbors=3,neighbor_tolerance_minutes=90.0)

def i8_enforce_numeric_features(frame,label):
    missing=[feature for feature in FEATURES if feature not in frame.columns]
    if missing:
        raise ValueError(f'{label} is missing {len(missing)} contracted features: {missing[:8]}')
    for feature in FEATURES:
        numeric=pd.to_numeric(frame[feature],errors='coerce')
        frame[feature]=numeric.replace([np.inf,-np.inf],np.nan).astype(np.float32)
    bad=[feature for feature in FEATURES
         if not (pd.api.types.is_integer_dtype(frame[feature])
                 or pd.api.types.is_float_dtype(frame[feature])
                 or pd.api.types.is_bool_dtype(frame[feature]))]
    if bad:
        raise TypeError(f'{label} has non-numeric contracted features: {bad}')
    print(label,'numeric feature contract: PASS | features:',len(FEATURES))
    return frame

def i8_base_features(frame,label):
    source=frame.sort_values(['station_id','timestamp_utc'],kind='stable').reset_index(drop=True)
    rows=source.to_dict('records')
    builder=FeatureBuilder(
        TemporalFeatureBuilder(i8_intervals,i8_feature_config),
        NeighborIndex(rows,i8_stations,i8_feature_config))
    output=[]
    for position,row in enumerate(rows,1):
        output.append(builder.transform(row))
        if position%50000==0: print(label,position,'/',len(rows))
    return pd.DataFrame(output,columns=OUTPUT_COLUMNS)

if REUSE_SAVED_MODELS and I8_DWD_TRAIN_FEATURES.exists() and I8_DWD_VAL_FEATURES.exists() and I8_DWD_PROFILE.exists():
    dwd_train=pd.read_csv(I8_DWD_TRAIN_FEATURES,low_memory=False)
    dwd_val=pd.read_csv(I8_DWD_VAL_FEATURES,low_memory=False)
    i8_profiles=joblib.load(I8_DWD_PROFILE)
    print('Reused cached DWD Phase 10 features.')
else:
    dwd_train_base=i8_base_features(dwd22,'DWD 2022')
    i8_profiles=fit_climatology(dwd_train_base)
    joblib.dump(i8_profiles,I8_DWD_PROFILE,compress=3)
    dwd_train=add_phase10_features(dwd_train_base,i8_profiles)
    dwd_train.to_csv(I8_DWD_TRAIN_FEATURES,index=False,compression={'method':'gzip','compresslevel':6})
    del dwd_train_base
    dwd_val_base=i8_base_features(dwd23,'DWD 2023')
    dwd_val=add_phase10_features(dwd_val_base,i8_profiles)
    dwd_val.to_csv(I8_DWD_VAL_FEATURES,index=False,compression={'method':'gzip','compresslevel':6})
    del dwd_val_base

dwd_train=i8_enforce_numeric_features(dwd_train,'DWD train')
dwd_val=i8_enforce_numeric_features(dwd_val,'DWD validation')
assert list(PHASE10_FEATURES)==FEATURES
assert set(FEATURES)<=set(dwd_train.columns) and set(FEATURES)<=set(dwd_val.columns)
assert not ({'temperature_dewpoint_spread_c','hour_sin','hour_cos','day_of_year_sin','day_of_year_cos'}&set(FEATURES))
for frame in (dwd_train,dwd_val):
    frame['station_id']=frame.station_id.astype(str)
    frame['emitted_timestamp_utc']=pd.to_datetime(frame.emitted_timestamp_utc,utc=True)
    frame['episode_id']=frame.episode_id.fillna('').astype(str)
    frame['available_to_detector']=pd.to_numeric(frame.available_to_detector).fillna(0).astype(int)
print({'dwd_train_features':dwd_train.shape,'dwd_validation_features':dwd_val.shape})
del dwd22,dwd23
"""),
    md(r"""## 35. Freeze DWD pseudo-unseen stations and reconstruct the accepted baseline

One station per climate is excluded from all candidate fitting. The existing India-trained detector is evaluated on DWD without adapting its thresholds; this measures genuine domain transfer.
"""),
    code(r"""# Recovery guard: a completed Cell 34 must provide both feature tables.
i8_missing_tables=[name for name in ('dwd_train','dwd_val') if name not in globals()]
if i8_missing_tables:
    if (I8_DWD_TRAIN_FEATURES.exists() and I8_DWD_VAL_FEATURES.exists()
            and I8_DWD_PROFILE.exists()):
        dwd_train=pd.read_csv(I8_DWD_TRAIN_FEATURES,low_memory=False)
        dwd_val=pd.read_csv(I8_DWD_VAL_FEATURES,low_memory=False)
        i8_profiles=joblib.load(I8_DWD_PROFILE)
        for frame in (dwd_train,dwd_val):
            frame['station_id']=frame.station_id.astype(str)
            frame['emitted_timestamp_utc']=pd.to_datetime(frame.emitted_timestamp_utc,utc=True)
            frame['episode_id']=frame.episode_id.fillna('').astype(str)
            frame['available_to_detector']=pd.to_numeric(frame.available_to_detector).fillna(0).astype(int)
            i8_enforce_numeric_features(frame,'Recovered DWD feature table')
        print('Recovered cached DWD feature tables after an interrupted/out-of-order run.')
    else:
        raise RuntimeError(
            'Cell 34 did not complete, so dwd_train/dwd_val do not exist and no cache is available. '
            'Restore the complete corrected Cell 34, run it to completion, then rerun Cell 35.'
        )
del i8_missing_tables

I8_DWD_HOLDOUTS=['DWD-05839','DWD-01684','DWD-04336','DWD-00232']
dwd_train['i8_domain']='dwd'; dwd_val['i8_domain']='dwd'
dwd_train['i8_scope']='train'
dwd_val['i8_scope']=np.select(
    [dwd_val.emitted_timestamp_utc<'2023-05-01',dwd_val.emitted_timestamp_utc<'2023-09-01'],
    ['tune','discovery'],default='confirmation')
i8_scope_map=i8_val_events.set_index('episode_id').scope.to_dict()
event_mask=dwd_val.episode_id.ne('')
dwd_val.loc[event_mask,'i8_scope']=dwd_val.loc[event_mask,'episode_id'].map(i8_scope_map)
assert dwd_val.loc[event_mask].groupby('episode_id').i8_scope.nunique().max()==1

def i8_old_scores(frame):
    X=frame[FEATURES]
    frame['cat_fault_mean']=np.mean([model.predict_proba(X)[:,1] for model in fault_models],axis=0)
    frame['cat_weather_mean']=np.mean([model.predict_proba(X)[:,1] for model in weather_models],axis=0)
    frame['base_score']=apply_platt(base_calibrator,frame.cat_fault_mean)
    for fault,models in specialist_models.items():
        raw=np.mean([model.predict_proba(frame[SPECIALIST_FEATURES[fault]])[:,1] for model in models],axis=0)
        frame[f'{fault}_raw']=raw
        frame[f'{fault}_score']=apply_platt(calibrators[fault],raw)
    frame['rescue_score']=frame[[f'{fault}_score' for fault in SPECIALIST_FEATURES]].max(axis=1)
    scored=add_hard_rules(frame)
    frame['hard_rule']=scored.hard_rule.to_numpy(bool)
    baseline=apply_two_tier(frame,selected.base_start,selected.base_continue,
                            selected.rescue_threshold,int(selected.min_points))
    baseline|=frozen_rule(frame,SELECTED_FROZEN_CONFIG)
    frame['i8_baseline_pred']=baseline.to_numpy(bool)
    frame['i8_baseline_weather']=frame.cat_weather_mean.ge(WEATHER_GUARD_THRESHOLD)
    return frame

dwd_val=i8_old_scores(dwd_val)
print('DWD pseudo-unseen rows:',int(dwd_val.station_id.isin(I8_DWD_HOLDOUTS).sum()))
"""),
    md(r"""## 36. Train domain-balanced CatBoost + LightGBM challengers

India and DWD receive equal aggregate training weight. Positive episode mass is balanced so long incidents cannot dominate. Thresholds are not fitted here; early stopping uses only January–April 2023 tune rows.
"""),
    code(r"""i8_old_train=dev.loc[dev.dev_split.eq('train')&dev.available_to_detector.eq(1)].copy()
i8_old_tune=dev.loc[dev.dev_split.eq('tune_model')&dev.available_to_detector.eq(1)].copy()
i8_old_train['i8_domain']='india'; i8_old_tune['i8_domain']='india'
i8_dwd_fit=dwd_train.loc[~dwd_train.station_id.isin(I8_DWD_HOLDOUTS)&dwd_train.available_to_detector.eq(1)].copy()
i8_dwd_tune=dwd_val.loc[dwd_val.i8_scope.eq('tune')&~dwd_val.station_id.isin(I8_DWD_HOLDOUTS)&dwd_val.available_to_detector.eq(1)].copy()
i8_fit=pd.concat([i8_old_train,i8_dwd_fit],ignore_index=True,sort=False)
i8_tune=pd.concat([i8_old_tune,i8_dwd_tune],ignore_index=True,sort=False)
i8_fit=i8_enforce_numeric_features(i8_fit,'Combined training table')
i8_tune=i8_enforce_numeric_features(i8_tune,'Combined tuning table')

def i8_target(frame,target):
    return frame.is_anomaly.astype(int).to_numpy() if target=='fault' else frame.is_weather_event.astype(int).to_numpy()

def i8_domain_episode_weights(frame,y):
    y=np.asarray(y,bool); weights=np.ones(len(frame),dtype=float)
    positions=np.flatnonzero(y)
    if len(positions):
        positive=frame.iloc[positions][['episode_id','row_id']].copy()
        keys=positive.episode_id.fillna('').astype(str)
        keys=keys.where(keys.ne(''),'single_'+positive.row_id.astype(str))
        lengths=keys.value_counts(); mass=keys.map(lambda key:1.0/lengths.loc[key]).to_numpy(float)
        mass*=len(mass)/max(mass.sum(),1e-12)
        weights[positions]=mass
        imbalance=(len(frame)-len(positions))/max(weights[positions].sum(),1e-12)
        weights[positions]*=min(math.sqrt(imbalance),18.0)
    for _,indices in frame.groupby('i8_domain').indices.items():
        indices=np.asarray(indices,dtype=int)
        weights[indices]*=len(frame)/(len(frame.i8_domain.unique())*max(weights[indices].sum(),1e-12))
    return weights

I8_LGB_SEEDS=[17,41]
i8_models={}; i8_training_history=[]
for target in ['fault','weather']:
    y_fit=i8_target(i8_fit,target); y_tune=i8_target(i8_tune,target)
    weights=i8_domain_episode_weights(i8_fit,y_fit)
    cat_path=ITER8_ROOT/f'iteration8_{target}_catboost.cbm'
    cat=CatBoostClassifier(
        iterations=1500,depth=7,learning_rate=.03,loss_function='Logloss',eval_metric='PRAUC',
        l2_leaf_reg=12,random_strength=.35,random_seed=81,task_type='GPU',devices='0',
        verbose=150,od_type='Iter',od_wait=140,allow_writing_files=False)
    if REUSE_SAVED_MODELS and cat_path.exists(): cat.load_model(cat_path)
    else:
        cat.fit(i8_fit[FEATURES],y_fit,sample_weight=weights,
                eval_set=(i8_tune[FEATURES],y_tune),use_best_model=True)
        cat.save_model(cat_path)
    lgb_models=[]
    for seed in I8_LGB_SEEDS:
        path=ITER8_ROOT/f'iteration8_{target}_lightgbm_seed{seed}.joblib'
        if REUSE_SAVED_MODELS and path.exists(): lgb=joblib.load(path)
        else:
            lgb=LGBMClassifier(
                objective='binary',n_estimators=1800,learning_rate=.025,num_leaves=31,
                min_child_samples=60,subsample=.85,colsample_bytree=.80,
                reg_alpha=1.0,reg_lambda=12.0,random_state=seed,n_jobs=-1,
                verbosity=-1,force_col_wise=True)
            lgb.fit(i8_fit[FEATURES],y_fit,sample_weight=weights,
                    eval_set=[(i8_tune[FEATURES],y_tune)],eval_metric='average_precision',
                    callbacks=[early_stopping(140,verbose=False),log_evaluation(0)])
            joblib.dump(lgb,path)
        lgb_models.append(lgb)
    i8_models[target]={'cat':cat,'lgb':lgb_models}
    i8_training_history.append({
        'target':target,'fit_rows':len(i8_fit),'fit_positives':int(y_fit.sum()),
        'tune_rows':len(i8_tune),'tune_positives':int(y_tune.sum()),
        'catboost_best_iteration':int(max(cat.get_best_iteration(),0)),
        'lightgbm_best_iterations':','.join(str(getattr(model,'best_iteration_',0)) for model in lgb_models)})

pd.DataFrame(i8_training_history).to_csv(ITER8_ROOT/'iteration8_training_history.csv',index=False)
display(pd.DataFrame(i8_training_history))
"""),
    code(r"""def i8_add_candidate_scores(frame):
    frame=i8_enforce_numeric_features(frame,'Candidate scoring table')
    X=frame[FEATURES]
    for target,bundle8 in i8_models.items():
        cat=bundle8['cat'].predict_proba(X)[:,1]
        lgb=np.mean([model.predict_proba(X)[:,1] for model in bundle8['lgb']],axis=0)
        frame[f'i8_{target}_cat']=cat
        frame[f'i8_{target}_lgb']=lgb
        frame[f'i8_{target}_score']=np.sqrt(np.clip(cat,0,1)*np.clip(lgb,0,1))
    return frame

i8_old_eval=dev.loc[~dev.dev_split.eq('train')&dev.available_to_detector.eq(1)].copy()
i8_old_eval['i8_domain']='india'
i8_old_eval['i8_scope']=i8_old_eval.dev_split.map({
    'tune_model':'tune','block_may_jun':'discovery','block_jul_sep':'discovery','block_oct_dec':'confirmation'})
i8_reference_columns={'iteration3_reference','iteration5_rescue'}
assert i8_reference_columns.issubset(i8_old_eval.columns),(
    'Accepted Iteration 5 reference components are missing: '
    f'{sorted(i8_reference_columns-set(i8_old_eval.columns))}')
i8_old_eval['i8_baseline_pred']=(
    i8_old_eval['iteration3_reference'].astype(bool)
    |i8_old_eval['iteration5_rescue'].astype(bool))
i8_old_eval['i8_baseline_weather']=i8_old_eval.cat_weather_mean.ge(WEATHER_GUARD_THRESHOLD)
i8_old_eval=i8_add_candidate_scores(i8_old_eval)
dwd_val=i8_add_candidate_scores(dwd_val)
i8_validation=pd.concat([i8_old_eval,dwd_val],ignore_index=True,sort=False)
i8_validation['row_id']=i8_validation.row_id.astype(str)
print(i8_validation.groupby(['i8_domain','i8_scope']).size())
"""),
    md(r"""## 37. Clean-only unsupervised challengers

The supplied research note correctly suggested Isolation Forest and reconstruction autoencoders, but its example fitted on the corrupted evaluation stream. Here both novelty models are fitted only on 2022 rows labelled as non-fault. Genuine regional-weather rows remain in the normal class so the models are not rewarded for calling weather a sensor failure.

The recurrent model is a unidirectional causal LSTM autoencoder. Every score at time *t* uses only a 24-step window ending at *t*. Raw absolute T/P/RH, dew point, calendar variables, labels and future values are excluded; the inputs are robust temporal and same-parameter neighbour residuals derived from the three permitted observations.
"""),
    code(r"""from sklearn.ensemble import IsolationForest
from torch import nn
from torch.utils.data import DataLoader,TensorDataset

I8_UNSUP_FEATURE_CANDIDATES=[
    'primary_missing_count','time_since_previous_minutes','gap_ratio',
    'regional_agreement_mean','regional_agreement_min',
    'regional_standardized_disagreement_max','regional_trend_disagreement_mean',
]
for sensor in ['temperature','pressure','humidity']:
    I8_UNSUP_FEATURE_CANDIDATES += [
        f'{sensor}_robust_z_24h',f'{sensor}_ewma_residual',f'{sensor}_frozen_run_length',
        f'neighbor_{sensor}_residual',f'neighbor_{sensor}_agreement_fraction',
        f'{sensor}_slope_6h',f'{sensor}_neighbor_residual_slope_6h',
        f'{sensor}_cusum_positive',f'{sensor}_cusum_negative',
    ]
I8_UNSUP_FEATURES=[feature for feature in I8_UNSUP_FEATURE_CANDIDATES if feature in FEATURES]
assert len(I8_UNSUP_FEATURES)>=30
assert not ({'temperature_value','pressure_value','humidity_value','temperature_dewpoint_spread_c',
             'hour_sin','hour_cos','day_of_year_sin','day_of_year_cos'}&set(I8_UNSUP_FEATURES))

I8_UNSUP_PACKAGE=ITER8_ROOT/'iteration8_isolation_forest.joblib'
i8_clean_fit=i8_fit.loc[i8_fit.is_anomaly.eq(0)].copy()

def i8_balanced_sample(frame,max_per_domain,seed):
    pieces=[]
    for domain,group in frame.groupby('i8_domain',sort=True):
        count=min(len(group),int(max_per_domain))
        pieces.append(group.sample(count,random_state=int(seed)+sum(map(ord,str(domain)))))
    return pd.concat(pieces,ignore_index=True)

if REUSE_SAVED_MODELS and I8_UNSUP_PACKAGE.exists():
    i8_unsup_package=joblib.load(I8_UNSUP_PACKAGE)
    i8_unsup_median=np.asarray(i8_unsup_package['median'],dtype=np.float32)
    i8_unsup_scale=np.asarray(i8_unsup_package['scale'],dtype=np.float32)
    i8_iforest=i8_unsup_package['model']
    i8_if_reference=np.asarray(i8_unsup_package['reference'],dtype=np.float32)
else:
    scaler_rows=i8_balanced_sample(i8_clean_fit,90000,8101)
    scaler_values=scaler_rows[I8_UNSUP_FEATURES].apply(pd.to_numeric,errors='coerce').to_numpy(np.float32)
    i8_unsup_median=np.nanmedian(scaler_values,axis=0).astype(np.float32)
    i8_unsup_median=np.where(np.isfinite(i8_unsup_median),i8_unsup_median,0.0).astype(np.float32)
    q25=np.nanpercentile(scaler_values,25,axis=0); q75=np.nanpercentile(scaler_values,75,axis=0)
    iqr=q75-q25
    i8_unsup_scale=np.where(np.isfinite(iqr)&(iqr>=1e-3),iqr,1.0).astype(np.float32)
    scaler_values=np.where(np.isfinite(scaler_values),scaler_values,i8_unsup_median)
    scaler_values=np.clip((scaler_values-i8_unsup_median)/i8_unsup_scale,-12,12)
    i8_iforest=IsolationForest(
        n_estimators=400,max_samples=min(4096,len(scaler_values)),max_features=.85,
        contamination='auto',bootstrap=False,n_jobs=-1,random_state=8101)
    i8_iforest.fit(scaler_values)
    i8_if_reference=np.sort(-i8_iforest.score_samples(scaler_values)).astype(np.float32)
    i8_unsup_package={'features':I8_UNSUP_FEATURES,'median':i8_unsup_median,'scale':i8_unsup_scale,
                      'model':i8_iforest,'reference':i8_if_reference}
    joblib.dump(i8_unsup_package,I8_UNSUP_PACKAGE,compress=3)

assert list(i8_unsup_package['features'])==I8_UNSUP_FEATURES

def i8_scaled_matrix(frame):
    values=frame[I8_UNSUP_FEATURES].apply(pd.to_numeric,errors='coerce').to_numpy(np.float32)
    values=np.where(np.isfinite(values),values,i8_unsup_median)
    return np.clip((values-i8_unsup_median)/i8_unsup_scale,-12,12).astype(np.float32)

def i8_tail_probability(raw,reference):
    reference=np.asarray(reference,dtype=np.float32)
    return np.searchsorted(reference,np.asarray(raw,dtype=np.float32),side='right')/max(len(reference),1)

def i8_isolation_scores(frame):
    raw=-i8_iforest.score_samples(i8_scaled_matrix(frame))
    return np.clip(i8_tail_probability(raw,i8_if_reference),0,1).astype(np.float32)

print({'unsupervised_features':len(I8_UNSUP_FEATURES),'clean_fit_rows':len(i8_clean_fit),
       'iforest_reference_rows':len(i8_if_reference)})
"""),
    code(r"""I8_SEQUENCE_WINDOW=24
I8_LSTM_PATH=ITER8_ROOT/'iteration8_causal_lstm_autoencoder.pt'

class I8CausalLSTMAutoencoder(nn.Module):
    def __init__(self,input_dim,hidden_dim=24):
        super().__init__()
        self.encoder=nn.LSTM(input_dim,hidden_dim,num_layers=1,batch_first=True,bidirectional=False)
        self.decoder=nn.Sequential(nn.Linear(hidden_dim,16),nn.GELU(),nn.Linear(16,input_dim))
    def forward(self,x):
        encoded,_=self.encoder(x)
        return self.decoder(encoded)

def i8_clean_sequences(frame,max_per_domain,seed):
    rng=np.random.default_rng(seed); domain_arrays=[]
    for domain,domain_frame in frame.groupby('i8_domain',sort=True):
        station_pieces=[]; station_groups=list(domain_frame.groupby('station_id',sort=True))
        per_station=max(1,int(np.ceil(max_per_domain/max(len(station_groups),1))))
        for _,group in station_groups:
            group=group.sort_values('emitted_timestamp_utc',kind='stable')
            values=i8_scaled_matrix(group)
            clean=group.is_anomaly.eq(0).to_numpy(bool)
            times=pd.to_datetime(group.emitted_timestamp_utc,utc=True)
            delta=times.diff().dt.total_seconds().div(60).to_numpy(float)
            bad_step=np.zeros(len(group),dtype=np.int32)
            bad_step[1:]=((delta[1:]<=0)|(delta[1:]>90)|~np.isfinite(delta[1:])).astype(np.int32)
            if len(group)<I8_SEQUENCE_WINDOW: continue
            clean_count=np.convolve(clean.astype(np.int32),np.ones(I8_SEQUENCE_WINDOW,dtype=np.int32),'valid')
            prefix=np.cumsum(bad_step); starts=np.arange(len(group)-I8_SEQUENCE_WINDOW+1)
            ends=starts+I8_SEQUENCE_WINDOW-1
            contiguous=(prefix[ends]-prefix[starts])==0
            eligible=starts[(clean_count==I8_SEQUENCE_WINDOW)&contiguous]
            if len(eligible)>per_station: eligible=np.sort(rng.choice(eligible,per_station,replace=False))
            if len(eligible): station_pieces.append(np.stack([values[s:s+I8_SEQUENCE_WINDOW] for s in eligible]))
        if station_pieces:
            domain_values=np.concatenate(station_pieces).astype(np.float32)
            if len(domain_values)>max_per_domain:
                domain_values=domain_values[rng.choice(len(domain_values),max_per_domain,replace=False)]
            domain_arrays.append(domain_values)
    if not domain_arrays: raise RuntimeError('No clean causal sequences were generated.')
    return np.concatenate(domain_arrays).astype(np.float32)

def i8_sequence_errors(model,sequences,batch_size=1024):
    loader=DataLoader(TensorDataset(torch.from_numpy(sequences)),batch_size=batch_size,shuffle=False,num_workers=0)
    values=[]; model.eval()
    with torch.no_grad():
        for (batch,) in loader:
            batch=batch.to(DEVICE)
            reconstruction=model(batch)
            values.append(torch.mean(torch.abs(reconstruction[:,-1]-batch[:,-1]),dim=1).cpu().numpy())
    return np.concatenate(values).astype(np.float32)

torch.manual_seed(8107); torch.cuda.manual_seed_all(8107)
i8_lstm=I8CausalLSTMAutoencoder(len(I8_UNSUP_FEATURES)).to(DEVICE)
i8_lstm_checkpoint=None
if REUSE_SAVED_MODELS and I8_LSTM_PATH.exists():
    i8_lstm_checkpoint=torch.load(I8_LSTM_PATH,map_location=DEVICE,weights_only=False)
    assert list(i8_lstm_checkpoint['features'])==I8_UNSUP_FEATURES
    assert int(i8_lstm_checkpoint['window'])==I8_SEQUENCE_WINDOW
    i8_lstm.load_state_dict(i8_lstm_checkpoint['state_dict'])
    i8_lstm_reference=np.asarray(i8_lstm_checkpoint['reference_errors'],dtype=np.float32)
    i8_lstm_history=i8_lstm_checkpoint['history']
    i8_lstm_train_sequences=int(i8_lstm_checkpoint['train_sequences'])
    i8_lstm_tune_sequences=int(i8_lstm_checkpoint['tune_sequences'])
else:
    i8_train_sequences=i8_clean_sequences(i8_fit,36000,8107)
    i8_tune_sequences=i8_clean_sequences(i8_tune,9000,8111)
    train_loader=DataLoader(TensorDataset(torch.from_numpy(i8_train_sequences)),batch_size=512,
                            shuffle=True,num_workers=0,pin_memory=(DEVICE=='cuda'))
    tune_tensor=torch.from_numpy(i8_tune_sequences).to(DEVICE)
    optimizer=torch.optim.AdamW(i8_lstm.parameters(),lr=8e-4,weight_decay=2e-4)
    loss_fn=nn.SmoothL1Loss(beta=.5)
    best_loss=float('inf'); best_state=None; patience=0; i8_lstm_history=[]
    for epoch in range(1,21):
        i8_lstm.train(); train_losses=[]
        for (batch,) in train_loader:
            batch=batch.to(DEVICE,non_blocking=True); optimizer.zero_grad(set_to_none=True)
            noisy=batch+.025*torch.randn_like(batch)
            reconstruction=i8_lstm(noisy)
            loss=.30*loss_fn(reconstruction,batch)+.70*loss_fn(reconstruction[:,-1],batch[:,-1])
            loss.backward(); torch.nn.utils.clip_grad_norm_(i8_lstm.parameters(),2.0); optimizer.step()
            train_losses.append(float(loss.detach().cpu()))
        i8_lstm.eval()
        with torch.no_grad():
            tune_reconstruction=i8_lstm(tune_tensor)
            tune_loss=float((.30*loss_fn(tune_reconstruction,tune_tensor)+
                             .70*loss_fn(tune_reconstruction[:,-1],tune_tensor[:,-1])).cpu())
        i8_lstm_history.append({'epoch':epoch,'train_loss':float(np.mean(train_losses)),'normal_tune_loss':tune_loss})
        print('LSTM-AE',i8_lstm_history[-1])
        if tune_loss<best_loss-1e-5:
            best_loss=tune_loss; patience=0
            best_state={key:value.detach().cpu().clone() for key,value in i8_lstm.state_dict().items()}
        else:
            patience+=1
            if patience>=4: break
    i8_lstm.load_state_dict(best_state); i8_lstm=i8_lstm.to(DEVICE)
    i8_lstm_reference=np.sort(i8_sequence_errors(i8_lstm,i8_train_sequences)).astype(np.float32)
    i8_lstm_train_sequences=len(i8_train_sequences); i8_lstm_tune_sequences=len(i8_tune_sequences)
    torch.save({'state_dict':i8_lstm.state_dict(),'reference_errors':i8_lstm_reference,
                'history':i8_lstm_history,'features':I8_UNSUP_FEATURES,'window':I8_SEQUENCE_WINDOW,
                'train_sequences':i8_lstm_train_sequences,'tune_sequences':i8_lstm_tune_sequences},I8_LSTM_PATH)
    del i8_train_sequences,i8_tune_sequences,tune_tensor

"""),
    code(r"""def i8_lstm_scores(frame):
    result=pd.Series(0.0,index=frame.index,dtype=float)
    for _,group in frame.groupby('station_id',sort=False):
        group=group.sort_values('emitted_timestamp_utc',kind='stable')
        values=i8_scaled_matrix(group); times=pd.to_datetime(group.emitted_timestamp_utc,utc=True)
        delta=times.diff().dt.total_seconds().div(60).to_numpy(float)
        breaks=np.flatnonzero((delta<=0)|(delta>90)|~np.isfinite(delta))
        starts=np.r_[0,breaks]; ends=np.r_[breaks,len(group)]
        for start,end in zip(starts,ends):
            if end-start<I8_SEQUENCE_WINDOW: continue
            segment=values[start:end]
            sequences=np.stack([segment[pos-I8_SEQUENCE_WINDOW+1:pos+1]
                                for pos in range(I8_SEQUENCE_WINDOW-1,len(segment))]).astype(np.float32)
            errors=i8_sequence_errors(i8_lstm,sequences)
            scores=np.clip(i8_tail_probability(errors,i8_lstm_reference),0,1)
            target_indices=group.index.to_numpy()[start+I8_SEQUENCE_WINDOW-1:end]
            result.loc[target_indices]=scores
    return result.to_numpy(np.float32)

i8_validation['i8_if_score']=i8_isolation_scores(i8_validation)
i8_validation['i8_lstm_ae_score']=i8_lstm_scores(i8_validation)
i8_validation['i8_tree_if_score']=np.maximum(
    i8_validation.i8_fault_score,np.sqrt(i8_validation.i8_fault_score*i8_validation.i8_if_score))
i8_validation['i8_tree_lstm_score']=np.maximum(
    i8_validation.i8_fault_score,np.sqrt(i8_validation.i8_fault_score*i8_validation.i8_lstm_ae_score))
i8_validation['i8_three_model_score']=np.maximum(
    i8_validation.i8_fault_score,
    np.cbrt(i8_validation.i8_fault_score*i8_validation.i8_if_score*i8_validation.i8_lstm_ae_score))
I8_SCORE_VARIANTS={
    'tree_only':'i8_fault_score','tree_plus_isolation_forest':'i8_tree_if_score',
    'tree_plus_lstm_autoencoder':'i8_tree_lstm_score','tree_if_lstm_consensus':'i8_three_model_score'}

i8_unsupervised_history=pd.DataFrame([
    {'model':'IsolationForest','fit_rows':len(i8_if_reference),'features':len(I8_UNSUP_FEATURES),
     'sequence_window':1,'epochs':0},
    {'model':'causal_LSTM_autoencoder','fit_rows':i8_lstm_train_sequences,'features':len(I8_UNSUP_FEATURES),
     'sequence_window':I8_SEQUENCE_WINDOW,'epochs':len(i8_lstm_history)},
])
i8_unsupervised_history.to_csv(ITER8_ROOT/'iteration8_unsupervised_training_history.csv',index=False)
display(i8_unsupervised_history)
display(i8_validation.groupby(['i8_domain','i8_scope'])[['i8_if_score','i8_lstm_ae_score']].quantile(.99))
"""),
    md(r"""## 38. Tune once, then freeze thresholds

Weather threshold is selected first on the tune scope with a strict fault-to-weather cap. The fault threshold is then selected with incident false-alarm and precision constraints. Discovery and confirmation are never searched.
"""),
    code(r"""from sklearn.metrics import average_precision_score

def i8_weather_prediction(frame,threshold):
    agreement=pd.to_numeric(frame.regional_agreement_mean,errors='coerce').fillna(0)
    return frame.i8_weather_score.ge(float(threshold))&agreement.ge(.50)

def i8_weather_metrics(frame,pred):
    y=frame.is_weather_event.astype(int)
    return {
        'precision':float(precision_score(y,pred,zero_division=0)),
        'recall':float(recall_score(y,pred,zero_division=0)),
        'f1':float(f1_score(y,pred,zero_division=0)),
        'auprc':float(average_precision_score(y,frame.i8_weather_score)) if y.sum()>0 else float('nan'),
        'weather_event_rows':int(y.sum()),
        'weather_event_episodes':int(frame.loc[y.eq(1),'episode_id'].replace('',np.nan).nunique()),
        'fault_to_weather_rate':float(pred.loc[frame.is_anomaly.eq(1)].mean()) if frame.is_anomaly.eq(1).any() else 0.0,
    }

i8_weather_frontier=[]
for threshold in np.linspace(.03,.95,47):
    rows=[]
    for domain in ['india','dwd']:
        part=i8_validation.loc[i8_validation.i8_scope.eq('tune')&i8_validation.i8_domain.eq(domain)].copy()
        rows.append({'domain':domain,**i8_weather_metrics(part,i8_weather_prediction(part,threshold))})
    i8_weather_frontier.append({
        'threshold':float(threshold),'min_precision':min(row['precision'] for row in rows),
        'min_f1':min(row['f1'] for row in rows),'mean_f1':float(np.mean([row['f1'] for row in rows])),
        'max_fault_to_weather':max(row['fault_to_weather_rate'] for row in rows)})
i8_weather_frontier=pd.DataFrame(i8_weather_frontier)
i8_weather_feasible=i8_weather_frontier.loc[(i8_weather_frontier.min_precision>=.75)&(i8_weather_frontier.max_fault_to_weather<=.01)]
if len(i8_weather_feasible):
    i8_weather_selected=i8_weather_feasible.sort_values(['min_f1','mean_f1'],ascending=False).iloc[0]
    I8_WEATHER_TUNE_STATUS='constraints_met'
else:
    i8_weather_frontier['violation']=np.maximum(0,.75-i8_weather_frontier.min_precision)+10*np.maximum(0,i8_weather_frontier.max_fault_to_weather-.01)
    i8_weather_selected=i8_weather_frontier.sort_values(['violation','min_f1','mean_f1'],ascending=[True,False,False]).iloc[0]
    I8_WEATHER_TUNE_STATUS='pareto_fallback_not_promotable'
I8_WEATHER_THRESHOLD=float(i8_weather_selected.threshold)
i8_weather_frontier.to_csv(ITER8_ROOT/'iteration8_weather_policy_frontier.csv',index=False)
display(i8_weather_selected.to_frame('selected_weather'))
"""),
    code(r"""def i8_candidate_fault_prediction(frame,score_col,threshold):
    raw=hysteresis(frame,score_col,float(threshold),max(0,float(threshold)-.07))
    weather=i8_weather_prediction(frame,I8_WEATHER_THRESHOLD)
    override=frame[score_col].ge(min(.99,float(threshold)+.18))
    return (raw&(~weather|override))|frame.hard_rule.astype(bool)

# Recompute deterministic hard-rule flags consistently on the combined validation table.
i8_validation['hard_rule']=add_hard_rules(i8_validation).hard_rule.to_numpy(bool)
i8_fault_frontier=[]
for variant,score_col in I8_SCORE_VARIANTS.items():
  for threshold in np.linspace(.08,.95,45):
      rows=[]
      for domain in ['india','dwd']:
          part=i8_validation.loc[i8_validation.i8_scope.eq('tune')&i8_validation.i8_domain.eq(domain)].copy()
          part['candidate']=i8_candidate_fault_prediction(part,score_col,threshold)
          metric=evaluate(part,score_col,'candidate')
          rows.append({'domain':domain,**metric})
      i8_fault_frontier.append({
          'variant':variant,'score_col':score_col,'threshold':float(threshold),
          'min_precision':min(row['precision'] for row in rows),
          'max_false_alarm':max(row['false_alarm_episodes_per_station_day'] for row in rows),
          'min_point_f1':min(row['f1'] for row in rows),'mean_point_f1':float(np.mean([row['f1'] for row in rows])),
          'min_event_f1':min(row['event_f1'] for row in rows),'mean_event_f1':float(np.mean([row['event_f1'] for row in rows])),
          'min_event_recall':min(row['event_recall'] for row in rows)})
i8_fault_frontier=pd.DataFrame(i8_fault_frontier)
i8_fault_feasible=i8_fault_frontier.loc[(i8_fault_frontier.min_precision>=.80)&(i8_fault_frontier.max_false_alarm<=.02)]
if len(i8_fault_feasible):
    i8_fault_selected=i8_fault_feasible.sort_values(['min_event_recall','min_event_f1','mean_point_f1'],ascending=False).iloc[0]
    I8_FAULT_TUNE_STATUS='constraints_met'
else:
    i8_fault_frontier['violation']=np.maximum(0,.80-i8_fault_frontier.min_precision)+10*np.maximum(0,i8_fault_frontier.max_false_alarm-.02)
    i8_fault_selected=i8_fault_frontier.sort_values(['violation','min_event_recall','mean_event_f1'],ascending=[True,False,False]).iloc[0]
    I8_FAULT_TUNE_STATUS='pareto_fallback_not_promotable'
I8_FAULT_THRESHOLD=float(i8_fault_selected.threshold)
I8_FAULT_VARIANT=str(i8_fault_selected.variant)
I8_FAULT_SCORE_COL=str(i8_fault_selected.score_col)
i8_fault_frontier.to_csv(ITER8_ROOT/'iteration8_fault_policy_frontier.csv',index=False)
display(i8_fault_selected.to_frame('selected_fault'))
"""),
    md(r"""## 39. Discovery and confirmation comparison

The frozen candidate is compared against the Iteration 5 development reference in India and its unadapted transfer baseline in DWD. Results are reported separately by domain, scope, climate and fault family.
"""),
    code(r"""def i8_weak_mean(metric):
    values=[metric['per_fault_episode_recall'].get(name,np.nan) for name in ['bias','drift','frozen_sensor']]
    values=[value for value in values if not pd.isna(value)]
    return float(np.mean(values)) if values else float('nan')

i8_comparison=[]; i8_fault_rows=[]; i8_weather_rows=[]
for scope in ['discovery','confirmation']:
  domain_masks={
      'india':i8_validation.i8_domain.eq('india'),
      'dwd_all':i8_validation.i8_domain.eq('dwd'),
      'dwd_holdout':i8_validation.i8_domain.eq('dwd')&i8_validation.station_id.isin(I8_DWD_HOLDOUTS),
  }
  for domain,domain_mask in domain_masks.items():
    part=i8_validation.loc[i8_validation.i8_scope.eq(scope)&domain_mask].copy()
    assert len(part)>0,f'Empty Iteration 8 evaluation slice: {scope}/{domain}'
    part['baseline']=part.i8_baseline_pred.astype(bool)
    part['candidate']=i8_candidate_fault_prediction(part,I8_FAULT_SCORE_COL,I8_FAULT_THRESHOLD)
    baseline=evaluate(part,'base_score','baseline')
    candidate=evaluate(part,I8_FAULT_SCORE_COL,'candidate')
    candidate_weather=i8_weather_metrics(part,i8_weather_prediction(part,I8_WEATHER_THRESHOLD))
    baseline_weather=i8_weather_metrics(part,part.i8_baseline_weather.astype(bool))
    i8_comparison.append({
        'scope':scope,'domain':domain,'rows':len(part),'candidate_variant':I8_FAULT_VARIANT,
        'baseline_precision':baseline['precision'],'candidate_precision':candidate['precision'],
        'baseline_recall':baseline['recall'],'candidate_recall':candidate['recall'],
        'baseline_point_f1':baseline['f1'],'candidate_point_f1':candidate['f1'],
        'point_f1_delta':candidate['f1']-baseline['f1'],
        'baseline_event_f1':baseline['event_f1'],'candidate_event_f1':candidate['event_f1'],
        'event_f1_delta':candidate['event_f1']-baseline['event_f1'],
        'baseline_weak_recall':i8_weak_mean(baseline),'candidate_weak_recall':i8_weak_mean(candidate),
        'weak_recall_delta':i8_weak_mean(candidate)-i8_weak_mean(baseline),
        'candidate_false_alarm':candidate['false_alarm_episodes_per_station_day'],
        'baseline_weather_f1':baseline_weather['f1'],'candidate_weather_f1':candidate_weather['f1'],
        'candidate_fault_to_weather':candidate_weather['fault_to_weather_rate']})
    for family,group in part.loc[part.is_anomaly.eq(1)&part.episode_id.ne('')].groupby('anomaly_type'):
        ids=group.episode_id.unique(); base_hits=[]; candidate_hits=[]
        for episode_id in ids:
            event=part.episode_id.eq(episode_id)
            base_hits.append(bool(part.loc[event,'baseline'].any()))
            candidate_hits.append(bool(part.loc[event,'candidate'].any()))
        i8_fault_rows.append({'scope':scope,'domain':domain,'anomaly_type':family,'episodes':len(ids),
                              'baseline_episode_recall':float(np.mean(base_hits)),
                              'candidate_episode_recall':float(np.mean(candidate_hits))})
    for cluster,group in part.groupby('cluster'):
        result=i8_weather_metrics(group,i8_weather_prediction(group,I8_WEATHER_THRESHOLD))
        i8_weather_rows.append({'scope':scope,'domain':domain,'cluster':cluster,**result})

i8_comparison=pd.DataFrame(i8_comparison)
i8_fault_recall=pd.DataFrame(i8_fault_rows)
i8_weather_by_cluster=pd.DataFrame(i8_weather_rows)
i8_comparison.to_csv(ITER8_ROOT/'iteration8_multidomain_confirmation.csv',index=False)
i8_fault_recall.to_csv(ITER8_ROOT/'iteration8_fault_episode_recall.csv',index=False)
i8_weather_by_cluster.to_csv(ITER8_ROOT/'iteration8_weather_by_cluster.csv',index=False)
display(i8_comparison); display(i8_fault_recall); display(i8_weather_by_cluster)
"""),
    md(r"""## 40. Root-cause model and explainability artifact

Root-cause fitting uses only labelled training fault rows. Feature importance is exported from the LightGBM challenger so every alert can expose the strongest causal signals; no label appears in inference features.
"""),
    code(r"""i8_root_train=i8_fit.loc[i8_fit.is_anomaly.eq(1)].copy()
i8_root_model=CatBoostClassifier(
    iterations=900,depth=7,learning_rate=.04,loss_function='MultiClass',eval_metric='TotalF1',
    l2_leaf_reg=10,random_seed=81,task_type='GPU',devices='0',verbose=150,
    allow_writing_files=False)
i8_root_path=ITER8_ROOT/'iteration8_root_cause_catboost.cbm'
if REUSE_SAVED_MODELS and i8_root_path.exists(): i8_root_model.load_model(i8_root_path)
else:
    i8_root_model.fit(i8_root_train[FEATURES],i8_root_train.anomaly_type.astype(str))
    i8_root_model.save_model(i8_root_path)

i8_confirmation=i8_validation.loc[i8_validation.i8_scope.eq('confirmation')].copy()
i8_confirmation['candidate']=i8_candidate_fault_prediction(
    i8_confirmation,I8_FAULT_SCORE_COL,I8_FAULT_THRESHOLD)
i8_root_eval=i8_confirmation.loc[i8_confirmation.is_anomaly.eq(1)&i8_confirmation.candidate].copy()
if len(i8_root_eval):
    root_prediction=np.asarray(i8_root_model.predict(i8_root_eval[FEATURES])).reshape(-1).astype(str)
    I8_ROOT_ACCURACY=float(np.mean(root_prediction==i8_root_eval.anomaly_type.astype(str).to_numpy()))
else: I8_ROOT_ACCURACY=float('nan')

importance=np.mean([model.feature_importances_ for model in i8_models['fault']['lgb']],axis=0)
i8_importance=(pd.DataFrame({'feature':FEATURES,'importance':importance})
               .sort_values('importance',ascending=False).reset_index(drop=True))
i8_importance.to_csv(ITER8_ROOT/'iteration8_feature_importance.csv',index=False)
display(i8_importance.head(25)); print('Detected-fault root-cause accuracy:',I8_ROOT_ACCURACY)
"""),
    md(r"""## 41. Promotion decision and integrity receipt

Failure of any gate produces a no-op decision. Passing every gate makes the challenger eligible for one locked DWD 2024 confirmation; it does not replace the deployed Phase 10 model by itself.
"""),
    code(r"""confirmation_rows=i8_comparison.loc[i8_comparison.scope.eq('confirmation')]
discovery_rows=i8_comparison.loc[i8_comparison.scope.eq('discovery')]
supported_confirmation_weather=i8_weather_by_cluster.loc[
    i8_weather_by_cluster.scope.eq('confirmation')&i8_weather_by_cluster.weather_event_rows.gt(0)]
assert len(supported_confirmation_weather)>0
i8_worst_confirmation_weather=float(supported_confirmation_weather.f1.min())
I8_PROMOTION_GATES={
    'tune_fault_constraints':I8_FAULT_TUNE_STATUS=='constraints_met',
    'tune_weather_constraints':I8_WEATHER_TUNE_STATUS=='constraints_met',
    'discovery_precision':bool(discovery_rows.candidate_precision.ge(.80).all()),
    'confirmation_precision':bool(confirmation_rows.candidate_precision.ge(.80).all()),
    'discovery_false_alarm':bool(discovery_rows.candidate_false_alarm.le(.02).all()),
    'confirmation_false_alarm':bool(confirmation_rows.candidate_false_alarm.le(.02).all()),
    'no_discovery_point_f1_regression':bool(discovery_rows.point_f1_delta.ge(0).all()),
    'no_confirmation_point_f1_regression':bool(confirmation_rows.point_f1_delta.ge(0).all()),
    'no_confirmation_event_f1_regression':bool(confirmation_rows.event_f1_delta.ge(0).all()),
    'positive_confirmation_weak_recall':bool(confirmation_rows.weak_recall_delta.ge(0).all() and confirmation_rows.weak_recall_delta.mean()>0),
    'confirmation_weather_f1_at_least_075':bool(confirmation_rows.candidate_weather_f1.ge(.75).all()),
    'worst_climate_weather_f1_at_least_065':bool(i8_worst_confirmation_weather>=.65),
    'dwd_holdout_confirmation_present':bool((confirmation_rows.domain=='dwd_holdout').any()),
    'fault_to_weather_at_most_001':bool(confirmation_rows.candidate_fault_to_weather.le(.01).all()),
}
I8_PROMOTED=all(I8_PROMOTION_GATES.values())
I8_STATUS='eligible_for_locked_dwd_2024_confirmation' if I8_PROMOTED else 'not_eligible_keep_iteration5_development_reference'

i8_feature_contract={
    'observation_inputs':['temperature','pressure','relative_humidity'],
    'model_features':FEATURES,'model_feature_count':len(FEATURES),
    'unsupervised_features':I8_UNSUP_FEATURES,'unsupervised_feature_count':len(I8_UNSUP_FEATURES),
    'unsupervised_window':I8_SEQUENCE_WINDOW,'unsupervised_fit':'2022 non-fault rows only',
    'new_source':'DWD CDC official 10-minute station observations',
    'dwd_training_year':2022,'dwd_validation_year':2023,
    'dwd_2024_opened':False,'any_2025_opened':False,
    'weather_families':list(WEATHER_FAMILIES),'fault_families':list(FAULT_FAMILIES),
    'causality':'current and previously emitted station/neighbor observations only',
    'forbidden':['dew_point','future_observation','2024_labels','2025_observations_or_labels'],
}
(ITER8_ROOT/'iteration8_feature_contract.json').write_text(json.dumps(i8_feature_contract,indent=2))

i8_receipt={
    'development_bundle_sha256':ITER8_EXPECTED_SHA,'original_bundle_sha256':OLD_EXPECTED_SHA,
    'source_validation_status':i8_source_report['status'],
    'dwd_2024_opened':False,'noaa_2024_opened':False,'any_2025_opened':False,
    'train_curriculum':i8_train_audit,'validation_curriculum':i8_val_audit,
    'pseudo_unseen_stations':I8_DWD_HOLDOUTS,
    'future_features_used':False,'dew_point_used':False,
    'isolation_forest_fit_on_evaluation':False,'lstm_bidirectional':False,
}
(ITER8_ROOT/'iteration8_data_curriculum_receipt.json').write_text(json.dumps(i8_receipt,indent=2))

result8={
    'iteration':'08_multiclimate_data_curriculum','status':I8_STATUS,'promoted':I8_PROMOTED,
    'device':DEVICE,'gpu':torch.cuda.get_device_name(0),
    'new_data':{'provider':'DWD','stations':16,'clusters':4,'cadence_minutes':10,
                'development_years':[2022,2023],'locked_2024_opened':False,'any_2025_opened':False},
    'curriculum':{'training':i8_train_audit,'validation':i8_val_audit},
    'models':['CatBoost fault','LightGBM fault seeds 17/41','Isolation Forest clean-only novelty',
              'causal LSTM reconstruction autoencoder','CatBoost weather','LightGBM weather seeds 17/41','CatBoost root cause'],
    'selected_fault_variant':I8_FAULT_VARIANT,
    'thresholds':{'fault':I8_FAULT_THRESHOLD,'fault_score_col':I8_FAULT_SCORE_COL,'weather':I8_WEATHER_THRESHOLD},
    'tune_status':{'fault':I8_FAULT_TUNE_STATUS,'weather':I8_WEATHER_TUNE_STATUS},
    'promotion_gates':I8_PROMOTION_GATES,
    'root_cause_accuracy_on_detected_confirmation_fault_rows':I8_ROOT_ACCURACY,
    'multidomain_confirmation':i8_comparison.to_dict('records'),
    'worst_confirmation_climate_weather_f1':i8_worst_confirmation_weather,
    'next_decision':'run one locked DWD 2024 confirmation' if I8_PROMOTED else 'retain Iteration 5 development reference',
}
(ITER8_ROOT/'iteration8_result_block.json').write_text(json.dumps(result8,indent=2,default=float))

print(json.dumps(result8,indent=2,default=float))
print('\nSEND BACK THESE ITERATION 8 FILES:')
for filename in [
    'iteration8_result_block.json','iteration8_data_curriculum_receipt.json',
    'iteration8_feature_contract.json','iteration8_training_history.csv',
    'iteration8_unsupervised_training_history.csv',
    'iteration8_multidomain_confirmation.csv','iteration8_fault_episode_recall.csv',
    'iteration8_weather_by_cluster.csv','iteration8_feature_importance.csv',
    'iteration8_weather_policy_frontier.csv','iteration8_fault_policy_frontier.csv',
]: print(ITER8_ROOT/filename)
"""),
    md(r"""## Iteration 8 stop rule

Return the eleven files printed above. Do not open the locked DWD 2024 confirmation bundle or any 2025 benchmark. We will audit whether new-data gains transfer simultaneously to India, DWD climates and pseudo-unseen stations. Only a fully passing candidate can proceed to one final locked confirmation.
"""),
])

notebook.setdefault("metadata", {}).setdefault("colab", {})["name"] = OUTPUT.name
OUTPUT.write_text(json.dumps(notebook, indent=1, ensure_ascii=False), encoding="utf-8")
print(OUTPUT)
