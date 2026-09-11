"""Build the SkyGuard Iteration 10R calibration/integrity repair Colab.

The repair is intentionally derived from the frozen Iteration 10 source notebook
so that the data curriculum, feature contract and evaluation protocol remain
comparable.  Only defects identified by the post-run audit are changed.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "notebooks" / "SkyGuard_AI_GPU_Iteration_10_Final_Incident_Intelligence_Colab.ipynb"
OUTPUT = ROOT / "notebooks" / "SkyGuard_AI_GPU_Iteration_10R_Calibration_Integrity_Repair_Colab.ipynb"
DELIVERABLE = ROOT / "deliverables" / OUTPUT.name


def source(cell: dict[str, object]) -> str:
    return "".join(cell.get("source", []))


def set_source(cell: dict[str, object], value: str) -> None:
    cell["source"] = value.strip("\n").splitlines(keepends=True)
    if cell["source"] and not cell["source"][-1].endswith("\n"):
        cell["source"][-1] += "\n"
    if cell.get("cell_type") == "code":
        cell["execution_count"] = None
        cell["outputs"] = []


def replace_between(text: str, start: str, end: str, replacement: str) -> str:
    left, separator, tail = text.partition(start)
    if not separator:
        raise RuntimeError(f"Start marker not found: {start!r}")
    _middle, separator, right = tail.partition(end)
    if not separator:
        raise RuntimeError(f"End marker not found: {end!r}")
    return left + replacement.rstrip() + "\n\n" + end + right


notebook = json.loads(BASE.read_text(encoding="utf-8"))
cells = notebook["cells"]
if len(cells) != 36:
    raise RuntimeError(f"Unexpected base notebook cell count: {len(cells)}")

# Give every generated artifact a separate namespace.  Revert the one official
# input-validation filename that belongs to the immutable starter bundle.
for cell in cells:
    text = source(cell)
    text = text.replace("iteration_10_final_incident_intelligence", "iteration_10r_calibration_integrity_repair")
    text = text.replace("iteration10_", "iteration10r_")
    text = text.replace("iteration10r_india_data_validation.json", "iteration10_india_data_validation.json")
    text = text.replace("SkyGuard_Iteration10_Result_Package.zip", "SkyGuard_Iteration10R_Result_Package.zip")
    text = text.replace("Iteration 10 (final development candidate)", "Iteration 10R (calibration and integrity repair)")
    set_source(cell, text)

set_source(cells[0], r"""
# SkyGuard AI — GPU Iteration 10R (calibration and integrity repair)

## Fail-safe incident intelligence for SIH26073

This standalone repair keeps the Iteration 10 data curriculum and causal feature
contract, but corrects the defects found by the independent returned-result audit:

1. cache files have a new schema namespace and preserve station IDs as strings;
2. India and DWD station holdouts must be present, non-empty and excluded from fit,
   early stopping, calibration and policy selection;
3. probability calibration preserves natural class prevalence (no balanced-class
   calibrator) and is audited before policy search;
4. drift rescue requires multi-window consensus plus spatial isolation;
5. weather and fault persistence are separate, mutually exclusive state machines;
6. threshold selection is worst-domain constrained and fails closed when no safe
   policy exists.

The notebook opens only 2022–2023 development observations. It never opens 2024
or 2025 and cannot automatically deploy a model.
""")

set_source(cells[1], r"""
## Exact run instructions

1. Upload these two unchanged files to `/content/drive/MyDrive/SkyGuard_AI_GPU/`:
   - `SkyGuard_Iteration10_Final_Starter_Bundle.zip`
   - `SkyGuard_Iteration8_Development_Data_Bundle.zip`
2. Select **Runtime → Change runtime type → T4 GPU**.
3. Keep `UNLOCK_FINAL_TESTS=False`, `REUSE_FEATURE_CACHE=True`, and
   `RUN_STRESS_SEEDS=True`.
4. Use **Runtime → Run all**. Iteration 10R writes to a new experiment directory,
   so the first run rebuilds every feature and cannot reuse the defective Iteration
   10 cache. A later resume may safely reuse only the 10R schema.
5. Return `iteration10r_result_block.json`,
   `iteration10r_calibration_development_audit.json`,
   `iteration10r_multidomain_confirmation.csv`,
   `iteration10r_policy_frontier.csv`, and the result ZIP.

Do not upload or open any locked-year observation bundle in this runtime.
""")

# Runtime: unique local directory and explicit cache schema.
runtime = source(cells[4])
runtime = runtime.replace(
    "RUN_STRESS_SEEDS=True\nDEVELOPMENT_YEARS=(2022,2023)",
    "RUN_STRESS_SEEDS=True\nCACHE_SCHEMA_VERSION='iteration10r-v2-string-station-id-natural-prior'\nDEVELOPMENT_YEARS=(2022,2023)",
)
runtime = runtime.replace("/content/skyguard_iteration10", "/content/skyguard_iteration10r")
runtime = runtime.replace(".iteration10_runtime", ".iteration10r_runtime")
set_source(cells[4], runtime)

# Data identities must stay strings before any split or holdout operation.
load = source(cells[8])
load = load.replace(
    "india=standardize(india,'india'); dwd=standardize(dwd,'dwd')\n"
    "india_stations['cluster']='india_'+india_stations.cluster.astype(str)",
    "india=standardize(india,'india'); dwd=standardize(dwd,'dwd')\n"
    "india_stations['station_id']=india_stations.station_id.astype(str).str.replace(r'\\.0$','',regex=True)\n"
    "dwd_stations['station_id']=dwd_stations.station_id.astype(str).str.replace(r'\\.0$','',regex=True)\n"
    "india['station_id']=india.station_id.astype(str).str.replace(r'\\.0$','',regex=True)\n"
    "dwd['station_id']=dwd.station_id.astype(str).str.replace(r'\\.0$','',regex=True)\n"
    "india_stations['cluster']='india_'+india_stations.cluster.astype(str)",
)
set_source(cells[8], load)

# Replace the feature materialisation cell: stale cache rejection, typed cache
# reload, manifest validation and non-empty holdout assertions.
cell14 = source(cells[14])
prefix = cell14.split("PROFILE_PATH=", 1)[0]
materialize = r"""
PROFILE_PATH=ITER10_ROOT/'iteration10r_climatology.joblib'
CACHE_MANIFEST_PATH=ITER10_ROOT/'iteration10r_feature_cache_manifest.json'

def cache_manifest_payload():
    return {
        'schema_version':CACHE_SCHEMA_VERSION,
        'bundle_sha256':EXPECTED_BUNDLE_SHA256,
        'development_years':list(DEVELOPMENT_YEARS),
        'strict_station_id_type':'string',
        'feature_contract_version':feature_contract['version'],
    }

def cache_manifest_valid():
    if not CACHE_MANIFEST_PATH.exists(): return False
    try: return json.loads(CACHE_MANIFEST_PATH.read_text())==cache_manifest_payload()
    except Exception: return False

