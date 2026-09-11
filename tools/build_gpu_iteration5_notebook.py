"""Build SkyGuard GPU Iteration 5: episode-balanced weak-fault consensus."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "notebooks" / "SkyGuard_AI_GPU_Iteration_04_Causal_Incident_State_Colab.ipynb"
OUTPUT = ROOT / "notebooks" / "SkyGuard_AI_GPU_Iteration_05_Weak_Fault_Consensus_Colab.ipynb"


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.splitlines(keepends=True),
    }


notebook = json.loads(SOURCE.read_text(encoding="utf-8"))
notebook["cells"][0] = md(r"""# SkyGuard AI — GPU Iteration 5

## Episode-balanced weak-fault consensus

Iterations 3 and 4 correctly rejected unsafe rule and persistence changes. The remaining development weakness is not incident continuity: it is the initial detection of **frozen sensors, slow drift, and fixed bias**.

This controlled experiment adds one new detection channel only:

1. Train CatBoost and LightGBM weak-fault experts using all 108 compliant causal features.
2. Weight training rows by fault episode so long injected episodes cannot dominate the loss.
3. Require CatBoost/LightGBM consensus, causal persistence, gap resets, and optional genuine-weather protection before the new channel can create an alert.
4. Select a policy on May–September 2023, then require October–December confirmation.
5. Keep the existing Iteration 3 detector unchanged unless the new channel passes every safety gate.

The 2024 time and unseen-station test files remain sealed. No label, future observation, prohibited calendar feature, or maintenance data is used by the detector.
""")

notebook["cells"].extend([
    md(r"""# Iteration 5 controlled experiment

Everything above reconstructs Iterations 2–4 from the saved Drive checkpoints. Iteration 4 selected a zero-grace fallback, so the reference detector below is exactly the validated Iteration 3 trigger. These cells write only to `iteration_05_weak_fault_consensus`.
"""),
    code(r"""from lightgbm import LGBMClassifier, early_stopping, log_evaluation

ITER5_ROOT=DRIVE_ROOT/'experiments'/'iteration_05_weak_fault_consensus'
ITER5_ROOT.mkdir(parents=True,exist_ok=True)
assert UNLOCK_FINAL_TESTS is False, 'Iteration 5 must not open final tests.'

WEAK_TYPES=('frozen_sensor','bias','drift')
WEAK_FEATURES=list(FEATURES)
assert len(WEAK_FEATURES)==108
assert not ({'hour_sin','hour_cos','day_of_year_sin','day_of_year_cos','temperature_dewpoint_spread_c'}&set(WEAK_FEATURES))
print('Iteration 5 artifacts:',ITER5_ROOT)
print('Weak fault families:',WEAK_TYPES,'| features:',len(WEAK_FEATURES))
"""),
    md(r"""## 19. Episode-balanced weak-fault experts

The former per-fault specialists trained with row-level imbalance. A 100-reading drift incident could therefore influence fitting far more than a 5-reading frozen incident. Here every positive episode receives equal total weight before the usual class-imbalance adjustment. The model still sees only the permitted, causal feature pipeline.

A shared weak-fault target is intentionally used instead of nine fault/sensor neural networks: the 2022 training partition contains only 2 frozen-humidity episodes and 3 temperature-bias episodes, which is not enough support for a trustworthy separate model.
"""),
    code(r"""def make_episode_balanced_weights(frame,positive_mask):
    # Each weak-fault episode receives equal total positive weight. Labels are not used at inference.
    positive=np.asarray(positive_mask,bool)
    weights=np.ones(len(frame),dtype=float)
    positions=np.flatnonzero(positive)
    assert len(positions)>0
    positives=frame.iloc[positions][['episode_id','row_id']].copy()
    episode_key=positives.episode_id.fillna('').astype(str)
    episode_key=episode_key.where(episode_key.ne(''),'single_row_'+positives.row_id.astype(str))
    episode_length=episode_key.value_counts()
    per_row=episode_key.map(lambda key:1.0/episode_length.loc[key]).to_numpy(float)
    # Preserve the original total positive mass, while distributing it evenly between episodes.
    per_row*=len(per_row)/max(per_row.sum(),1e-12)
    weights[positions]=per_row
    imbalance=(len(frame)-len(positions))/max(weights[positions].sum(),1e-12)
    weights[positions]*=min(math.sqrt(imbalance),15.0)
    audit={
        'positive_rows':int(len(positions)),
        'positive_episodes':int(episode_key.nunique()),
        'median_episode_rows':float(episode_length.median()),
        'max_episode_rows':int(episode_length.max()),
        'positive_weight_sum':float(weights[positions].sum()),
        'negative_weight_sum':float(weights[~positive].sum()),
    }
    return weights,audit

