"""Build GPU Iteration 9: domain-invariant calibration and multi-seed stress testing."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "notebooks" / "SkyGuard_AI_GPU_Iteration_08_MultiClimate_Data_Curriculum_Colab.ipynb"
OUTPUT = ROOT / "notebooks" / "SkyGuard_AI_GPU_Iteration_09_Domain_Invariant_Calibration_Colab.ipynb"


def md(text: str) -> dict[str, object]:
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text: str) -> dict[str, object]:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.splitlines(keepends=True),
    }


notebook = json.loads(SOURCE.read_text(encoding="utf-8"))
for cell in notebook["cells"]:
    source = "".join(cell.get("source", [])).replace("\ufffd", "-")
    if cell.get("cell_type") == "code":
        cell["execution_count"] = None
        cell["outputs"] = []
        source = source.replace(
            "SEND BACK THESE ITERATION 8 FILES:",
            "HISTORICAL ITERATION 8 CHECKPOINT - continue through Iteration 9:",
        )
    elif cell.get("cell_type") == "markdown":
        source = source.replace(
            "## Iteration 8 stop rule",
            "## Historical Iteration 8 checkpoint - continue to Iteration 9",
        )
    cell["source"] = source.splitlines(keepends=True)

notebook["cells"][0] = md(r"""# SkyGuard AI — GPU Iteration 9

## Domain-invariant calibration and multi-seed confirmation stress test

Iteration 8 delivered a large DWD transfer gain, but it was correctly not promoted: only 8 of 14 gates passed. Confirmation precision, India point F1, India weather-event recognition, worst-climate weather F1 and the fault-to-weather cap still failed. Feature importance also exposed a likely domain shortcut: absolute rolling climate levels and station spacing were among the strongest predictors.

This notebook starts from the frozen Iteration 8 development checkpoint and directly addresses those failures:

1. Remove absolute climate-level and station-spacing shortcuts from a new residual-only LightGBM contract.
2. Preserve physical limit rules separately so extreme observations are still caught.
3. Calibrate full-tree, residual-tree, Isolation Forest and causal LSTM scores with an L2-regularized meta-model that never receives station ID, domain or climate labels.
4. Use a causal per-station score normalization based only on prior observations.
5. Split January–April tune data chronologically into calibration and policy halves.
6. Freeze thresholds before discovery, confirmation and multi-seed stress evaluation.
7. Add two independent DWD 2023 injection seeds; together with the Iteration 8 seed, each family/climate is tested three times without changing anomaly prevalence.
8. Report root-cause macro F1, per-family episode recall, seed confidence intervals and every rejected ablation.

DWD/NOAA 2024 and all 2025 observations or labels remain sealed.
""")

notebook["cells"][1] = md(r"""## Run instructions

1. Keep the two existing bundles in `/content/drive/MyDrive/SkyGuard_AI_GPU/`:
   - `SkyGuard_GPU_Data_Bundle.zip`
   - `SkyGuard_Iteration8_Development_Data_Bundle.zip`
2. Keep the completed Iteration 8 experiment folder in Drive. The notebook reuses its cached features and models.
3. Do **not** upload or extract any locked 2024 bundle and do not add any 2025 file.
4. Select **Runtime → Change runtime type → T4 GPU**.
5. Leave `UNLOCK_FINAL_TESTS=False`, `REUSE_SAVED_MODELS=True` and `RUN_ITER9_STRESS=True`.
6. Run all cells in order. First execution is expected to take roughly 90–240 minutes. Each stress seed is cached, so a disconnected runtime can safely restart and reuse completed work.
7. Return the Iteration 9 JSON/CSV files printed by the final cell. Do not open a locked test unless every promotion gate passes and Codex audits the outputs first.
""")

notebook["cells"].extend([
    md(r"""# Iteration 9 controlled development phase

The accepted Iteration 5 deployment and the non-promoted Iteration 8 challenger remain immutable. This section uses only the already-approved 2022 training observations and 2023 development observations.
"""),
    code(r"""from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report,confusion_matrix
from sklearn.preprocessing import StandardScaler

ITER9_ROOT=DRIVE_ROOT/'experiments'/'iteration_09_domain_invariant_calibration'
ITER9_ROOT.mkdir(parents=True,exist_ok=True)
I9_BASE_RESULT_PATH=ITER8_ROOT/'iteration8_result_block.json'
assert I9_BASE_RESULT_PATH.exists(),'Run the Iteration 8 cells first or restore its Drive checkpoint.'
i9_base_result=json.loads(I9_BASE_RESULT_PATH.read_text())
assert i9_base_result['new_data']['locked_2024_opened'] is False
assert i9_base_result['new_data']['any_2025_opened'] is False
assert UNLOCK_FINAL_TESTS is False

RUN_ITER9_STRESS=True
I9_BASE_STRESS_SEED=8023
I9_NEW_STRESS_SEEDS=[9029,9049]
I9_ALL_STRESS_SEEDS=[I9_BASE_STRESS_SEED]+I9_NEW_STRESS_SEEDS
I9_MIN_PRECISION=.80
I9_MAX_FALSE_ALARM=.02
I9_MAX_FAULT_TO_WEATHER=.01

print({
    'iteration8_status':i9_base_result['status'],
    'iteration8_passed_gates':sum(bool(value) for value in i9_base_result['promotion_gates'].values()),
    'iteration8_total_gates':len(i9_base_result['promotion_gates']),
    'iteration9_root':str(ITER9_ROOT),
    'stress_seeds':I9_ALL_STRESS_SEEDS,
    'locked_2024_opened':False,
    'any_2025_opened':False,
})
"""),
    md(r"""## 42. Freeze a domain-invariant residual feature contract

The new ML challenger is not allowed to use absolute temperature/pressure/humidity levels, station spacing, absolute rolling climate levels, absolute neighbour means or station/domain labels. Those fields were useful in-domain but can encode geography and caused brittle cross-climate transfer. Physical range checks remain separate deterministic safety rules.
"""),
    code(r"""I9_EXCLUDED_SHORTCUT_FEATURES={
    'temperature_value','pressure_value','humidity_value',
    'temperature_humidity_interaction','pressure_temperature_ratio',
    'nearest_neighbor_km',
}
for sensor in ['temperature','pressure','humidity']:
    I9_EXCLUDED_SHORTCUT_FEATURES.update({
        f'{sensor}_lag1',f'{sensor}_rolling_median_24h',f'{sensor}_ewma_prior',
        f'neighbor_{sensor}_weighted_mean',f'neighbor_{sensor}_median',
    })

I9_RESIDUAL_FEATURES=[feature for feature in FEATURES if feature not in I9_EXCLUDED_SHORTCUT_FEATURES]
assert len(I9_RESIDUAL_FEATURES)>=80
assert not (I9_EXCLUDED_SHORTCUT_FEATURES&set(I9_RESIDUAL_FEATURES))
assert not ({'station_id','i8_domain','cluster','latitude','longitude','elevation_m'}&set(I9_RESIDUAL_FEATURES))
assert {'temperature_slope_3h','temperature_slope_6h','temperature_slope_12h',
        'pressure_cusum_positive','humidity_cusum_negative',
        'regional_agreement_mean','regional_trend_disagreement_mean'}<=set(I9_RESIDUAL_FEATURES)

