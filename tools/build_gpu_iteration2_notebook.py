"""Build SkyGuard GPU Iteration 2: weak-fault rescue and robust policy."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks" / "SkyGuard_AI_GPU_Iteration_02_Weak_Fault_Rescue_Colab.ipynb"


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": text.splitlines(keepends=True)}


cells = [
md(r"""# SkyGuard AI — GPU Iteration 2

## Weak-fault rescue and robust multi-block policy

Iteration 1 established that the five-seed CatBoost detector is the best new base learner. This notebook makes one controlled change: it adds calibrated, one-vs-rest **frozen**, **bias**, and **drift** specialists plus a persistence rescue policy.

### Evidence driving this iteration

- CatBoost improved policy-block F1 from 54.55% to 55.14%, AUCPR from 46.93% to 49.52%, precision to 92.50%, and reduced false-alarm episodes to 0.0152/station-day.
- The TCN was rejected: AUCPR 20.82%, F1 22.29%, and excessive false alarms.
- The previous isotonic hybrid was rejected for detection ranking: AUCPR fell to 38.36%.
- Hand-made specialist scores were saturated (combined mean 0.95) and are replaced here.
- Frozen recall was 0%; bias/drift were 50% each.

The 2024 final tests remain sealed.
"""),
md(r"""## Run instructions

Use the same Google Drive bundle and Iteration 1 model directory. Select a T4 GPU, run all cells, and leave `UNLOCK_FINAL_TESTS=False`. This notebook does not retrain the rejected TCN.
"""),
code(r"""!pip -q install catboost==1.2.10 lightgbm==4.6.0 scikit-learn==1.7.2 pyarrow==21.0.0 psutil==7.0.0
from google.colab import drive
drive.mount('/content/drive')
"""),
code(r"""from pathlib import Path
DRIVE_ROOT=Path('/content/drive/MyDrive/SkyGuard_AI_GPU')
BUNDLE_ZIP=DRIVE_ROOT/'SkyGuard_GPU_Data_Bundle.zip'
DATA_ROOT=DRIVE_ROOT/'SkyGuard_GPU_Data_Bundle'
ITER1=DRIVE_ROOT/'experiments'/'iteration_01_detection'
ARTIFACT_ROOT=DRIVE_ROOT/'experiments'/'iteration_02_weak_fault_rescue'
ARTIFACT_ROOT.mkdir(parents=True,exist_ok=True)

UNLOCK_FINAL_TESTS=False
REUSE_SAVED_MODELS=True
SEEDS=[17,29,41,53,67]
SPECIALIST_SEEDS=[17,41,67]
print('Iteration 1:',ITER1)
print('Iteration 2:',ARTIFACT_ROOT)
"""),
code(r"""import os,json,time,math,hashlib,zipfile,warnings,platform
import joblib,numpy as np,pandas as pd,matplotlib.pyplot as plt,psutil
from IPython.display import display
from sklearn.metrics import average_precision_score,precision_score,recall_score,f1_score,confusion_matrix
from sklearn.linear_model import LogisticRegression
from catboost import CatBoostClassifier
import torch

warnings.filterwarnings('ignore')
pd.set_option('display.max_columns',50)
pd.set_option('display.float_format',lambda x:f'{x:,.5f}')
DEVICE='cuda' if torch.cuda.is_available() else 'cpu'
print({'python':platform.python_version(),'device':DEVICE,
       'gpu':torch.cuda.get_device_name(0) if DEVICE=='cuda' else None,
       'ram_gb':round(psutil.virtual_memory().total/2**30,2)})
assert DEVICE=='cuda','Select a GPU runtime.'

if not DATA_ROOT.exists():
    assert BUNDLE_ZIP.exists(),f'Missing {BUNDLE_ZIP}'
    with zipfile.ZipFile(BUNDLE_ZIP) as archive: archive.extractall(DRIVE_ROOT)