weak_train_mask=dev.dev_split.eq('train')
weak_tune_mask=dev.dev_split.eq('tune_model')
weak_y=dev.anomaly_type.isin(WEAK_TYPES).astype(int)
weak_train_y=weak_y.loc[weak_train_mask].to_numpy(int)
weak_tune_y=weak_y.loc[weak_tune_mask].to_numpy(int)
weak_train_weights,weak_weight_audit=make_episode_balanced_weights(dev.loc[weak_train_mask],weak_train_y.astype(bool))

assert weak_train_y.sum()>100 and weak_tune_y.sum()>30
print('Episode-balanced training audit:',weak_weight_audit)
print('Train positives:',int(weak_train_y.sum()),'Tune positives:',int(weak_tune_y.sum()))
"""),
    code(r"""WEAK_SEEDS=[17,41,67]
weak_cat_models=[]; weak_lgb_models=[]; weak_model_history=[]
X_train=dev.loc[weak_train_mask,WEAK_FEATURES]
X_tune=dev.loc[weak_tune_mask,WEAK_FEATURES]

for seed in WEAK_SEEDS:
    cat_path=ITER5_ROOT/f'weak_union_catboost_seed{seed}.cbm'
    cat=CatBoostClassifier(
        iterations=1400,depth=7,learning_rate=.03,loss_function='Logloss',eval_metric='PRAUC',
        l2_leaf_reg=10,random_strength=.35,random_seed=seed,task_type='GPU',devices='0',
        verbose=150,od_type='Iter',od_wait=120,allow_writing_files=False,
    )
    if REUSE_SAVED_MODELS and cat_path.exists():
        cat.load_model(cat_path)
    else:
        cat.fit(X_train,weak_train_y,sample_weight=weak_train_weights,
                eval_set=(X_tune,weak_tune_y),use_best_model=True)
        cat.save_model(cat_path)
    weak_cat_models.append(cat)

    lgb_path=ITER5_ROOT/f'weak_union_lightgbm_seed{seed}.joblib'
    if REUSE_SAVED_MODELS and lgb_path.exists():
        lgb=joblib.load(lgb_path)
    else:
        lgb=LGBMClassifier(
            objective='binary',n_estimators=1600,learning_rate=.025,num_leaves=31,
            max_depth=-1,min_child_samples=40,subsample=.85,colsample_bytree=.85,
            reg_alpha=1.0,reg_lambda=10.0,random_state=seed,n_jobs=-1,
            verbosity=-1,force_col_wise=True,
        )
        lgb.fit(X_train,weak_train_y,sample_weight=weak_train_weights,
                eval_set=[(X_tune,weak_tune_y)],eval_metric='average_precision',
                callbacks=[early_stopping(120,verbose=False),log_evaluation(0)])
        joblib.dump(lgb,lgb_path)
    weak_lgb_models.append(lgb)

    cat_best=cat.get_best_iteration()
    lgb_best=getattr(lgb,'best_iteration_',None)
    weak_model_history.append({
        'seed':seed,
        'catboost_best_iteration':int(cat_best if cat_best is not None and cat_best>=0 else cat.tree_count_-1),
        'lightgbm_best_iteration':int(lgb_best if lgb_best else lgb.n_estimators),
    })

print('Weak expert histories:',weak_model_history)
"""),
    code(r"""dev['weak_cat_score']=np.mean([model.predict_proba(dev[WEAK_FEATURES])[:,1] for model in weak_cat_models],axis=0)