i9_contract_rows=[]
for feature in FEATURES:
    i9_contract_rows.append({
        'feature':feature,
        'residual_model_allowed':feature in I9_RESIDUAL_FEATURES,
        'exclusion_reason':'absolute climate/domain shortcut' if feature in I9_EXCLUDED_SHORTCUT_FEATURES else '',
    })
i9_feature_ablation=pd.DataFrame(i9_contract_rows)
i9_feature_ablation.to_csv(ITER9_ROOT/'iteration9_feature_ablation_contract.csv',index=False)
print({'full_feature_count':len(FEATURES),'residual_feature_count':len(I9_RESIDUAL_FEATURES),
       'excluded_shortcuts':len(I9_EXCLUDED_SHORTCUT_FEATURES)})
display(i9_feature_ablation.loc[~i9_feature_ablation.residual_model_allowed])
"""),
    md(r"""## 43. Chronological calibration/policy split

The first half of each domain's January–April tune window is used for early stopping and L2 calibration. The later half is used once for threshold selection. Pseudo-unseen DWD stations are excluded from both halves.
"""),
    code(r"""def i9_non_holdout_tune(frame):
    mask=frame.i8_scope.eq('tune')
    mask&=~(frame.i8_domain.eq('dwd')&frame.station_id.isin(I8_DWD_HOLDOUTS))
    return frame.loc[mask].copy()

def i9_assign_tune_stage(frame):
    result=frame.copy(); result['i9_tune_stage']=''
    for domain,indices in result.groupby('i8_domain',sort=True).groups.items():
        timestamps=pd.to_datetime(result.loc[indices,'emitted_timestamp_utc'],utc=True)
        cutoff=timestamps.quantile(.50)
        result.loc[indices,'i9_tune_stage']=np.where(timestamps.le(cutoff),'calibration','policy')
    return result

i9_tune=i9_assign_tune_stage(i9_non_holdout_tune(i8_validation))
i9_early=i9_tune.loc[i9_tune.i9_tune_stage.eq('calibration')].copy()
i9_policy=i9_tune.loc[i9_tune.i9_tune_stage.eq('policy')].copy()
assert set(i9_tune.i9_tune_stage)=={'calibration','policy'}
assert not (i9_tune.i8_domain.eq('dwd')&i9_tune.station_id.isin(I8_DWD_HOLDOUTS)).any()
assert i9_early.is_anomaly.sum()>0 and i9_policy.is_anomaly.sum()>0
assert i9_early.is_weather_event.sum()>0 and i9_policy.is_weather_event.sum()>0
display(i9_tune.groupby(['i8_domain','i9_tune_stage'])[['is_anomaly','is_weather_event']].agg(['size','sum']))
"""),
    md(r"""## 44. Train residual-only, domain-balanced LightGBM models

Three regularized seeds are trained for fault and genuine-weather targets. The training weights equalize India/DWD contribution and episode mass. No station ID, domain label or excluded shortcut reaches these models.
"""),
    code(r"""I9_LGB_SEEDS=[17,41,67]
i9_models={}; i9_model_history=[]
i9_early_features=i8_enforce_numeric_features(i9_early.copy(),'Iteration 9 early-stop table')

for target in ['fault','weather']:
    y_fit=i8_target(i8_fit,target); y_early=i8_target(i9_early_features,target)
    weights=i8_domain_episode_weights(i8_fit,y_fit)
    models=[]
    for seed in I9_LGB_SEEDS:
        path=ITER9_ROOT/f'iteration9_{target}_residual_lightgbm_seed{seed}.joblib'
        if REUSE_SAVED_MODELS and path.exists():
            model=joblib.load(path)
        else:
            model=LGBMClassifier(
                objective='binary',n_estimators=2400,learning_rate=.018,num_leaves=31,
                min_child_samples=90,subsample=.85,colsample_bytree=.82,
                reg_alpha=2.0,reg_lambda=20.0,random_state=seed,n_jobs=-1,
                verbosity=-1,force_col_wise=True)
            model.fit(
                i8_fit[I9_RESIDUAL_FEATURES],y_fit,sample_weight=weights,
                eval_set=[(i9_early_features[I9_RESIDUAL_FEATURES],y_early)],
                eval_metric='average_precision',
                callbacks=[early_stopping(180,verbose=False),log_evaluation(0)])
            joblib.dump(model,path,compress=3)
        models.append(model)
        i9_model_history.append({
            'target':target,'seed':seed,'features':len(I9_RESIDUAL_FEATURES),
            'fit_rows':len(i8_fit),'fit_positives':int(y_fit.sum()),
            'early_rows':len(i9_early_features),'early_positives':int(y_early.sum()),
            'best_iteration':int(getattr(model,'best_iteration_',0)),
        })
    i9_models[target]=models

pd.DataFrame(i9_model_history).to_csv(ITER9_ROOT/'iteration9_model_training_history.csv',index=False)
display(pd.DataFrame(i9_model_history))
"""),
    md(r"""## 45. Causal per-station normalization

Each residual score is converted to a robust z-like value relative to that station's previous 30 days. The current/future value never enters its own baseline. New stations fall back to a training-only global median and IQR.
"""),
    code(r"""def i9_logit_probability(values):
    clipped=np.clip(np.asarray(values,dtype=float),1e-6,1-1e-6)
    return np.log(clipped/(1-clipped))

def i9_add_residual_scores(frame):
    frame=i8_enforce_numeric_features(frame,'Iteration 9 residual scoring table')
    X=frame[I9_RESIDUAL_FEATURES]
    for target,models in i9_models.items():
        probabilities=np.mean([model.predict_proba(X)[:,1] for model in models],axis=0)
        frame[f'i9_{target}_residual_score']=np.clip(probabilities,0,1).astype(np.float32)
    return frame

i9_fit_reference=i9_add_residual_scores(i8_fit.copy())
I9_SCORE_REFERENCE={}
for target in ['fault','weather']:
    score=f'i9_{target}_residual_score'
    if target=='fault': clean=i9_fit_reference.is_anomaly.eq(0)
    else: clean=i9_fit_reference.is_anomaly.eq(0)&i9_fit_reference.is_weather_event.eq(0)
    values=i9_logit_probability(i9_fit_reference.loc[clean,score])
    median=float(np.nanmedian(values)); q25,q75=np.nanpercentile(values,[25,75])
    scale=float(max((q75-q25)/1.349,1e-3))
    I9_SCORE_REFERENCE[target]={'median':median,'scale':scale}