"""),
md("## 1. Load exact development partitions and Phase 10 contract"),
code(r"""FEATURE_DIR=DATA_ROOT/'data'/'features_phase10'
BASELINE_FILE=DATA_ROOT/'models'/'phase10_final.joblib'

def load_table(name):
    frame=pd.read_csv(FEATURE_DIR/f'{name}_features.csv.gz',low_memory=False)
    frame['station_id']=frame.station_id.astype(str)
    frame['emitted_timestamp_utc']=pd.to_datetime(frame.emitted_timestamp_utc,utc=True)
    frame['episode_id']=frame.episode_id.fillna('').astype(str)
    return frame.sort_values(['station_id','emitted_timestamp_utc','row_id']).reset_index(drop=True)

train=load_table('train'); validation=load_table('validation')
train['dev_split']='train'
ts=validation.emitted_timestamp_utc
validation['dev_split']=np.select(
    [ts<'2023-05-01',ts<'2023-07-01',ts<'2023-10-01'],
    ['tune_model','block_may_jun','block_jul_sep'],default='block_oct_dec')
episode_part=(validation.loc[validation.episode_id.ne('')].sort_values('emitted_timestamp_utc')
              .groupby('episode_id').dev_split.first())
mask=validation.episode_id.ne('')
validation.loc[mask,'dev_split']=validation.loc[mask,'episode_id'].map(episode_part)
dev=pd.concat([train,validation],ignore_index=True)
del train,validation
dev=dev.loc[dev.available_to_detector.eq(1)].copy().reset_index(drop=True)

bundle=joblib.load(BASELINE_FILE); FEATURES=list(bundle['event_features'])
assert len(FEATURES)==108 and not ({'temperature_dewpoint_spread_c','hour_sin','hour_cos','day_of_year_sin','day_of_year_cos'}&set(FEATURES))
assert dev.loc[dev.episode_id.ne('')].groupby('episode_id').dev_split.nunique().max()==1
display(dev.groupby('dev_split').agg(rows=('row_id','size'),fault_rows=('is_anomaly','sum'),
                                     episodes=('episode_id',lambda s:s[s.ne('')].nunique()),stations=('station_id','nunique')))
"""),
md("## 2. Exact Phase 10 and Iteration 1 CatBoost scores"),
code(r"""event_model=bundle['event_model']; classes=list(event_model.classes_)
fault_index=classes.index('sensor_fault'); weather_index=classes.index('genuine_weather')
proba=event_model.predict_proba(dev[FEATURES].replace([np.inf,-np.inf],np.nan))
dev['phase10_fault']=proba[:,fault_index]; dev['phase10_weather']=proba[:,weather_index]
PHASE10_THRESHOLD=float(bundle['policy']['known_station']['threshold'])

def load_cat_models(prefix,seeds):
    models=[]
    for seed in seeds:
        path=ITER1/f'{prefix}_seed{seed}.cbm'
        assert path.exists(),f'Missing {path}. Run Iteration 1 CatBoost cell or restore Drive artifacts.'
        model=CatBoostClassifier(); model.load_model(path); models.append(model)
    return models

fault_models=load_cat_models('cat_fault',SEEDS)
weather_models=load_cat_models('cat_weather',SEEDS)
X=dev[FEATURES]
fault_seed_scores=np.column_stack([m.predict_proba(X)[:,1] for m in fault_models])
weather_seed_scores=np.column_stack([m.predict_proba(X)[:,1] for m in weather_models])
dev['cat_fault_mean']=fault_seed_scores.mean(1)
dev['cat_fault_median']=np.median(fault_seed_scores,axis=1)
dev['cat_weather_mean']=weather_seed_scores.mean(1)
dev['cat_weather_median']=np.median(weather_seed_scores,axis=1)
print('Loaded',len(fault_models),'fault and',len(weather_models),'weather models.')
"""),
md("## 3. Strict metrics and fast causal alert policies"),
code(r"""def point_metrics(y,p,score):
    y=np.asarray(y,int); p=np.asarray(p,bool); score=np.asarray(score,float)
    tn,fp,fn,tp=confusion_matrix(y,p,labels=[0,1]).ravel()
    return {'tp':int(tp),'fp':int(fp),'fn':int(fn),'tn':int(tn),
            'precision':precision_score(y,p,zero_division=0),'recall':recall_score(y,p,zero_division=0),
            'f1':f1_score(y,p,zero_division=0),'auprc':average_precision_score(y,score)}