def normalise_feature_identifiers(table,label):
    result=table.copy()
    for name in ('station_id','eval_station_id','row_id'):
        if name not in result: raise ValueError(f'{label}: missing identifier {name}')
        result[name]=result[name].astype(str).str.replace(r'\.0$','',regex=True)
    if result.station_id.str.endswith('.0').any():
        raise ValueError(f'{label}: numeric station-id corruption survived cache load')
    return result

def read_feature_cache(path,label):
    table=pd.read_csv(path,dtype={'station_id':str,'eval_station_id':str,'row_id':str},low_memory=False)
    return normalise_feature_identifiers(table,label)

def materialize(specs,tag,profiles=None,fit_profiles=False):
    paths={spec['key']:ITER10_ROOT/f'{CACHE_SCHEMA_VERSION}_{tag}_{spec["key"]}_features.csv.gz' for spec in specs}
    reusable=(REUSE_FEATURE_CACHE and cache_manifest_valid() and all(path.exists() for path in paths.values())
              and (not fit_profiles or PROFILE_PATH.exists()))
    if reusable:
        tables=[read_feature_cache(paths[spec['key']],f'{tag}:{spec["key"]}') for spec in specs]
        if fit_profiles: profiles=joblib.load(PROFILE_PATH)
        print('Reused schema-validated',tag,'feature cache.')
        return pd.concat(tables,ignore_index=True,sort=False),profiles
    if REUSE_FEATURE_CACHE:
        print('No compatible 10R cache found; rebuilding',tag,'without reading Iteration 10 cache.')
    bases=[build_base_features(spec) for spec in specs]
    if fit_profiles:
        profiles=fit_climatology(pd.concat(bases,ignore_index=True,sort=False))
        joblib.dump(profiles,PROFILE_PATH,compress=3)
    assert profiles is not None
    tables=[]
    for spec,base in zip(specs,bases):
        table=normalise_feature_identifiers(add_phase10_features(base,profiles),f'built:{spec["key"]}')
        table.to_csv(paths[spec['key']],index=False,compression={'method':'gzip','compresslevel':5})
        tables.append(table); del base; gc.collect()
    CACHE_MANIFEST_PATH.write_text(json.dumps(cache_manifest_payload(),indent=2))
    return pd.concat(tables,ignore_index=True,sort=False),profiles

train_features,climatology=materialize(train_specs,'train',fit_profiles=True)
main_features,_=materialize(main_specs,'main',profiles=climatology)
train_features=normalise_feature_identifiers(train_features,'train features')
main_features=normalise_feature_identifiers(main_features,'main features')
assert train_features.row_id.is_unique and main_features.row_id.is_unique
assert set(PHASE10_FEATURES)<=set(train_features.columns)

HOLDOUT_INTEGRITY={
    'india_main_rows':int((main_features.i10_domain.eq('india')&main_features.station_id.isin(INDIA_HOLDOUTS)).sum()),
    'dwd_main_rows':int((main_features.i10_domain.eq('dwd')&main_features.station_id.isin(DWD_HOLDOUTS)).sum()),
    'india_train_rows':int((train_features.i10_domain.eq('india')&train_features.station_id.isin(INDIA_HOLDOUTS)).sum()),
    'dwd_train_rows':int((train_features.i10_domain.eq('dwd')&train_features.station_id.isin(DWD_HOLDOUTS)).sum()),
}
assert HOLDOUT_INTEGRITY['india_main_rows']>0 and HOLDOUT_INTEGRITY['dwd_main_rows']>0
assert HOLDOUT_INTEGRITY['india_train_rows']==0 and HOLDOUT_INTEGRITY['dwd_train_rows']==0
for domain,station_table in (('india',india_stations),('dwd',dwd_stations)):
    observed=set(main_features.loc[main_features.i10_domain.eq(domain),'station_id'])
    expected=set(station_table.station_id.astype(str))
    assert observed<=expected and observed, (domain,sorted(observed-expected)[:5])
print({'train_features':train_features.shape,'main_features':main_features.shape,
       'profile_station_count':len(climatology['temperature_station']),
       'cache_schema':CACHE_SCHEMA_VERSION,'holdout_integrity':HOLDOUT_INTEGRITY})
"""
set_source(cells[14], prefix + materialize)

# Cadence profile now records the expected reporting interval, which lets the
# state model adapt to India's mixed 30/180-minute archive without a domain ID.
cadence = source(cells[16])
old_cadence = r"""def cadence_profiles(frame):
    rows=[]
    clean=frame.loc[frame.i10_scope.eq('train')&frame.eval_label_category.eq('normal')&frame.available_to_detector.eq(1)].copy()
    clean['gap_ratio_num']=pd.to_numeric(clean.gap_ratio,errors='coerce')
    for (domain,station),group in clean.groupby(['i10_domain','station_id'],sort=False):
        ratio=group.gap_ratio_num.dropna(); regular=float(ratio.between(.75,1.25).mean()) if len(ratio) else 0.0
        q999=float(ratio.quantile(.999)) if len(ratio) else np.nan
        verified=bool(len(ratio)>=500 and regular>=.75 and np.isfinite(q999))
        rows.append({'i10_domain':domain,'station_id':str(station),'samples':len(ratio),'regularity':regular,
                     'training_gap_ratio_q999':q999,'verified_heartbeat':verified,
                     'automatic_gap_ratio_threshold':max(4.0,1.25*q999) if verified else np.inf})
    return pd.DataFrame(rows)

cadence_contract=cadence_profiles(train_features)
cadence_contract.to_csv(ITER10_ROOT/'iteration10r_communication_contract.csv',index=False)
cadence_map={(row.i10_domain,str(row.station_id)):(bool(row.verified_heartbeat),float(row.automatic_gap_ratio_threshold))
             for row in cadence_contract.itertuples()}
"""
new_cadence = r"""def cadence_profiles(frame):
    rows=[]
    clean=frame.loc[frame.i10_scope.eq('train')&frame.eval_label_category.eq('normal')&frame.available_to_detector.eq(1)].copy()
    clean['gap_ratio_num']=pd.to_numeric(clean.gap_ratio,errors='coerce')
    clean['delta_minutes_num']=pd.to_numeric(clean.time_since_previous_minutes,errors='coerce')
    for (domain,station),group in clean.groupby(['i10_domain','station_id'],sort=False):
        ratio=group.gap_ratio_num.dropna(); regular=float(ratio.between(.75,1.25).mean()) if len(ratio) else 0.0
        q999=float(ratio.quantile(.999)) if len(ratio) else np.nan
        regular_delta=group.loc[group.gap_ratio_num.between(.75,1.25),'delta_minutes_num'].dropna()
        expected=float(regular_delta.median()) if len(regular_delta) else 60.0
        verified=bool(len(ratio)>=500 and regular>=.75 and np.isfinite(q999))
        rows.append({'i10_domain':domain,'station_id':str(station),'samples':len(ratio),'regularity':regular,
                     'expected_interval_minutes':expected,'training_gap_ratio_q999':q999,
                     'verified_heartbeat':verified,
                     'automatic_gap_ratio_threshold':max(4.0,1.25*q999) if verified else np.inf})
    return pd.DataFrame(rows)