def i9_causal_station_z(frame,score_col,reference,window=720,min_periods=72):
    result=pd.Series(np.nan,index=frame.index,dtype=float)
    for _,group in frame.groupby('station_id',sort=False):
        ordered=group.sort_values('emitted_timestamp_utc',kind='stable')
        logits=pd.Series(i9_logit_probability(ordered[score_col]),index=ordered.index)
        past=logits.shift(1)
        rolling=past.rolling(window=window,min_periods=min_periods)
        median=rolling.median(); q25=rolling.quantile(.25); q75=rolling.quantile(.75)
        scale=((q75-q25)/1.349).clip(lower=1e-3)
        z=(logits-median)/scale
        fallback=(logits-reference['median'])/reference['scale']
        result.loc[ordered.index]=z.where(z.notna(),fallback).clip(-12,12)
    return result.astype(np.float32)

i8_validation=i9_add_residual_scores(i8_validation)
for target in ['fault','weather']:
    i8_validation[f'i9_{target}_residual_z']=i9_causal_station_z(
        i8_validation,f'i9_{target}_residual_score',I9_SCORE_REFERENCE[target])

display(i8_validation.groupby(['i8_domain','i8_scope'])[
    ['i9_fault_residual_score','i9_fault_residual_z','i9_weather_residual_score','i9_weather_residual_z']
].quantile(.99))
del i9_fit_reference
"""),
    md(r"""## 46. L2-regularized incident score calibration

The calibrators receive model scores and normalized temporal/spatial consistency signals only. They cannot see domain, station, coordinates, climate cluster or labels at inference. This is calibrated fusion, not max-score inflation.
"""),
    code(r"""I9_FAULT_META_FEATURES=[
    'i8_fault_score','i9_fault_residual_score','i8_if_score','i8_lstm_ae_score',
    'i9_fault_residual_z','regional_standardized_disagreement_max',
    'regional_trend_disagreement_mean','regional_agreement_mean',
]
I9_WEATHER_META_FEATURES=[
    'i8_weather_score','i9_weather_residual_score','i9_weather_residual_z',
    'regional_agreement_mean','regional_agreement_min','regional_agreeing_sensor_count',
    'regional_standardized_disagreement_max','regional_trend_disagreement_mean',
    'i9_fault_residual_score',
]
assert not ({'i8_domain','station_id','cluster','latitude','longitude','nearest_neighbor_km'}&
            set(I9_FAULT_META_FEATURES+I9_WEATHER_META_FEATURES))

def i9_fit_calibrator(frame,features,target):
    X=frame[features].apply(pd.to_numeric,errors='coerce').replace([np.inf,-np.inf],np.nan)
    medians=X.median().fillna(0.0)
    X=X.fillna(medians).to_numpy(np.float64)
    scaler=StandardScaler().fit(X)
    y=i8_target(frame,target)
    weights=i8_domain_episode_weights(frame,y)
    model=LogisticRegression(
        penalty='l2',C=.35,solver='lbfgs',max_iter=2000,random_state=9101)
    model.fit(scaler.transform(X),y,sample_weight=weights)
    return {'features':features,'medians':medians.to_dict(),'scaler':scaler,'model':model}

def i9_calibrated_score(frame,package):
    features=package['features']
    X=frame[features].apply(pd.to_numeric,errors='coerce').replace([np.inf,-np.inf],np.nan)
    X=X.fillna(pd.Series(package['medians'])).to_numpy(np.float64)
    return package['model'].predict_proba(package['scaler'].transform(X))[:,1].astype(np.float32)

i9_calibration=i9_assign_tune_stage(i9_non_holdout_tune(i8_validation))
i9_calibration=i9_calibration.loc[i9_calibration.i9_tune_stage.eq('calibration')].copy()
i9_calibrators={
    'fault':i9_fit_calibrator(i9_calibration,I9_FAULT_META_FEATURES,'fault'),
    'weather':i9_fit_calibrator(i9_calibration,I9_WEATHER_META_FEATURES,'weather'),
}
joblib.dump(i9_calibrators,ITER9_ROOT/'iteration9_l2_calibrators.joblib',compress=3)

def i9_add_calibrated_scores(frame):
    frame['i9_fault_stack_score']=i9_calibrated_score(frame,i9_calibrators['fault'])
    frame['i9_weather_stack_score']=i9_calibrated_score(frame,i9_calibrators['weather'])
    frame['i9_fault_consensus_score']=np.sqrt(
        np.clip(frame.i8_fault_score,0,1)*np.clip(frame.i9_fault_residual_score,0,1)).astype(np.float32)
    frame['i9_weather_consensus_score']=np.sqrt(
        np.clip(frame.i8_weather_score,0,1)*np.clip(frame.i9_weather_residual_score,0,1)).astype(np.float32)
    return frame

i8_validation=i9_add_calibrated_scores(i8_validation)
i9_coefficients=[]
for target,package in i9_calibrators.items():
    for feature,coefficient in zip(package['features'],package['model'].coef_[0]):
        i9_coefficients.append({'target':target,'feature':feature,'coefficient':float(coefficient)})
i9_coefficients=pd.DataFrame(i9_coefficients)
i9_coefficients.to_csv(ITER9_ROOT/'iteration9_calibrator_coefficients.csv',index=False)
display(i9_coefficients.sort_values(['target','coefficient'],ascending=[True,False]))
"""),
    md(r"""## 47. Freeze weather and fault policies on the policy half only

All variants are retained in the frontier. Selection requires minimum precision and false-alarm constraints in both India and DWD; no discovery or confirmation row is searched.
"""),
    code(r"""I9_WEATHER_VARIANTS={
    'residual_only':'i9_weather_residual_score',
    'full_residual_consensus':'i9_weather_consensus_score',
    'l2_calibrated_stack':'i9_weather_stack_score',
}
I9_FAULT_VARIANTS={
    'residual_only':'i9_fault_residual_score',
    'full_residual_consensus':'i9_fault_consensus_score',
    'l2_calibrated_stack':'i9_fault_stack_score',
}

def i9_weather_prediction(frame,score_col,threshold):
    agreement=pd.to_numeric(frame.regional_agreement_mean,errors='coerce').fillna(0)
    agreeing=pd.to_numeric(frame.regional_agreeing_sensor_count,errors='coerce').fillna(0)
    hard=frame.hard_rule.astype(bool) if 'hard_rule' in frame else pd.Series(False,index=frame.index)
    return frame[score_col].ge(float(threshold))&agreement.ge(.50)&agreeing.ge(1)&~hard

def i9_weather_metrics(frame,pred,score_col):
    y=frame.is_weather_event.astype(int)
    return {
        'precision':float(precision_score(y,pred,zero_division=0)),
        'recall':float(recall_score(y,pred,zero_division=0)),
        'f1':float(f1_score(y,pred,zero_division=0)),
        'auprc':float(average_precision_score(y,frame[score_col])) if y.sum()>0 else float('nan'),
        'weather_event_rows':int(y.sum()),
        'weather_event_episodes':int(frame.loc[y.eq(1),'episode_id'].replace('',np.nan).nunique()),
        'fault_to_weather_rate':float(pred.loc[frame.is_anomaly.eq(1)].mean()) if frame.is_anomaly.eq(1).any() else 0.0,
    }