def predicted_events(group,pred_col):
    g=group.sort_values('emitted_timestamp_utc'); times=g.emitted_timestamp_utc.tolist(); pred=g[pred_col].to_numpy(bool)
    dt=g.emitted_timestamp_utc.diff().dt.total_seconds().div(60); positive=dt[dt.gt(0)]
    gap=max(60,2.5*(float(positive.median()) if len(positive) else 60))
    events=[]; start=None; previous=None
    for pos in np.flatnonzero(pred):
        separated=(previous is None or pos!=previous+1 or (times[pos]-times[previous]).total_seconds()/60>gap)
        if separated:
            if start is not None: events.append((times[start],times[previous]))
            start=pos
        previous=pos
    if start is not None: events.append((times[start],times[previous]))
    return events

def event_metrics(frame,pred_col):
    truth=[]
    labelled=frame.loc[frame.is_anomaly.eq(1)&frame.episode_id.ne('')]
    for (station,episode),g in labelled.groupby(['station_id','episode_id']):
        truth.append((station,episode,g.emitted_timestamp_utc.min(),g.emitted_timestamp_utc.max(),g.anomaly_type.mode().iloc[0]))
    predictions=[]; station_days=0
    for station,g in frame.groupby('station_id',sort=False):
        g=g.sort_values('emitted_timestamp_utc'); station_days+=max((g.emitted_timestamp_utc.iloc[-1]-g.emitted_timestamp_utc.iloc[0]).total_seconds()/86400,1/24)
        predictions.extend((station,a,b) for a,b in predicted_events(g,pred_col))
    used=set(); hits=[]; delays=[]; per_fault={}
    for station,episode,start,end,fault in truth:
        candidates=[(i,p) for i,p in enumerate(predictions) if i not in used and p[0]==station and p[1]<=end and p[2]>=start]
        hit=bool(candidates)
        if hit:
            i,p=min(candidates,key=lambda item:item[1][1]); used.add(i); delays.append(max(0,(max(start,p[1])-start).total_seconds()/60))
        hits.append(hit); per_fault.setdefault(fault,[]).append(hit)
    tp=sum(hits); fp=len(predictions)-len(used); fn=len(truth)-tp
    ep=tp/max(tp+fp,1); er=tp/max(tp+fn,1)
    return {'true_episodes':len(truth),'predicted_episodes':len(predictions),'event_precision':ep,'event_recall':er,
            'event_f1':2*ep*er/max(ep+er,1e-12),'false_alarm_episodes_per_station_day':fp/max(station_days,1e-12),
            'delay_median_min':float(np.median(delays)) if delays else None,'delay_p90_min':float(np.quantile(delays,.9)) if delays else None,
            'delay_mean_min':float(np.mean(delays)) if delays else None,
            'per_fault_episode_recall':{k:float(np.mean(v)) for k,v in sorted(per_fault.items())}}

def hysteresis(frame,score_col,start,cont):
    result=pd.Series(False,index=frame.index)
    for _,g in frame.groupby('station_id',sort=False):
        g=g.sort_values('emitted_timestamp_utc'); active=False; out=np.zeros(len(g),bool)
        for pos,score in enumerate(g[score_col].fillna(0).to_numpy(float)):
            if not active and score>=start: active=True
            elif active and score<cont: active=False
            out[pos]=active
        result.loc[g.index]=out
    return result