cadence_contract=cadence_profiles(train_features)
cadence_contract.to_csv(ITER10_ROOT/'iteration10r_communication_contract.csv',index=False)
cadence_map={(row.i10_domain,str(row.station_id)):(bool(row.verified_heartbeat),
             float(row.automatic_gap_ratio_threshold),float(row.expected_interval_minutes))
             for row in cadence_contract.itertuples()}
"""
if old_cadence not in cadence:
    raise RuntimeError("Cadence block did not match the base notebook")
set_source(cells[16], cadence.replace(old_cadence, new_cadence))

# Keep January for model early stopping and February exclusively for probability
# calibration.  Both exclude station holdouts.
row_training = source(cells[18])
row_training = row_training.replace(
    "calibration=main_features.loc[main_features.i10_scope.eq('calibration')&main_features.available_to_detector.eq(1)&\n"
    "    ~((main_features.i10_domain.eq('india')&main_features.station_id.isin(INDIA_HOLDOUTS))|\n"
    "      (main_features.i10_domain.eq('dwd')&main_features.station_id.isin(DWD_HOLDOUTS)))].reset_index(drop=True)\n"
    "y_fit=target_values(fit); y_cal=target_values(calibration); fit_weights=episode_domain_weights(fit,y_fit)\n"
    "assert set(np.unique(y_fit))=={0,1,2} and set(np.unique(y_cal))=={0,1,2}",
    "eligible_main=main_features.loc[main_features.i10_scope.eq('calibration')&main_features.available_to_detector.eq(1)&\n"
    "    ~((main_features.i10_domain.eq('india')&main_features.station_id.isin(INDIA_HOLDOUTS))|\n"
    "      (main_features.i10_domain.eq('dwd')&main_features.station_id.isin(DWD_HOLDOUTS)))].copy()\n"
    "eligible_time=pd.to_datetime(eligible_main.causal_arrival_timestamp_utc,utc=True)\n"
    "model_tune=eligible_main.loc[eligible_time.lt(pd.Timestamp('2023-02-01',tz='UTC'))].reset_index(drop=True)\n"
    "y_fit=target_values(fit); y_tune=target_values(model_tune); fit_weights=episode_domain_weights(fit,y_fit)\n"
    "assert set(np.unique(y_fit))=={0,1,2} and set(np.unique(y_tune))=={0,1,2}",
)
row_training = row_training.replace("(calibration[STRICT_FEATURES],y_cal)", "(model_tune[STRICT_FEATURES],y_tune)")
set_source(cells[18], row_training)

# State evidence: a single extreme slope can no longer trigger drift rescue.
set_source(cells[20], r"""
def add_row_scores(frame):
    result=enforce_numeric(frame,STRICT_FEATURES,'scoring')
    predictions=[model.predict_proba(result[STRICT_FEATURES]) for model in base_lgb]
    predictions.append(base_cat.predict_proba(result[STRICT_FEATURES]))
    probability=np.mean(np.stack(predictions),axis=0)
    probability=np.clip(probability,1e-7,1); probability/=probability.sum(axis=1,keepdims=True)
    for index,name in enumerate(CLASS_NAMES): result[f'row_p_{name}']=probability[:,index].astype(np.float32)
    return result

def _causal_run_lengths(result,mask):
    runs=np.zeros(len(result),dtype=np.float32)
    for _series,indices in result.groupby('eval_station_id',sort=False).groups.items():
        count=0
        for index in indices:
            count=count+1 if bool(mask[index]) else 0; runs[index]=count
    return runs

def add_hard_and_state_features(frame):
    result=frame.copy()
    result['station_id']=result.station_id.astype(str).str.replace(r'\.0$','',regex=True)
    temp=pd.to_numeric(result.temperature_value,errors='coerce')
    pressure=pd.to_numeric(result.pressure_value,errors='coerce')
    humidity=pd.to_numeric(result.humidity_value,errors='coerce')
    gap=pd.to_numeric(result.gap_ratio,errors='coerce')
    interval=[cadence_map.get((domain,str(station)),(False,np.inf,60.0))
              for domain,station in zip(result.i10_domain,result.station_id)]
    verified=np.asarray([item[0] for item in interval],dtype=bool)
    gap_threshold=np.asarray([item[1] for item in interval],dtype=float)
    expected_interval=np.asarray([item[2] for item in interval],dtype=float)
    duplicate=result.out_of_order_indicator.fillna(0).astype(bool)&pd.to_numeric(result.time_since_previous_minutes,errors='coerce').le(0)
    timestamp_error=result.out_of_order_indicator.fillna(0).astype(bool)&pd.to_numeric(result.time_since_previous_minutes,errors='coerce').lt(-1)
    communication_gap=verified&gap.gt(gap_threshold).fillna(False).to_numpy()
    physical=(temp.lt(-80)|temp.gt(65)|pressure.lt(800)|pressure.gt(1150)|humidity.lt(0)|humidity.gt(100)).fillna(False)
    multi_freeze=(pd.to_numeric(result.temperature_frozen_run_length,errors='coerce').ge(6)&
                  pd.to_numeric(result.pressure_frozen_run_length,errors='coerce').ge(6)&
                  pd.to_numeric(result.humidity_frozen_run_length,errors='coerce').ge(6)).fillna(False)
    codes=np.full(len(result),'',dtype=object)
    codes[np.asarray(multi_freeze)]='MULTI_SENSOR_FREEZE'
    codes[np.asarray(physical)]='PHYSICAL_LIMIT'
    codes[np.asarray(communication_gap)]='COMMUNICATION_GAP'
    codes[np.asarray(duplicate)]='DUPLICATE_PACKET'
    codes[np.asarray(timestamp_error)]='TIMESTAMP_ERROR'
    result['hard_fault_code']=codes
    result['hard_fault']=(codes!='').astype(np.int8)
    result['verified_heartbeat']=verified.astype(np.int8)
    result['expected_interval_minutes']=np.clip(expected_interval,1,360).astype(np.float32)
    result['slow_cadence_station']=(expected_interval>=120).astype(np.int8)
    neighbor_count=pd.to_numeric(result.neighbor_station_count,errors='coerce').fillna(0)
    temp_agree=pd.to_numeric(result.neighbor_temperature_agreement_fraction,errors='coerce')
    humidity_agree=pd.to_numeric(result.neighbor_humidity_agreement_fraction,errors='coerce')
    result['safe_weather_agreement']=pd.concat([temp_agree,humidity_agree],axis=1).mean(axis=1,skipna=True).fillna(0).astype(np.float32)
    result['safe_weather_sensor_count']=(temp_agree.ge(.55).astype(int)+humidity_agree.ge(.55).astype(int)).astype(np.int8)
    result['neighbor_support_count']=neighbor_count.clip(0,5).astype(np.float32)
    result['regional_extent']=neighbor_count.div(5).clip(0,1).astype(np.float32)
    result['independent_weather_gate']=(neighbor_count.ge(2)&result.safe_weather_agreement.ge(.50)&
        result.safe_weather_sensor_count.ge(1)).astype(np.int8)

    slope_terms=[]
    for sensor,floor in (('temperature',.15),('pressure',.12),('humidity',.6)):
        for hours in (6,12,24):
            slope_terms.append(pd.to_numeric(result[f'{sensor}_slope_{hours}h'],errors='coerce').abs().div(floor))
    cusum_terms=[pd.to_numeric(result[f'{sensor}_cusum_{direction}'],errors='coerce').div(8)
                 for sensor in ('temperature','pressure','humidity') for direction in ('positive','negative')]
    drift_matrix=(pd.concat(slope_terms+cusum_terms,axis=1).replace([np.inf,-np.inf],np.nan)
                  .fillna(0).clip(0,12).to_numpy(np.float32))
    ordered=np.sort(drift_matrix,axis=1)
    result['drift_evidence_score']=ordered[:,-2].astype(np.float32)
    result['drift_support_count']=(drift_matrix>=2.5).sum(axis=1).astype(np.float32)
    result['isolated_drift_gate']=(result.drift_support_count.ge(3)&result.safe_weather_agreement.lt(.35)&
        result.independent_weather_gate.eq(0)).astype(np.int8)

    result=result.sort_values(['eval_station_id','causal_arrival_timestamp_utc','stream_order'],kind='stable').reset_index(drop=True)
    grouping=result.groupby('eval_station_id',sort=False)
    for name in ('row_p_sensor_fault','row_p_genuine_weather','drift_evidence_score','safe_weather_agreement'):
        result[f'{name}_mean5']=(grouping[name].rolling(5,min_periods=1).mean().reset_index(level=0,drop=True).astype(np.float32))
        result[f'{name}_max5']=(grouping[name].rolling(5,min_periods=1).max().reset_index(level=0,drop=True).astype(np.float32))
    fault_candidate=(result.row_p_sensor_fault.ge(.12)|result.hard_fault.eq(1)).to_numpy()
    weather_candidate=(result.row_p_genuine_weather.ge(.15)&result.independent_weather_gate.eq(1)).to_numpy()
    result['fault_candidate_run_length']=_causal_run_lengths(result,fault_candidate)
    result['weather_candidate_run_length']=_causal_run_lengths(result,weather_candidate)
    return result

