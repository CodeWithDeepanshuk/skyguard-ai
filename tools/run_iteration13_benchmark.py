"""Run Iteration 13 only when genuine IMD temporal readiness is satisfied."""
from __future__ import annotations

import argparse, hashlib, json, os, platform, subprocess, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.ensemble import HistGradientBoostingClassifier, IsolationForest
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, balanced_accuracy_score, brier_score_loss,
    confusion_matrix, f1_score, fbeta_score, matthews_corrcoef, precision_score, recall_score, roc_auc_score)

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src')); sys.path.insert(0,str(ROOT/'tools'))
from iteration12_imd_aws import readiness, sha256_file
from skyguard.benchmark import InjectionConfig, inject_partition, split_genuine_observations, verify_no_source_overlap
from skyguard.detection.hybrid import add_causal_features, add_spatial_context, analyze_row
from skyguard.health import sensor_health

FEATURES=[f"{s}_{x}" for s in ("temperature","pressure","humidity") for x in
          ("delta","second_difference","rolling_mad","rolling_iqr","rolling_variance","robust_z","rolling_slope","frozen_run","past_variability","cusum")]
FEATURES += ["hour_sin","hour_cos","day_sin","day_cos","neighbor_count","spatial_coherence_score","spatial_disagreement_score"]
PROMOTION_GATE={"defined_before_test":True,"min_precision":.70,"min_recall":.45,"max_false_alerts_per_station_day":.05,
                "max_unseen_station_f1_regression":.03,"requires_calibrated_confidence":True,"automatic_promotion":False}

def metric_row(name,y,pred,score,frame):
    tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
    days=max(1,frame.assign(day=pd.to_datetime(frame.timestamp_utc,utc=True).dt.floor('D')).groupby(['station_id','day']).ngroups)
    return {"model":name,"precision":precision_score(y,pred,zero_division=0),"recall":recall_score(y,pred,zero_division=0),
            "f1":f1_score(y,pred,zero_division=0),"f2":fbeta_score(y,pred,beta=2,zero_division=0),
            "pr_auc":average_precision_score(y,score),"roc_auc":roc_auc_score(y,score) if len(np.unique(y))>1 else None,
            "specificity":tn/max(1,tn+fp),"balanced_accuracy":balanced_accuracy_score(y,pred),
            "mcc":matthews_corrcoef(y,pred),"false_positive_rate":fp/max(1,fp+tn),"false_negative_rate":fn/max(1,fn+tp),
            "false_alerts_per_station_day":fp/days,"support":len(y)}

def features(frame):
    out=add_spatial_context(add_causal_features(frame))
    for col in FEATURES: out[col]=pd.to_numeric(out.get(col,np.nan),errors='coerce')
    return out

def prepare_X(frame,medians=None):
    x=frame[FEATURES].replace([np.inf,-np.inf],np.nan)
    if medians is None: medians=x.median().fillna(0)
    return x.fillna(medians),medians

def event_metrics(frame,pred):
    d=frame.copy(); d['pred']=pred
    truth=d[d.episode_id.ne('')].groupby('episode_id')
    true_events=len(truth); detected=truth.pred.max().sum() if true_events else 0
    delays=[]
    for _,g in truth:
        hit=g[g.pred.astype(bool)]
        if len(hit): delays.append((pd.Timestamp(hit.timestamp_utc.iloc[0])-pd.Timestamp(g.timestamp_utc.iloc[0])).total_seconds()/60)
    d['pred']=d['pred'].astype(bool)
    pred_runs=int(d.groupby('station_id',sort=False).pred.apply(lambda s:(s & ~s.shift(fill_value=False)).sum()).sum())
    return {"true_events":true_events,"detected_events":int(detected),"event_recall":float(detected/max(1,true_events)),
            "predicted_alert_runs":pred_runs,"event_precision_proxy":float(detected/max(1,pred_runs)),
            "mean_delay_minutes":float(np.mean(delays)) if delays else None,"median_delay_minutes":float(np.median(delays)) if delays else None,
            "p95_delay_minutes":float(np.percentile(delays,95)) if delays else None}