i9_policy=i9_assign_tune_stage(i9_non_holdout_tune(i8_validation))
i9_policy=i9_policy.loc[i9_policy.i9_tune_stage.eq('policy')].copy()
i9_weather_frontier=[]
for variant,score_col in I9_WEATHER_VARIANTS.items():
  for threshold in np.linspace(.03,.97,48):
    rows=[]
    for domain in ['india','dwd']:
        part=i9_policy.loc[i9_policy.i8_domain.eq(domain)].copy()
        pred=i9_weather_prediction(part,score_col,threshold)
        rows.append({'domain':domain,**i9_weather_metrics(part,pred,score_col)})
    i9_weather_frontier.append({
        'variant':variant,'score_col':score_col,'threshold':float(threshold),
        'min_precision':min(row['precision'] for row in rows),
        'min_f1':min(row['f1'] for row in rows),
        'mean_f1':float(np.mean([row['f1'] for row in rows])),
        'max_fault_to_weather':max(row['fault_to_weather_rate'] for row in rows),
    })
i9_weather_frontier=pd.DataFrame(i9_weather_frontier)
i9_weather_feasible=i9_weather_frontier.loc[
    i9_weather_frontier.min_precision.ge(I9_MIN_PRECISION)&
    i9_weather_frontier.max_fault_to_weather.le(I9_MAX_FAULT_TO_WEATHER)]
if len(i9_weather_feasible):
    i9_weather_selected=i9_weather_feasible.sort_values(
        ['min_f1','mean_f1','min_precision'],ascending=False).iloc[0]
    I9_WEATHER_TUNE_STATUS='constraints_met'
else:
    i9_weather_frontier['violation']=np.maximum(0,I9_MIN_PRECISION-i9_weather_frontier.min_precision)+10*np.maximum(
        0,i9_weather_frontier.max_fault_to_weather-I9_MAX_FAULT_TO_WEATHER)
    i9_weather_selected=i9_weather_frontier.sort_values(
        ['violation','min_f1','mean_f1'],ascending=[True,False,False]).iloc[0]
    I9_WEATHER_TUNE_STATUS='pareto_fallback_not_promotable'
I9_WEATHER_VARIANT=str(i9_weather_selected.variant)
I9_WEATHER_SCORE_COL=str(i9_weather_selected.score_col)
I9_WEATHER_THRESHOLD=float(i9_weather_selected.threshold)
i9_weather_frontier.to_csv(ITER9_ROOT/'iteration9_weather_policy_frontier.csv',index=False)
display(i9_weather_selected.to_frame('selected_weather'))
"""),
    code(r"""def i9_fault_prediction(frame,score_col,threshold):
    raw=hysteresis(frame,score_col,float(threshold),max(.01,float(threshold)-.06))
    weather=i9_weather_prediction(frame,I9_WEATHER_SCORE_COL,I9_WEATHER_THRESHOLD)
    disagreement=pd.to_numeric(frame.regional_standardized_disagreement_max,errors='coerce').fillna(0)
    override=frame[score_col].ge(min(.995,float(threshold)+.16))&disagreement.ge(2.5)
    return (raw&(~weather|override))|frame.hard_rule.astype(bool)

i9_fault_frontier=[]
for variant,score_col in I9_FAULT_VARIANTS.items():
  for threshold in np.linspace(.08,.97,46):
    rows=[]
    for domain in ['india','dwd']:
        part=i9_policy.loc[i9_policy.i8_domain.eq(domain)].copy()
        part['candidate']=i9_fault_prediction(part,score_col,threshold)
        metric=evaluate(part,score_col,'candidate')
        rows.append({'domain':domain,**metric})
    i9_fault_frontier.append({
        'variant':variant,'score_col':score_col,'threshold':float(threshold),
        'min_precision':min(row['precision'] for row in rows),
        'max_false_alarm':max(row['false_alarm_episodes_per_station_day'] for row in rows),
        'min_point_f1':min(row['f1'] for row in rows),
        'mean_point_f1':float(np.mean([row['f1'] for row in rows])),
        'min_event_f1':min(row['event_f1'] for row in rows),
        'mean_event_f1':float(np.mean([row['event_f1'] for row in rows])),
        'min_event_recall':min(row['event_recall'] for row in rows),
    })
i9_fault_frontier=pd.DataFrame(i9_fault_frontier)
i9_fault_feasible=i9_fault_frontier.loc[
    i9_fault_frontier.min_precision.ge(.82)&i9_fault_frontier.max_false_alarm.le(I9_MAX_FALSE_ALARM)]
if len(i9_fault_feasible):
    i9_fault_selected=i9_fault_feasible.sort_values(
        ['min_event_recall','min_event_f1','mean_point_f1'],ascending=False).iloc[0]
    I9_FAULT_TUNE_STATUS='constraints_met'
else:
    i9_fault_frontier['violation']=np.maximum(0,.82-i9_fault_frontier.min_precision)+10*np.maximum(
        0,i9_fault_frontier.max_false_alarm-I9_MAX_FALSE_ALARM)
    i9_fault_selected=i9_fault_frontier.sort_values(
        ['violation','min_event_recall','mean_event_f1'],ascending=[True,False,False]).iloc[0]
    I9_FAULT_TUNE_STATUS='pareto_fallback_not_promotable'
I9_FAULT_VARIANT=str(i9_fault_selected.variant)
I9_FAULT_SCORE_COL=str(i9_fault_selected.score_col)
I9_FAULT_THRESHOLD=float(i9_fault_selected.threshold)
i9_fault_frontier.to_csv(ITER9_ROOT/'iteration9_fault_policy_frontier.csv',index=False)
display(i9_fault_selected.to_frame('selected_fault'))
"""),
    md(r"""## 48. Main India/DWD confirmation ablation

Iteration 9 is compared with both the deployed Iteration 5 reference and the rejected Iteration 8 challenger. Promotion cannot hide a regression behind an aggregate average.
"""),
    code(r"""def i9_metric_bundle(frame,pred,score_col):
    part=frame.copy(); part['candidate']=np.asarray(pred,bool)
    return evaluate(part,score_col,'candidate')

def i9_weak_mean(metric):
    values=[metric['per_fault_episode_recall'].get(name,np.nan) for name in ['bias','drift','frozen_sensor']]
    values=[value for value in values if not pd.isna(value)]
    return float(np.mean(values)) if values else float('nan')