train_state=add_hard_and_state_features(add_row_scores(train_features))
main_state=add_hard_and_state_features(add_row_scores(main_features))
STATE_FEATURES=[
    'row_p_normal','row_p_genuine_weather','row_p_sensor_fault',
    'row_p_sensor_fault_mean5','row_p_sensor_fault_max5','row_p_genuine_weather_mean5','row_p_genuine_weather_max5',
    'drift_evidence_score','drift_evidence_score_mean5','drift_evidence_score_max5','drift_support_count','isolated_drift_gate',
    'safe_weather_agreement','safe_weather_agreement_mean5','safe_weather_agreement_max5','safe_weather_sensor_count',
    'neighbor_support_count','regional_extent','independent_weather_gate','hard_fault','verified_heartbeat',
    'expected_interval_minutes','slow_cadence_station','fault_candidate_run_length','weather_candidate_run_length',
    'primary_missing_count','time_since_previous_minutes','gap_ratio','out_of_order_indicator',
    'temperature_frozen_run_length','pressure_frozen_run_length','humidity_frozen_run_length',
]
train_state=enforce_numeric(train_state,STATE_FEATURES,'train state')
main_state=enforce_numeric(main_state,STATE_FEATURES,'main state')
normal_drift=train_state.loc[train_state.eval_label_category.eq('normal'),'drift_evidence_score'].dropna()
TRAIN_DRIFT_RESCUE_FLOOR=float(np.clip(normal_drift.quantile(.999),4.0,10.0))
print({'strict_features':len(STRICT_FEATURES),'state_features':len(STATE_FEATURES),
       'train_drift_rescue_floor':TRAIN_DRIFT_RESCUE_FLOOR})
""")

# Natural-prevalence calibration.  The old balanced calibrator was the principal
# reason almost every normal row received fault probability around 0.36.
set_source(cells[21], r"""
## 10. Train and calibrate the incident-state classifier

January 2023 is used only for early stopping. February 2023 is used only for a
natural-prevalence L2 calibration layer. No class-balancing is permitted in the
calibrator. An iterative prior correction makes the mean calibrated class
probability agree with the observed February prevalence while preserving ranking.
""")
set_source(cells[22], r"""
state_fit=train_state.loc[train_state.available_to_detector.eq(1)].reset_index(drop=True)
eligible_state=main_state.loc[main_state.i10_scope.eq('calibration')&main_state.available_to_detector.eq(1)&
    ~((main_state.i10_domain.eq('india')&main_state.station_id.isin(INDIA_HOLDOUTS))|
      (main_state.i10_domain.eq('dwd')&main_state.station_id.isin(DWD_HOLDOUTS)))].copy()
eligible_state_time=pd.to_datetime(eligible_state.causal_arrival_timestamp_utc,utc=True)
state_tune=eligible_state.loc[eligible_state_time.lt(pd.Timestamp('2023-02-01',tz='UTC'))].reset_index(drop=True)
state_cal=eligible_state.loc[eligible_state_time.ge(pd.Timestamp('2023-02-01',tz='UTC'))].reset_index(drop=True)
ys_fit=target_values(state_fit); ys_tune=target_values(state_tune); ys_cal=target_values(state_cal)
assert set(np.unique(ys_tune))=={0,1,2} and set(np.unique(ys_cal))=={0,1,2}
state_weights=episode_domain_weights(state_fit,ys_fit)
STATE_SEEDS=(2017,2041,2067); state_models=[]
for seed in STATE_SEEDS:
    model=LGBMClassifier(objective='multiclass',num_class=3,n_estimators=1000,learning_rate=.03,
        num_leaves=31,min_child_samples=100,subsample=.9,colsample_bytree=.9,reg_alpha=3.0,reg_lambda=25.0,
        random_state=seed,n_jobs=-1,verbosity=-1,force_col_wise=True)
    model.fit(state_fit[STATE_FEATURES],ys_fit,sample_weight=state_weights,
              eval_set=[(state_tune[STATE_FEATURES],ys_tune)],eval_metric='multi_logloss',
              callbacks=[early_stopping(100,verbose=False),log_evaluation(0)])
    joblib.dump(model,ITER10_ROOT/f'iteration10r_state_lightgbm_seed{seed}.joblib',compress=3)
    state_models.append(model); model_history.append({'stage':'incident_state','model':'lightgbm','seed':seed,
                                                       'best_iteration':int(model.best_iteration_ or model.n_estimators)})

def raw_state_probability(frame):
    values=np.mean(np.stack([model.predict_proba(frame[STATE_FEATURES]) for model in state_models]),axis=0)
    values=np.clip(values,1e-7,1); return values/values.sum(axis=1,keepdims=True)

def calibration_design(raw):
    values=np.clip(np.asarray(raw,dtype=float),1e-7,1)
    return np.log(np.clip(values[:,1:]/values[:,[0]],1e-7,1e7))

def apply_prior_scaling(probability,scales):
    adjusted=np.clip(np.asarray(probability,dtype=float),1e-9,1)*np.asarray(scales,dtype=float)
    return adjusted/adjusted.sum(axis=1,keepdims=True)