dev['weak_lgb_score']=np.mean([model.predict_proba(dev[WEAK_FEATURES])[:,1] for model in weak_lgb_models],axis=0)
dev['weak_consensus_min']=np.minimum(dev.weak_cat_score,dev.weak_lgb_score)
dev['weak_consensus_geom']=np.sqrt(np.clip(dev.weak_cat_score,0,1)*np.clip(dev.weak_lgb_score,0,1))

weak_score_columns=['weak_cat_score','weak_lgb_score','weak_consensus_min','weak_consensus_geom']
weak_model_validation=[]
for split in ['tune_model',*POLICY_BLOCKS]:
    part=dev.loc[dev.dev_split.eq(split)]
    union_y=part.anomaly_type.isin(WEAK_TYPES).astype(int)
    for score_col in weak_score_columns:
        weak_model_validation.append({
            'split':split,'target':'weak_union','score':score_col,
            'auprc':float(average_precision_score(union_y,part[score_col])),
        })
    for fault in WEAK_TYPES:
        fault_y=part.anomaly_type.eq(fault).astype(int)
        for score_col in weak_score_columns:
            weak_model_validation.append({
                'split':split,'target':fault,'score':score_col,
                'auprc':float(average_precision_score(fault_y,part[score_col])),
            })
weak_model_validation=pd.DataFrame(weak_model_validation)
weak_model_validation.to_csv(ITER5_ROOT/'iteration5_weak_model_validation.csv',index=False)
display(weak_model_validation.pivot(index=['split','target'],columns='score',values='auprc').round(4))
"""),
    md(r"""## 20. Causal consensus gate and two-block policy selection

An Iteration 5 rescue can begin only when both model families agree, the score persists across consecutive emitted readings, and the observation is not classified by the existing weather channel as a likely genuine regional event. A temporal gap resets the persistence counter.

Thresholds are selected using May–September 2023. October–December 2023 is an internal confirmation block and must independently pass every safeguard. This makes the experiment stricter than reusing a single block for both calibration and reporting.
"""),
    code(r"""def gap_aware_run_length(frame,score_col,threshold,max_gap_minutes):
    result=pd.Series(0,index=frame.index,dtype=int)
    for _,group in frame.groupby('station_id',sort=False):
        group=group.sort_values('emitted_timestamp_utc')
        scores=group[score_col].fillna(0).to_numpy(float)
        timestamps=group.emitted_timestamp_utc.tolist()
        runs=np.zeros(len(group),dtype=int); run=0; previous=None
        for position,(timestamp,score) in enumerate(zip(timestamps,scores)):
            if previous is not None and (timestamp-previous).total_seconds()/60>max_gap_minutes:
                run=0
            run=run+1 if score>=threshold else 0
            runs[position]=run
            previous=timestamp
        result.loc[group.index]=runs
    return result

def weak_episode_mean(metric):
    values=[metric['per_fault_episode_recall'].get(fault,np.nan) for fault in WEAK_TYPES]
    values=[value for value in values if not pd.isna(value)]
    return float(np.mean(values)) if values else float('nan')

WEAK_REFERENCE={}
dev['iteration3_reference']=False
for block in POLICY_BLOCKS:
    part=dev.loc[dev.dev_split.eq(block)].copy()
    baseline=apply_two_tier(part,selected.base_start,selected.base_continue,
                            selected.rescue_threshold,int(selected.min_points))
    baseline|=frozen_rule(part,SELECTED_FROZEN_CONFIG)
    dev.loc[part.index,'iteration3_reference']=baseline.to_numpy(bool)
    metrics=evaluate(part.assign(iteration3_reference=baseline),'base_score','iteration3_reference')
    WEAK_REFERENCE[block]=metrics

WEAK_SCORE_OPTIONS=['weak_consensus_min','weak_consensus_geom']
WEAK_THRESHOLDS=[.15,.25,.35,.45,.55,.65,.75]
WEAK_MIN_POINTS=[2,3,4,6]
WEAK_MAX_GAPS=[90,180]
WEAK_WEATHER_GUARDS=[True,False]
WEATHER_GUARD_THRESHOLD=float(weather_selected.threshold)
dev['weak_weather_safe']=dev.cat_weather_mean.fillna(0).lt(WEATHER_GUARD_THRESHOLD)