i9_main_rows=[]; i9_family_rows=[]; i9_weather_cluster_rows=[]
for scope in ['discovery','confirmation']:
  domain_masks={
      'india':i8_validation.i8_domain.eq('india'),
      'dwd_all':i8_validation.i8_domain.eq('dwd'),
      'dwd_holdout':i8_validation.i8_domain.eq('dwd')&i8_validation.station_id.isin(I8_DWD_HOLDOUTS),
  }
  for domain,domain_mask in domain_masks.items():
    part=i8_validation.loc[i8_validation.i8_scope.eq(scope)&domain_mask].copy()
    i5_pred=part.i8_baseline_pred.astype(bool)
    i8_pred=i8_candidate_fault_prediction(part,I8_FAULT_SCORE_COL,I8_FAULT_THRESHOLD)
    i9_pred=i9_fault_prediction(part,I9_FAULT_SCORE_COL,I9_FAULT_THRESHOLD)
    i5=i9_metric_bundle(part,i5_pred,'base_score')
    i8m=i9_metric_bundle(part,i8_pred,I8_FAULT_SCORE_COL)
    i9m=i9_metric_bundle(part,i9_pred,I9_FAULT_SCORE_COL)
    i8_weather=i8_weather_metrics(part,i8_weather_prediction(part,I8_WEATHER_THRESHOLD))
    i9_weather=i9_weather_metrics(
        part,i9_weather_prediction(part,I9_WEATHER_SCORE_COL,I9_WEATHER_THRESHOLD),I9_WEATHER_SCORE_COL)
    i9_main_rows.append({
        'scope':scope,'domain':domain,'rows':len(part),
        'iteration5_precision':i5['precision'],'iteration8_precision':i8m['precision'],'iteration9_precision':i9m['precision'],
        'iteration5_point_f1':i5['f1'],'iteration8_point_f1':i8m['f1'],'iteration9_point_f1':i9m['f1'],
        'point_f1_delta_vs_i8':i9m['f1']-i8m['f1'],
        'iteration5_event_f1':i5['event_f1'],'iteration8_event_f1':i8m['event_f1'],'iteration9_event_f1':i9m['event_f1'],
        'event_f1_delta_vs_i8':i9m['event_f1']-i8m['event_f1'],
        'iteration8_weak_recall':i9_weak_mean(i8m),'iteration9_weak_recall':i9_weak_mean(i9m),
        'weak_recall_delta_vs_i8':i9_weak_mean(i9m)-i9_weak_mean(i8m),
        'iteration9_false_alarm':i9m['false_alarm_episodes_per_station_day'],
        'iteration8_weather_f1':i8_weather['f1'],'iteration9_weather_f1':i9_weather['f1'],
        'iteration9_fault_to_weather':i9_weather['fault_to_weather_rate'],
    })
    for family,group in part.loc[part.is_anomaly.eq(1)&part.episode_id.ne('')].groupby('anomaly_type'):
        episode_ids=group.episode_id.unique()
        i8_hits=[]; i9_hits=[]
        for episode_id in episode_ids:
            event=part.episode_id.eq(episode_id)
            i8_hits.append(bool(i8_pred.loc[event].any()))
            i9_hits.append(bool(i9_pred.loc[event].any()))
        i9_family_rows.append({
            'scope':scope,'domain':domain,'anomaly_type':family,'episodes':len(episode_ids),
            'iteration8_episode_recall':float(np.mean(i8_hits)),
            'iteration9_episode_recall':float(np.mean(i9_hits)),
        })
    for cluster,group in part.groupby('cluster'):
        weather=i9_weather_metrics(
            group,i9_weather_prediction(group,I9_WEATHER_SCORE_COL,I9_WEATHER_THRESHOLD),I9_WEATHER_SCORE_COL)
        i9_weather_cluster_rows.append({'scope':scope,'domain':domain,'cluster':cluster,**weather})

i9_main=pd.DataFrame(i9_main_rows)
i9_family=pd.DataFrame(i9_family_rows)
i9_weather_clusters=pd.DataFrame(i9_weather_cluster_rows)
i9_main.to_csv(ITER9_ROOT/'iteration9_multidomain_confirmation.csv',index=False)
i9_family.to_csv(ITER9_ROOT/'iteration9_fault_episode_recall.csv',index=False)
i9_weather_clusters.to_csv(ITER9_ROOT/'iteration9_weather_by_cluster.csv',index=False)
display(i9_main); display(i9_family); display(i9_weather_clusters)
"""),
    md(r"""## 49. Residual-only root-cause diagnosis

The diagnosis model uses the same shortcut-free contract. We report macro F1 and per-family recall, not only row accuracy on the easiest detected incidents.
"""),
    code(r"""from sklearn.metrics import accuracy_score

I9_ROOT_MODEL_PATH=ITER9_ROOT/'iteration9_residual_root_cause_catboost.cbm'
i9_root_train=i8_fit.loc[i8_fit.is_anomaly.eq(1)].copy()

def i9_root_episode_class_weights(frame):
    keys=frame.episode_id.fillna('').astype(str)
    keys=keys.where(keys.ne(''),'single_'+frame.row_id.astype(str))
    lengths=keys.value_counts()
    weights=keys.map(lambda key:1.0/max(lengths.loc[key],1)).to_numpy(float)
    labels=frame.anomaly_type.astype(str)
    for _,indices in labels.groupby(labels,sort=True).groups.items():
        positions=frame.index.get_indexer(indices)
        positions=positions[positions>=0]
        weights[positions]*=len(frame)/(labels.nunique()*max(weights[positions].sum(),1e-12))
    for _,indices in frame.groupby('i8_domain',sort=True).groups.items():
        positions=frame.index.get_indexer(indices)
        positions=positions[positions>=0]
        weights[positions]*=len(frame)/(frame.i8_domain.nunique()*max(weights[positions].sum(),1e-12))
    return weights/np.mean(weights)

i9_root_weights=i9_root_episode_class_weights(i9_root_train)
i9_root_model=CatBoostClassifier(
    iterations=1200,depth=7,learning_rate=.035,loss_function='MultiClass',
    eval_metric='TotalF1',l2_leaf_reg=16,random_seed=91,task_type='GPU',devices='0',
    verbose=150,allow_writing_files=False)
if REUSE_SAVED_MODELS and I9_ROOT_MODEL_PATH.exists():
    i9_root_model.load_model(I9_ROOT_MODEL_PATH)
else:
    i9_root_model.fit(i9_root_train[I9_RESIDUAL_FEATURES],i9_root_train.anomaly_type.astype(str),
                      sample_weight=i9_root_weights)
    i9_root_model.save_model(I9_ROOT_MODEL_PATH)

i9_root_rows=[]; i9_root_class_rows=[]
for domain in ['india','dwd']:
    part=i8_validation.loc[i8_validation.i8_scope.eq('confirmation')&i8_validation.i8_domain.eq(domain)].copy()
    detected=i9_fault_prediction(part,I9_FAULT_SCORE_COL,I9_FAULT_THRESHOLD)
    for evaluation_slice,mask in {
        'all_fault_rows':part.is_anomaly.eq(1),
        'detected_fault_rows':part.is_anomaly.eq(1)&detected,
    }.items():
        sample=part.loc[mask].copy()
        if not len(sample): continue
        truth=sample.anomaly_type.astype(str).to_numpy()
        prediction=np.asarray(i9_root_model.predict(sample[I9_RESIDUAL_FEATURES])).reshape(-1).astype(str)
        i9_root_rows.append({
            'domain':domain,'slice':evaluation_slice,'rows':len(sample),
            'accuracy':float(accuracy_score(truth,prediction)),
            'macro_f1':float(f1_score(truth,prediction,average='macro',zero_division=0)),
        })
        report=classification_report(truth,prediction,output_dict=True,zero_division=0)
        for label,values in report.items():
            if isinstance(values,dict) and label not in {'accuracy','macro avg','weighted avg'}:
                i9_root_class_rows.append({
                    'domain':domain,'slice':evaluation_slice,'anomaly_type':label,
                    'precision':values['precision'],'recall':values['recall'],'f1':values['f1-score'],
                    'support':values['support'],
                })