cal_raw=raw_state_probability(state_cal)
calibrator=LogisticRegression(C=.35,penalty='l2',class_weight=None,max_iter=3000,random_state=26073)
calibrator.fit(calibration_design(cal_raw),ys_cal)
cal_base=calibrator.predict_proba(calibration_design(cal_raw))
target_prior=np.bincount(ys_cal,minlength=3).astype(float); target_prior/=target_prior.sum()
prior_scales=np.ones(3,dtype=float)
for _ in range(200):
    current=apply_prior_scaling(cal_base,prior_scales).mean(axis=0)
    prior_scales*=target_prior/np.clip(current,1e-9,None)
    prior_scales/=prior_scales[0]
calibrated_cal=apply_prior_scaling(cal_base,prior_scales)
joblib.dump({'model':calibrator,'prior_scales':prior_scales,'classes':CLASS_NAMES.tolist()},
            ITER10_ROOT/'iteration10r_l2_incident_calibrator.joblib',compress=3)

def calibrated_state_probability(raw):
    base=calibrator.predict_proba(calibration_design(raw))
    return apply_prior_scaling(base,prior_scales)

def add_state_probability(frame):
    result=frame.copy(); raw=raw_state_probability(result); calibrated=calibrated_state_probability(raw)
    for index,name in enumerate(CLASS_NAMES):
        result[f'state_raw_p_{name}']=raw[:,index].astype(np.float32)
        result[f'state_p_{name}']=calibrated[:,index].astype(np.float32)
    return result

calibration_development_audit={
    'rows':len(state_cal),'observed_class_prior':dict(zip(CLASS_NAMES,target_prior.tolist())),
    'mean_raw_probability':dict(zip(CLASS_NAMES,cal_raw.mean(axis=0).tolist())),
    'mean_calibrated_probability':dict(zip(CLASS_NAMES,calibrated_cal.mean(axis=0).tolist())),
    'raw':{},'calibrated':{},
}
for name,index in (('fault',2),('weather',1)):
    labels=(ys_cal==index).astype(int)
    calibration_development_audit['raw'][name]=calibration_metrics(labels,cal_raw[:,index],bins=10)
    calibration_development_audit['calibrated'][name]=calibration_metrics(labels,calibrated_cal[:,index],bins=10)
normal_mask=ys_cal==0
normal_fault=calibrated_cal[normal_mask,2]
calibration_development_audit['normal_fault_probability_q99']=float(np.quantile(normal_fault,.99))
calibration_development_audit['normal_fault_probability_q999']=float(np.quantile(normal_fault,.999))
calibration_development_audit['maximum_prior_absolute_error']=float(np.max(np.abs(calibrated_cal.mean(axis=0)-target_prior)))
CALIBRATION_SAFETY_PASS=bool(
    np.isfinite(calibrated_cal).all() and
    calibration_development_audit['maximum_prior_absolute_error']<=.002 and
    calibration_development_audit['normal_fault_probability_q99']<=.20 and
    calibration_development_audit['calibrated']['fault']['expected_calibration_error']<=
        calibration_development_audit['raw']['fault']['expected_calibration_error']+.005)
calibration_development_audit['safety_pass']=CALIBRATION_SAFETY_PASS
(ITER10_ROOT/'iteration10r_calibration_development_audit.json').write_text(
    json.dumps(calibration_development_audit,indent=2))

train_state=add_state_probability(train_state); main_state=add_state_probability(main_state)
pd.DataFrame(model_history).to_csv(ITER10_ROOT/'iteration10r_model_training_history.csv',index=False)
print({'calibration_safety_pass':CALIBRATION_SAFETY_PASS,
       'observed_prior':target_prior.tolist(),'calibrated_mean':calibrated_cal.mean(axis=0).tolist(),
       'normal_fault_q99':calibration_development_audit['normal_fault_probability_q99']})
print(pd.DataFrame(model_history))
""")

# Stateful policy replacement.  Preserve the evaluator/matching functions in the
# base cell, but replace state transitions and policy search.
policy_cell = source(cells[26])
apply_policy_code = r"""def apply_policy(frame,policy):
    source=(frame.sort_values(['eval_station_id','causal_arrival_timestamp_utc','stream_order'],kind='stable')
            .reset_index(drop=True).copy())
    decisions=np.full(len(source),'normal',dtype=object); confidence=np.zeros(len(source),dtype=np.float32)
    first_alert=np.full(len(source),'',dtype=object)
    for _series,indices in source.groupby('eval_station_id',sort=False).groups.items():
        fault_votes=deque(maxlen=int(policy['n'])); weather_votes=deque(maxlen=int(policy['n']))
        active='normal'; active_alert=''; recovery=0
        for index in indices:
            row=source.loc[index]
            fp=float(row.state_p_sensor_fault); wp=float(row.state_p_genuine_weather)
            now=pd.Timestamp(row.causal_arrival_timestamp_utc); hard=bool(row.hard_fault)
            weather_supported=(bool(row.independent_weather_gate) and
                float(row.safe_weather_agreement)>=float(policy.get('weather_agreement_threshold',.55)) and
                wp>=float(policy.get('weather_probability_floor',.10)) and
                (wp>=policy['weather_threshold'] or wp>=1.20*fp))
            drift_rescue=(bool(policy.get('enable_drift_rescue',False)) and bool(row.isolated_drift_gate) and
                float(row.drift_support_count)>=3 and
                float(row.drift_evidence_score)>=float(policy['drift_rescue_threshold']) and
                fp>=float(policy['drift_min_fault_probability']) and not weather_supported)
            fault_vote=hard or ((fp>=policy['fault_threshold']) and not weather_supported) or drift_rescue
            weather_vote=weather_supported and not hard
            window=pd.Timedelta(minutes=float(policy.get('window_minutes',720)))
            while fault_votes and now-fault_votes[0][0]>window: fault_votes.popleft()
            while weather_votes and now-weather_votes[0][0]>window: weather_votes.popleft()
            if weather_vote: fault_votes.clear()
            if fault_vote: weather_votes.clear()
            fault_votes.append((now,int(fault_vote))); weather_votes.append((now,int(weather_vote)))
            slow_high_confidence=(float(row.expected_interval_minutes)>=120 and
                                  fp>=max(.90,float(policy['fault_threshold'])*1.20))
            required_fault=1 if slow_high_confidence else int(policy['k'])
            required_weather=1 if (float(row.expected_interval_minutes)>=120 and wp>=.90) else int(policy['k'])
            desired='normal'
            if hard or sum(value for _time,value in fault_votes)>=required_fault: desired='sensor_fault'
            elif sum(value for _time,value in weather_votes)>=required_weather: desired='genuine_weather'
            strong_cross_class_fault=hard or (desired=='sensor_fault' and bool(row.isolated_drift_gate) and fp>=.90)
            if active=='normal' and desired!='normal':
                active=desired; active_alert=str(row.causal_arrival_timestamp_utc); recovery=0
            elif active!='normal':
                if desired==active: recovery=0
                elif desired!='normal' and desired!=active:
                    if active=='genuine_weather' and strong_cross_class_fault:
                        active='sensor_fault'; active_alert=str(row.causal_arrival_timestamp_utc); recovery=0
                    else:
                        recovery+=1
                        if recovery>=int(policy.get('recovery_points',2)):
                            active=desired; active_alert=str(row.causal_arrival_timestamp_utc); recovery=0
                else:
                    recovery+=1
                    if recovery>=int(policy.get('recovery_points',2)):
                        active='normal'; active_alert=''; recovery=0
            decisions[index]=active
            confidence[index]=1.0 if hard else (fp if active=='sensor_fault' else (wp if active=='genuine_weather' else float(row.state_p_normal)))
            first_alert[index]=active_alert
    source['decision_state']=decisions; source['decision_confidence']=confidence; source['first_alert_utc']=first_alert
    source['decision_run_id']=source.groupby('eval_station_id',sort=False).decision_state.transform(
        lambda values: values.ne(values.shift()).cumsum()).astype(int)
    return source