def persistent_signal(frame,score_col,threshold,min_points):
    result=pd.Series(False,index=frame.index)
    for _,g in frame.groupby('station_id',sort=False):
        g=g.sort_values('emitted_timestamp_utc'); run=0; out=np.zeros(len(g),bool)
        for pos,score in enumerate(g[score_col].fillna(0).to_numpy(float)):
            run=run+1 if score>=threshold else 0
            out[pos]=run>=min_points
        result.loc[g.index]=out
    return result

def evaluate(frame,score_col,pred_col): return {**point_metrics(frame.is_anomaly,frame[pred_col],frame[score_col]),**event_metrics(frame,pred_col)}
"""),
md(r"""## 4. Train focused frozen, bias, and drift specialists

Each specialist uses a small causal feature family and three fixed seeds. Models train on 2022, use January–April 2023 only for early stopping, and never see the three robust policy blocks during fitting.
"""),
code(r"""FROZEN_FEATURES=[c for c in FEATURES if any(token in c for token in [
    'frozen_run_length','rolling_mad_24h','rolling_median_24h','delta1','rate_per_hour','neighbor_'])]
BIAS_FEATURES=[c for c in FEATURES if any(token in c for token in [
    'cusum_','climatology_residual','ewma_residual','neighbor_residual','regional_agreement'])]
DRIFT_FEATURES=[c for c in FEATURES if any(token in c for token in [
    '_slope_','cusum_','monotonic_run','climatology_residual','neighbor_residual','regional_'])]
SPECIALIST_FEATURES={'frozen_sensor':FROZEN_FEATURES,'bias':BIAS_FEATURES,'drift':DRIFT_FEATURES}
print({k:len(v) for k,v in SPECIALIST_FEATURES.items()})
assert all(len(v)>=12 for v in SPECIALIST_FEATURES.values())

train_mask=dev.dev_split.eq('train'); tune_mask=dev.dev_split.eq('tune_model')
specialist_models={}; specialist_history={}
for fault,features in SPECIALIST_FEATURES.items():
    y_train=dev.loc[train_mask,'anomaly_type'].eq(fault).astype(int)
    y_tune=dev.loc[tune_mask,'anomaly_type'].eq(fault).astype(int)
    ratio=(len(y_train)-y_train.sum())/max(y_train.sum(),1)
    models=[]; history=[]
    for seed in SPECIALIST_SEEDS:
        path=ARTIFACT_ROOT/f'{fault}_specialist_seed{seed}.cbm'
        model=CatBoostClassifier(iterations=1000,depth=7,learning_rate=.035,loss_function='Logloss',eval_metric='PRAUC',
            scale_pos_weight=min(math.sqrt(ratio),25),l2_leaf_reg=8,random_strength=.4,random_seed=seed,
            task_type='GPU',devices='0',verbose=100,od_type='Iter',od_wait=100,allow_writing_files=False)
        if REUSE_SAVED_MODELS and path.exists(): model.load_model(path)
        else:
            model.fit(dev.loc[train_mask,features],y_train,eval_set=(dev.loc[tune_mask,features],y_tune),use_best_model=True)
            model.save_model(path)
        best=model.get_best_iteration()
        models.append(model); history.append({'seed':seed,'best_iteration':int(best if best is not None else model.tree_count_-1)})
    specialist_models[fault]=models; specialist_history[fault]=history
    raw=np.mean([m.predict_proba(dev[features])[:,1] for m in models],axis=0)
    dev[f'{fault}_raw']=raw
print(specialist_history)
"""),
md("## 5. Rank-preserving Platt calibration for comparable rescue scores"),
code(r"""fit_mask=dev.dev_split.eq('block_may_jun')
calibrators={}

def fit_platt(raw,y):
    raw=np.clip(np.asarray(raw,float),1e-6,1-1e-6); logit=np.log(raw/(1-raw)).reshape(-1,1)
    model=LogisticRegression(C=1,max_iter=2000).fit(logit,np.asarray(y,int)); return model

def apply_platt(model,raw):
    raw=np.clip(np.asarray(raw,float),1e-6,1-1e-6); return model.predict_proba(np.log(raw/(1-raw)).reshape(-1,1))[:,1]