def run(data_path:Path,out:Path,timezone_confirmed:bool):
    out.mkdir(parents=True,exist_ok=True)
    genuine=pd.read_parquet(data_path)
    required={"source","source_is_genuine","source_snapshot_hash","generated_or_simulated"}
    if required-set(genuine): raise ValueError(f"Missing Iteration 12 provenance: {sorted(required-set(genuine))}")
    if not genuine.source.eq('IMD_AUTHORIZED_AWS_API').all() or not genuine.source_is_genuine.astype(bool).all() or genuine.generated_or_simulated.astype(bool).any():
        raise ValueError('Dataset is not exclusively genuine authorized IMD AWS observations')
    _,ready=readiness(genuine,timestamp_timezone_confirmed=timezone_confirmed)
    (out/'DATA_PROVENANCE.json').write_text(json.dumps({**ready,"dataset_sha256":sha256_file(data_path)},indent=2),encoding='utf-8')
    if not ready['ready_for_pilot_training']:
        message='NOT ENOUGH GENUINE TEMPORAL DATA FOR THIS EXPERIMENT'
        (out/'BLOCKED.txt').write_text(message,encoding='utf-8'); print(message); return 2
    parts,split_contract=split_genuine_observations(genuine)
    seeds={"train":1301,"validation":1307,"future_test":1319,"unseen_station_test":1321}
    injected={}; events=[]
    for name,part in parts.items():
        injected[name],ev,_=inject_partition(part,name,InjectionConfig(events_per_type=3,seed=seeds[name]))
        events.append(ev)
    verify_no_source_overlap(injected)
    featured={name:features(frame) for name,frame in injected.items()}
    xtrain,med=prepare_X(featured['train']); ytrain=featured['train'].benchmark_label.to_numpy(int)
    xval,_=prepare_X(featured['validation'],med); yval=featured['validation'].benchmark_label.to_numpy(int)
    iso=IsolationForest(n_estimators=250,contamination='auto',random_state=13,n_jobs=-1).fit(xtrain[ytrain==0])
    iso_val=-iso.score_samples(xval); iso_threshold=float(np.quantile(iso_val[yval==0],.99))
    hgb=HistGradientBoostingClassifier(max_iter=250,max_leaf_nodes=31,l2_regularization=2,random_state=13).fit(xtrain,ytrain)
    raw_val=hgb.predict_proba(xval)[:,1]
    calibrator=LogisticRegression(random_state=13).fit(raw_val.reshape(-1,1),yval)
    rows=[]; event_rows=[]; false_rows=[]; fault_rows=[]; root_rows=[]; correction_rows=[]; health_rows=[]; latency_rows=[]; explanation_rows=[]; negative_controls=[]
    for partition in ('future_test','unseen_station_test'):
        frame=featured[partition]; x,_=prepare_X(frame,med); y=frame.benchmark_label.to_numpy(int)
        records=frame.to_dict('records')
        start_ns=time.perf_counter_ns(); hybrid_decisions=[analyze_row(r) for r in records]; elapsed_ns=time.perf_counter_ns()-start_ns
        decision_latencies=np.full(len(frame),elapsed_ns/max(1,len(frame))/1e6)
        scores={
            'range_qc':(~(frame.temperature_c.between(-60,65)&frame.pressure_hpa.between(850,1100)&frame.relative_humidity_pct.between(0,100))).astype(float).to_numpy(),
            'hampel':np.clip(frame[[f'{s}_robust_z' for s in ('temperature','pressure','humidity')]].abs().max(axis=1).fillna(0).to_numpy()/6,0,1),
            'isolation_forest':-iso.score_samples(x),
            'hist_gradient_boosting':calibrator.predict_proba(hgb.predict_proba(x)[:,1].reshape(-1,1))[:,1],
            'hybrid':np.array([r['anomaly_probability'] for r in hybrid_decisions]),
        }
        thresholds={'range_qc':.5,'hampel':4/6,'isolation_forest':iso_threshold,'hist_gradient_boosting':.5,'hybrid':.5}
        for name,score in scores.items():
            pred=score>=thresholds[name]; row=metric_row(name,y,pred,score,frame); row['partition']=partition; rows.append(row)
            event_rows.append({"partition":partition,"model":name,**event_metrics(frame,pred)})
            if name=='hybrid':
                fp=frame.loc[pred & (y==0),['station_id','timestamp_utc','fault_type','spatial_context_available','spatial_coherence_score']].copy()
                fp['model_score']=score[pred & (y==0)]; fp['reason']='hybrid_false_positive'; false_rows.append(fp)
        for (fault,severity),g in frame[frame.benchmark_label.eq(1)].groupby(['fault_type','fault_severity']):
            idx=g.index.to_numpy(); score=scores['hist_gradient_boosting'][idx]
            fault_rows.append({"partition":partition,"fault_type":fault,"severity":severity,"support":len(g),"recall":float((score>=.5).mean())})
        for index,decision in enumerate(hybrid_decisions):
            if frame.iloc[index].benchmark_label == 1:
                root_rows.append({"partition":partition,"fault_type":frame.iloc[index].fault_type,
                                  "predicted_root_cause":decision['root_cause'],"detected":decision['is_anomaly']})
            if decision['is_anomaly'] and len(explanation_rows)<40:
                explanation_rows.append({"partition":partition,"station_id":frame.iloc[index].station_id,
                                         "timestamp_utc":frame.iloc[index].timestamp_utc,"probability":decision['anomaly_probability'],
                                         "severity":decision['severity'],"root_cause":decision['root_cause'],
                                         "explanation":decision['explanation']})
            if (not frame.iloc[index].injection_applied and decision['possible_genuine_meteorological_event']):
                negative_controls.append({"partition":partition,"station_id":frame.iloc[index].station_id,
                                          "timestamp_utc":frame.iloc[index].timestamp_utc,
                                          "label":"candidate_genuine_event","confirmed_ground_truth":False,
                                          "spatial_coherence_score":frame.iloc[index].spatial_coherence_score,
                                          "fault_probability":decision['anomaly_probability']})
        hgb_score=scores['hist_gradient_boosting']; hgb_pred=hgb_score>=.5
        for sensor,col in (("temperature","temperature_c"),("pressure","pressure_hpa"),("humidity","relative_humidity_pct")):
            mask=hgb_pred & frame.injection_applied.astype(bool).to_numpy() & frame.fault_parameters.str.contains(col,regex=False).to_numpy()
            suggested=pd.to_numeric(frame[f'{sensor}_rolling_median'],errors='coerce').to_numpy()
            truth=pd.to_numeric(frame[f'original_{col}'],errors='coerce').to_numpy()
            valid=mask & np.isfinite(suggested) & np.isfinite(truth)
            error=suggested[valid]-truth[valid]
            correction_rows.append({"partition":partition,"parameter":sensor,"eligible_detected_rows":int(mask.sum()),
                                    "corrected_rows":int(valid.sum()),"coverage":float(valid.sum()/max(1,mask.sum())),
                                    "mae":float(np.mean(np.abs(error))) if len(error) else None,
                                    "rmse":float(np.sqrt(np.mean(error**2))) if len(error) else None,
                                    "method":"causal_prior_rolling_median"})
        for station,g in frame.assign(pred=hgb_pred).groupby('station_id'):
            missing_rate=float(g[['temperature_c','pressure_hpa','relative_humidity_pct']].isna().mean().mean())
            health=sensor_health(history_rows=len(g),short_term_anomaly_rate=float(g.pred.tail(24).mean()),
                                 long_term_anomaly_rate=float(g.pred.mean()),missingness_rate=missing_rate)
            health_rows.append({"partition":partition,"station_id":station,**health})
        latency_rows.append({"partition":partition,"component":"hybrid_decision_on_precomputed_causal_features",
                             "p50_ms":float(np.percentile(decision_latencies,50)),"p95_ms":float(np.percentile(decision_latencies,95)),
                             "p99_ms":float(np.percentile(decision_latencies,99)),"throughput_rows_per_second":float(len(frame)/(elapsed_ns/1e9))})
    pd.DataFrame(rows).to_csv(out/'MODEL_COMPARISON.csv',index=False)
    pd.DataFrame(event_rows).to_csv(out/'EVENT_METRICS.csv',index=False)
    pd.DataFrame(fault_rows).to_csv(out/'FAULT_TYPE_RESULTS.csv',index=False)
    pd.concat(false_rows,ignore_index=True).sort_values('model_score',ascending=False).to_csv(out/'FALSE_POSITIVE_ANALYSIS.csv',index=False)
    pd.concat(events,ignore_index=True).drop(columns=['source_row_ids']).to_csv(out/'INJECTION_EVENTS.csv',index=False)
    pd.DataFrame(root_rows).groupby(['partition','fault_type','predicted_root_cause']).size().rename('rows').reset_index().to_csv(out/'ROOT_CAUSE_CONFUSION.csv',index=False)
    pd.DataFrame(correction_rows).to_csv(out/'CORRECTION_METRICS.csv',index=False)
    pd.DataFrame(health_rows).to_json(out/'SENSOR_HEALTH.json',orient='records',indent=2,default_handler=str)
    pd.DataFrame(latency_rows).to_csv(out/'REALTIME_METRICS.csv',index=False)
    pd.DataFrame(explanation_rows).to_csv(out/'EXPLAINABILITY_EXAMPLES.csv',index=False)
    pd.DataFrame(negative_controls,columns=['partition','station_id','timestamp_utc','label','confirmed_ground_truth','spatial_coherence_score','fault_probability']).to_csv(out/'CANDIDATE_GENUINE_EVENTS.csv',index=False)
    scale_rows=[]; sample_records=featured['future_test'].to_dict('records')
    for station_count in (50,100,500,1000,2500,5000):
        if not sample_records: break
        workload=(sample_records*((station_count+len(sample_records)-1)//len(sample_records)))[:station_count]
        started=time.perf_counter(); [analyze_row(row) for row in workload]; seconds=time.perf_counter()-started
        scale_rows.append({"workload_station_streams":station_count,"workload_type":"synthetic workload scaling",
                           "additional_meteorological_stations_claimed":False,"seconds":seconds,
                           "throughput_decisions_per_second":station_count/max(seconds,1e-9)})
    pd.DataFrame(scale_rows).to_csv(out/'SCALABILITY_METRICS.csv',index=False)
    brier=brier_score_loss(yval,calibrator.predict_proba(raw_val.reshape(-1,1))[:,1])
    manifest={"iteration":13,"git_commit":subprocess.run(['git','rev-parse','HEAD'],capture_output=True,text=True).stdout.strip(),
              "python":sys.version,"platform":platform.platform(),"dataset_sha256":sha256_file(data_path),"split":split_contract,
              "seeds":seeds,"features":FEATURES,"promotion_gate":PROMOTION_GATE,"validation_brier":brier,
              "created_at_utc":pd.Timestamp.now(tz='UTC').isoformat(),"raw_data_modified":False}
    (out/'experiment_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    (out/'promotion_gate.json').write_text(json.dumps(PROMOTION_GATE,indent=2),encoding='utf-8')
    return 0

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--data',type=Path,required=True); p.add_argument('--out',type=Path,required=True)
    p.add_argument('--timezone-confirmed',action='store_true'); args=p.parse_args()
    raise SystemExit(run(args.data,args.out,args.timezone_confirmed))