"""
policy_cell = replace_between(policy_cell, "def apply_policy(frame,policy):", "def predicted_incidents", apply_policy_code)

# Add row-level safety diagnostics to every evaluation result.
policy_cell = policy_cell.replace(
    "result={'scope':scope,'fault':fault,'weather':weather,'fault_to_weather_rate':float(fault_to_weather),\n"
    "            'weather_to_fault_rate':float(weather_to_fault),'station_days':station_days}",
    "normal_mask=decisions.eval_label_category.eq('normal').to_numpy()\n"
    "    normal_to_fault=float(decisions.loc[normal_mask,'decision_state'].eq('sensor_fault').mean()) if normal_mask.any() else 0.0\n"
    "    result={'scope':scope,'fault':fault,'weather':weather,'fault_to_weather_rate':float(fault_to_weather),\n"
    "            'weather_to_fault_rate':float(weather_to_fault),'station_days':station_days,\n"
    "            'normal_to_fault_row_rate':normal_to_fault,\n"
    "            'predicted_fault_row_fraction':float(decisions.decision_state.eq('sensor_fault').mean()),\n"
    "            'predicted_weather_row_fraction':float(decisions.decision_state.eq('genuine_weather').mean())}",
)

selection_code = r"""policy_holdout=((main_state.i10_domain.eq('india')&main_state.station_id.isin(INDIA_HOLDOUTS))|
                 (main_state.i10_domain.eq('dwd')&main_state.station_id.isin(DWD_HOLDOUTS)))
policy_selection_state=main_state.loc[~policy_holdout].copy()
assert not ((policy_selection_state.i10_domain.eq('india')&policy_selection_state.station_id.isin(INDIA_HOLDOUTS))|
            (policy_selection_state.i10_domain.eq('dwd')&policy_selection_state.station_id.isin(DWD_HOLDOUTS))).any()
policy_normal=policy_selection_state.loc[policy_selection_state.i10_scope.eq('policy')&
    policy_selection_state.eval_label_category.eq('normal'),'state_p_sensor_fault'].dropna()
fault_threshold_grid=sorted(set(float(np.clip(value,.05,.98)) for value in
    [*policy_normal.quantile([.98,.99,.995,.999]).tolist(),.20,.50,.80,.95]))
weather_threshold_grid=(.35,.55,.75,.90)
policy_drift=policy_selection_state.loc[policy_selection_state.i10_scope.eq('policy')&
    policy_selection_state.eval_label_category.eq('normal')&policy_selection_state.isolated_drift_gate.eq(1),
    'drift_evidence_score'].dropna()
policy_drift_threshold=float(np.clip(policy_drift.quantile(.999) if len(policy_drift) else TRAIN_DRIFT_RESCUE_FLOOR,
                                     TRAIN_DRIFT_RESCUE_FLOOR,11.5))
def evaluate_policy_candidate(policy,search_stage):
    measured=evaluation(policy_selection_state,main_events,'policy',policy)
    domain_results={domain:evaluation(policy_selection_state.loc[policy_selection_state.i10_domain.eq(domain)],
                                      main_events,'policy',policy)
                    for domain in ('india','dwd')}
    min_precision=min(item['fault']['precision'] for item in domain_results.values())
    min_fault_f1=min(item['fault']['f1'] for item in domain_results.values())
    max_false=max(item['fault']['false_alerts_per_station_day'] for item in domain_results.values())
    max_normal_to_fault=max(item['normal_to_fault_row_rate'] for item in domain_results.values())
    max_weather_to_fault=max(item['weather_to_fault_rate'] for item in domain_results.values())
    fault=measured['fault']; weather=measured['weather']
    eligible=(CALIBRATION_SAFETY_PASS and min_precision>=.70 and max_false<=.02 and
              max_normal_to_fault<=.005 and max_weather_to_fault<=.10)
    objective=(2.5*min_precision+1.5*min_fault_f1+weather['f1']+fault['recall']
               -20.0*max_false-5.0*max_normal_to_fault-2.0*max_weather_to_fault)
    return {**policy,'search_stage':search_stage,'fault_precision':fault['precision'],
        'fault_recall':fault['recall'],'fault_f1':fault['f1'],
        'false_alerts_per_station_day':fault['false_alerts_per_station_day'],
        'weather_f1':weather['f1'],'weather_precision':weather['precision'],'weather_recall':weather['recall'],
        'fault_to_weather_rate':measured['fault_to_weather_rate'],'weather_to_fault_rate':measured['weather_to_fault_rate'],
        'normal_to_fault_row_rate':measured['normal_to_fault_row_rate'],'worst_domain_fault_precision':min_precision,
        'worst_domain_fault_f1':min_fault_f1,'worst_domain_false_alerts_per_station_day':max_false,
        'worst_domain_normal_to_fault_rate':max_normal_to_fault,'worst_domain_weather_to_fault_rate':max_weather_to_fault,
        'objective':objective,'policy_eligible':bool(eligible)}

frontier=[]
for k,n in ((1,2),(2,3),(3,5)):
    for fault_threshold in fault_threshold_grid:
        for weather_threshold in weather_threshold_grid:
            policy={'fault_threshold':float(fault_threshold),'weather_threshold':float(weather_threshold),
                    'k':k,'n':n,'window_minutes':720,'enable_drift_rescue':False,
                    'drift_rescue_threshold':policy_drift_threshold,
                    'drift_min_fault_probability':max(.08,.50*float(fault_threshold)),
                    'weather_agreement_threshold':.55,'weather_probability_floor':.10,'recovery_points':2}
            frontier.append(evaluate_policy_candidate(policy,'core'))

# Drift is a challenger, not an always-on rescue.  Only the twelve strongest core
# policies are re-evaluated with isolated multi-window drift evidence enabled.
core_frontier=pd.DataFrame(frontier).sort_values(['policy_eligible','objective'],ascending=[False,False])
for candidate in core_frontier.head(12).to_dict('records'):
    policy={key:candidate[key] for key in ('fault_threshold','weather_threshold','k','n','window_minutes',
        'drift_rescue_threshold','drift_min_fault_probability','weather_agreement_threshold',
        'weather_probability_floor','recovery_points')}
    policy['enable_drift_rescue']=True
    frontier.append(evaluate_policy_candidate(policy,'drift_challenge'))
