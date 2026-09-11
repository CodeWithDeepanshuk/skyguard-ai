"""Build the standalone SkyGuard Iteration 10 final incident-intelligence Colab.

The notebook intentionally trains and selects policy only on 2022-2023.  It
contains no code path that opens the locked 2024/2025 observations.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks" / "SkyGuard_AI_GPU_Iteration_10_Final_Incident_Intelligence_Colab.ipynb"
DELIVERABLE = ROOT / "deliverables" / OUTPUT.name


def md(text: str) -> dict[str, object]:
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text: str) -> dict[str, object]:
    return {
        "cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
        "source": text.splitlines(keepends=True),
    }


cells: list[dict[str, object]] = [
    md(r"""# SkyGuard AI — GPU Iteration 10 (final development candidate)

## Causal incident intelligence, complete SIH26073 fault coverage, and multi-climate confirmation

This is a **standalone** final-development notebook. It fixes the architectural failures seen through Iteration 9 instead of merely adding a larger neural network:

1. official corrected NOAA/NCEI India data plus official DWD multi-climate data;
2. all SIH inputs restricted to temperature, pressure and relative humidity;
3. separate meteorological and operational replay lanes covering six genuine-weather families and thirteen fault/communication families;
4. domain-invariant causal row evidence;
5. mutually exclusive `normal / genuine_weather / sensor_fault` incident state;
6. independent neighbour-weather gate, k-of-n persistence, hysteresis and instant hard-fault path;
7. dedicated drift evidence, incident-level root cause, calibrated confidence and advisory corrections;
8. station/time/season-safe splits, fresh injection seeds and locked-year protection.

Passing this notebook makes the candidate **eligible for one separately authorised locked confirmation**. It never deploys itself and never opens 2024 or 2025.
"""),
    md(r"""## Exact run instructions

1. Upload these two unchanged files to `/content/drive/MyDrive/SkyGuard_AI_GPU/`:
   - `SkyGuard_Iteration10_Final_Starter_Bundle.zip`
   - `SkyGuard_Iteration8_Development_Data_Bundle.zip`
2. Select **Runtime → Change runtime type → T4 GPU**.
3. Keep `UNLOCK_FINAL_TESTS=False`, `REUSE_FEATURE_CACHE=True`, and `RUN_STRESS_SEEDS=True`.
4. Use **Runtime → Run all**. The first run can take 2–5 hours because every feature is rebuilt causally; Drive caches make a resumed run much faster.
5. Send back the files listed by the final cell, especially `iteration10_result_block.json` and the confirmation/episode/root/calibration CSV/JSON files.

Do not upload any locked-year observation bundle into this runtime.
"""),
    code(r"""# Colab dependencies. Torch is already present on a T4 runtime.
