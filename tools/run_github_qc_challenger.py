"""Development-only ablation. Never opens protected tests or promotes a model."""
import sys, json, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from lightgbm import LGBMClassifier
from sklearn.metrics import precision_score, recall_score, f1_score, average_precision_score

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from data.run_phase10_models import load_split
from skyguard.features.phase10 import PHASE10_FEATURES
from skyguard.features.spatial_qc import add_spatial_qc

def metrics(frame, scores, threshold):
    y=frame.event_label.eq('sensor_fault').to_numpy()
    pred=scores>=threshold
    weather=frame.event_label.eq('genuine_weather').to_numpy()
    days=frame[['station_id','emitted_timestamp_utc']].copy()
    days['day']=days.emitted_timestamp_utc.astype(str).str[:10]
    denominator=len(days[['station_id','day']].drop_duplicates())
    episodes=frame.loc[y & frame.episode_id.fillna('').ne(''),['station_id','episode_id']].drop_duplicates()
    detected=frame.loc[y & pred & frame.episode_id.fillna('').ne(''),['station_id','episode_id']].drop_duplicates()
    return dict(precision=float(precision_score(y,pred,zero_division=0)),recall=float(recall_score(y,pred,zero_division=0)),f1=float(f1_score(y,pred,zero_division=0)),auprc=float(average_precision_score(y,scores)),false_alarms_per_station_day=float((pred & ~y).sum()/max(1,denominator)),weather_false_fault_rate=float(pred[weather].mean()) if weather.any() else None,episode_recall=len(detected)/max(1,len(episodes)))

def main():
    output=ROOT/'reports'/'github_qc_challenger'
    output.mkdir(exist_ok=True)
    train=load_split('train'); validation=load_split('validation')
    # Labelled development years only. Previously inspected 2023 is not blind.
    assert set(pd.to_datetime(train.emitted_timestamp_utc,utc=True).dt.year)=={2022}
    assert set(pd.to_datetime(validation.emitted_timestamp_utc,utc=True).dt.year)=={2023}
    train=add_spatial_qc(train); validation=add_spatial_qc(validation)
    dates=pd.to_datetime(validation.emitted_timestamp_utc,utc=True)
    tune=validation.loc[dates<'2023-07-01'].copy()
    confirm=validation.loc[dates>='2023-07-01'].copy()
    # Remove episodes crossing the selection boundary from confirmation.
    used=set(zip(tune.station_id.astype(str),tune.episode_id.fillna('').astype(str)))
    confirm=confirm.loc[[(not str(e) or (str(s),str(e)) not in used) for s,e in zip(confirm.station_id,confirm.episode_id.fillna(''))]]
    features=list(PHASE10_FEATURES)
    additions=[c for c in train if c.startswith('qc_')]
    report={'status':'development_only_not_promoted','blind_test':False,'protected_test_files_opened':False,'rows':{'train':len(train),'tune':len(tune),'confirmation':len(confirm)},'candidates':{}}
    for name,columns in [('matched_baseline',features),('robust_spatial_challenger',features+additions)]:
        def X(frame): return frame[columns].apply(pd.to_numeric,errors='coerce').replace([np.inf,-np.inf],np.nan).astype('float32')
        model=LGBMClassifier(n_estimators=300,num_leaves=23,max_depth=8,learning_rate=.04,min_child_samples=50,reg_alpha=1,reg_lambda=12,random_state=26073,n_jobs=4,verbosity=-1)
        print('Training',name,len(train),flush=True)
        model.fit(X(train),train.event_label.eq('sensor_fault'))
        scores=model.predict_proba(X(tune))[:,1]
        frontier=[]
        for threshold in np.unique(np.r_[np.linspace(.02,.98,50),1.000001]):
            m=metrics(tune,scores,threshold); frontier.append({'threshold':float(threshold),**m})
        feasible=[m for m in frontier if m['false_alarms_per_station_day']<=.05 and (m['weather_false_fault_rate'] or 0)<=.02]
        policy=max(feasible,key=lambda m:m['f1'])
        confirmation=metrics(confirm,model.predict_proba(X(confirm))[:,1],policy['threshold'])
        report['candidates'][name]={'features':len(columns),'selection':policy,'confirmation':confirmation}
        joblib.dump({'model':model,'features':columns,'threshold':policy['threshold'],'status':'development_only'},output/f'{name}.joblib',compress=3)
        print(name,confirmation,flush=True)
    a=report['candidates']['matched_baseline']['confirmation']; b=report['candidates']['robust_spatial_challenger']['confirmation']
    report['development_gate_passed']=b['f1']>a['f1'] and b['recall']>=a['recall'] and b['false_alarms_per_station_day']<=a['false_alarms_per_station_day'] and (b['weather_false_fault_rate'] or 0)<=(a['weather_false_fault_rate'] or 0)
    report['live_model_sha256']=hashlib.sha256((ROOT/'models/phase10_final.joblib').read_bytes()).hexdigest()
    (output/'comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__': main()