run_cache={}
for score_col in WEAK_SCORE_OPTIONS:
    for threshold in WEAK_THRESHOLDS:
        for max_gap in WEAK_MAX_GAPS:
            run_cache[(score_col,threshold,max_gap)]=gap_aware_run_length(dev,score_col,threshold,max_gap)

def evaluate_weak_policy(score_col,threshold,min_points,max_gap_minutes,weather_guard):
    rescue=run_cache[(score_col,threshold,max_gap_minutes)].ge(min_points)
    if weather_guard:
        rescue&=dev.weak_weather_safe
    candidate=dev.iteration3_reference|rescue
    rows=[]
    for block in POLICY_BLOCKS:
        part=dev.loc[dev.dev_split.eq(block)].copy()
        part['candidate']=candidate.loc[part.index].to_numpy(bool)
        metric=evaluate(part,'base_score','candidate')
        reference=WEAK_REFERENCE[block]
        weak_recall=weak_episode_mean(metric)
        base_weak_recall=weak_episode_mean(reference)
        rows.append({
            'block':block,**metric,
            'weak_episode_recall':weak_recall,
            'point_f1_delta':metric['f1']-reference['f1'],
            'event_f1_delta':metric['event_f1']-reference['event_f1'],
            'weak_episode_recall_delta':weak_recall-base_weak_recall,
        })
    summary={
        'score_col':score_col,'threshold':float(threshold),'min_points':int(min_points),
        'max_gap_minutes':int(max_gap_minutes),'weather_guard':bool(weather_guard),'rows':rows,
    }
    for scope,blocks in {'tune':['block_may_jun','block_jul_sep'],'all':POLICY_BLOCKS}.items():
        scoped=[row for row in rows if row['block'] in blocks]
        summary[f'{scope}_min_precision']=float(min(row['precision'] for row in scoped))
        summary[f'{scope}_max_false_alarm']=float(max(row['false_alarm_episodes_per_station_day'] for row in scoped))
        summary[f'{scope}_min_point_f1_delta']=float(min(row['point_f1_delta'] for row in scoped))
        summary[f'{scope}_mean_point_f1_delta']=float(np.mean([row['point_f1_delta'] for row in scoped]))
        summary[f'{scope}_min_event_f1_delta']=float(min(row['event_f1_delta'] for row in scoped))
        summary[f'{scope}_mean_event_f1_delta']=float(np.mean([row['event_f1_delta'] for row in scoped]))
        summary[f'{scope}_mean_weak_episode_recall_delta']=float(np.mean([row['weak_episode_recall_delta'] for row in scoped]))
    return summary

def passes_safety(summary,scope):
    return (
        summary[f'{scope}_min_precision']>=.75 and
        summary[f'{scope}_max_false_alarm']<=.02 and
        summary[f'{scope}_min_point_f1_delta']>=0 and
        summary[f'{scope}_min_event_f1_delta']>=-.01 and
        summary[f'{scope}_mean_event_f1_delta']>=0 and
        summary[f'{scope}_mean_point_f1_delta']>0 and
        summary[f'{scope}_mean_weak_episode_recall_delta']>0
    )

policy_candidates=[]
for score_col in WEAK_SCORE_OPTIONS:
    for threshold in WEAK_THRESHOLDS:
        for min_points in WEAK_MIN_POINTS:
            for max_gap in WEAK_MAX_GAPS:
                for weather_guard in WEAK_WEATHER_GUARDS:
                    policy_candidates.append(evaluate_weak_policy(
                        score_col,threshold,min_points,max_gap,weather_guard))

policy_frontier=pd.DataFrame([{key:value for key,value in row.items() if key!='rows'} for row in policy_candidates])
policy_frontier['passes_tune_gates']=policy_frontier.apply(lambda row:passes_safety(row.to_dict(),'tune'),axis=1)
policy_frontier['passes_all_gates']=policy_frontier.apply(lambda row:passes_safety(row.to_dict(),'all'),axis=1)
policy_frontier.to_csv(ITER5_ROOT/'iteration5_policy_frontier.csv',index=False)