for fault in SPECIALIST_FEATURES:
    col=f'{fault}_raw'; y=dev.anomaly_type.eq(fault).astype(int)
    calibrators[fault]=fit_platt(dev.loc[fit_mask,col],y.loc[fit_mask])
    dev[f'{fault}_score']=apply_platt(calibrators[fault],dev[col])

base_calibrator=fit_platt(dev.loc[fit_mask,'cat_fault_mean'],dev.loc[fit_mask,'is_anomaly'])
dev['base_score']=apply_platt(base_calibrator,dev.cat_fault_mean)
dev['rescue_score']=dev[[f'{f}_score' for f in SPECIALIST_FEATURES]].max(axis=1)

rows=[]
for fault in SPECIALIST_FEATURES:
    for block in ['block_jul_sep','block_oct_dec']:
        m=dev.dev_split.eq(block); y=dev.anomaly_type.eq(fault).astype(int)
        rows.append({'fault':fault,'block':block,'auprc':average_precision_score(y[m],dev.loc[m,f'{fault}_score'])})
specialist_validation=pd.DataFrame(rows)
display(specialist_validation)
"""),
md(r"""## 6. Hard rules and two-tier rescue policy

The high-precision CatBoost channel creates ordinary alerts. Frozen/bias/drift specialists may rescue an incident only after their evidence persists for multiple consecutive readings. Hard packet/timestamp/physical errors remain deterministic overrides.
"""),
code(r"""def add_hard_rules(frame):
    z=frame.copy()
    duplicate=z.duplicated(['station_id','emitted_timestamp_utc'],keep=False)
    timestamp=z.out_of_order_indicator.fillna(0).gt(0)
    physical=((z.temperature_value.notna()&~z.temperature_value.between(-60,60))|
              (z.pressure_value.notna()&~z.pressure_value.between(800,1100))|
              (z.humidity_value.notna()&~z.humidity_value.between(0,100)))
    z['hard_rule']=(duplicate|timestamp|physical)
    return z
dev=add_hard_rules(dev)

POLICY_BLOCKS=['block_may_jun','block_jul_sep','block_oct_dec']

def apply_two_tier(frame,base_start,base_continue,rescue_threshold,min_points):
    base=hysteresis(frame,'base_score',base_start,base_continue)
    rescue=persistent_signal(frame,'rescue_score',rescue_threshold,min_points)
    return base|rescue|frame.hard_rule

def search_robust_policy(frame):
    rows=[]
    for base_start in np.linspace(.30,.90,8):
      for rescue_threshold in [.50,.60,.70,.80,.90]:
       for min_points in [2,3,4]:
        block_metrics=[]
        for block in POLICY_BLOCKS:
            part=frame.loc[frame.dev_split.eq(block)].copy()
            part['pred']=apply_two_tier(part,base_start,max(0,base_start-.08),rescue_threshold,min_points)
            block_metrics.append((block,evaluate(part,'base_score','pred')))
        summary={'base_start':base_start,'base_continue':max(0,base_start-.08),
                 'rescue_threshold':rescue_threshold,'min_points':min_points}
        for block,m in block_metrics:
            for key in ['precision','recall','f1','auprc','event_precision','event_recall','event_f1',
                        'false_alarm_episodes_per_station_day','delay_mean_min','delay_p90_min']:
                summary[f'{block}_{key}']=m[key]
        summary['min_precision']=min(m['precision'] for _,m in block_metrics)
        summary['max_false_alarm']=max(m['false_alarm_episodes_per_station_day'] for _,m in block_metrics)
        summary['min_event_recall']=min(m['event_recall'] for _,m in block_metrics)
        summary['mean_event_f1']=np.mean([m['event_f1'] for _,m in block_metrics])
        summary['mean_point_f1']=np.mean([m['f1'] for _,m in block_metrics])
        rows.append(summary)
    frontier=pd.DataFrame(rows)
    feasible=frontier.loc[(frontier.min_precision>=.75)&(frontier.max_false_alarm<=.02)]
    if len(feasible):
        selected=feasible.sort_values(['min_event_recall','mean_event_f1','mean_point_f1'],ascending=False).iloc[0]
        status='constraints_met_all_blocks'
    else:
        frontier['violation']=np.maximum(0,.75-frontier.min_precision)/.75+np.maximum(0,frontier.max_false_alarm-.02)/.02
        selected=frontier.sort_values(['violation','min_event_recall','mean_event_f1'],ascending=[True,False,False]).iloc[0]
        status='pareto_fallback'
    return selected,frontier,status