policy_frontier=pd.DataFrame(frontier).sort_values(['policy_eligible','objective'],ascending=[False,False])
eligible=policy_frontier.loc[policy_frontier.policy_eligible]
if len(eligible):
    selected=eligible.iloc[0]; POLICY_PROMOTABLE=True; policy_status='ELIGIBLE_POLICY_FROZEN'
else:
    selected=policy_frontier.sort_values(
        ['worst_domain_false_alerts_per_station_day','worst_domain_normal_to_fault_rate','worst_domain_fault_precision'],
        ascending=[True,True,False]).iloc[0]
    POLICY_PROMOTABLE=False; policy_status='NO_ELIGIBLE_POLICY_DIAGNOSTIC_ONLY'
policy_keys=('fault_threshold','weather_threshold','k','n','window_minutes','enable_drift_rescue',
             'drift_rescue_threshold','drift_min_fault_probability','weather_agreement_threshold',
             'weather_probability_floor','recovery_points')
EVALUATION_POLICY={key:(bool(selected[key]) if key=='enable_drift_rescue' else
                        int(selected[key]) if key in {'k','n','recovery_points'} else float(selected[key]))
                   for key in policy_keys}
FROZEN_POLICY=EVALUATION_POLICY if POLICY_PROMOTABLE else None
policy_frontier.to_csv(ITER10_ROOT/'iteration10r_policy_frontier.csv',index=False)
(ITER10_ROOT/'iteration10r_frozen_policy.json').write_text(json.dumps({
    'status':policy_status,'frozen_policy':FROZEN_POLICY,'diagnostic_policy':EVALUATION_POLICY,
    'eligible_policy_count':int(len(eligible))},indent=2))
print({'policy_status':policy_status,'eligible_policy_count':len(eligible),
       'evaluation_policy':EVALUATION_POLICY,'calibration_safety_pass':CALIBRATION_SAFETY_PASS})
display(policy_frontier.head(20))
"""
policy_cell = replace_between(policy_cell, "policy_holdout=", "", selection_code) if False else policy_cell
# The policy-selection block is the final block in this code cell.
start_index = policy_cell.find("policy_holdout=")
if start_index < 0:
    raise RuntimeError("Policy selection marker not found")
policy_cell = policy_cell[:start_index] + selection_code.strip() + "\n"
set_source(cells[26], policy_cell)

# Downstream metrics are always diagnostic when policy gates fail; no failed policy
# is represented as frozen/deployable.
for index in (28, 30):
    set_source(cells[index], source(cells[index]).replace("FROZEN_POLICY", "EVALUATION_POLICY"))

health = source(cells[32])
correction_code = r"""SENSOR_FIELDS={
    'temperature':('temperature_value','temperature_rolling_median_24h','neighbor_temperature_median','original_temperature_c','temperature_rolling_mad_24h'),
    'pressure':('pressure_value','pressure_rolling_median_24h',None,'original_pressure_hpa','pressure_rolling_mad_24h'),
    'humidity':('humidity_value','humidity_rolling_median_24h','neighbor_humidity_median','original_relative_humidity_pct','humidity_rolling_mad_24h')}

def collect_correction_rows(decisions):
    rows=[]; eligible_pairs=defaultdict(int)
    true_fault=decisions.loc[decisions.eval_label_category.eq('sensor_fault')]
    for value in true_fault.eval_anomaly_sensor:
        for sensor in str(value).split(','):
            if sensor in SENSOR_FIELDS: eligible_pairs[sensor]+=1
    matched=decisions.loc[decisions.decision_state.eq('sensor_fault')&
                          decisions.eval_label_category.eq('sensor_fault')]
    for row in matched.itertuples():
        sensors=[name for name in str(row.eval_anomaly_sensor).split(',') if name in SENSOR_FIELDS]
        for sensor in sensors:
            observed_col,prior_col,neighbor_col,truth_col,mad_col=SENSOR_FIELDS[sensor]
            observed=pd.to_numeric(pd.Series([getattr(row,observed_col)]),errors='coerce').iloc[0]
            truth=pd.to_numeric(pd.Series([getattr(row,truth_col)]),errors='coerce').iloc[0]
            candidates=[pd.to_numeric(pd.Series([getattr(row,prior_col)]),errors='coerce').iloc[0]]
            if neighbor_col:
                candidates.append(pd.to_numeric(pd.Series([getattr(row,neighbor_col)]),errors='coerce').iloc[0])
            candidates=[float(value) for value in candidates if np.isfinite(value)]
            if not candidates or not np.isfinite(truth) or not np.isfinite(observed): continue
            estimate=float(np.median(candidates))
            mad=pd.to_numeric(pd.Series([getattr(row,mad_col)]),errors='coerce').iloc[0]
            base_scale=max(float(mad)*1.4826 if np.isfinite(mad) else 0.0,
                           {'temperature':.5,'pressure':.7,'humidity':2.0}[sensor])
            rows.append({'sensor':sensor,'observed':float(observed),'truth':float(truth),'estimate':estimate,
                'base_scale':base_scale,'absolute_error_observed':abs(float(observed)-float(truth)),
                'absolute_error_corrected':abs(estimate-float(truth))})
    return pd.DataFrame(rows),eligible_pairs

correction_calibration_frame=main_state.loc[main_state.i10_scope.eq('calibration')&
    main_state.available_to_detector.eq(1)&
    ~((main_state.i10_domain.eq('india')&main_state.station_id.isin(INDIA_HOLDOUTS))|
      (main_state.i10_domain.eq('dwd')&main_state.station_id.isin(DWD_HOLDOUTS)))].copy()
correction_calibration_decisions=apply_policy(correction_calibration_frame,EVALUATION_POLICY)
correction_calibration,_=collect_correction_rows(correction_calibration_decisions)
conformal_policy={}
for sensor in SENSOR_FIELDS:
    block=correction_calibration.loc[correction_calibration.sensor.eq(sensor)] if len(correction_calibration) else pd.DataFrame()
    if len(block)>=20:
        ratios=(block.absolute_error_corrected/block.base_scale.clip(lower=1e-9)).replace([np.inf,-np.inf],np.nan).dropna()
        rank=min(1.0,math.ceil((len(ratios)+1)*.90)/max(len(ratios),1))
        multiplier=max(1.645,float(np.quantile(ratios,rank,method='higher')))
        source_name='development_conformal_90'
    else:
        multiplier=3.0; source_name='conservative_small_sample_fallback'
    conformal_policy[sensor]={'multiplier':multiplier,'calibration_rows':int(len(block)),
                              'target_marginal_coverage':.90,'source':source_name}
(ITER10_ROOT/'iteration10r_correction_conformal_policy.json').write_text(json.dumps(conformal_policy,indent=2))