tune_feasible=[candidate for candidate in policy_candidates if passes_safety(candidate,'tune')]
if tune_feasible:
    proposed=sorted(tune_feasible,key=lambda row:(
        row['tune_mean_weak_episode_recall_delta'],row['tune_mean_point_f1_delta'],
        row['tune_mean_event_f1_delta'],row['tune_min_precision']),reverse=True)[0]
    if passes_safety(proposed,'all'):
        ITER5_STATUS='constraints_met_with_confirmation'
        SELECTED_WEAK_POLICY={key:proposed[key] for key in ['score_col','threshold','min_points','max_gap_minutes','weather_guard']}
    else:
        ITER5_STATUS='failed_october_confirmation_keep_iteration3'
        SELECTED_WEAK_POLICY={'score_col':'weak_consensus_min','threshold':1.10,'min_points':999,'max_gap_minutes':90,'weather_guard':True}
else:
    proposed=sorted(policy_candidates,key=lambda row:(
        row['all_min_point_f1_delta'],row['all_mean_point_f1_delta'],row['all_mean_weak_episode_recall_delta']),reverse=True)[0]
    ITER5_STATUS='no_safe_development_gain_keep_iteration3'
    SELECTED_WEAK_POLICY={'score_col':'weak_consensus_min','threshold':1.10,'min_points':999,'max_gap_minutes':90,'weather_guard':True}

print('Tune-feasible candidates:',len(tune_feasible),'of',len(policy_candidates))
print('Iteration 5 status:',ITER5_STATUS)
display(pd.Series(SELECTED_WEAK_POLICY,name='selected_policy').to_frame())
display(policy_frontier.sort_values(['passes_all_gates','all_mean_weak_episode_recall_delta','all_mean_point_f1_delta'],ascending=False).head(12))
"""),
    md("## 21. Full three-block ablation and fault coverage"),
    code(r"""def materialize_weak_rescue(frame,policy):
    if int(policy['min_points'])>100:
        return pd.Series(False,index=frame.index)
    run=gap_aware_run_length(frame,policy['score_col'],float(policy['threshold']),int(policy['max_gap_minutes']))
    rescue=run.ge(int(policy['min_points']))
    if bool(policy['weather_guard']):
        rescue&=frame.cat_weather_mean.fillna(0).lt(WEATHER_GUARD_THRESHOLD)
    return rescue

rows=[]; combined=[]
dev['iteration5_rescue']=materialize_weak_rescue(dev,SELECTED_WEAK_POLICY)
for block in POLICY_BLOCKS:
    part=dev.loc[dev.dev_split.eq(block)].copy()
    part['iteration3']=part.iteration3_reference.to_numpy(bool)
    # Slice the full causal run so persistence before a block boundary is preserved exactly as evaluated.
    part['weak_rescue']=dev.loc[part.index,'iteration5_rescue'].to_numpy(bool)
    part['iteration5']=part.iteration3|part.weak_rescue
    for variant,pred_col in [('Iteration3 reference','iteration3'),('Iteration5 weak consensus','iteration5')]:
        metric=evaluate(part,'base_score',pred_col)
        metric['weak_episode_recall']=weak_episode_mean(metric)
        rows.append({'block':block,'variant':variant,**metric})
    combined.append(part)

ablation5=pd.DataFrame(rows)
ablation5.to_csv(ITER5_ROOT/'iteration5_multiblock_ablation.csv',index=False)
display(ablation5[['block','variant','precision','recall','f1','event_precision','event_recall','event_f1',
                   'weak_episode_recall','false_alarm_episodes_per_station_day','delay_mean_min','delay_p90_min']])

combined=pd.concat(combined,ignore_index=True)
combined['pred']=combined.iteration5
fault_recall5=(pd.Series(event_metrics(combined,'pred')['per_fault_episode_recall'],name='episode_recall')
               .sort_values().rename_axis('anomaly_type').reset_index())
fault_recall5.to_csv(ITER5_ROOT/'iteration5_fault_episode_recall.csv',index=False)
point_recall5=(combined.loc[combined.is_anomaly.eq(1)].groupby('anomaly_type').pred.mean()
               .rename('point_recall').sort_values().rename_axis('anomaly_type').reset_index())
point_recall5.to_csv(ITER5_ROOT/'iteration5_point_fault_recall.csv',index=False)
display(fault_recall5); display(point_recall5)
"""),
    md(r"""## 22. Save result package and stop rule