selected,frontier,POLICY_STATUS=search_robust_policy(dev)
frontier.to_csv(ARTIFACT_ROOT/'iteration2_policy_frontier.csv',index=False)
display(selected.to_frame('selected')); print(POLICY_STATUS)
"""),
md("## 7. Multi-block ablation and weak-fault recall"),
code(r"""def robust_base_policy(frame,score_col):
    candidates=[]
    for threshold in np.linspace(.10,.95,25):
        block_results=[]
        for block in POLICY_BLOCKS:
            part=frame.loc[frame.dev_split.eq(block)].copy()
            part['pred']=hysteresis(part,score_col,threshold,max(0,threshold-.08))
            block_results.append(evaluate(part,score_col,'pred'))
        candidates.append({'threshold':threshold,
            'min_precision':min(m['precision'] for m in block_results),
            'max_false_alarm':max(m['false_alarm_episodes_per_station_day'] for m in block_results),
            'min_event_recall':min(m['event_recall'] for m in block_results),
            'mean_event_f1':np.mean([m['event_f1'] for m in block_results])})
    feasible=[x for x in candidates if x['min_precision']>=.75 and x['max_false_alarm']<=.02]
    return max(feasible or candidates,key=lambda x:(x['min_event_recall'],x['mean_event_f1']))

rows=[]; combined=[]
base_policy=robust_base_policy(dev,'base_score')
print('Robust CatBoost base policy:',base_policy)
for block in POLICY_BLOCKS:
    part=dev.loc[dev.dev_split.eq(block)].copy()
    part['phase10_pred']=part.phase10_fault.ge(PHASE10_THRESHOLD)
    rows.append({'block':block,'variant':'Phase10 fixed',**evaluate(part,'phase10_fault','phase10_pred')})
    part['cat_pred']=hysteresis(part,'base_score',base_policy['threshold'],max(0,base_policy['threshold']-.08))
    rows.append({'block':block,'variant':'CatBoost base',**evaluate(part,'base_score','cat_pred')})
    part['rescue_pred']=apply_two_tier(part,selected.base_start,selected.base_continue,selected.rescue_threshold,int(selected.min_points))
    rows.append({'block':block,'variant':'CatBoost + weak-fault rescue',**evaluate(part,'base_score','rescue_pred')})
    combined.append(part)
ablation=pd.DataFrame(rows)
ablation.to_csv(ARTIFACT_ROOT/'iteration2_multiblock_ablation.csv',index=False)
display(ablation[['block','variant','precision','recall','f1','auprc','event_precision','event_recall','event_f1',
                  'false_alarm_episodes_per_station_day','delay_mean_min','delay_p90_min']])