i9_root_metrics=pd.DataFrame(i9_root_rows)
i9_root_classes=pd.DataFrame(i9_root_class_rows)
i9_root_metrics.to_csv(ITER9_ROOT/'iteration9_root_cause_metrics.csv',index=False)
i9_root_classes.to_csv(ITER9_ROOT/'iteration9_root_cause_per_class.csv',index=False)
display(i9_root_metrics); display(i9_root_classes)
"""),
    md(r"""## 50. Three-seed DWD confirmation stress test

The original 8023 validation seed is joined by two new independent seeds. Each replica keeps the same event prevalence and the same chronological scopes; thresholds and calibrators remain frozen. Feature tables are cached one seed at a time.
"""),
    code(r"""def i9_prepare_scored_frame(frame):
    frame=i8_enforce_numeric_features(frame,'Iteration 9 stress feature table')
    frame['station_id']=frame.station_id.astype(str)
    frame['emitted_timestamp_utc']=pd.to_datetime(frame.emitted_timestamp_utc,utc=True)
    frame['episode_id']=frame.episode_id.fillna('').astype(str)
    frame['available_to_detector']=pd.to_numeric(frame.available_to_detector).fillna(0).astype(int)
    frame['i8_domain']='dwd'
    frame['i8_scope']=np.select(
        [frame.emitted_timestamp_utc<'2023-05-01',frame.emitted_timestamp_utc<'2023-09-01'],
        ['tune','discovery'],default='confirmation')
    frame=i8_old_scores(frame)
    frame=i8_add_candidate_scores(frame)
    frame['i8_if_score']=i8_isolation_scores(frame)
    frame['i8_lstm_ae_score']=i8_lstm_scores(frame)
    frame['i8_tree_if_score']=np.maximum(
        frame.i8_fault_score,np.sqrt(frame.i8_fault_score*frame.i8_if_score))
    frame['i8_tree_lstm_score']=np.maximum(
        frame.i8_fault_score,np.sqrt(frame.i8_fault_score*frame.i8_lstm_ae_score))
    frame['i8_three_model_score']=np.maximum(
        frame.i8_fault_score,np.cbrt(frame.i8_fault_score*frame.i8_if_score*frame.i8_lstm_ae_score))
    frame=i9_add_residual_scores(frame)
    for target in ['fault','weather']:
        frame[f'i9_{target}_residual_z']=i9_causal_station_z(
            frame,f'i9_{target}_residual_score',I9_SCORE_REFERENCE[target])
    frame['hard_rule']=add_hard_rules(frame).hard_rule.to_numpy(bool)
    return i9_add_calibrated_scores(frame)

def i9_build_stress_seed(seed):
    cache=ITER9_ROOT/f'iteration9_dwd_stress_seed{seed}_features.csv.gz'
    if REUSE_SAVED_MODELS and cache.exists():
        frame=pd.read_csv(cache,low_memory=False)
        print('Reused stress cache',seed)
    else:
        raw=load_dwd(2023)
        curriculum=MultiClimateCurriculum(raw,f'i9_stress_seed{seed}',seed=int(seed))
        curriculum.build_validation(i8_validation_scopes)
        audit=curriculum.validate()
        assert audit['status']=='PASS' and audit['weather_events']==72 and audit['fault_events']==60
        base=i8_base_features(curriculum.frame,f'Iteration 9 stress seed {seed}')
        frame=add_phase10_features(base,i8_profiles)
        frame.to_csv(cache,index=False,compression={'method':'gzip','compresslevel':6})
        del raw,curriculum,base
    return i9_prepare_scored_frame(frame)

def i9_summarize_seed(frame,seed):
    summary=[]; family=[]; clusters=[]
    for scope in ['discovery','confirmation']:
      for domain,mask in {
          'dwd_all':pd.Series(True,index=frame.index),
          'dwd_holdout':frame.station_id.isin(I8_DWD_HOLDOUTS),
      }.items():
        part=frame.loc[frame.i8_scope.eq(scope)&mask].copy()
        i8_pred=i8_candidate_fault_prediction(part,I8_FAULT_SCORE_COL,I8_FAULT_THRESHOLD)
        i9_pred=i9_fault_prediction(part,I9_FAULT_SCORE_COL,I9_FAULT_THRESHOLD)
        i8m=i9_metric_bundle(part,i8_pred,I8_FAULT_SCORE_COL)
        i9m=i9_metric_bundle(part,i9_pred,I9_FAULT_SCORE_COL)
        weather=i9_weather_metrics(
            part,i9_weather_prediction(part,I9_WEATHER_SCORE_COL,I9_WEATHER_THRESHOLD),I9_WEATHER_SCORE_COL)
        summary.append({
            'seed':seed,'scope':scope,'domain':domain,'rows':len(part),
            'iteration8_precision':i8m['precision'],'iteration9_precision':i9m['precision'],
            'iteration8_point_f1':i8m['f1'],'iteration9_point_f1':i9m['f1'],
            'point_f1_delta_vs_i8':i9m['f1']-i8m['f1'],
            'iteration8_event_f1':i8m['event_f1'],'iteration9_event_f1':i9m['event_f1'],
            'event_f1_delta_vs_i8':i9m['event_f1']-i8m['event_f1'],
            'iteration8_weak_recall':i9_weak_mean(i8m),'iteration9_weak_recall':i9_weak_mean(i9m),
            'iteration9_false_alarm':i9m['false_alarm_episodes_per_station_day'],
            'iteration9_weather_f1':weather['f1'],
            'iteration9_fault_to_weather':weather['fault_to_weather_rate'],
            'iteration9_drift_episode_recall':float(i9m['per_fault_episode_recall'].get('drift',np.nan)),
        })
        for anomaly_type,value in i9m['per_fault_episode_recall'].items():
            family.append({'seed':seed,'scope':scope,'domain':domain,'anomaly_type':anomaly_type,
                           'iteration9_episode_recall':value})
        for cluster,group in part.groupby('cluster'):
            metric=i9_weather_metrics(
                group,i9_weather_prediction(group,I9_WEATHER_SCORE_COL,I9_WEATHER_THRESHOLD),I9_WEATHER_SCORE_COL)
            clusters.append({'seed':seed,'scope':scope,'domain':domain,'cluster':cluster,**metric})
    return summary,family,clusters