corrections,eligible_pairs=collect_correction_rows(confirmation_decisions)
if len(corrections):
    corrections['interval_multiplier']=corrections.sensor.map(
        {name:value['multiplier'] for name,value in conformal_policy.items()}).astype(float)
    corrections['interval_low']=corrections.estimate-corrections.interval_multiplier*corrections.base_scale
    corrections['interval_high']=corrections.estimate+corrections.interval_multiplier*corrections.base_scale
    corrections['squared_error_observed']=(corrections.observed-corrections.truth)**2
    corrections['squared_error_corrected']=(corrections.estimate-corrections.truth)**2
    correction_metrics=(corrections.assign(covered=lambda x:(x.truth>=x.interval_low)&(x.truth<=x.interval_high))
        .groupby('sensor').agg(rows=('truth','size'),observed_mae=('absolute_error_observed','mean'),
         corrected_mae=('absolute_error_corrected','mean'),observed_mse=('squared_error_observed','mean'),
         corrected_mse=('squared_error_corrected','mean'),interval_coverage=('covered','mean'),
         interval_multiplier=('interval_multiplier','first')).reset_index())
    correction_metrics['observed_rmse']=np.sqrt(correction_metrics.observed_mse)
    correction_metrics['corrected_rmse']=np.sqrt(correction_metrics.corrected_mse)
    correction_metrics['mae_improvement_pct']=100*(correction_metrics.observed_mae-correction_metrics.corrected_mae).div(
        correction_metrics.observed_mae.clip(lower=1e-9))
    correction_metrics['eligible_true_fault_rows']=correction_metrics.sensor.map(eligible_pairs).fillna(0).astype(int)
    correction_metrics['end_to_end_coverage']=correction_metrics.rows.div(correction_metrics.eligible_true_fault_rows.clip(lower=1))
    correction_metrics['coverage_gap_to_90']=correction_metrics.interval_coverage-.90
else:
    correction_metrics=pd.DataFrame(columns=['sensor','rows','observed_mae','corrected_mae','observed_rmse',
        'corrected_rmse','mae_improvement_pct','interval_coverage','interval_multiplier',
        'eligible_true_fault_rows','end_to_end_coverage','coverage_gap_to_90'])
correction_metrics.to_csv(ITER10_ROOT/'iteration10r_correction_metrics.csv',index=False)
"""
health = replace_between(health, "SENSOR_FIELDS=", "fault_incidents=", correction_code)
health = health.replace(
    "score=float(np.clip(100-8*len(incidents)-10*drift-6*critical,0,100))\n"
    "    status='healthy' if score>=80 else ('degrading' if score>=50 else 'critical')\n"
    "    action='no action' if status=='healthy' else ('inspect within seven days' if status=='degrading' else 'immediate calibration/inspection')",
    "if POLICY_PROMOTABLE:\n"
    "        score=float(np.clip(100-8*len(incidents)-10*drift-6*critical,0,100))\n"
    "        status='healthy' if score>=80 else ('degrading' if score>=50 else 'critical')\n"
    "        action='no action' if status=='healthy' else ('inspect within seven days' if status=='degrading' else 'immediate calibration/inspection')\n"
    "    else:\n"
    "        score=np.nan; status='shadow_unvalidated'; action='no automatic maintenance action until detection gates pass'",
)
set_source(cells[32], health)

# Final result: add repaired integrity/calibration gates and preserve the distinction
# between an eligible frozen policy and a diagnostic fallback.
final = source(cells[34])
final = final.replace(
    "promotion_gates={\n",
    "promotion_gates={\n"
    "    'calibration_development_safety_pass':CALIBRATION_SAFETY_PASS,\n"
    "    'eligible_policy_found':POLICY_PROMOTABLE,\n"
    "    'india_and_dwd_holdout_rows_nonzero':HOLDOUT_INTEGRITY['india_main_rows']>0 and HOLDOUT_INTEGRITY['dwd_main_rows']>0,\n"
    "    'holdouts_absent_from_training':HOLDOUT_INTEGRITY['india_train_rows']==0 and HOLDOUT_INTEGRITY['dwd_train_rows']==0,\n",
    1,
)
final = final.replace(
    "'feature_contract':feature_contract,'frozen_policy':FROZEN_POLICY,",
    "'feature_contract':feature_contract,'frozen_policy':FROZEN_POLICY,'diagnostic_policy':EVALUATION_POLICY,\n"
    "    'policy_promotable':POLICY_PROMOTABLE,'calibration_development_audit':calibration_development_audit,\n"
    "    'holdout_integrity':HOLDOUT_INTEGRITY,",
)
final = final.replace(
    "'station_holdouts_used_for_fit_calibration_or_policy':False},",
    "'station_holdouts_used_for_fit_calibration_or_policy':False,\n"
    "       'verified_holdout_row_counts':HOLDOUT_INTEGRITY,'cache_schema':CACHE_SCHEMA_VERSION},",
)
final = final.replace("'iteration':'10_final_incident_intelligence'", "'iteration':'10r_calibration_integrity_repair'")
final = final.replace(
    "integrity={'status':'PASS'",
    "integrity={'status':'PASS' if (CALIBRATION_SAFETY_PASS and all(value>0 for key,value in HOLDOUT_INTEGRITY.items() if key.endswith('main_rows')) and all(value==0 for key,value in HOLDOUT_INTEGRITY.items() if key.endswith('train_rows'))) else 'FAIL'",
)
final = final.replace(
    "'confirmation_used_for_selection':False,'automatic_deployment':False}",
    "'confirmation_used_for_selection':False,'automatic_deployment':False,\n"
    "           'cache_schema':CACHE_SCHEMA_VERSION,'holdout_integrity':HOLDOUT_INTEGRITY,\n"
    "           'calibration_safety_pass':CALIBRATION_SAFETY_PASS,'policy_promotable':POLICY_PROMOTABLE}",
)
set_source(cells[34], final)

set_source(cells[35], r"""
# Mandatory stop and return-to-Codex rule

Do **not** open 2024 or 2025 from this notebook. Return these files from the
Iteration 10R experiment folder:

- `iteration10r_result_block.json`
- `iteration10r_calibration_development_audit.json`
- `iteration10r_multidomain_confirmation.csv`
- `iteration10r_fault_episode_recall.csv`
- `iteration10r_multiseed_stress.csv`
- `iteration10r_root_cause_metrics.csv`
- `iteration10r_root_cause_per_class.csv`
- `iteration10r_calibration_metrics.json`
- `iteration10r_correction_metrics.csv`
- `iteration10r_policy_frontier.csv`
- `iteration10r_feature_contract.json`
- `iteration10r_integrity_receipt.json`
- `iteration10r_runtime_metrics.json`
- `SkyGuard_Iteration10R_Result_Package.zip`

If `policy_promotable` is false, the generated results are diagnostic only. Do not
connect them to automatic maintenance, correction or deployment actions.
""")

for cell in cells:
    if cell.get("cell_type") == "code":
        cell["execution_count"] = None
        cell["outputs"] = []

notebook["metadata"]["colab"]["name"] = OUTPUT.name
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
DELIVERABLE.parent.mkdir(parents=True, exist_ok=True)
payload = json.dumps(notebook, indent=1, ensure_ascii=False) + "\n"
OUTPUT.write_text(payload, encoding="utf-8")
DELIVERABLE.write_text(payload, encoding="utf-8")
print(json.dumps({"notebook": str(OUTPUT), "deliverable": str(DELIVERABLE),
                  "cells": len(cells), "bytes": OUTPUT.stat().st_size}, indent=2))