combined=pd.concat(combined,ignore_index=True); combined['pred']=combined.rescue_pred
fault_recall=pd.Series(event_metrics(combined,'pred')['per_fault_episode_recall'],name='episode_recall').sort_values().to_frame()
fault_recall.to_csv(ARTIFACT_ROOT/'iteration2_fault_episode_recall.csv')
display(fault_recall)
"""),
md("## 8. Repair the weather channel by selecting the robust existing score"),
code(r"""weather_candidates=['phase10_weather','cat_weather_mean','cat_weather_median']
weather_rows=[]
for score_col in weather_candidates:
 for threshold in np.linspace(.02,.90,45):
    metrics=[]
    for block in POLICY_BLOCKS:
        part=dev.loc[dev.dev_split.eq(block)]; pred=part[score_col].ge(threshold)
        metrics.append({'block':block,'precision':precision_score(part.is_weather_event,pred,zero_division=0),
                        'recall':recall_score(part.is_weather_event,pred,zero_division=0),
                        'f1':f1_score(part.is_weather_event,pred,zero_division=0)})
    weather_rows.append({'score':score_col,'threshold':threshold,'min_f1':min(m['f1'] for m in metrics),
                         'mean_f1':np.mean([m['f1'] for m in metrics]),'blocks':metrics})
weather_frontier=pd.DataFrame(weather_rows)
weather_selected=weather_frontier.sort_values(['min_f1','mean_f1'],ascending=False).iloc[0]
weather_frontier.drop(columns='blocks').to_csv(ARTIFACT_ROOT/'iteration2_weather_frontier.csv',index=False)
display(weather_selected.to_frame('selected'))
"""),
md("## 9. Save Iteration 2 result package"),
code(r"""result={
 'iteration':'02_weak_fault_rescue','device':DEVICE,'gpu':torch.cuda.get_device_name(0),
 'final_tests_opened':bool(UNLOCK_FINAL_TESTS),'tcn_promoted':False,'isotonic_fusion_promoted':False,
 'specialist_history':specialist_history,'specialist_validation':specialist_validation.to_dict('records'),
 'policy_status':POLICY_STATUS,'selected_policy':selected.to_dict(),'robust_base_policy':base_policy,
 'multiblock_ablation':ablation.drop(columns=['per_fault_episode_recall'],errors='ignore').to_dict('records'),
 'fault_episode_recall':fault_recall.episode_recall.to_dict(),
 'weather_selected':{'score':weather_selected.score,'threshold':float(weather_selected.threshold),
                     'min_f1':float(weather_selected.min_f1),'mean_f1':float(weather_selected.mean_f1)},
}
(ARTIFACT_ROOT/'iteration2_result_block.json').write_text(json.dumps(result,indent=2,default=float))
joblib.dump({'specialist_calibrators':calibrators,'base_calibrator':base_calibrator,
             'specialist_features':SPECIALIST_FEATURES,'selected_policy':selected.to_dict(),
             'weather_score':weather_selected.score,'weather_threshold':float(weather_selected.threshold)},
            ARTIFACT_ROOT/'iteration2_policy.joblib')
print(json.dumps(result,indent=2,default=float))
print('\nSEND BACK THESE FILES:')
for name in ['iteration2_result_block.json','iteration2_multiblock_ablation.csv','iteration2_fault_episode_recall.csv','iteration2_weather_frontier.csv']:
    print(ARTIFACT_ROOT/name)
"""),
md(r"""## 10. Final-test seal

Iteration 2 intentionally contains no final-test scoring cell. Even if `UNLOCK_FINAL_TESTS` is changed accidentally, no 2024 file is loaded. After reviewing these outputs, we will either retain CatBoost alone or freeze the rescue policy, and only a separate finalization notebook will open the tests once.
"""),
md(r"""## Return to Codex

Send the four files listed above. We will accept the rescue policy only if it improves weak-fault/event recall consistently across the three 2023 blocks while preserving precision and the 0.02 false-alarm budget. Otherwise CatBoost alone remains the winner.
"""),
]

notebook={
    "cells":cells,
    "metadata":{"accelerator":"GPU","colab":{"name":OUTPUT.name,"provenance":[]},
                "kernelspec":{"display_name":"Python 3","language":"python","name":"python3"},
                "language_info":{"name":"python","version":"3"}},
    "nbformat":4,"nbformat_minor":5,
}
OUTPUT.parent.mkdir(parents=True,exist_ok=True)
OUTPUT.write_text(json.dumps(notebook,indent=1,ensure_ascii=False),encoding='utf-8')
print(OUTPUT)