i9_stress_summary=[]; i9_stress_family=[]; i9_stress_clusters=[]
base_stress=i8_validation.loc[i8_validation.i8_domain.eq('dwd')].copy()
rows,families,clusters=i9_summarize_seed(base_stress,I9_BASE_STRESS_SEED)
i9_stress_summary+=rows; i9_stress_family+=families; i9_stress_clusters+=clusters

if RUN_ITER9_STRESS:
    for seed in I9_NEW_STRESS_SEEDS:
        stress=i9_build_stress_seed(seed)
        rows,families,clusters=i9_summarize_seed(stress,seed)
        i9_stress_summary+=rows; i9_stress_family+=families; i9_stress_clusters+=clusters
        del stress

i9_stress_summary=pd.DataFrame(i9_stress_summary)
i9_stress_family=pd.DataFrame(i9_stress_family)
i9_stress_clusters=pd.DataFrame(i9_stress_clusters)
i9_stress_summary.to_csv(ITER9_ROOT/'iteration9_multiseed_stress.csv',index=False)
i9_stress_family.to_csv(ITER9_ROOT/'iteration9_multiseed_fault_recall.csv',index=False)
i9_stress_clusters.to_csv(ITER9_ROOT/'iteration9_multiseed_weather_by_cluster.csv',index=False)
display(i9_stress_summary); display(i9_stress_family); display(i9_stress_clusters)
"""),
    md(r"""## 51. Seed-level confidence intervals

Intervals are bootstrapped across independent injection seeds, not across correlated rows. Three seeds are still a small sample, so the interval is evidence of stability—not a claim of final population certainty.
"""),
    code(r"""def i9_seed_interval(values,seed=9191,repetitions=5000):
    values=np.asarray(values,dtype=float); values=values[np.isfinite(values)]
    if not len(values): return {'mean':float('nan'),'ci_lower':float('nan'),'ci_upper':float('nan'),'seeds':0}
    rng=np.random.default_rng(seed)
    draws=rng.choice(values,size=(repetitions,len(values)),replace=True).mean(axis=1)
    return {'mean':float(values.mean()),'ci_lower':float(np.quantile(draws,.025)),
            'ci_upper':float(np.quantile(draws,.975)),'seeds':len(values)}

i9_ci_rows=[]
metrics=['iteration9_precision','iteration9_point_f1','iteration9_event_f1',
         'iteration9_weak_recall','iteration9_false_alarm','iteration9_weather_f1',
         'iteration9_fault_to_weather','iteration9_drift_episode_recall']
for (scope,domain),group in i9_stress_summary.groupby(['scope','domain']):
    for metric in metrics:
        i9_ci_rows.append({'scope':scope,'domain':domain,'metric':metric,
                           **i9_seed_interval(group[metric])})
i9_confidence=pd.DataFrame(i9_ci_rows)
i9_confidence.to_csv(ITER9_ROOT/'iteration9_seed_confidence_intervals.csv',index=False)
display(i9_confidence)
"""),
    md(r"""## 52. Strict promotion decision and SIH impact receipt

Passing means “eligible for one locked 2024 confirmation,” not automatically deployed. Any failed gate keeps Iteration 5 as the accepted project model.
"""),
    code(r"""i9_confirmation=i9_main.loc[i9_main.scope.eq('confirmation')].copy()
i9_supported_weather=i9_weather_clusters.loc[
    i9_weather_clusters.scope.eq('confirmation')&i9_weather_clusters.weather_event_rows.gt(0)].copy()
i9_stress_confirmation=i9_stress_summary.loc[i9_stress_summary.scope.eq('confirmation')].copy()
i9_stress_supported_weather=i9_stress_clusters.loc[
    i9_stress_clusters.scope.eq('confirmation')&i9_stress_clusters.weather_event_rows.gt(0)].copy()
i9_root_confirmation=i9_root_metrics.loc[i9_root_metrics.slice.eq('detected_fault_rows')]

I9_PROMOTION_GATES={
    'policy_fault_constraints':I9_FAULT_TUNE_STATUS=='constraints_met',
    'policy_weather_constraints':I9_WEATHER_TUNE_STATUS=='constraints_met',
    'main_confirmation_precision':bool(i9_confirmation.iteration9_precision.ge(I9_MIN_PRECISION).all()),
    'main_confirmation_false_alarm':bool(i9_confirmation.iteration9_false_alarm.le(I9_MAX_FALSE_ALARM).all()),
    'no_main_point_f1_regression_vs_i8':bool(i9_confirmation.point_f1_delta_vs_i8.ge(0).all()),
    'no_main_event_f1_regression_vs_i8':bool(i9_confirmation.event_f1_delta_vs_i8.ge(0).all()),
    'no_main_weak_recall_regression_vs_i8':bool(i9_confirmation.weak_recall_delta_vs_i8.ge(0).all()),
    'india_confirmation_weather_f1_at_least_065':bool(
        i9_confirmation.loc[i9_confirmation.domain.eq('india'),'iteration9_weather_f1'].ge(.65).all()),
    'dwd_confirmation_weather_f1_at_least_075':bool(
        i9_confirmation.loc[i9_confirmation.domain.str.startswith('dwd'),'iteration9_weather_f1'].ge(.75).all()),
    'worst_supported_climate_weather_f1_at_least_065':bool(
        len(i9_supported_weather)>0 and i9_supported_weather.f1.min()>=.65),
    'main_fault_to_weather_at_most_001':bool(
        i9_confirmation.iteration9_fault_to_weather.le(I9_MAX_FAULT_TO_WEATHER).all()),
    'three_stress_seeds_completed':bool(set(i9_stress_summary.seed.astype(int))==set(I9_ALL_STRESS_SEEDS)),
    'stress_confirmation_precision':bool(i9_stress_confirmation.iteration9_precision.ge(I9_MIN_PRECISION).all()),
    'stress_confirmation_false_alarm':bool(i9_stress_confirmation.iteration9_false_alarm.le(I9_MAX_FALSE_ALARM).all()),
    'stress_no_point_f1_regression_vs_i8':bool(i9_stress_confirmation.point_f1_delta_vs_i8.ge(0).all()),
    'stress_no_event_f1_regression_vs_i8':bool(i9_stress_confirmation.event_f1_delta_vs_i8.ge(0).all()),
    'stress_weather_f1_at_least_075':bool(i9_stress_confirmation.iteration9_weather_f1.ge(.75).all()),
    'stress_fault_to_weather_at_most_001':bool(
        i9_stress_confirmation.iteration9_fault_to_weather.le(I9_MAX_FAULT_TO_WEATHER).all()),
    'stress_drift_episode_recall_at_least_050':bool(
        i9_stress_confirmation.iteration9_drift_episode_recall.fillna(0).mean()>=.50),
    'root_cause_detected_macro_f1_at_least_070':bool(
        len(i9_root_confirmation)>0 and i9_root_confirmation.macro_f1.ge(.70).all()),
    'root_cause_detected_accuracy_at_least_080':bool(
        len(i9_root_confirmation)>0 and i9_root_confirmation.accuracy.ge(.80).all()),
    'shortcut_contract_clean':bool(not (I9_EXCLUDED_SHORTCUT_FEATURES&set(I9_RESIDUAL_FEATURES))),
    'locked_years_sealed':True,
}
I9_PROMOTED=all(I9_PROMOTION_GATES.values())
I9_STATUS='eligible_for_one_locked_2024_confirmation' if I9_PROMOTED else 'not_eligible_keep_iteration5_deployment'