The selected policy is a deliberately impossible threshold whenever no candidate passes all safeguards. In that case the reported Iteration 5 rows are the unmodified Iteration 3 reference, not a disguised lower-quality model.
"""),
    code(r"""iteration5_rows=ablation5.loc[ablation5.variant.eq('Iteration5 weak consensus')]
operational_fault_recall=dict(zip(fault_recall5.anomaly_type,fault_recall5.episode_recall))
operational_fault_recall['duplicate_packet']=float(communication_result['duplicate_episode_recall'])
result5={
    'iteration':'05_episode_balanced_weak_fault_consensus',
    'device':DEVICE,'gpu':torch.cuda.get_device_name(0),
    'final_tests_opened':False,
    'status':ITER5_STATUS,
    'source_baseline':'Iteration3 trigger; Iteration4 was an identical zero-grace fallback',
    'model_families':['episode-balanced CatBoost weak-union ensemble','episode-balanced LightGBM weak-union ensemble'],
    'feature_count':len(WEAK_FEATURES),'weak_fault_types':list(WEAK_TYPES),
    'episode_weight_audit':weak_weight_audit,
    'model_history':weak_model_history,
    'selected_policy':SELECTED_WEAK_POLICY,
    'policy_candidates':int(len(policy_candidates)),
    'tune_feasible_candidates':int(len(tune_feasible)),
    'promotion_gates':{
        'min_precision':.75,'max_false_alarm_episodes_per_station_day':.02,
        'minimum_point_f1_delta':0.0,'minimum_event_f1_delta':-.01,
        'minimum_mean_event_f1_delta':0.0,'positive_mean_point_f1_delta':True,
        'positive_mean_weak_episode_recall_delta':True,
        'october_december_confirmation_required':True,
    },
    'iteration5_blocks':iteration5_rows.drop(columns=['per_fault_episode_recall'],errors='ignore').to_dict('records'),
    'fault_episode_recall_static':dict(zip(fault_recall5.anomaly_type,fault_recall5.episode_recall)),
    'fault_episode_recall_operational':operational_fault_recall,
    'point_fault_recall':dict(zip(point_recall5.anomaly_type,point_recall5.point_recall)),
    'communication_coverage':{
        'replay_duplicate_packet_precision':float(communication_result['duplicate_packet_precision']),
        'replay_duplicate_packet_recall':float(communication_result['duplicate_packet_recall']),
        'replay_duplicate_episode_recall':float(communication_result['duplicate_episode_recall']),
    },
}
(ITER5_ROOT/'iteration5_result_block.json').write_text(json.dumps(result5,indent=2,default=float))
(ITER5_ROOT/'iteration5_feature_contract.json').write_text(json.dumps({
    'features':WEAK_FEATURES,'forbidden_features':['hour_sin','hour_cos','day_of_year_sin','day_of_year_cos','temperature_dewpoint_spread_c'],
    'causal':True,'detector_inputs':['temperature','pressure','relative_humidity']
},indent=2))
print(json.dumps(result5,indent=2,default=float))
print('\nSEND BACK THESE FILES:')
for name in ['iteration5_result_block.json','iteration5_policy_frontier.csv','iteration5_multiblock_ablation.csv',
             'iteration5_fault_episode_recall.csv','iteration5_point_fault_recall.csv','iteration5_weak_model_validation.csv']:
    print(ITER5_ROOT/name)
"""),
    md(r"""## Promotion decision

Promote Iteration 5 only when a policy selected without October–December labels also passes October–December confirmation and every one of these all-block requirements:

- point precision at least 75%;
- false-alert episodes at most 0.02 per station-day;
- no point-F1 regression in any block;
- no event-F1 regression larger than one percentage point in any block;
- positive mean point-F1 gain;
- positive mean weak-fault episode-recall gain.

Otherwise keep Iteration 3/2 unchanged. Regardless of the result, do not open the previously inspected 2024 benchmark. The next trustworthy promotion step is a newly created blind time/station benchmark.
"""),
])

notebook.setdefault("metadata", {}).setdefault("colab", {})["name"] = OUTPUT.name
OUTPUT.write_text(json.dumps(notebook, indent=1, ensure_ascii=False), encoding="utf-8")
print(OUTPUT)