!pip -q install lightgbm==4.6.0 catboost==1.2.8 joblib==1.5.2 scikit-learn==1.7.2 shap==0.48.0 psutil==7.0.0
"""),
    md(r"""## 1. Runtime, reproducibility and immutable safety settings"""),
    code(r"""from __future__ import annotations

import gc,hashlib,json,math,os,random,shutil,sys,time,zipfile
from collections import defaultdict,deque
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import psutil
import torch
from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier,early_stopping,log_evaluation
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score,average_precision_score,balanced_accuracy_score,
                             classification_report,confusion_matrix,f1_score)

GLOBAL_SEED=26073
random.seed(GLOBAL_SEED); np.random.seed(GLOBAL_SEED); torch.manual_seed(GLOBAL_SEED)
if torch.cuda.is_available(): torch.cuda.manual_seed_all(GLOBAL_SEED)

UNLOCK_FINAL_TESTS=False
REUSE_FEATURE_CACHE=True
RUN_STRESS_SEEDS=True
DEVELOPMENT_YEARS=(2022,2023)
LOCKED_YEARS=(2024,2025)
MAIN_SEED=10023
STRESS_SEEDS=(10061,10103)
assert UNLOCK_FINAL_TESTS is False

try:
    from google.colab import drive
    drive.mount('/content/drive',force_remount=False)
except ImportError:
    print('Non-Colab runtime: using the current filesystem.')

DRIVE_ROOT=Path('/content/drive/MyDrive/SkyGuard_AI_GPU') if Path('/content/drive').exists() else Path.cwd()
ITER10_ROOT=DRIVE_ROOT/'experiments'/'iteration_10_final_incident_intelligence'
ITER10_ROOT.mkdir(parents=True,exist_ok=True)
LOCAL_ROOT=Path('/content/skyguard_iteration10') if Path('/content').exists() else Path.cwd()/'.iteration10_runtime'
LOCAL_ROOT.mkdir(parents=True,exist_ok=True)
print({'gpu':torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU',
       'python':sys.version.split()[0],'drive_root':str(DRIVE_ROOT),'output':str(ITER10_ROOT),
       'locked_years_opened':False})
"""),
    md(r"""## 2. Locate, verify and extract the two approved development bundles"""),
    code(r"""STARTER_NAME='SkyGuard_Iteration10_Final_Starter_Bundle.zip'
DWD_NAME='SkyGuard_Iteration8_Development_Data_Bundle.zip'
EXPECTED_BUNDLE_SHA256={
    STARTER_NAME:'47b5db0ccea2b46f4adbc24ac41a8ccf4a08c4f140234544009a4ba95bf850f7',
    DWD_NAME:'7f47466805309faf528d6abc8f04a588c4accbaf454989e36a2b4ff5b31681d4',
}

def sha256_file(path,block=1024*1024):
    digest=hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda:handle.read(block),b''): digest.update(chunk)
    return digest.hexdigest()

def find_bundle(name):
    exact=DRIVE_ROOT/name
    if exact.exists(): return exact
    matches=list(DRIVE_ROOT.rglob(name))
    if len(matches)!=1: raise FileNotFoundError(f'Expected exactly one {name}; found {matches}')
    return matches[0]

def safe_extract(bundle,destination):
    destination=Path(destination).resolve()
    with zipfile.ZipFile(bundle) as archive:
        for member in archive.infolist():
            target=(destination/member.filename).resolve()
            if destination not in target.parents and target!=destination:
                raise RuntimeError(f'Unsafe ZIP member: {member.filename}')
        archive.extractall(destination)

bundles={name:find_bundle(name) for name in (STARTER_NAME,DWD_NAME)}
for name,path in bundles.items():
    actual=sha256_file(path)
    assert actual==EXPECTED_BUNDLE_SHA256[name],f'{name} checksum mismatch: {actual}'
    print(name,actual,Path(path).stat().st_size)

if LOCAL_ROOT.exists():
    shutil.rmtree(LOCAL_ROOT)
LOCAL_ROOT.mkdir(parents=True)
for path in bundles.values(): safe_extract(path,LOCAL_ROOT)

STARTER=LOCAL_ROOT/'SkyGuard_Iteration10_Final_Starter_Bundle'
DWD_BUNDLE=LOCAL_ROOT/'SkyGuard_Iteration8_Development_Data_Bundle'
starter_manifest=json.loads((STARTER/'bundle_manifest.json').read_text())
dwd_manifest=json.loads((DWD_BUNDLE/'bundle_manifest.json').read_text())
for entry in starter_manifest['files']:
    path=STARTER/entry['path']; assert path.is_file() and sha256_file(path)==entry['sha256']
for entry in dwd_manifest['files']:
    path=DWD_BUNDLE/entry['relative_path']; assert path.is_file() and sha256_file(path)==entry['sha256']
assert starter_manifest['development_years']==[2022,2023]
assert starter_manifest['locked_observation_years_included']==[]
assert dwd_manifest['contains_2024_observations'] is False and dwd_manifest['contains_2025_observations'] is False
sys.path.insert(0,str(STARTER/'src'))
print({'starter_files':len(starter_manifest['files']),'dwd_files':len(dwd_manifest['files']),
       'bundle_integrity':'PASS','locked_observations_loaded':False})
"""),
    md(r"""## 3. Load and independently audit official India + DWD development observations

DWD is reduced from 10-minute to exact hourly timestamps to keep the final run within a free T4 session. India retains its genuine mixed cadence. Dew point and every non-SIH observation are blanked or retained only as audit metadata."""),
    code(r"""from skyguard.faults.curriculum import (FAULT_FAMILIES as SUBTLE_FAULT_FAMILIES,
    WEATHER_FAMILIES,MultiClimateCurriculum)
from skyguard.faults.injector import FaultInjector
from skyguard.faults.models import FAULT_TYPES as OPERATIONAL_FAULT_FAMILIES
from skyguard.features.builder import FeatureBuilder
from skyguard.features.contracts import FeatureConfig,OUTPUT_COLUMNS
from skyguard.features.neighbors import NeighborIndex
from skyguard.features.temporal import TemporalFeatureBuilder
from skyguard.features.phase10 import PHASE10_FEATURES,add_phase10_features,fit_climatology
from skyguard.evaluation.incident_metrics import calibration_metrics,incident_metrics,match_incidents

PRIMARY=['temperature_c','pressure_hpa','relative_humidity_pct']

india=pd.read_csv(STARTER/'data'/'india_aws_2022_2023.csv.gz',dtype={'station_id':str},low_memory=False)
india_stations=pd.read_csv(STARTER/'config'/'india_stations.csv',dtype={'station_id':str})
india_report=json.loads((STARTER/'reports'/'iteration10_india_data_validation.json').read_text())
assert india_report['status']=='PASS'

def load_dwd(year):
    frame=pd.read_csv(DWD_BUNDLE/'data'/f'dwd_aws_10min_{year}.csv.gz',dtype={'station_id':str},low_memory=False)
    ts=pd.to_datetime(frame.timestamp_utc,utc=True)
    frame=frame.loc[ts.dt.minute.eq(0)].copy().reset_index(drop=True)
    frame['timestamp_utc']=pd.to_datetime(frame.timestamp_utc,utc=True).dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    return frame

dwd=pd.concat([load_dwd(2022),load_dwd(2023)],ignore_index=True)
dwd_stations=pd.read_csv(DWD_BUNDLE/'config'/'iteration8_dwd_stations.csv',dtype={'station_id':str})

def standardize(frame,domain):
    result=frame.copy()
    result['station_id']=result.station_id.astype(str)
    result['timestamp_utc']=pd.to_datetime(result.timestamp_utc,utc=True).dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    result['year']=pd.to_datetime(result.timestamp_utc,utc=True).dt.year.astype(int)
    result['cluster']=domain+'_'+result.cluster.astype(str)
    result['evaluation_role']=result.evaluation_role.astype(str)
    result['dew_point_c']=''
    for column in ('temperature_quality','pressure_quality'): 
        if column not in result: result[column]=''
    result=result.dropna(subset=PRIMARY).sort_values(['station_id','timestamp_utc'],kind='stable').reset_index(drop=True)
    result['i10_domain']=domain
    return result

india=standardize(india,'india'); dwd=standardize(dwd,'dwd')
india_stations['cluster']='india_'+india_stations.cluster.astype(str)
dwd_stations['cluster']='dwd_'+dwd_stations.cluster.astype(str)
INDIA_HOLDOUTS=sorted(india_stations.loc[india_stations.evaluation_role.eq('station_holdout'),'station_id'].tolist())
DWD_HOLDOUTS=['DWD-05839','DWD-01684','DWD-04336','DWD-00232']

for name,frame,stations in [('india',india,india_stations),('dwd',dwd,dwd_stations)]:
    assert set(frame.year.unique())=={2022,2023}
    assert frame.station_id.nunique()==len(stations)
    assert frame.cluster.nunique()==4
    assert not frame.duplicated(['station_id','timestamp_utc']).any()
    assert np.isfinite(frame[PRIMARY].to_numpy(float)).all()
    print(name,{'rows':len(frame),'stations':frame.station_id.nunique(),'clusters':frame.cluster.nunique(),
                'years':sorted(frame.year.unique().tolist())})
print({'india_holdouts':INDIA_HOLDOUTS,'dwd_holdouts':DWD_HOLDOUTS,
       'three_input_contract':PRIMARY,'locked_years_opened':False})
"""),
    md(r"""## 4. Build two non-overwriting replay lanes

The meteorological lane contributes six coherent regional weather families and subtle spike/bias/drift/frozen/noise faults. The operational lane independently contributes all thirteen fault families, including dropout, duplicate packet, timestamp, unit/scaling, corruption and multi-sensor failure. No event crosses a chronological scope."""),
    code(r"""SCOPE_RANGES={
    'calibration':('2023-01-08','2023-02-22'),
    'policy':('2023-03-05','2023-04-22'),
    'discovery':('2023-05-05','2023-08-25'),
    'confirmation':('2023-09-05','2023-12-22'),
}

def scope_from_time(values):
    ts=pd.to_datetime(values,utc=True)
    result=np.full(len(ts),'buffer',dtype=object)
    for scope,(start,end) in SCOPE_RANGES.items():
        mask=(ts>=pd.Timestamp(start,tz='UTC'))&(ts<=pd.Timestamp(end,tz='UTC')+pd.Timedelta(days=1)-pd.Timedelta(seconds=1))
        result[mask]=scope
    return result

def base_for(domain,year,include_holdouts):
    source=india if domain=='india' else dwd
    holdouts=INDIA_HOLDOUTS if domain=='india' else DWD_HOLDOUTS
    mask=source.year.eq(year)
    if not include_holdouts: mask&=~source.station_id.isin(holdouts)
    return source.loc[mask].copy().reset_index(drop=True)

def meteorological_lane(domain,year,seed,scopes=None):
    train=year==2022
    source=base_for(domain,year,include_holdouts=not train)
    if not train and scopes and set(scopes)!=set(SCOPE_RANGES):
        starts=[pd.Timestamp(value[0],tz='UTC') for value in scopes.values()]
        ends=[pd.Timestamp(value[1],tz='UTC') for value in scopes.values()]
        ts=pd.to_datetime(source.timestamp_utc,utc=True)
        source=source.loc[(ts>=min(starts)-pd.Timedelta(days=30))&
                          (ts<=max(ends)+pd.Timedelta(days=1))].copy().reset_index(drop=True)
    split=f'{domain}_meteorological_s{seed}_{"train" if train else "validation"}'
    injector=MultiClimateCurriculum(source,split,seed=seed)
    if train:
        injector.build_training('2022-01-08','2022-12-22',weather_repetitions=2,fault_repetitions=4)
    else:
        injector.build_validation(scopes or SCOPE_RANGES)
    audit=injector.validate(); assert audit['status']=='PASS'
    frame=injector.frame.copy(); frame['i10_domain']=domain; frame['i10_lane']='meteorological'; frame['i10_seed']=seed
    frame['i10_scope']='train' if train else scope_from_time(frame.timestamp_utc)
    events=injector.event_frame().copy()
    events['i10_domain']=domain; events['i10_lane']='meteorological'; events['i10_seed']=seed
    return frame,events,audit

def operational_lane(domain,year,seed,scopes=None):
    train=year==2022
    source=base_for(domain,year,include_holdouts=not train)
    frames=[]; events=[]
    if train:
        parts=[('train','2022-01-05','2022-12-27',source)]
    else:
        parts=[]
        for scope,(start,end) in (scopes or SCOPE_RANGES).items():
            ts=pd.to_datetime(source.timestamp_utc,utc=True)
            mask=(ts>=pd.Timestamp(start,tz='UTC'))&(ts<=pd.Timestamp(end,tz='UTC')+pd.Timedelta(days=1)-pd.Timedelta(seconds=1))
            parts.append((scope,start,end,source.loc[mask].copy()))
    for offset,(scope,_start,_end,part) in enumerate(parts):
        rows=part.sort_values(['station_id','timestamp_utc'],kind='stable').to_dict('records')
        split=f'{domain}_operational_s{seed}_{scope}'
        injector=FaultInjector(rows,split,seed+offset*997)
        injector.inject_suite(episodes_per_fault=5 if train else 1,weather_events=12 if train else 4)
        frame=pd.DataFrame(injector.rows)
        frame['i10_domain']=domain; frame['i10_lane']='operational'; frame['i10_seed']=seed; frame['i10_scope']=scope
        frames.append(frame)
        event=pd.DataFrame([item.to_dict() for item in injector.episodes])
        event['scope']=scope; event['i10_domain']=domain; event['i10_lane']='operational'; event['i10_seed']=seed
        events.append(event)
    return pd.concat(frames,ignore_index=True),pd.concat(events,ignore_index=True),{'status':'PASS'}

def make_curricula(seed,year,scopes=None):
    specs=[]; event_parts=[]; audits=[]
    for domain in ('india','dwd'):
        for lane_function in (meteorological_lane,operational_lane):
            frame,events,audit=lane_function(domain,year,seed,scopes)
            specs.append({'frame':frame,'domain':domain,'lane':frame.i10_lane.iloc[0],
                          'seed':seed,'year':year,'key':f'{domain}_{frame.i10_lane.iloc[0]}_{year}_s{seed}'})
            event_parts.append(events); audits.append(audit)
    events=pd.concat(event_parts,ignore_index=True,sort=False)
    assert events.episode_id.is_unique
    return specs,events,audits

train_specs,train_events,train_audits=make_curricula(GLOBAL_SEED+10,2022)
main_specs,main_events,main_audits=make_curricula(MAIN_SEED,2023)
all_development_events=pd.concat([train_events,main_events],ignore_index=True,sort=False)
all_development_events.to_csv(ITER10_ROOT/'iteration10_curriculum_events.csv',index=False)
coverage=(main_events.groupby(['scope','i10_domain','i10_lane','label_category','anomaly_type']).size()
          .rename('events').reset_index())
assert set(OPERATIONAL_FAULT_FAMILIES)<=set(main_events.anomaly_type)
assert set(WEATHER_FAMILIES)<=set(main_events.anomaly_type)
print({'training_events':len(train_events),'main_validation_events':len(main_events),
       'fault_families':sorted(main_events.loc[main_events.label_category.eq('sensor_fault'),'anomaly_type'].unique()),
       'weather_families':sorted(main_events.loc[main_events.label_category.eq('genuine_weather_scenario'),'anomaly_type'].unique())})
display(coverage)
"""),
    md(r"""## 5. Strict causal feature contract and pressure-datum protection

The corrected India parser recovers genuine station pressure where sea-level pressure is absent. Because station pressure and sea-level pressure have different elevation datums, Iteration 10 forbids absolute pressure and all instantaneous cross-station pressure fields. It retains station-local pressure deltas, rates, robust z, slopes, CUSUM and frozen-run evidence."""),
    code(r"""I10_EXCLUDED={
    'temperature_value','pressure_value','humidity_value','temperature_humidity_interaction',
    'pressure_temperature_ratio','nearest_neighbor_km','pressure_climatology_residual',
    'regional_agreement_mean','regional_agreement_min','regional_agreeing_sensor_count',
    'regional_standardized_disagreement_max','regional_trend_disagreement_mean',
}
for sensor in ('temperature','pressure','humidity'):
    I10_EXCLUDED.update({f'{sensor}_lag1',f'{sensor}_rolling_median_24h',f'{sensor}_ewma_prior',
                         f'neighbor_{sensor}_weighted_mean',f'neighbor_{sensor}_median'})
I10_EXCLUDED.update({feature for feature in PHASE10_FEATURES if feature.startswith('neighbor_pressure_')})
STRICT_FEATURES=[feature for feature in PHASE10_FEATURES if feature not in I10_EXCLUDED]
assert not any(feature.startswith('neighbor_pressure_') for feature in STRICT_FEATURES)
assert not ({'pressure_value','pressure_climatology_residual'}&set(STRICT_FEATURES))
assert {'pressure_delta1','pressure_rate_per_hour','pressure_robust_z_24h','pressure_slope_12h',
        'pressure_cusum_positive','pressure_frozen_run_length'}<=set(STRICT_FEATURES)
assert not ({'station_id','cluster','i10_domain','latitude','longitude','elevation_m','pressure_source'}&set(STRICT_FEATURES))

feature_contract={
    'version':'iteration10_strict_causal_v1','inputs':['temperature_c','pressure_hpa','relative_humidity_pct'],
    'phase10_features':len(PHASE10_FEATURES),'strict_features':len(STRICT_FEATURES),
    'excluded':sorted(I10_EXCLUDED),'pressure_policy':'no absolute or instantaneous cross-station pressure',
    'arrival_order_metadata_is_model_input':False,'station_or_domain_identifier_is_model_input':False,
}
(ITER10_ROOT/'iteration10_feature_contract.json').write_text(json.dumps(feature_contract,indent=2))
print(feature_contract)
"""),
    md(r"""## 6. Generate and cache causal features

Duplicate packets are physically replayed twice. Dropouts do not update detector state. Shifted packet timestamps cannot reorder arrival state because the feature engine receives an explicit routing-only stream order and causal arrival timestamp."""),
    code(r"""station_frames={'india':india_stations.copy(),'dwd':dwd_stations.copy()}

def station_contract(domain):
    frame=station_frames[domain]
    return {str(row['station_id']):{key:str(value) for key,value in row.items()}
            for row in frame.to_dict('records')}

def expected_intervals(frame):
    output={}
    source=frame.copy(); source['_t']=pd.to_datetime(source.timestamp_utc,utc=True)
    for station,group in source.sort_values('_t').groupby('station_id',sort=False):
        delta=group._t.diff().dt.total_seconds().div(60)
        plausible=delta[(delta>0)&(delta<=360)].round()
        output[str(station)]=float(plausible.mode().iloc[0]) if len(plausible) else 60.0
    return output

def expand_replay(frame):
    source=frame.sort_values(['station_id','timestamp_utc'],kind='stable').reset_index(drop=True)
    expanded=[]
    for row in source.to_dict('records'):
        first=dict(row); first['packet_copy_index']=0; expanded.append(first)
        if str(row.get('stream_action','emit'))=='duplicate':
            second=dict(row); second['packet_copy_index']=1; expanded.append(second)
    result=pd.DataFrame(expanded)
    result['stream_order']=result.groupby('station_id',sort=False).cumcount().astype(int)
    return result

def build_base_features(spec):
    frame=spec['frame'].copy()
    intervals=expected_intervals(frame)
    source=expand_replay(frame)
    rows=source.to_dict('records')
    config=FeatureConfig(max_neighbors=5,neighbor_tolerance_minutes=180.0)
    builder=FeatureBuilder(TemporalFeatureBuilder(intervals,config),
                           NeighborIndex(rows,station_contract(spec['domain']),config))
    output=[]
    for position,row in enumerate(rows,1):
        item=builder.transform(row)
        item['packet_copy_index']=int(row['packet_copy_index'])
        item['stream_order']=int(row['stream_order'])
        item['causal_arrival_timestamp_utc']=row['timestamp_utc']
        output.append(item)
        if position%50000==0: print(spec['key'],position,'/',len(rows))
    result=pd.DataFrame(output)
    duplicates=result.row_id.duplicated(keep=False)
    if duplicates.any():
        occurrence=result.groupby('row_id').cumcount()
        result.loc[duplicates,'row_id']=result.loc[duplicates,'row_id']+'-p'+occurrence.loc[duplicates].astype(str)
    result['i10_domain']=spec['domain']; result['i10_lane']=spec['lane']; result['i10_seed']=spec['seed']
    result['i10_scope']='train' if spec['year']==2022 else scope_from_time(result.causal_arrival_timestamp_utc)
    result['eval_station_id']=result.i10_domain+'|'+result.i10_lane+'|'+result.station_id.astype(str)
    for column in ('is_anomaly','is_weather_event','available_to_detector','timestamp_offset_seconds'):
        result[column]=pd.to_numeric(result[column],errors='coerce').fillna(0).astype(int)
    return result

PROFILE_PATH=ITER10_ROOT/'iteration10_climatology.joblib'

def materialize(specs,tag,profiles=None,fit_profiles=False):
    paths={spec['key']:ITER10_ROOT/f'{tag}_{spec["key"]}_features.csv.gz' for spec in specs}
    if REUSE_FEATURE_CACHE and all(path.exists() for path in paths.values()) and (not fit_profiles or PROFILE_PATH.exists()):
        tables=[pd.read_csv(paths[spec['key']],low_memory=False) for spec in specs]
        if fit_profiles: profiles=joblib.load(PROFILE_PATH)
        print('Reused',tag,'feature cache.')
        return pd.concat(tables,ignore_index=True,sort=False),profiles
    bases=[build_base_features(spec) for spec in specs]
    if fit_profiles:
        profiles=fit_climatology(pd.concat(bases,ignore_index=True,sort=False))
        joblib.dump(profiles,PROFILE_PATH,compress=3)
    assert profiles is not None
    tables=[]
    for spec,base in zip(specs,bases):
        table=add_phase10_features(base,profiles)
        table.to_csv(paths[spec['key']],index=False,compression={'method':'gzip','compresslevel':5})
        tables.append(table); del base; gc.collect()
    return pd.concat(tables,ignore_index=True,sort=False),profiles

train_features,climatology=materialize(train_specs,'train',fit_profiles=True)
main_features,_=materialize(main_specs,'main',profiles=climatology)
assert train_features.row_id.is_unique and main_features.row_id.is_unique
assert set(PHASE10_FEATURES)<=set(train_features.columns)
print({'train_features':train_features.shape,'main_features':main_features.shape,
       'profile_station_count':len(climatology['temperature_station'])})
"""),
    md(r"""## 7. Evaluator-only label bridges and verified-heartbeat contract

No dropped packet reaches a row detector. For learning/evaluation only, its episode label is bridged to the next emitted packet where a causal gap can first be detected. The bridge is never an inference feature. Automatic communication-gap alerts require a stable 2022 heartbeat; irregular archives remain advisory."""),
    code(r"""def bridge_detection_labels(frame):
    result=frame.copy()
    result['eval_label_category']=result.label_category.fillna('normal').astype(str)
    result['eval_anomaly_type']=result.anomaly_type.fillna('normal').astype(str)
    result['eval_anomaly_sensor']=result.anomaly_sensor.fillna('').astype(str)
    result['eval_episode_id']=result.episode_id.fillna('').astype(str)
    duplicate_first=result.eval_anomaly_type.eq('duplicate_packet')&result.packet_copy_index.eq(0)
    result.loc[duplicate_first,['eval_label_category','eval_anomaly_type','eval_anomaly_sensor','eval_episode_id']]=['normal','normal','','']
    ordered=result.sort_values(['eval_station_id','causal_arrival_timestamp_utc','stream_order'],kind='stable')
    for _series,index in ordered.groupby('eval_station_id',sort=False).groups.items():
        pending=None
        for position in index:
            row=result.loc[position]
            if str(row.stream_action)=='drop' and str(row.episode_id):
                pending=(str(row.episode_id),'dropout','communication')
            elif int(row.available_to_detector)==1 and pending is not None:
                result.loc[position,['eval_label_category','eval_anomaly_type','eval_anomaly_sensor','eval_episode_id']]=[
                    'sensor_fault',pending[1],pending[2],pending[0]]
                pending=None
    return result

train_features=bridge_detection_labels(train_features)
main_features=bridge_detection_labels(main_features)

def cadence_profiles(frame):
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
cadence_contract.to_csv(ITER10_ROOT/'iteration10_communication_contract.csv',index=False)
cadence_map={(row.i10_domain,str(row.station_id)):(bool(row.verified_heartbeat),float(row.automatic_gap_ratio_threshold))
             for row in cadence_contract.itertuples()}
print(cadence_contract.groupby('i10_domain').agg(stations=('station_id','size'),verified=('verified_heartbeat','sum'),
      median_regularity=('regularity','median')).reset_index())
"""),
    md(r"""## 8. Train domain-balanced causal row-evidence ensemble

This first stage is deliberately high-recall evidence, not the final alert. LightGBM seeds plus one GPU CatBoost model learn the three mutually exclusive classes. Absolute climate levels, location and pressure-datum shortcuts are unavailable."""),
    code(r"""TARGET_MAP={'normal':0,'genuine_weather_scenario':1,'sensor_fault':2}
CLASS_NAMES=np.array(['normal','genuine_weather','sensor_fault'])

def enforce_numeric(frame,features,label):
    missing=[name for name in features if name not in frame]
    if missing: raise ValueError(f'{label} missing features: {missing[:10]}')
    result=frame.copy()
    for name in features:
        result[name]=pd.to_numeric(result[name],errors='coerce').replace([np.inf,-np.inf],np.nan).astype(np.float32)
    bad=[name for name in features if not pd.api.types.is_numeric_dtype(result[name])]
    if bad: raise TypeError(f'{label} object features: {bad}')
    return result

def target_values(frame): return frame.eval_label_category.map(TARGET_MAP).fillna(0).astype(int).to_numpy()

def episode_domain_weights(frame,y):
    weights=np.zeros(len(frame),dtype=np.float64)
    work=frame.reset_index(drop=True)
    for (_domain,_lane),indices in work.groupby(['i10_domain','i10_lane'],sort=False).groups.items():
        idx=np.asarray(list(indices),dtype=int); local_y=y[idx]
        present=np.unique(local_y)
        for cls in present:
            cls_idx=idx[local_y==cls]
            if cls==0:
                weights[cls_idx]=1.0/max(len(cls_idx),1)
            else:
                episode=work.loc[cls_idx,'eval_episode_id'].replace('','unlabelled').astype(str)
                unique=episode.unique()
                for name in unique:
                    ep_idx=cls_idx[episode.to_numpy()==name]
                    weights[ep_idx]=1.0/max(len(unique)*len(ep_idx),1)
        weights[idx]/=max(len(present),1)
    weights/=max(weights.mean(),1e-12)
    return weights.astype(np.float32)

train_features=enforce_numeric(train_features,STRICT_FEATURES,'train')
main_features=enforce_numeric(main_features,STRICT_FEATURES,'main')
fit=train_features.loc[train_features.available_to_detector.eq(1)].reset_index(drop=True)
calibration=main_features.loc[main_features.i10_scope.eq('calibration')&main_features.available_to_detector.eq(1)&
    ~((main_features.i10_domain.eq('india')&main_features.station_id.isin(INDIA_HOLDOUTS))|
      (main_features.i10_domain.eq('dwd')&main_features.station_id.isin(DWD_HOLDOUTS)))].reset_index(drop=True)
y_fit=target_values(fit); y_cal=target_values(calibration); fit_weights=episode_domain_weights(fit,y_fit)
assert set(np.unique(y_fit))=={0,1,2} and set(np.unique(y_cal))=={0,1,2}

BASE_LGB_SEEDS=(1017,1041,1067)
base_lgb=[]; model_history=[]
for seed in BASE_LGB_SEEDS:
    model=LGBMClassifier(objective='multiclass',num_class=3,n_estimators=1400,learning_rate=.035,
        num_leaves=63,max_depth=-1,min_child_samples=80,subsample=.85,colsample_bytree=.8,
        reg_alpha=2.0,reg_lambda=20.0,random_state=seed,n_jobs=-1,verbosity=-1,force_col_wise=True)
    model.fit(fit[STRICT_FEATURES],y_fit,sample_weight=fit_weights,
              eval_set=[(calibration[STRICT_FEATURES],y_cal)],eval_metric='multi_logloss',
              callbacks=[early_stopping(120,verbose=False),log_evaluation(0)])
    joblib.dump(model,ITER10_ROOT/f'iteration10_base_lightgbm_seed{seed}.joblib',compress=3)
    base_lgb.append(model); model_history.append({'stage':'row_evidence','model':'lightgbm','seed':seed,
                                                   'best_iteration':int(model.best_iteration_ or model.n_estimators)})

base_cat=CatBoostClassifier(iterations=1400,depth=8,learning_rate=.045,loss_function='MultiClass',
    eval_metric='MultiClass',l2_leaf_reg=12.0,random_seed=1097,random_strength=.4,
    task_type='GPU' if torch.cuda.is_available() else 'CPU',devices='0',allow_writing_files=False,verbose=200)
base_cat.fit(fit[STRICT_FEATURES],y_fit,sample_weight=fit_weights,
             eval_set=(calibration[STRICT_FEATURES],y_cal),use_best_model=True)
base_cat.save_model(str(ITER10_ROOT/'iteration10_base_catboost.cbm'))
model_history.append({'stage':'row_evidence','model':'catboost','seed':1097,
                      'best_iteration':int(base_cat.get_best_iteration())})
pd.DataFrame(model_history).to_csv(ITER10_ROOT/'iteration10_model_training_history.csv',index=False)
print(pd.DataFrame(model_history))
"""),
    md(r"""## 9. Causal state features, independent weather gate and hard-fault path"""),
    code(r"""def add_row_scores(frame):
    result=enforce_numeric(frame,STRICT_FEATURES,'scoring')
    predictions=[model.predict_proba(result[STRICT_FEATURES]) for model in base_lgb]
    predictions.append(base_cat.predict_proba(result[STRICT_FEATURES]))
    probability=np.mean(np.stack(predictions),axis=0)
    probability=np.clip(probability,1e-7,1); probability/=probability.sum(axis=1,keepdims=True)
    for index,name in enumerate(CLASS_NAMES): result[f'row_p_{name}']=probability[:,index].astype(np.float32)
    return result

def add_hard_and_state_features(frame):
    result=frame.copy()
    temp=pd.to_numeric(result.temperature_value,errors='coerce')
    pressure=pd.to_numeric(result.pressure_value,errors='coerce')
    humidity=pd.to_numeric(result.humidity_value,errors='coerce')
    gap=pd.to_numeric(result.gap_ratio,errors='coerce')
    interval=[cadence_map.get((domain,str(station)),(False,np.inf))
              for domain,station in zip(result.i10_domain,result.station_id)]
    verified=np.asarray([item[0] for item in interval],dtype=bool)
    gap_threshold=np.asarray([item[1] for item in interval],dtype=float)
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
    temp_agree=pd.to_numeric(result.neighbor_temperature_agreement_fraction,errors='coerce')
    humidity_agree=pd.to_numeric(result.neighbor_humidity_agreement_fraction,errors='coerce')
    result['safe_weather_agreement']=pd.concat([temp_agree,humidity_agree],axis=1).mean(axis=1,skipna=True).fillna(0).astype(np.float32)
    result['safe_weather_sensor_count']=(temp_agree.ge(.55).astype(int)+humidity_agree.ge(.55).astype(int)).astype(np.int8)
    result['regional_extent']=pd.to_numeric(result.neighbor_station_count,errors='coerce').fillna(0).div(5).clip(0,1).astype(np.float32)
    result['independent_weather_gate']=(pd.to_numeric(result.neighbor_station_count,errors='coerce').ge(2)&
        result.safe_weather_agreement.ge(.50)&result.safe_weather_sensor_count.ge(1)).astype(np.int8)
    slope_terms=[]
    for sensor,floor in (('temperature',.15),('pressure',.12),('humidity',.6)):
        for hours in (6,12,24):
            slope_terms.append(pd.to_numeric(result[f'{sensor}_slope_{hours}h'],errors='coerce').abs().div(floor))
    cusum_terms=[pd.to_numeric(result[f'{sensor}_cusum_{direction}'],errors='coerce').div(8)
                 for sensor in ('temperature','pressure','humidity') for direction in ('positive','negative')]
    result['drift_evidence_score']=pd.concat(slope_terms+cusum_terms,axis=1).max(axis=1,skipna=True).fillna(0).clip(0,12).astype(np.float32)
    result=result.sort_values(['eval_station_id','causal_arrival_timestamp_utc','stream_order'],kind='stable').reset_index(drop=True)
    grouping=result.groupby('eval_station_id',sort=False)
    for source in ('row_p_sensor_fault','row_p_genuine_weather','drift_evidence_score','safe_weather_agreement'):
        result[f'{source}_mean5']=(grouping[source].rolling(5,min_periods=1).mean().reset_index(level=0,drop=True).astype(np.float32))
        result[f'{source}_max5']=(grouping[source].rolling(5,min_periods=1).max().reset_index(level=0,drop=True).astype(np.float32))
    candidate=(result.row_p_sensor_fault.ge(.12)|result.row_p_genuine_weather.ge(.15)|result.hard_fault.eq(1)).to_numpy()
    runs=np.zeros(len(result),dtype=np.float32)
    for _series,indices in result.groupby('eval_station_id',sort=False).groups.items():
        count=0
        for index in indices:
            count=count+1 if candidate[index] else 0; runs[index]=count
    result['candidate_run_length']=runs
    return result

train_state=add_hard_and_state_features(add_row_scores(train_features))
main_state=add_hard_and_state_features(add_row_scores(main_features))
STATE_FEATURES=[
    'row_p_normal','row_p_genuine_weather','row_p_sensor_fault',
    'row_p_sensor_fault_mean5','row_p_sensor_fault_max5','row_p_genuine_weather_mean5','row_p_genuine_weather_max5',
    'drift_evidence_score','drift_evidence_score_mean5','drift_evidence_score_max5',
    'safe_weather_agreement','safe_weather_agreement_mean5','safe_weather_agreement_max5','safe_weather_sensor_count',
    'regional_extent','independent_weather_gate','hard_fault','verified_heartbeat','candidate_run_length',
    'primary_missing_count','time_since_previous_minutes','gap_ratio','out_of_order_indicator',
    'temperature_frozen_run_length','pressure_frozen_run_length','humidity_frozen_run_length',
]
train_state=enforce_numeric(train_state,STATE_FEATURES,'train state')
main_state=enforce_numeric(main_state,STATE_FEATURES,'main state')
print({'strict_features':len(STRICT_FEATURES),'state_features':len(STATE_FEATURES)})
"""),
    md(r"""## 10. Train and calibrate the incident-state classifier

The model sees causal rolling evidence, never future incident summaries. A separate L2 multinomial calibrator is fitted only on January–February; thresholds remain untouched until March–April policy selection."""),
    code(r"""state_fit=train_state.loc[train_state.available_to_detector.eq(1)].reset_index(drop=True)
state_cal=main_state.loc[main_state.i10_scope.eq('calibration')&main_state.available_to_detector.eq(1)&
    ~((main_state.i10_domain.eq('india')&main_state.station_id.isin(INDIA_HOLDOUTS))|
      (main_state.i10_domain.eq('dwd')&main_state.station_id.isin(DWD_HOLDOUTS)))].reset_index(drop=True)
ys_fit=target_values(state_fit); ys_cal=target_values(state_cal); state_weights=episode_domain_weights(state_fit,ys_fit)
STATE_SEEDS=(2017,2041,2067); state_models=[]
for seed in STATE_SEEDS:
    model=LGBMClassifier(objective='multiclass',num_class=3,n_estimators=1000,learning_rate=.03,
        num_leaves=31,min_child_samples=100,subsample=.9,colsample_bytree=.9,reg_alpha=3.0,reg_lambda=25.0,
        random_state=seed,n_jobs=-1,verbosity=-1,force_col_wise=True)
    model.fit(state_fit[STATE_FEATURES],ys_fit,sample_weight=state_weights,
              eval_set=[(state_cal[STATE_FEATURES],ys_cal)],eval_metric='multi_logloss',
              callbacks=[early_stopping(100,verbose=False),log_evaluation(0)])
    joblib.dump(model,ITER10_ROOT/f'iteration10_state_lightgbm_seed{seed}.joblib',compress=3)
    state_models.append(model); model_history.append({'stage':'incident_state','model':'lightgbm','seed':seed,
                                                       'best_iteration':int(model.best_iteration_ or model.n_estimators)})

def raw_state_probability(frame):
    values=np.mean(np.stack([model.predict_proba(frame[STATE_FEATURES]) for model in state_models]),axis=0)
    values=np.clip(values,1e-7,1); return values/values.sum(axis=1,keepdims=True)

cal_raw=raw_state_probability(state_cal)
calibrator=LogisticRegression(C=.5,penalty='l2',class_weight='balanced',max_iter=2000,random_state=26073)
calibrator.fit(np.log(np.clip(cal_raw,1e-7,1)),ys_cal)
joblib.dump(calibrator,ITER10_ROOT/'iteration10_l2_incident_calibrator.joblib',compress=3)

def add_state_probability(frame):
    result=frame.copy(); raw=raw_state_probability(result)
    calibrated=calibrator.predict_proba(np.log(np.clip(raw,1e-7,1)))
    for index,name in enumerate(CLASS_NAMES):
        result[f'state_raw_p_{name}']=raw[:,index].astype(np.float32)
        result[f'state_p_{name}']=calibrated[:,index].astype(np.float32)
    return result

train_state=add_state_probability(train_state); main_state=add_state_probability(main_state)
pd.DataFrame(model_history).to_csv(ITER10_ROOT/'iteration10_model_training_history.csv',index=False)
print(pd.DataFrame(model_history))
"""),
    md(r"""## 11. Hierarchical root-cause model with deterministic communication priority"""),
    code(r"""ROOT_FEATURES=list(dict.fromkeys(STRICT_FEATURES+STATE_FEATURES))
assert len(ROOT_FEATURES)==len(set(ROOT_FEATURES))
root_fit=train_state.loc[train_state.available_to_detector.eq(1)&train_state.eval_label_category.eq('sensor_fault')].copy()
root_cal=main_state.loc[main_state.i10_scope.eq('calibration')&main_state.available_to_detector.eq(1)&
    main_state.eval_label_category.eq('sensor_fault')&
    ~((main_state.i10_domain.eq('india')&main_state.station_id.isin(INDIA_HOLDOUTS))|
      (main_state.i10_domain.eq('dwd')&main_state.station_id.isin(DWD_HOLDOUTS)))].copy()
root_classes=sorted(root_fit.eval_anomaly_type.unique().tolist()); root_index={name:i for i,name in enumerate(root_classes)}
yr_fit=root_fit.eval_anomaly_type.map(root_index).astype(int).to_numpy(); yr_cal=root_cal.eval_anomaly_type.map(root_index).astype(int).to_numpy()
class_counts=root_fit.eval_anomaly_type.value_counts()
class_weights=(len(root_fit)/(len(class_counts)*root_fit.eval_anomaly_type.map(class_counts))).clip(.2,5.0).to_numpy()
root_weights=episode_domain_weights(root_fit,root_fit.eval_label_category.map({'sensor_fault':2}).fillna(0).to_numpy())*class_weights
ROOT_FAMILY={
    **{name:'communication_data_order' for name in ('dropout','duplicate_packet','timestamp_error','communication_corruption')},
    **{name:'abrupt_sensor_fault' for name in ('spike','sudden_drop','unit_error','scaling_error')},
    **{name:'persistent_degradation' for name in ('bias','drift','noise','frozen_sensor')},
    'multi_sensor_failure':'multi_sensor_station_fault',
}
root_families=sorted(set(ROOT_FAMILY.values())); root_family_index={name:i for i,name in enumerate(root_families)}
yf_fit=root_fit.eval_anomaly_type.map(ROOT_FAMILY).map(root_family_index).astype(int).to_numpy()
yf_cal=root_cal.eval_anomaly_type.map(ROOT_FAMILY).map(root_family_index).astype(int).to_numpy()
root_family_model=CatBoostClassifier(iterations=900,depth=7,learning_rate=.045,loss_function='MultiClass',
    eval_metric='MultiClass',l2_leaf_reg=12.0,random_seed=3071,random_strength=.4,
    task_type='GPU' if torch.cuda.is_available() else 'CPU',devices='0',allow_writing_files=False,verbose=200)
root_family_model.fit(root_fit[ROOT_FEATURES],yf_fit,sample_weight=root_weights,
                      eval_set=(root_cal[ROOT_FEATURES],yf_cal),use_best_model=True)
root_family_model.save_model(str(ITER10_ROOT/'iteration10_root_family_catboost.cbm'))
root_model=CatBoostClassifier(iterations=1300,depth=9,learning_rate=.04,loss_function='MultiClass',
    eval_metric='MultiClass',l2_leaf_reg=14.0,random_seed=3097,random_strength=.5,
    task_type='GPU' if torch.cuda.is_available() else 'CPU',devices='0',allow_writing_files=False,verbose=200)
root_model.fit(root_fit[ROOT_FEATURES],yr_fit,sample_weight=root_weights,
               eval_set=(root_cal[ROOT_FEATURES],yr_cal),use_best_model=True)
root_model.save_model(str(ITER10_ROOT/'iteration10_incident_root_cause_catboost.cbm'))
(ITER10_ROOT/'iteration10_root_classes.json').write_text(json.dumps(root_classes,indent=2))

DETERMINISTIC_ROOT={'DUPLICATE_PACKET':'duplicate_packet','TIMESTAMP_ERROR':'timestamp_error',
                    'COMMUNICATION_GAP':'dropout','MULTI_SENSOR_FREEZE':'multi_sensor_failure'}
def add_root_scores(frame):
    result=frame.copy(); probability=root_model.predict_proba(result[ROOT_FEATURES])
    family_probability=root_family_model.predict_proba(result[ROOT_FEATURES])
    family_index=np.argmax(family_probability,axis=1)
    predicted_families=[root_families[item] for item in family_index]
    labels=[]; confidence=[]
    for row_index,family in enumerate(predicted_families):
        allowed=[position for position,name in enumerate(root_classes) if ROOT_FAMILY[name]==family]
        restricted=probability[row_index,allowed]; normalized=restricted/max(restricted.sum(),1e-9)
        best_local=int(np.argmax(normalized)); labels.append(root_classes[allowed[best_local]])
        confidence.append(float(family_probability[row_index,family_index[row_index]]*normalized[best_local]))
    result['root_family_row']=predicted_families
    result['root_cause_row']=labels
    result['root_confidence_row']=np.asarray(confidence,dtype=np.float32)
    for code,label in DETERMINISTIC_ROOT.items():
        mask=result.hard_fault_code.eq(code); result.loc[mask,'root_cause_row']=label
        result.loc[mask,'root_family_row']=ROOT_FAMILY[label]; result.loc[mask,'root_confidence_row']=1.0
    result.loc[result.root_confidence_row.lt(.45),'root_cause_row']='uncertain_fault'
    return result

main_state=add_root_scores(main_state)
print({'root_families':root_families,'root_classes':root_classes,'fit_rows':len(root_fit),'calibration_rows':len(root_cal)})
"""),
    md(r"""## 12. Stateful policy, one-to-one incident matching and policy-only search"""),
    code(r"""STATION_CLUSTER={(str(row.i10_domain),str(row.station_id)):str(row.cluster)
                 for row in pd.concat([india,dwd],ignore_index=True).drop_duplicates(['i10_domain','station_id']).itertuples()}

def apply_policy(frame,policy):
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
            now=pd.Timestamp(row.causal_arrival_timestamp_utc)
            hard=bool(row.hard_fault)
            weather_vote=(wp>=policy['weather_threshold'] and bool(row.independent_weather_gate) and wp>fp)
            drift_rescue=(float(row.drift_evidence_score)>=float(policy.get('drift_rescue_threshold',5.0)) and
                          fp>=float(policy.get('drift_min_fault_probability',.20)) and not weather_vote)
            fault_vote=(fp>=policy['fault_threshold'] and not weather_vote) or drift_rescue or hard
            window=pd.Timedelta(minutes=float(policy.get('window_minutes',720)))
            while fault_votes and now-fault_votes[0][0]>window: fault_votes.popleft()
            while weather_votes and now-weather_votes[0][0]>window: weather_votes.popleft()
            fault_votes.append((now,int(fault_vote))); weather_votes.append((now,int(weather_vote)))
            desired='normal'
            if hard or sum(value for _time,value in fault_votes)>=policy['k']: desired='sensor_fault'
            elif sum(value for _time,value in weather_votes)>=policy['k']: desired='genuine_weather'
            if active=='normal' and desired!='normal':
                active=desired; active_alert=str(row.causal_arrival_timestamp_utc); recovery=0
            elif active!='normal':
                if desired==active: recovery=0
                elif desired!='normal' and desired!=active: active=desired; active_alert=str(row.causal_arrival_timestamp_utc); recovery=0
                else:
                    recovery+=1
                    if recovery>=int(policy.get('recovery_points',2)): active='normal'; active_alert=''; recovery=0
            decisions[index]=active
            confidence[index]=1.0 if hard else (fp if active=='sensor_fault' else (wp if active=='genuine_weather' else float(row.state_p_normal)))
            first_alert[index]=active_alert
    source['decision_state']=decisions; source['decision_confidence']=confidence; source['first_alert_utc']=first_alert
    source['decision_run_id']=source.groupby('eval_station_id',sort=False).decision_state.transform(
        lambda values: values.ne(values.shift()).cumsum()).astype(int)
    return source

def predicted_incidents(decisions):
    rows=[]
    active=decisions.loc[decisions.decision_state.ne('normal')].copy()
    for (station,state,_state_run),group in active.groupby(
            ['eval_station_id','decision_state','decision_run_id'],sort=False):
        group=group.sort_values(['causal_arrival_timestamp_utc','stream_order'],kind='stable')
        arrival=pd.to_datetime(group.causal_arrival_timestamp_utc,utc=True)
        breaks=arrival.diff().gt(pd.Timedelta(hours=6)).fillna(True).cumsum()
        for _run,part in group.groupby(breaks,sort=False):
            fault_part=part.loc[part.decision_state.eq('sensor_fault')].copy()
            fault_part['_root_weight']=fault_part.decision_confidence*fault_part.root_confidence_row
            roots=fault_part.groupby('root_cause_row')._root_weight.sum()
            root=str(roots.idxmax()) if len(roots) else 'not_a_fault'
            rows.append({'station_id':station,'start_utc':str(part.causal_arrival_timestamp_utc.iloc[0]),
                         'end_utc':str(part.causal_arrival_timestamp_utc.iloc[-1]),
                         'first_alert_utc':str(part.first_alert_utc.replace('',np.nan).dropna().iloc[0]),
                         'decision_state':state,'confidence':float(part.decision_confidence.max()),
                         'root_cause':root,'scope':str(part.i10_scope.mode().iloc[0]),
                         'i10_domain':str(part.i10_domain.iloc[0]),'i10_lane':str(part.i10_lane.iloc[0])})
    columns=['station_id','start_utc','end_utc','first_alert_utc','decision_state','confidence',
             'root_cause','scope','i10_domain','i10_lane']
    return pd.DataFrame(rows,columns=columns)

def truth_incidents(events,scope,category):
    selected=events.loc[events.scope.eq(scope)&events.label_category.eq(category)].copy(); rows=[]
    for event in selected.itertuples():
        for station in str(event.stations).split(','):
            event_cluster=str(getattr(event,'cluster',''))
            if not event_cluster or event_cluster=='nan':
                event_cluster=STATION_CLUSTER.get((str(event.i10_domain),str(station)),'unknown')
            rows.append({'station_id':f'{event.i10_domain}|{event.i10_lane}|{station}',
                         'start_utc':event.start_utc,'end_utc':event.end_utc,'root_cause':event.anomaly_type,
                         'episode_id':event.episode_id,'cluster':event_cluster,
                         'i10_domain':event.i10_domain,'i10_lane':event.i10_lane})
    columns=['station_id','start_utc','end_utc','root_cause','episode_id','cluster','i10_domain','i10_lane']
    return pd.DataFrame(rows,columns=columns)

def evaluation(frame,events,scope,policy,return_frames=False):
    block=frame.loc[frame.i10_scope.eq(scope)&frame.available_to_detector.eq(1)].copy()
    decisions=apply_policy(block,policy); predicted=predicted_incidents(decisions)
    pred_fault=predicted.loc[predicted.decision_state.eq('sensor_fault')].reset_index(drop=True) if len(predicted) else predicted
    pred_weather=predicted.loc[predicted.decision_state.eq('genuine_weather')].reset_index(drop=True) if len(predicted) else predicted
    truth_fault=truth_incidents(events,scope,'sensor_fault')
    truth_weather=truth_incidents(events,scope,'genuine_weather_scenario')
    allowed=set(block.eval_station_id.astype(str).unique())
    truth_fault=truth_fault.loc[truth_fault.station_id.astype(str).isin(allowed)].reset_index(drop=True)
    truth_weather=truth_weather.loc[truth_weather.station_id.astype(str).isin(allowed)].reset_index(drop=True)
    station_days=int(block.assign(_date=pd.to_datetime(block.causal_arrival_timestamp_utc,utc=True).dt.date)
                     .drop_duplicates(['eval_station_id','_date']).shape[0])
    fault=incident_metrics(truth_fault,pred_fault,station_days,tolerance_minutes=180)
    weather=incident_metrics(truth_weather,pred_weather,station_days,tolerance_minutes=180)
    fault_to_weather=len(match_incidents(truth_fault,pred_weather,tolerance_minutes=180))/max(len(truth_fault),1)
    weather_to_fault=len(match_incidents(truth_weather,pred_fault,tolerance_minutes=180))/max(len(truth_weather),1)
    result={'scope':scope,'fault':fault,'weather':weather,'fault_to_weather_rate':float(fault_to_weather),
            'weather_to_fault_rate':float(weather_to_fault),'station_days':station_days}
    if return_frames: return result,decisions,predicted,truth_fault,truth_weather
    return result

policy_holdout=((main_state.i10_domain.eq('india')&main_state.station_id.isin(INDIA_HOLDOUTS))|
                (main_state.i10_domain.eq('dwd')&main_state.station_id.isin(DWD_HOLDOUTS)))
policy_selection_state=main_state.loc[~policy_holdout].copy()
assert not ((policy_selection_state.i10_domain.eq('india')&policy_selection_state.station_id.isin(INDIA_HOLDOUTS))|
            (policy_selection_state.i10_domain.eq('dwd')&policy_selection_state.station_id.isin(DWD_HOLDOUTS))).any()
frontier=[]
for k,n in ((2,3),(3,5),(4,6),(5,8)):
    for fault_threshold in np.arange(.50,.86,.05):
        for weather_threshold in np.arange(.30,.86,.10):
            policy={'fault_threshold':float(fault_threshold),'weather_threshold':float(weather_threshold),
                    'k':k,'n':n,'window_minutes':720,'drift_rescue_threshold':5.0,
                    'drift_min_fault_probability':.20,'recovery_points':2}
            measured=evaluation(policy_selection_state,main_events,'policy',policy)
            fault=measured['fault']; weather=measured['weather']
            objective=(2.0*fault['precision']+fault['f1']+weather['f1']
                       -10.0*fault['false_alerts_per_station_day']
                       -2.0*measured['fault_to_weather_rate']
                       -1.0*measured['weather_to_fault_rate'])
            frontier.append({**policy,'fault_precision':fault['precision'],'fault_recall':fault['recall'],'fault_f1':fault['f1'],
                'false_alerts_per_station_day':fault['false_alerts_per_station_day'],'weather_f1':weather['f1'],
                'weather_precision':weather['precision'],'weather_recall':weather['recall'],
                'fault_to_weather_rate':measured['fault_to_weather_rate'],
                'weather_to_fault_rate':measured['weather_to_fault_rate'],'objective':objective,
                'policy_eligible':fault['precision']>=.70 and fault['false_alerts_per_station_day']<=.03})
policy_frontier=pd.DataFrame(frontier).sort_values('objective',ascending=False)
eligible=policy_frontier.loc[policy_frontier.policy_eligible]
if len(eligible):
    selected=eligible.iloc[0]
else:
    safe_candidates=policy_frontier.loc[policy_frontier.fault_threshold>=.65]
    if len(safe_candidates):
        selected=safe_candidates.sort_values(['fault_precision','false_alerts_per_station_day'],ascending=[False,True]).iloc[0]
    else:
        selected=policy_frontier.sort_values(['fault_precision','false_alerts_per_station_day'],ascending=[False,True]).iloc[0]
FROZEN_POLICY={key:(int(selected[key]) if key in {'k','n','recovery_points'} else float(selected[key]))
               for key in ('fault_threshold','weather_threshold','k','n','window_minutes',
                            'drift_rescue_threshold','drift_min_fault_probability','recovery_points')}
policy_frontier.to_csv(ITER10_ROOT/'iteration10_policy_frontier.csv',index=False)
(ITER10_ROOT/'iteration10_frozen_policy.json').write_text(json.dumps(FROZEN_POLICY,indent=2))
print({'frozen_policy':FROZEN_POLICY,'eligible_policy_found':bool(len(eligible))})
display(policy_frontier.head(15))
"""),
    md(r"""## 13. Discovery audit and untouched confirmation evaluation"""),
    code(r"""discovery_result=evaluation(main_state,main_events,'discovery',FROZEN_POLICY)
confirmation_result,confirmation_decisions,confirmation_predictions,truth_fault_confirm,truth_weather_confirm=(
    evaluation(main_state,main_events,'confirmation',FROZEN_POLICY,return_frames=True))

def family_recall(truth,predicted):
    predicted_fault=predicted.loc[predicted.decision_state.eq('sensor_fault')].reset_index(drop=True) if len(predicted) else predicted
    matches=match_incidents(truth,predicted_fault,tolerance_minutes=180)
    matched={item.truth_index for item in matches}; rows=[]
    for family,indices in truth.groupby('root_cause').groups.items():
        index_set=set(indices); hit=len(index_set&matched)
        rows.append({'fault_family':family,'true_incidents':len(index_set),'detected_incidents':hit,'episode_recall':hit/max(len(index_set),1)})
    return pd.DataFrame(rows).sort_values('episode_recall')

fault_episode_recall=family_recall(truth_fault_confirm,confirmation_predictions)
fault_episode_recall.to_csv(ITER10_ROOT/'iteration10_fault_episode_recall.csv',index=False)

available=confirmation_decisions.available_to_detector.eq(1)
y_true=target_values(confirmation_decisions.loc[available])
y_pred=np.select([confirmation_decisions.loc[available].decision_state.eq('genuine_weather'),
                  confirmation_decisions.loc[available].decision_state.eq('sensor_fault')],[1,2],default=0)
point_metrics={'accuracy':float(accuracy_score(y_true,y_pred)),'balanced_accuracy':float(balanced_accuracy_score(y_true,y_pred)),
               'macro_f1':float(f1_score(y_true,y_pred,average='macro',zero_division=0)),
               'fault_f1':float(f1_score(y_true==2,y_pred==2,zero_division=0)),
               'weather_f1':float(f1_score(y_true==1,y_pred==1,zero_division=0)),
               'fault_auprc':float(average_precision_score((y_true==2).astype(int),
                   confirmation_decisions.loc[available,'state_p_sensor_fault'])),
               'weather_auprc':float(average_precision_score((y_true==1).astype(int),
                   confirmation_decisions.loc[available,'state_p_genuine_weather']))}
point_confusion=confusion_matrix(y_true,y_pred,labels=[0,1,2])
point_metrics['confusion_matrix_normal_weather_fault']=point_confusion.astype(int).tolist()
for index,name in enumerate(CLASS_NAMES):
    point_metrics[f'{name}_tp']=int(point_confusion[index,index])
    point_metrics[f'{name}_fn']=int(point_confusion[index,:].sum()-point_confusion[index,index])
    point_metrics[f'{name}_fp']=int(point_confusion[:,index].sum()-point_confusion[index,index])
    point_metrics[f'{name}_tn']=int(point_confusion.sum()-point_confusion[index,:].sum()-
                                    point_confusion[:,index].sum()+point_confusion[index,index])

calibration_report={}
for name,index in (('fault',2),('weather',1)):
    calibration_report[name]=calibration_metrics((y_true==index).astype(int),
        confirmation_decisions.loc[available,f'state_p_{CLASS_NAMES[index]}'].to_numpy(),bins=10)
(ITER10_ROOT/'iteration10_calibration_metrics.json').write_text(json.dumps(calibration_report,indent=2))

root_matches=match_incidents(truth_fault_confirm,
    confirmation_predictions.loc[confirmation_predictions.decision_state.eq('sensor_fault')].reset_index(drop=True),180)
pred_fault=confirmation_predictions.loc[confirmation_predictions.decision_state.eq('sensor_fault')].reset_index(drop=True)
if root_matches:
    root_true=[str(truth_fault_confirm.iloc[item.truth_index].root_cause) for item in root_matches]
    root_pred=[str(pred_fault.iloc[item.prediction_index].root_cause) for item in root_matches]
    root_family_true=[ROOT_FAMILY.get(value,'unknown_fault') for value in root_true]
    root_family_pred=[ROOT_FAMILY.get(value,'unknown_fault') for value in root_pred]
    accepted=np.asarray([value!='uncertain_fault' for value in root_pred],dtype=bool)
    root_metrics={'matched_incidents':len(root_matches),'accuracy':float(accuracy_score(root_true,root_pred)),
                  'macro_f1':float(f1_score(root_true,root_pred,average='macro',zero_division=0)),
                  'broad_family_accuracy':float(accuracy_score(root_family_true,root_family_pred)),
                  'broad_family_macro_f1':float(f1_score(root_family_true,root_family_pred,average='macro',zero_division=0)),
                  'accepted_coverage':float(accepted.mean()),
                  'accepted_accuracy':float(accuracy_score(np.asarray(root_true)[accepted],np.asarray(root_pred)[accepted])) if accepted.any() else 0.0}
    root_per_class=(pd.DataFrame(classification_report(root_true,root_pred,output_dict=True,zero_division=0)).T
                    .reset_index().rename(columns={'index':'root_cause'}))
else: root_metrics={'matched_incidents':0,'accuracy':0.0,'macro_f1':0.0,
                    'broad_family_accuracy':0.0,'broad_family_macro_f1':0.0,
                    'accepted_coverage':0.0,'accepted_accuracy':0.0}
if not root_matches: root_per_class=pd.DataFrame(columns=['root_cause','precision','recall','f1-score','support'])
pd.DataFrame([root_metrics]).to_csv(ITER10_ROOT/'iteration10_root_cause_metrics.csv',index=False)
root_per_class.to_csv(ITER10_ROOT/'iteration10_root_cause_per_class.csv',index=False)

pred_weather_confirm=confirmation_predictions.loc[
    confirmation_predictions.decision_state.eq('genuine_weather')].reset_index(drop=True)
weather_cluster_rows=[]
for cluster,truth_group in truth_weather_confirm.groupby('cluster',sort=True):
    station_set=set(truth_group.station_id.astype(str))
    prediction_group=pred_weather_confirm.loc[pred_weather_confirm.station_id.astype(str).isin(station_set)].reset_index(drop=True)
    metrics=incident_metrics(truth_group.reset_index(drop=True),prediction_group,
                             max(1,confirmation_result['station_days']),tolerance_minutes=180)
    weather_cluster_rows.append({'cluster':cluster,**metrics})
weather_by_cluster=pd.DataFrame(weather_cluster_rows)
weather_by_cluster.to_csv(ITER10_ROOT/'iteration10_weather_by_cluster.csv',index=False)

latency=pd.DataFrame([
    {'class':'sensor_fault','median_minutes':confirmation_result['fault']['median_latency_minutes'],
     'mean_minutes':confirmation_result['fault']['mean_latency_minutes'],
     'p90_minutes':confirmation_result['fault']['p90_latency_minutes']},
    {'class':'genuine_weather','median_minutes':confirmation_result['weather']['median_latency_minutes'],
     'mean_minutes':confirmation_result['weather']['mean_latency_minutes'],
     'p90_minutes':confirmation_result['weather']['p90_latency_minutes']},
])
latency.to_csv(ITER10_ROOT/'iteration10_detection_latency.csv',index=False)

season_name=np.select([
    pd.to_datetime(confirmation_decisions.causal_arrival_timestamp_utc,utc=True).dt.month.isin([12,1,2]),
    pd.to_datetime(confirmation_decisions.causal_arrival_timestamp_utc,utc=True).dt.month.isin([3,4,5]),
    pd.to_datetime(confirmation_decisions.causal_arrival_timestamp_utc,utc=True).dt.month.isin([6,7,8,9]),
],['winter','pre_monsoon','monsoon'],default='post_monsoon')
confirmation_decisions['season']=season_name
season_rows=[]
for season,block in confirmation_decisions.loc[confirmation_decisions.available_to_detector.eq(1)].groupby('season'):
    actual=target_values(block); predicted=np.select([block.decision_state.eq('genuine_weather'),
        block.decision_state.eq('sensor_fault')],[1,2],default=0)
    season_rows.append({'season':season,'rows':len(block),'macro_f1':float(f1_score(actual,predicted,average='macro',zero_division=0)),
        'fault_f1':float(f1_score(actual==2,predicted==2,zero_division=0)),
        'weather_f1':float(f1_score(actual==1,predicted==1,zero_division=0))})
pd.DataFrame(season_rows).to_csv(ITER10_ROOT/'iteration10_season_metrics.csv',index=False)

group_rows=[]
for label,mask in {
    'all':np.ones(len(confirmation_decisions),dtype=bool),
    'india':confirmation_decisions.i10_domain.eq('india'),
    'dwd':confirmation_decisions.i10_domain.eq('dwd'),
    'india_station_holdout':confirmation_decisions.i10_domain.eq('india')&confirmation_decisions.station_id.isin(INDIA_HOLDOUTS),
    'dwd_station_holdout':confirmation_decisions.i10_domain.eq('dwd')&confirmation_decisions.station_id.isin(DWD_HOLDOUTS),
}.items():
    block=confirmation_decisions.loc[mask]
    measured=evaluation(main_state.loc[main_state.eval_station_id.isin(block.eval_station_id.unique())],main_events,'confirmation',FROZEN_POLICY)
    point_block=block.loc[block.available_to_detector.eq(1)]
    point_actual=target_values(point_block); point_predicted=np.select([
        point_block.decision_state.eq('genuine_weather'),point_block.decision_state.eq('sensor_fault')],[1,2],default=0)
    group_rows.append({'group':label,'fault_precision':measured['fault']['precision'],'fault_recall':measured['fault']['recall'],
        'fault_f1':measured['fault']['f1'],'false_alerts_per_station_day':measured['fault']['false_alerts_per_station_day'],
        'point_fault_f1':float(f1_score(point_actual==2,point_predicted==2,zero_division=0)),
        'weather_f1':measured['weather']['f1'],'fault_to_weather_rate':measured['fault_to_weather_rate'],
        'weather_to_fault_rate':measured['weather_to_fault_rate']})
multidomain_confirmation=pd.DataFrame(group_rows)
multidomain_confirmation.to_csv(ITER10_ROOT/'iteration10_multidomain_confirmation.csv',index=False)
print({'point_metrics':point_metrics,'incident_confirmation':confirmation_result,'root_metrics':root_metrics})
display(multidomain_confirmation); display(fault_episode_recall)
"""),
    md(r"""## 14. Fresh-seed confirmation stress test with the frozen models and policy

No model, calibrator, threshold or persistence setting is refitted. Only new injected episodes are generated."""),
    code(r"""def score_frozen_feature_table(features):
    table=bridge_detection_labels(features)
    table=enforce_numeric(table,STRICT_FEATURES,'stress')
    table=add_hard_and_state_features(add_row_scores(table))
    table=enforce_numeric(table,STATE_FEATURES,'stress state')
    table=add_state_probability(table)
    return add_root_scores(table)

stress_rows=[{'seed':MAIN_SEED,**{
    'fault_precision':confirmation_result['fault']['precision'],'fault_recall':confirmation_result['fault']['recall'],
    'fault_f1':confirmation_result['fault']['f1'],'false_alerts_per_station_day':confirmation_result['fault']['false_alerts_per_station_day'],
    'weather_f1':confirmation_result['weather']['f1'],'fault_to_weather_rate':confirmation_result['fault_to_weather_rate'],
    'weather_to_fault_rate':confirmation_result['weather_to_fault_rate']}}]
if RUN_STRESS_SEEDS:
    confirm_scope={'confirmation':SCOPE_RANGES['confirmation']}
    for seed in STRESS_SEEDS:
        specs,events,_audits=make_curricula(seed,2023,confirm_scope)
        features,_=materialize(specs,f'stress_s{seed}',profiles=climatology)
        scored=score_frozen_feature_table(features)
        measured=evaluation(scored,events,'confirmation',FROZEN_POLICY)
        stress_rows.append({'seed':seed,'fault_precision':measured['fault']['precision'],
            'fault_recall':measured['fault']['recall'],'fault_f1':measured['fault']['f1'],
            'false_alerts_per_station_day':measured['fault']['false_alerts_per_station_day'],
            'weather_f1':measured['weather']['f1'],'fault_to_weather_rate':measured['fault_to_weather_rate'],
            'weather_to_fault_rate':measured['weather_to_fault_rate']})
        del features,scored; gc.collect()
stress=pd.DataFrame(stress_rows)
stress.to_csv(ITER10_ROOT/'iteration10_multiseed_stress.csv',index=False)
print(stress)
"""),
    md(r"""## 15. Advisory correction, station health, explainability and speed evidence"""),
    code(r"""SENSOR_FIELDS={'temperature':('temperature_value','temperature_rolling_median_24h','neighbor_temperature_median','original_temperature_c','temperature_rolling_mad_24h'),
               'pressure':('pressure_value','pressure_rolling_median_24h',None,'original_pressure_hpa','pressure_rolling_mad_24h'),
               'humidity':('humidity_value','humidity_rolling_median_24h','neighbor_humidity_median','original_relative_humidity_pct','humidity_rolling_mad_24h')}
correction_rows=[]
matched_rows=confirmation_decisions.loc[confirmation_decisions.decision_state.eq('sensor_fault')&
    confirmation_decisions.eval_label_category.eq('sensor_fault')].copy()
eligible_pairs=defaultdict(int)
for value in confirmation_decisions.loc[
        confirmation_decisions.eval_label_category.eq('sensor_fault'),'eval_anomaly_sensor']:
    for sensor in str(value).split(','):
        if sensor in SENSOR_FIELDS: eligible_pairs[sensor]+=1
for row in matched_rows.itertuples():
    sensors=[name for name in str(row.eval_anomaly_sensor).split(',') if name in SENSOR_FIELDS]
    for sensor in sensors:
        observed_col,prior_col,neighbor_col,truth_col,mad_col=SENSOR_FIELDS[sensor]
        observed=pd.to_numeric(pd.Series([getattr(row,observed_col)]),errors='coerce').iloc[0]
        truth=pd.to_numeric(pd.Series([getattr(row,truth_col)]),errors='coerce').iloc[0]
        candidates=[pd.to_numeric(pd.Series([getattr(row,prior_col)]),errors='coerce').iloc[0]]
        if neighbor_col: candidates.append(pd.to_numeric(pd.Series([getattr(row,neighbor_col)]),errors='coerce').iloc[0])
        candidates=[float(value) for value in candidates if np.isfinite(value)]
        if not candidates or not np.isfinite(truth) or not np.isfinite(observed): continue
        estimate=float(np.median(candidates)); mad=pd.to_numeric(pd.Series([getattr(row,mad_col)]),errors='coerce').iloc[0]
        scale=max(float(mad)*1.4826 if np.isfinite(mad) else 0.0,{'temperature':.5,'pressure':.7,'humidity':2.0}[sensor])
        correction_rows.append({'sensor':sensor,'observed':float(observed),'truth':float(truth),'estimate':estimate,
            'absolute_error_observed':abs(float(observed)-float(truth)),'absolute_error_corrected':abs(estimate-float(truth)),
            'interval_low':estimate-1.645*scale,'interval_high':estimate+1.645*scale})
corrections=pd.DataFrame(correction_rows)
if len(corrections):
    corrections['squared_error_observed']=(corrections.observed-corrections.truth)**2
    corrections['squared_error_corrected']=(corrections.estimate-corrections.truth)**2
    correction_metrics=(corrections.assign(covered=lambda x:(x.truth>=x.interval_low)&(x.truth<=x.interval_high))
        .groupby('sensor').agg(rows=('truth','size'),observed_mae=('absolute_error_observed','mean'),
         corrected_mae=('absolute_error_corrected','mean'),observed_mse=('squared_error_observed','mean'),
         corrected_mse=('squared_error_corrected','mean'),interval_coverage=('covered','mean')).reset_index())
    correction_metrics['observed_rmse']=np.sqrt(correction_metrics.observed_mse)
    correction_metrics['corrected_rmse']=np.sqrt(correction_metrics.corrected_mse)
    correction_metrics['mae_improvement_pct']=100*(correction_metrics.observed_mae-correction_metrics.corrected_mae).div(
        correction_metrics.observed_mae.clip(lower=1e-9))
    correction_metrics['eligible_true_fault_rows']=correction_metrics.sensor.map(eligible_pairs).fillna(0).astype(int)
    correction_metrics['end_to_end_coverage']=correction_metrics.rows.div(
        correction_metrics.eligible_true_fault_rows.clip(lower=1))
else: correction_metrics=pd.DataFrame(columns=['sensor','rows','observed_mae','corrected_mae','observed_rmse',
    'corrected_rmse','mae_improvement_pct','interval_coverage','eligible_true_fault_rows','end_to_end_coverage'])
correction_metrics.to_csv(ITER10_ROOT/'iteration10_correction_metrics.csv',index=False)

fault_incidents=confirmation_predictions.loc[confirmation_predictions.decision_state.eq('sensor_fault')]
health=[]
for station,group in confirmation_decisions.groupby('eval_station_id'):
    incidents=fault_incidents.loc[fault_incidents.station_id.eq(station)]
    drift=int(incidents.root_cause.eq('drift').sum()) if len(incidents) else 0
    critical=int(incidents.confidence.ge(.9).sum()) if len(incidents) else 0
    score=float(np.clip(100-8*len(incidents)-10*drift-6*critical,0,100))
    status='healthy' if score>=80 else ('degrading' if score>=50 else 'critical')
    action='no action' if status=='healthy' else ('inspect within seven days' if status=='degrading' else 'immediate calibration/inspection')
    health.append({'station_id':station,'health_score':score,'status':status,'predicted_fault_incidents':len(incidents),
                   'drift_incidents':drift,'recommended_action':action})
sensor_health=pd.DataFrame(health); sensor_health.to_csv(ITER10_ROOT/'iteration10_sensor_health.csv',index=False)

importance=np.mean(np.stack([model.feature_importances_ for model in state_models]),axis=0)
explainability=pd.DataFrame({'feature':STATE_FEATURES,'mean_gain_importance':importance}).sort_values('mean_gain_importance',ascending=False)
explainability.to_csv(ITER10_ROOT/'iteration10_explainability_feature_importance.csv',index=False)
try:
    import shap
    sample=state_cal[STATE_FEATURES].sample(min(500,len(state_cal)),random_state=26073)
    values=shap.TreeExplainer(state_models[0]).shap_values(sample)
    array=np.asarray(values)
    if array.ndim==2:
        mean_abs=np.mean(np.abs(array),axis=0)
    elif array.ndim==3 and array.shape[1]==len(STATE_FEATURES):
        mean_abs=np.mean(np.abs(array),axis=(0,2))
    elif array.ndim==3 and array.shape[2]==len(STATE_FEATURES):
        mean_abs=np.mean(np.abs(array),axis=(0,1))
    else:
        raise ValueError(f'Unexpected SHAP shape: {array.shape}')
    pd.DataFrame({'feature':STATE_FEATURES,'mean_abs_shap':mean_abs}).sort_values('mean_abs_shap',ascending=False).to_csv(
        ITER10_ROOT/'iteration10_state_shap_importance.csv',index=False)
    shap_status='PASS'
except Exception as error:
    shap_status=f'feature importance available; SHAP optional step failed: {type(error).__name__}: {error}'

sample=main_state.iloc[:min(50000,len(main_state))]
started=time.perf_counter(); _=raw_state_probability(sample); seconds=time.perf_counter()-started
model_files=list(ITER10_ROOT.glob('iteration10_*lightgbm*.joblib'))+list(ITER10_ROOT.glob('iteration10_*catboost*.cbm'))
performance={'rows':len(sample),'seconds':seconds,'rows_per_second':len(sample)/max(seconds,1e-9),
             'model_bytes':sum(path.stat().st_size for path in model_files),'cpu_rss_mb':psutil.Process().memory_info().rss/1024**2,
             'shap_status':shap_status}
(ITER10_ROOT/'iteration10_runtime_metrics.json').write_text(json.dumps(performance,indent=2))
print({'correction':correction_metrics.to_dict('records'),'performance':performance})
display(explainability.head(15)); display(sensor_health.sort_values('health_score').head(10))
"""),
    md(r"""## 16. Objective-level promotion gates and reproducible result package

These gates judge whether the proposed architecture actually solves SIH26073. A failed gate is reported honestly; it does not trigger hidden tuning on confirmation data."""),
    code(r"""family_map=fault_episode_recall.set_index('fault_family').episode_recall.to_dict()
comm_families=[name for name in ('dropout','duplicate_packet','timestamp_error','communication_corruption') if name in family_map]
comm_recall=float(np.mean([family_map[name] for name in comm_families])) if comm_families else 0.0
weak_families=[name for name in ('bias','drift','noise','frozen_sensor') if name in family_map]
weak_recall=float(np.mean([family_map[name] for name in weak_families])) if weak_families else 0.0

i9_reference=json.loads((STARTER/'reference'/'iteration9'/'iteration9_result_block.json').read_text())
i9_confirmation=pd.DataFrame(i9_reference['multidomain_confirmation']).query("scope == 'confirmation'")
reference_f1={}
for old_name,new_name in (('india','india'),('dwd_all','dwd'),('dwd_holdout','dwd_station_holdout')):
    row=i9_confirmation.loc[i9_confirmation.domain.eq(old_name)].iloc[0]
    reference_f1[new_name]={
        'best_point_f1':float(max(row.iteration5_point_f1,row.iteration8_point_f1,row.iteration9_point_f1)),
        'best_event_f1':float(max(row.iteration5_event_f1,row.iteration8_event_f1,row.iteration9_event_f1)),
    }
group_index=multidomain_confirmation.set_index('group')
primary_groups=['india','dwd','india_station_holdout','dwd_station_holdout']
worst_weather_cluster_f1=float(weather_by_cluster.f1.min()) if len(weather_by_cluster) else 0.0
domain_precision_pass=all(float(group_index.loc[name,'fault_precision'])>=.80 for name in primary_groups)
domain_false_alarm_pass=all(float(group_index.loc[name,'false_alerts_per_station_day'])<=.02 for name in primary_groups)
domain_weather_pass=all(float(group_index.loc[name,'weather_f1'])>=.75 for name in ('india','dwd'))
domain_fault_to_weather_pass=all(float(group_index.loc[name,'fault_to_weather_rate'])<=.01 for name in primary_groups)
no_primary_event_regression=all(float(group_index.loc[name,'fault_f1'])>=reference_f1[name]['best_event_f1']
                                for name in ('india','dwd','dwd_station_holdout'))
no_primary_point_regression=all(float(group_index.loc[name,'point_fault_f1'])>=reference_f1[name]['best_point_f1']
                                for name in ('india','dwd','dwd_station_holdout'))

promotion_gates={
    'incident_fault_precision_gte_0_80_every_domain_and_holdout':domain_precision_pass,
    'incident_fault_f1_gte_0_70':confirmation_result['fault']['f1']>=.70,
    'false_alerts_per_station_day_lte_0_02_every_domain_and_holdout':domain_false_alarm_pass,
    'no_primary_incident_f1_regression_vs_best_retained':no_primary_event_regression,
    'no_primary_point_f1_regression_vs_best_retained':no_primary_point_regression,
    'fault_episode_recall_gte_0_70':confirmation_result['fault']['recall']>=.70,
    'drift_episode_recall_gte_0_50':family_map.get('drift',0)>=.50,
    'frozen_episode_recall_gte_0_80':family_map.get('frozen_sensor',0)>=.80,
    'communication_mean_recall_gte_0_80':comm_recall>=.80,
    'weak_fault_mean_recall_gte_0_60':weak_recall>=.60,
    'india_and_dwd_weather_incident_f1_gte_0_75':domain_weather_pass,
    'worst_supported_cluster_weather_f1_gte_0_65':worst_weather_cluster_f1>=.65,
    'fault_to_weather_rate_lte_0_01_every_domain_and_holdout':domain_fault_to_weather_pass,
    'root_cause_accuracy_gte_0_80':root_metrics['accuracy']>=.80,
    'root_cause_macro_f1_gte_0_70':root_metrics['macro_f1']>=.70,
    'fault_ece_lte_0_08':calibration_report['fault']['expected_calibration_error']<=.08,
    'weather_ece_lte_0_08':calibration_report['weather']['expected_calibration_error']<=.08,
    'median_fault_detection_latency_lte_180_minutes':(
        confirmation_result['fault']['median_latency_minutes'] is not None and
        confirmation_result['fault']['median_latency_minutes']<=180),
    'three_fresh_seed_runs_present':set(stress.seed.astype(int))=={MAIN_SEED,*STRESS_SEEDS},
    'every_seed_precision_and_false_alarm_pass':bool((stress.fault_precision>=.80).all() and
        (stress.false_alerts_per_station_day<=.02).all()),
    'locked_2024_2025_unopened':True,
}
promotion_gates={key:bool(value) for key,value in promotion_gates.items()}
promoted=all(promotion_gates.values())
status='eligible_for_one_authorised_locked_confirmation' if promoted else 'retain_current_shadow_deployment_and_review_failed_gates'

problem_coverage={
    'real_time_anomaly_alerts':'implemented causal row + state engine',
    'spike_frozen_communication_faults':'13 operational families plus 5 subtle families evaluated',
    'temporal_seasonal_learning':'rolling robust/EWMA/slope/CUSUM/climatology residuals',
    'multivariate_consistency':'T/P/RH causal interactions and consistency features',
    'genuine_weather_separation':'independent neighbour gate plus exclusive three-way state',
    'confidence_and_explainability':'L2 calibrated probabilities, LightGBM importance and SHAP export',
    'sensor_degradation_maintenance':'dedicated drift evidence and station health recommendations',
    'corrected_values':'causal advisory estimates with held-out original-value MAE/coverage',
    'scalability':'batch throughput and model-size evidence',
    'dashboard_and_live_api':'existing SkyGuard dashboard/API; Iteration 10 remains shadow until gates pass',
}
(ITER10_ROOT/'iteration10_problem_coverage.json').write_text(json.dumps(problem_coverage,indent=2))

result_block={
    'iteration':'10_final_incident_intelligence','status':status,'promoted':promoted,
    'device':torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU',
    'development_years':[2022,2023],'locked_2024_opened':False,'any_2025_opened':False,
    'data':{'india_rows':len(india),'dwd_hourly_rows':len(dwd),'india_stations':int(india.station_id.nunique()),
            'dwd_stations':int(dwd.station_id.nunique()),'official_data_validation':'PASS'},
    'feature_contract':feature_contract,'frozen_policy':FROZEN_POLICY,
    'point_metrics':point_metrics,'incident_confirmation':confirmation_result,
    'root_cause':root_metrics,'calibration':calibration_report,
    'mean_communication_recall':comm_recall,'mean_weak_fault_recall':weak_recall,
    'multiseed_stress':stress.to_dict('records'),'correction':correction_metrics.to_dict('records'),
    'runtime':performance,'promotion_gates':promotion_gates,'passed_gates':sum(promotion_gates.values()),
    'reference_f1_from_retained_iterations':reference_f1,
    'total_gates':len(promotion_gates),'problem_coverage':problem_coverage,
    'selection_integrity':{'fit':'2022 development stations only','calibration':'2023 Jan-Feb development stations',
       'policy':'2023 Mar-Apr development stations','discovery':'2023 May-Aug all stations',
       'confirmation':'2023 Sep-Dec all stations','confirmation_used_for_selection':False,
       'station_holdouts_used_for_fit_calibration_or_policy':False},
    'next_decision':'authorise exactly one locked confirmation only after independent audit' if promoted else
                    'inspect failed gates; do not deploy Iteration 10 automatically',
}
(ITER10_ROOT/'iteration10_result_block.json').write_text(json.dumps(result_block,indent=2))

integrity={'status':'PASS','bundle_sha256':EXPECTED_BUNDLE_SHA256,'development_years':[2022,2023],
           'locked_years_opened':[],'fresh_seeds':[MAIN_SEED,*STRESS_SEEDS],
           'feature_identifiers_excluded':True,'pressure_datum_protected':True,
           'confirmation_used_for_selection':False,'automatic_deployment':False}
(ITER10_ROOT/'iteration10_integrity_receipt.json').write_text(json.dumps(integrity,indent=2))

package_files=[path for path in ITER10_ROOT.glob('iteration10_*') if path.is_file()]
package_path=ITER10_ROOT/'SkyGuard_Iteration10_Result_Package.zip'
with zipfile.ZipFile(package_path,'w',zipfile.ZIP_DEFLATED,compresslevel=7) as archive:
    for path in package_files: archive.write(path,path.name)
print(json.dumps({'status':status,'passed_gates':sum(promotion_gates.values()),'total_gates':len(promotion_gates),
                  'failed_gates':[key for key,value in promotion_gates.items() if not value],
                  'result_block':str(ITER10_ROOT/'iteration10_result_block.json'),
                  'result_package':str(package_path),'package_sha256':sha256_file(package_path),
                  'locked_years_opened':[]},indent=2))
"""),
    md(r"""# Mandatory stop and return-to-Codex rule

Do **not** open 2024 or 2025 from this notebook. Return these files from the experiment folder:

- `iteration10_result_block.json`
- `iteration10_multidomain_confirmation.csv`
- `iteration10_fault_episode_recall.csv`
- `iteration10_multiseed_stress.csv`
- `iteration10_root_cause_metrics.csv`
- `iteration10_root_cause_per_class.csv`
- `iteration10_calibration_metrics.json`
- `iteration10_correction_metrics.csv`
- `iteration10_weather_by_cluster.csv`
- `iteration10_detection_latency.csv`
- `iteration10_season_metrics.csv`
- `iteration10_sensor_health.csv`
- `iteration10_policy_frontier.csv`
- `iteration10_feature_contract.json`
- `iteration10_integrity_receipt.json`
- `iteration10_runtime_metrics.json`
- `SkyGuard_Iteration10_Result_Package.zip`

Only an independent audit of these outputs can authorise the next decision.
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
payload = json.dumps(notebook, indent=1, ensure_ascii=False) + "\n"
OUTPUT.write_text(payload, encoding="utf-8")
DELIVERABLE.parent.mkdir(parents=True, exist_ok=True)
DELIVERABLE.write_text(payload, encoding="utf-8")
print(json.dumps({"notebook": str(OUTPUT), "deliverable": str(DELIVERABLE),
                  "cells": len(cells), "bytes": OUTPUT.stat().st_size}, indent=2))