i9_feature_importance=pd.DataFrame({
    'feature':I9_RESIDUAL_FEATURES,
    'importance':np.mean([model.feature_importances_ for model in i9_models['fault']],axis=0),
}).sort_values('importance',ascending=False).reset_index(drop=True)
i9_feature_importance.to_csv(ITER9_ROOT/'iteration9_residual_feature_importance.csv',index=False)

i9_feature_contract={
    'observation_inputs':['temperature','pressure','relative_humidity'],
    'full_feature_count':len(FEATURES),'residual_feature_count':len(I9_RESIDUAL_FEATURES),
    'residual_features':I9_RESIDUAL_FEATURES,
    'excluded_shortcuts':sorted(I9_EXCLUDED_SHORTCUT_FEATURES),
    'calibrator_features':{'fault':I9_FAULT_META_FEATURES,'weather':I9_WEATHER_META_FEATURES},
    'causal_score_normalization':{'window_rows':720,'min_history_rows':72,'uses_current_or_future_in_baseline':False},
    'development_years':[2022,2023],'dwd_2024_opened':False,'any_2025_opened':False,
    'forbidden':['domain','station_id','climate_cluster','coordinates','future_observation','locked_year_labels'],
}
(ITER9_ROOT/'iteration9_feature_contract.json').write_text(json.dumps(i9_feature_contract,indent=2))

i9_integrity={
    'iteration8_result_sha256':sha256_file(I9_BASE_RESULT_PATH),
    'development_years':[2022,2023],'dwd_2024_opened':False,'noaa_2024_opened':False,'any_2025_opened':False,
    'threshold_selection_scope':'later half of non-holdout tune rows only',
    'calibration_scope':'earlier half of non-holdout tune rows only',
    'discovery_or_confirmation_used_for_selection':False,
    'stress_seeds':I9_ALL_STRESS_SEEDS,'stress_event_prevalence_held_constant':True,
    'domain_or_station_identifier_used_by_model':False,
}
(ITER9_ROOT/'iteration9_integrity_receipt.json').write_text(json.dumps(i9_integrity,indent=2))

result9={
    'iteration':'09_domain_invariant_calibration_multiseed_stress',
    'status':I9_STATUS,'promoted':I9_PROMOTED,'device':DEVICE,
    'gpu':torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu',
    'base_deployment':'Iteration 5','iteration8_promoted':bool(i9_base_result['promoted']),
    'development_years':[2022,2023],'locked_2024_opened':False,'any_2025_opened':False,
    'models':['residual-only LightGBM seeds 17/41/67','L2 fault calibrator','L2 weather calibrator',
              'clean-only Isolation Forest (Iteration 8 frozen)','causal LSTM autoencoder (Iteration 8 frozen)',
              'residual-only CatBoost root-cause classifier'],
    'selected_policy':{
        'fault_variant':I9_FAULT_VARIANT,'fault_score_col':I9_FAULT_SCORE_COL,'fault_threshold':I9_FAULT_THRESHOLD,
        'weather_variant':I9_WEATHER_VARIANT,'weather_score_col':I9_WEATHER_SCORE_COL,
        'weather_threshold':I9_WEATHER_THRESHOLD,
    },
    'feature_contract':{'full':len(FEATURES),'residual':len(I9_RESIDUAL_FEATURES),
                        'excluded_shortcuts':sorted(I9_EXCLUDED_SHORTCUT_FEATURES)},
    'stress_seeds':I9_ALL_STRESS_SEEDS,
    'promotion_gates':I9_PROMOTION_GATES,
    'passed_gates':sum(bool(value) for value in I9_PROMOTION_GATES.values()),
    'total_gates':len(I9_PROMOTION_GATES),
    'multidomain_confirmation':i9_main.to_dict('records'),
    'root_cause_metrics':i9_root_metrics.to_dict('records'),
    'stress_confirmation':i9_stress_confirmation.to_dict('records'),
    'next_decision':'audit then run one locked DWD 2024 confirmation' if I9_PROMOTED else 'retain Iteration 5 and inspect failed Iteration 9 gates',
}
(ITER9_ROOT/'iteration9_result_block.json').write_text(json.dumps(result9,indent=2,default=float))

i9_problem_coverage={
    'problem_statement_id':'SIH26073',
    'observation_inputs':['temperature','pressure','relative_humidity'],
    'iteration9_directly_validates':[
        'fault anomaly detection','genuine weather versus sensor fault separation',
        'spike detection','frozen sensor detection','bias and drift detection',
        'multivariate and neighbour consistency','false alarm control',
        'root-cause classification','confidence calibration','causal real-time inference',
        'unseen station and multi-climate transfer',
    ],
    'existing_end_to_end_modules_preserved':[
        'streaming API and replay','communication gap and duplicate detection',
        'alert severity and explanation','sensor health and maintenance recommendation',
        'advisory corrected value','offline dashboard and incident reports',
    ],
    'promotion_requires_all_functional_gates':True,
    'locked_test_required_after_development_pass':True,
}
(ITER9_ROOT/'iteration9_problem_coverage.json').write_text(json.dumps(i9_problem_coverage,indent=2))

print(json.dumps(result9,indent=2,default=float))
print('\nSEND BACK THESE ITERATION 9 FILES:')
for filename in [
    'iteration9_result_block.json','iteration9_integrity_receipt.json','iteration9_feature_contract.json',
    'iteration9_problem_coverage.json','iteration9_model_training_history.csv',
    'iteration9_multidomain_confirmation.csv','iteration9_fault_episode_recall.csv',
    'iteration9_weather_by_cluster.csv','iteration9_root_cause_metrics.csv',
    'iteration9_root_cause_per_class.csv','iteration9_multiseed_stress.csv',
    'iteration9_multiseed_fault_recall.csv','iteration9_multiseed_weather_by_cluster.csv',
    'iteration9_seed_confidence_intervals.csv','iteration9_calibrator_coefficients.csv',
    'iteration9_residual_feature_importance.csv','iteration9_weather_policy_frontier.csv',
    'iteration9_fault_policy_frontier.csv',
]: print(ITER9_ROOT/filename)
"""),
    md(r"""## Iteration 9 stop rule

Return the eighteen result files printed above. Do not open DWD/NOAA 2024 or any 2025 file even if the notebook reports eligibility. A separate audit must first reconcile JSON, CSV, seed counts, root-cause metrics and all promotion gates.
"""),
])

notebook.setdefault("metadata", {}).setdefault("colab", {})["name"] = OUTPUT.name
OUTPUT.write_text(json.dumps(notebook, indent=1, ensure_ascii=False), encoding="utf-8")
print(OUTPUT)
