"""Build SkyGuard GPU Iteration 6: communication safety and station transfer."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "notebooks" / "SkyGuard_AI_GPU_Iteration_05_Weak_Fault_Consensus_Colab.ipynb"
OUTPUT = ROOT / "notebooks" / "SkyGuard_AI_GPU_Iteration_06_Communication_Weather_Transfer_Colab.ipynb"


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
for cell in notebook["cells"]:
    source = "".join(cell.get("source", []))
    if cell.get("cell_type") == "code":
        source = source.replace(
            "SEND BACK THESE FILES:",
            "HISTORICAL CHECKPOINT FILES — continue running; do not return these yet:",
        )
    elif cell.get("cell_type") == "markdown":
        source = source.replace("## Return to Codex", "## Historical checkpoint — continue running")
        source = source.replace("## Promotion decision", "## Historical Iteration 5 decision — continue to Iteration 6")
    cell["source"] = source.splitlines(keepends=True)

notebook["cells"][0] = md(r"""# SkyGuard AI — GPU Iteration 6

## Communication safety and station-invariant transfer

The sealed 2025 benchmark exposed three distinct limitations: unsafe gap alerts on irregular archival feeds, weak weather recognition on unseen stations, and weak-fault rescue that did not transfer to unseen stations. This notebook addresses those causes using **2022–2023 development data only**.

It does not read, extract, score, search, or reference the 2025 blind benchmark. The former benchmark is now evidence, not a tuning set.

Iteration 6 performs three controlled experiments:

1. Audit whether arrival gaps alone can support automatic dropout fault alerts. If not, require an explicit station heartbeat contract and keep unknown-cadence gaps advisory.
2. Train station-invariant weather experts while reserving one development station per cluster as pseudo-unseen confirmation.
3. Train station-balanced weak-fault experts using relative/causal features and require gains on discovery blocks, October confirmation, and pseudo-unseen stations.

All former Iteration 1–5 sections are reconstruction checkpoints. Continue through them without returning intermediate files.
""")

notebook["cells"].extend([
    md(r"""# Iteration 6 controlled development phase

No 2024 or 2025 final benchmark is opened. Selection uses discovery stations in May–September 2023. October–December and four pseudo-unseen development stations are confirmation sets only.
"""),
    code(r"""ITER6_ROOT=DRIVE_ROOT/'experiments'/'iteration_06_communication_weather_transfer'
ITER6_ROOT.mkdir(parents=True,exist_ok=True)
assert UNLOCK_FINAL_TESTS is False,'Iteration 6 must keep former final tests locked.'
assert 'blind_2025' not in str(ITER6_ROOT).lower()

station_contract=(dev[['station_id','cluster']].drop_duplicates()
                  .sort_values(['cluster','station_id']).reset_index(drop=True))
PSEUDO_HOLDOUT_STATIONS=(station_contract.groupby('cluster',sort=True).station_id.last().astype(str).tolist())
DISCOVERY_STATIONS=sorted(set(dev.station_id.astype(str))-set(PSEUDO_HOLDOUT_STATIONS))
assert len(PSEUDO_HOLDOUT_STATIONS)==4 and len(DISCOVERY_STATIONS)==16

dev['iteration5_reference']=dev.iteration3_reference|dev.iteration5_rescue
print('Iteration 6 root:',ITER6_ROOT)
print('Pseudo-unseen stations:',PSEUDO_HOLDOUT_STATIONS)
display(station_contract.assign(pseudo_unseen=station_contract.station_id.astype(str).isin(PSEUDO_HOLDOUT_STATIONS)))
"""),
    md(r"""## 23. Communication-gap identifiability audit

An archive can omit reports for many reasons that are not labelled sensor faults. A gap-only detector cannot safely call every long silence a station failure unless the source supplies an expected heartbeat/cadence contract.

The detector below learns cadence statistics from 2022 arrival timestamps only. `stream_action` is used exclusively by the simulator/evaluator to omit injected packets and create ground truth; it is never an inference feature.
"""),
    code(r"""def build_cadence_profiles(profile_frame):
    profiles={}
    emitted=(profile_frame.loc[profile_frame.stream_action.ne('drop')]
             .drop_duplicates(['station_id','emitted_timestamp_utc']))
    for station,group in emitted.groupby('station_id',sort=False):
        delta=(group.sort_values('emitted_timestamp_utc').emitted_timestamp_utc.diff()
               .dt.total_seconds().div(60))
        plausible=delta[(delta>0)&(delta<=180)].round().astype(int)
        cadence=float(plausible.mode().iloc[0]) if len(plausible) else 60.0
        all_ratio=(delta[delta>0]/max(cadence,1)).clip(upper=1000)
        profiles[str(station)]={
            'cadence_minutes':cadence,
            'training_regularity':float((abs(plausible-cadence)<=max(5,.2*cadence)).mean()),
            'training_gap_ratio_q99':float(all_ratio.quantile(.99)),
            'training_gap_ratio_q999':float(all_ratio.quantile(.999)),
        }
    return profiles

def build_gap_events(profile_frame,replay_frame):
    profiles=build_cadence_profiles(profile_frame)
    rows=[]
    for station,group in replay_frame.groupby('station_id',sort=False):
        station=str(station); group=group.sort_values('emitted_timestamp_utc')
        dropped=group.loc[group.stream_action.eq('drop'),['emitted_timestamp_utc','episode_id']].copy()
        observed=(group.loc[group.stream_action.ne('drop')]
                  .drop_duplicates('emitted_timestamp_utc').sort_values('emitted_timestamp_utc'))
        events=pd.DataFrame({'current':observed.emitted_timestamp_utc})
        events['previous']=events.current.shift()
        events=events.dropna().copy()
        events['gap_minutes']=(events.current-events.previous).dt.total_seconds()/60
        cadence=profiles[station]['cadence_minutes']
        events['cadence_minutes']=cadence
        events['gap_ratio']=events.gap_minutes/max(cadence,1)
        regular=(abs(events.gap_minutes-cadence)<=max(5,.2*cadence)).astype(float)
        events['recent_regularity']=regular.shift().rolling(48,min_periods=12).mean().fillna(0)
        events['training_regularity']=profiles[station]['training_regularity']
        events['training_gap_ratio_q99']=profiles[station]['training_gap_ratio_q99']
        events['training_gap_ratio_q999']=profiles[station]['training_gap_ratio_q999']
        events['station_id']=station
        timestamp=events.current
        events['dev_split']=np.select(
            [timestamp<'2023-05-01',timestamp<'2023-07-01',timestamp<'2023-10-01'],
            ['tune_model','block_may_jun','block_jul_sep'],default='block_oct_dec')

        drop_times=dropped.emitted_timestamp_utc.to_numpy(dtype='datetime64[ns]')
        starts=events.previous.to_numpy(dtype='datetime64[ns]')
        ends=events.current.to_numpy(dtype='datetime64[ns]')
        left=np.searchsorted(drop_times,starts,side='right')
        right=np.searchsorted(drop_times,ends,side='left')
        events['is_injected_dropout_gap']=right>left
        rows.append(events)
    return pd.concat(rows,ignore_index=True),profiles

# Colab may retain the reconstructed `dev` table while releasing the two source
# tables after an interrupted or out-of-order run. Reload only those lightweight
# inputs when necessary; no model is retrained and no final/blind file is opened.
if 'train' not in globals() or not isinstance(train,pd.DataFrame):
    train=load_table('train')
    train['dev_split']='train'
if 'validation' not in globals() or not isinstance(validation,pd.DataFrame):
    validation=load_table('validation')
    validation_timestamp=validation.emitted_timestamp_utc
    validation['dev_split']=np.select(
        [validation_timestamp<'2023-05-01',validation_timestamp<'2023-07-01',
         validation_timestamp<'2023-10-01'],
        ['tune_model','block_may_jun','block_jul_sep'],default='block_oct_dec')

gap_events6,cadence_profiles6=build_gap_events(train,validation)
print('Gap events:',len(gap_events6),'| injected dropout gaps:',int(gap_events6.is_injected_dropout_gap.sum()))
display(pd.DataFrame(cadence_profiles6).T.describe().T)
"""),
    code(r"""def gap_policy_metrics(events,prediction):
    truth=events.is_injected_dropout_gap.to_numpy(bool); pred=np.asarray(prediction,bool)
    tp=int((truth&pred).sum()); fp=int((~truth&pred).sum()); fn=int((truth&~pred).sum())
    precision=tp/max(tp+fp,1); recall=tp/max(tp+fn,1)
    first=events.previous.min(); last=events.current.max()
    station_days=max((last-first).total_seconds()/86400,1)*events.station_id.nunique()
    return {'tp':tp,'fp':fp,'fn':fn,'precision':precision,'recall':recall,
            'f1':2*precision*recall/max(precision+recall,1e-12),
            'false_gap_alerts_per_station_day':fp/max(station_days,1e-12)}

gap_selection=gap_events6.loc[
    gap_events6.station_id.astype(str).isin(DISCOVERY_STATIONS)&
    gap_events6.dev_split.isin(['block_may_jun','block_jul_sep'])].copy()
gap_frontier=[]
for ratio_threshold in [2.5,3,4,5,6,8,10,12,15,20,30,40]:
  for recent_regularity in [.50,.70,.80,.90,.95,.98]:
    for historical_multiplier in [0,1,1.5,2,3]:
        historical_floor=(gap_selection.training_gap_ratio_q999*historical_multiplier
                          if historical_multiplier else 0)
        threshold=np.maximum(ratio_threshold,historical_floor)
        prediction=(gap_selection.gap_ratio>=threshold)&(gap_selection.recent_regularity>=recent_regularity)
        gap_frontier.append({
            'ratio_threshold':ratio_threshold,'recent_regularity':recent_regularity,
            'historical_q999_multiplier':historical_multiplier,
            **gap_policy_metrics(gap_selection,prediction),
        })
gap_frontier=pd.DataFrame(gap_frontier).sort_values(['f1','precision','recall'],ascending=False)
gap_frontier.to_csv(ITER6_ROOT/'iteration6_communication_frontier.csv',index=False)

safe_gap_candidates=gap_frontier.loc[
    (gap_frontier.precision>=.80)&(gap_frontier.recall>=.80)&
    (gap_frontier.false_gap_alerts_per_station_day<=.02)]
gap_confirmation=[]
if len(safe_gap_candidates):
    proposed_gap=safe_gap_candidates.iloc[0].to_dict()
    for scope,mask in {
        'oct_dec_discovery':gap_events6.station_id.astype(str).isin(DISCOVERY_STATIONS)&gap_events6.dev_split.eq('block_oct_dec'),
        'pseudo_unseen_all_2023':gap_events6.station_id.astype(str).isin(PSEUDO_HOLDOUT_STATIONS)&gap_events6.dev_split.isin(POLICY_BLOCKS),
    }.items():
        part=gap_events6.loc[mask].copy()
        floor=(part.training_gap_ratio_q999*proposed_gap['historical_q999_multiplier']
               if proposed_gap['historical_q999_multiplier'] else 0)
        threshold=np.maximum(proposed_gap['ratio_threshold'],floor)
        pred=(part.gap_ratio>=threshold)&(part.recent_regularity>=proposed_gap['recent_regularity'])
        gap_confirmation.append({'scope':scope,**gap_policy_metrics(part,pred)})
    gap_confirmation_pass=all(
        row['precision']>=.80 and row['recall']>=.80 and row['false_gap_alerts_per_station_day']<=.02
        for row in gap_confirmation)
else:
    proposed_gap=None; gap_confirmation_pass=False

if proposed_gap and gap_confirmation_pass:
    GAP_POLICY_STATUS='automatic_archive_gap_policy_supported_with_confirmation'
    SELECTED_GAP_POLICY=proposed_gap
else:
    GAP_POLICY_STATUS='heartbeat_contract_required_archive_gaps_advisory_only'
    SELECTED_GAP_POLICY={
        'automatic_fault_alert_without_contract':False,
        'unknown_cadence_output':'unverified_data_gap_advisory',
        'strict_mode_requirement':'adapter supplies expected cadence and heartbeat SLA',
        'duplicate_packet_detection_remains_automatic':True,
    }

gap_confirmation=pd.DataFrame(gap_confirmation)
gap_confirmation.to_csv(ITER6_ROOT/'iteration6_communication_confirmation.csv',index=False)
print('Communication policy:',GAP_POLICY_STATUS)
display(gap_frontier.head(15)); display(gap_confirmation)
display(pd.Series(SELECTED_GAP_POLICY,name='selected').to_frame())
"""),
    md(r"""### Communication interpretation

If the safe frontier is empty, Iteration 6 does not hide the failure by selecting an extreme threshold. It changes the operational contract:

- duplicate packets remain automatic because their fingerprint has deterministic evidence;
- a configured AWS heartbeat may generate automatic dropout incidents;
- an unknown-cadence archive/live source generates an advisory data-gap status, not a sensor-fault maintenance alert.

This prevents thousands of unsupported fault claims while preserving strict dropout detection for sources that actually promise periodic delivery.
"""),
    md(r"""## 24. Station-invariant weather experts

Absolute temperature or pressure distributions can identify a station rather than weather coherence. The challenger therefore excludes raw values, raw lags, calendar encodings and dew-point-derived features. It uses causal rates, robust residuals, slopes, CUSUM and neighbour/regional agreement.
"""),
    code(r"""WEATHER_INV_TOKENS=(
    'neighbor_','regional_','robust_z','ewma_residual','rate_per_hour','_delta1',
    '_slope_','cusum_','monotonic_run','rolling_mad','climatology_residual',
    'agreement_fraction','missing','gap_ratio','out_of_order_indicator',
)
WEATHER_INV_FEATURES=[feature for feature in FEATURES if any(token in feature for token in WEATHER_INV_TOKENS)]
FORBIDDEN_ABSOLUTE={
    'temperature_value','pressure_value','humidity_value','temperature_lag1','pressure_lag1','humidity_lag1',
    'temperature_rolling_median_24h','pressure_rolling_median_24h','humidity_rolling_median_24h',
}
WEATHER_INV_FEATURES=[feature for feature in WEATHER_INV_FEATURES if feature not in FORBIDDEN_ABSOLUTE]
assert len(WEATHER_INV_FEATURES)>=45
assert not (FORBIDDEN_ABSOLUTE&set(WEATHER_INV_FEATURES))
assert not ({'hour_sin','hour_cos','day_of_year_sin','day_of_year_cos','temperature_dewpoint_spread_c'}&set(WEATHER_INV_FEATURES))

def station_episode_balanced_weights(frame,target):
    target=np.asarray(target,bool); station=frame.station_id.astype(str)
    counts=station.value_counts(); weights=station.map(lambda value:1.0/counts.loc[value]).to_numpy(float)
    weights*=len(weights)/max(weights.sum(),1e-12)
    positions=np.flatnonzero(target)
    if len(positions):
        positive=frame.iloc[positions][['episode_id','row_id']].copy()
        key=positive.episode_id.fillna('').astype(str)
        key=key.where(key.ne(''),'single_'+positive.row_id.astype(str))
        episode_length=key.value_counts()
        episode_weight=key.map(lambda value:1.0/episode_length.loc[value]).to_numpy(float)
        episode_weight*=len(episode_weight)/max(episode_weight.sum(),1e-12)
        positive=positive.assign(station=station.iloc[positions].to_numpy())
        station_positive=positive.station.value_counts()
        station_weight=positive.station.map(lambda value:1.0/station_positive.loc[value]).to_numpy(float)
        station_weight*=len(station_weight)/max(station_weight.sum(),1e-12)
        combined=np.sqrt(episode_weight*station_weight)
        imbalance=(len(frame)-len(positions))/max(len(positions),1)
        weights[positions]=combined*min(math.sqrt(imbalance),20.0)
    return weights

discovery=dev.station_id.astype(str).isin(DISCOVERY_STATIONS)&dev.available_to_detector.eq(1)
pseudo=dev.station_id.astype(str).isin(PSEUDO_HOLDOUT_STATIONS)&dev.available_to_detector.eq(1)
weather_train=discovery&dev.dev_split.eq('train')
weather_tune=discovery&dev.dev_split.eq('tune_model')
weather_y=dev.is_weather_event.astype(int)
weather_weights=station_episode_balanced_weights(dev.loc[weather_train],weather_y.loc[weather_train].to_numpy(bool))

print('Weather invariant features:',len(WEATHER_INV_FEATURES))
print('Discovery train weather rows:',int(weather_y.loc[weather_train].sum()),
      '| tune:',int(weather_y.loc[weather_tune].sum()),
      '| pseudo-unseen validation:',int(weather_y.loc[pseudo&~dev.dev_split.eq('train')].sum()))
"""),
    code(r"""WEATHER6_SEEDS=[17,41,67]
weather6_cat_models=[]; weather6_lgb_models=[]; weather6_history=[]
for seed in WEATHER6_SEEDS:
    cat_path=ITER6_ROOT/f'weather_invariant_catboost_seed{seed}.cbm'
    cat=CatBoostClassifier(
        iterations=1400,depth=7,learning_rate=.03,loss_function='Logloss',eval_metric='PRAUC',
        l2_leaf_reg=12,random_strength=.5,random_seed=seed,task_type='GPU',devices='0',
        verbose=150,od_type='Iter',od_wait=120,allow_writing_files=False,
    )
    if REUSE_SAVED_MODELS and cat_path.exists(): cat.load_model(cat_path)
    else:
        cat.fit(dev.loc[weather_train,WEATHER_INV_FEATURES],weather_y.loc[weather_train],
                sample_weight=weather_weights,
                eval_set=(dev.loc[weather_tune,WEATHER_INV_FEATURES],weather_y.loc[weather_tune]),
                use_best_model=True)
        cat.save_model(cat_path)
    weather6_cat_models.append(cat)

    lgb_path=ITER6_ROOT/f'weather_invariant_lightgbm_seed{seed}.joblib'
    if REUSE_SAVED_MODELS and lgb_path.exists(): lgb=joblib.load(lgb_path)
    else:
        lgb=LGBMClassifier(
            objective='binary',n_estimators=1800,learning_rate=.02,num_leaves=31,
            min_child_samples=50,subsample=.85,colsample_bytree=.80,
            reg_alpha=2.0,reg_lambda=15.0,random_state=seed,n_jobs=-1,
            verbosity=-1,force_col_wise=True,
        )
        lgb.fit(dev.loc[weather_train,WEATHER_INV_FEATURES],weather_y.loc[weather_train],
                sample_weight=weather_weights,
                eval_set=[(dev.loc[weather_tune,WEATHER_INV_FEATURES],weather_y.loc[weather_tune])],
                eval_metric='average_precision',callbacks=[early_stopping(120,verbose=False),log_evaluation(0)])
        joblib.dump(lgb,lgb_path)
    weather6_lgb_models.append(lgb)
    weather6_history.append({'seed':seed,'cat_trees':int(cat.tree_count_),
                             'lgb_iteration':int(getattr(lgb,'best_iteration_',0) or lgb.n_estimators)})

dev['weather6_cat']=np.mean([model.predict_proba(dev[WEATHER_INV_FEATURES])[:,1]
                             for model in weather6_cat_models],axis=0)
dev['weather6_lgb']=np.mean([model.predict_proba(dev[WEATHER_INV_FEATURES])[:,1]
                             for model in weather6_lgb_models],axis=0)
dev['weather6_mean']=(dev.weather6_cat+dev.weather6_lgb)/2
dev['weather6_min']=np.minimum(dev.weather6_cat,dev.weather6_lgb)
dev['weather6_geom']=np.sqrt(np.clip(dev.weather6_cat,0,1)*np.clip(dev.weather6_lgb,0,1))
print(weather6_history)
"""),
    code(r"""def weather_quality(frame,pred_col,score_col):
    truth=frame.is_weather_event.astype(int); pred=frame[pred_col].astype(bool)
    precision=precision_score(truth,pred,zero_division=0); recall=recall_score(truth,pred,zero_division=0)
    station_f1=[]
    for _,group in frame.groupby('station_id'):
        if group.is_weather_event.sum()>0:
            station_f1.append(f1_score(group.is_weather_event,group[pred_col],zero_division=0))
    return {
        'weather_precision':float(precision),'weather_recall':float(recall),
        'weather_f1':float(f1_score(truth,pred,zero_division=0)),
        'weather_auprc':float(average_precision_score(truth,frame[score_col])),
        'positive_station_macro_f1':float(np.mean(station_f1)) if station_f1 else 0.0,
        'fault_to_weather_rate':float(pred.loc[frame.is_anomaly.eq(1)].mean()) if frame.is_anomaly.sum() else 0.0,
    }

WEATHER6_DISCOVERY_BLOCKS=['block_may_jun','block_jul_sep']
weather6_candidates=[]
for score_col in ['weather6_mean','weather6_min','weather6_geom']:
  for threshold in np.linspace(.05,.80,31):
    rows=[]
    for block in WEATHER6_DISCOVERY_BLOCKS:
        part=dev.loc[discovery&dev.dev_split.eq(block)].copy()
        part['current_pred']=part.cat_weather_mean.ge(float(WEATHER_GUARD_THRESHOLD))
        part['candidate_pred']=part[score_col].ge(threshold)
        current=weather_quality(part,'current_pred','cat_weather_mean')
        candidate=weather_quality(part,'candidate_pred',score_col)
        rows.append({'block':block,**candidate,'f1_delta':candidate['weather_f1']-current['weather_f1'],
                     'macro_delta':candidate['positive_station_macro_f1']-current['positive_station_macro_f1']})
    weather6_candidates.append({
        'score_col':score_col,'threshold':float(threshold),'rows':rows,
        'min_f1_delta':float(min(row['f1_delta'] for row in rows)),
        'mean_f1_delta':float(np.mean([row['f1_delta'] for row in rows])),
        'min_macro_delta':float(min(row['macro_delta'] for row in rows)),
        'max_fault_to_weather':float(max(row['fault_to_weather_rate'] for row in rows)),
        'mean_weather_f1':float(np.mean([row['weather_f1'] for row in rows])),
    })

weather6_frontier=pd.DataFrame([{key:value for key,value in row.items() if key!='rows'}
                                for row in weather6_candidates])
weather6_frontier['passes_discovery']=(
    (weather6_frontier.min_f1_delta>=0)&(weather6_frontier.mean_f1_delta>0)&
    (weather6_frontier.min_macro_delta>=-.02)&(weather6_frontier.max_fault_to_weather<=.01))
weather6_frontier.to_csv(ITER6_ROOT/'iteration6_weather_policy_frontier.csv',index=False)

feasible_weather=[row for row in weather6_candidates if (
    row['min_f1_delta']>=0 and row['mean_f1_delta']>0 and row['min_macro_delta']>=-.02 and
    row['max_fault_to_weather']<=.01)]
proposed_weather=(sorted(feasible_weather,key=lambda row:(row['mean_weather_f1'],row['mean_f1_delta'],
                                                          row['min_macro_delta']),reverse=True)[0]
                  if feasible_weather else None)

def compare_weather_scope(mask,score_col,threshold,scope):
    part=dev.loc[mask].copy()
    part['current_pred']=part.cat_weather_mean.ge(float(WEATHER_GUARD_THRESHOLD))
    part['candidate_pred']=part[score_col].ge(float(threshold))
    current=weather_quality(part,'current_pred','cat_weather_mean')
    candidate=weather_quality(part,'candidate_pred',score_col)
    return {'scope':scope,**{f'current_{k}':v for k,v in current.items()},
            **{f'candidate_{k}':v for k,v in candidate.items()},
            'f1_delta':candidate['weather_f1']-current['weather_f1'],
            'macro_delta':candidate['positive_station_macro_f1']-current['positive_station_macro_f1']}

weather6_confirmation=[]
if proposed_weather:
    score_col=proposed_weather['score_col']; threshold=proposed_weather['threshold']
    weather6_confirmation.append(compare_weather_scope(
        discovery&dev.dev_split.eq('block_oct_dec'),score_col,threshold,'oct_dec_discovery'))
    weather6_confirmation.append(compare_weather_scope(
        pseudo&dev.dev_split.isin(POLICY_BLOCKS),score_col,threshold,'pseudo_unseen_all_2023'))
    confirmation_pass=all(
        row['f1_delta']>=0 and row['macro_delta']>=-.02 and row['candidate_fault_to_weather_rate']<=.01
        for row in weather6_confirmation)
else:
    confirmation_pass=False

if proposed_weather and confirmation_pass:
    WEATHER6_STATUS='station_invariant_weather_confirmed'
    SELECTED_WEATHER6={'score_col':proposed_weather['score_col'],'threshold':proposed_weather['threshold']}
else:
    WEATHER6_STATUS='no_confirmed_weather_gain_keep_iteration5_weather'
    SELECTED_WEATHER6={'score_col':'cat_weather_mean','threshold':float(WEATHER_GUARD_THRESHOLD)}

weather6_confirmation=pd.DataFrame(weather6_confirmation)
weather6_confirmation.to_csv(ITER6_ROOT/'iteration6_weather_confirmation.csv',index=False)
dev['weather6_prediction']=dev[SELECTED_WEATHER6['score_col']].ge(float(SELECTED_WEATHER6['threshold']))
print('Weather status:',WEATHER6_STATUS,SELECTED_WEATHER6)
display(weather6_frontier.sort_values(['passes_discovery','mean_weather_f1'],ascending=False).head(15))
display(weather6_confirmation)
"""),
    md(r"""## 25. Station-balanced weak-fault transfer challenger

Iteration 5 used all 108 features and improved only known-station future time. This challenger removes absolute station-identifying values, balances positive episodes and stations, and excludes four pseudo-unseen stations from fitting and policy selection.
"""),
    code(r"""WEAK6_TOKENS=(
    'neighbor_','regional_','robust_z','ewma_residual','rate_per_hour','_delta1','_slope_',
    'cusum_','monotonic_run','frozen_run_length','rolling_mad','climatology_residual',
    'missing','gap_ratio','out_of_order_indicator','time_since_previous_minutes',
)
WEAK6_FEATURES=[feature for feature in FEATURES if any(token in feature for token in WEAK6_TOKENS)]
WEAK6_FEATURES=[feature for feature in WEAK6_FEATURES if feature not in FORBIDDEN_ABSOLUTE]
assert len(WEAK6_FEATURES)>=50
assert not (FORBIDDEN_ABSOLUTE&set(WEAK6_FEATURES))

weak6_y=dev.anomaly_type.isin(WEAK_TYPES).astype(int)
weak6_train=discovery&dev.dev_split.eq('train')
weak6_tune=discovery&dev.dev_split.eq('tune_model')
weak6_weights=station_episode_balanced_weights(dev.loc[weak6_train],weak6_y.loc[weak6_train].to_numpy(bool))
print('Weak transfer features:',len(WEAK6_FEATURES),'| train positives:',int(weak6_y.loc[weak6_train].sum()))
"""),
    code(r"""WEAK6_SEEDS=[17,41,67]
weak6_cat_models=[]; weak6_lgb_models=[]; weak6_history=[]
for seed in WEAK6_SEEDS:
    cat_path=ITER6_ROOT/f'weak_transfer_catboost_seed{seed}.cbm'
    cat=CatBoostClassifier(
        iterations=1500,depth=7,learning_rate=.025,loss_function='Logloss',eval_metric='PRAUC',
        l2_leaf_reg=15,random_strength=.55,random_seed=seed,task_type='GPU',devices='0',
        verbose=150,od_type='Iter',od_wait=130,allow_writing_files=False,
    )
    if REUSE_SAVED_MODELS and cat_path.exists(): cat.load_model(cat_path)
    else:
        cat.fit(dev.loc[weak6_train,WEAK6_FEATURES],weak6_y.loc[weak6_train],sample_weight=weak6_weights,
                eval_set=(dev.loc[weak6_tune,WEAK6_FEATURES],weak6_y.loc[weak6_tune]),use_best_model=True)
        cat.save_model(cat_path)
    weak6_cat_models.append(cat)

    lgb_path=ITER6_ROOT/f'weak_transfer_lightgbm_seed{seed}.joblib'
    if REUSE_SAVED_MODELS and lgb_path.exists(): lgb=joblib.load(lgb_path)
    else:
        lgb=LGBMClassifier(
            objective='binary',n_estimators=1800,learning_rate=.02,num_leaves=31,min_child_samples=45,
            subsample=.85,colsample_bytree=.80,reg_alpha=2.0,reg_lambda=15.0,
            random_state=seed,n_jobs=-1,verbosity=-1,force_col_wise=True,
        )
        lgb.fit(dev.loc[weak6_train,WEAK6_FEATURES],weak6_y.loc[weak6_train],sample_weight=weak6_weights,
                eval_set=[(dev.loc[weak6_tune,WEAK6_FEATURES],weak6_y.loc[weak6_tune])],
                eval_metric='average_precision',callbacks=[early_stopping(130,verbose=False),log_evaluation(0)])
        joblib.dump(lgb,lgb_path)
    weak6_lgb_models.append(lgb)
    weak6_history.append({'seed':seed,'cat_trees':int(cat.tree_count_),
                          'lgb_iteration':int(getattr(lgb,'best_iteration_',0) or lgb.n_estimators)})

dev['weak6_cat']=np.mean([model.predict_proba(dev[WEAK6_FEATURES])[:,1] for model in weak6_cat_models],axis=0)
dev['weak6_lgb']=np.mean([model.predict_proba(dev[WEAK6_FEATURES])[:,1] for model in weak6_lgb_models],axis=0)
dev['weak6_min']=np.minimum(dev.weak6_cat,dev.weak6_lgb)
dev['weak6_geom']=np.sqrt(np.clip(dev.weak6_cat,0,1)*np.clip(dev.weak6_lgb,0,1))
print(weak6_history)
"""),
    code(r"""def weak_fault_mean_from_metric(metric):
    values=[metric['per_fault_episode_recall'].get(fault,np.nan) for fault in WEAK_TYPES]
    values=[value for value in values if not pd.isna(value)]
    return float(np.mean(values)) if values else 0.0

weak6_run_cache={}
visible6=dev.available_to_detector.eq(1)
for score_col in ['weak6_min','weak6_geom']:
  for threshold in [.10,.20,.30,.40,.50,.60,.70,.80]:
    for max_gap in [90,180,360]:
        full_run=pd.Series(0,index=dev.index,dtype=int)
        full_run.loc[visible6]=gap_aware_run_length(
            dev.loc[visible6],score_col,threshold,max_gap).astype(int)
        weak6_run_cache[(score_col,threshold,max_gap)]=full_run

def evaluate_weak6_candidate(score_col,threshold,min_points,max_gap):
    rescue=weak6_run_cache[(score_col,threshold,max_gap)].ge(min_points)
    rescue&=~dev.weather6_prediction
    candidate=dev.iteration5_reference|rescue
    rows=[]
    for block in WEATHER6_DISCOVERY_BLOCKS:
        mask=discovery&dev.dev_split.eq(block)
        part=dev.loc[mask].copy()
        part['baseline']=dev.loc[mask,'iteration5_reference'].to_numpy(bool)
        part['candidate']=candidate.loc[mask].to_numpy(bool)
        baseline=evaluate(part,'base_score','baseline'); metric=evaluate(part,'base_score','candidate')
        rows.append({
            'block':block,**metric,
            'point_f1_delta':metric['f1']-baseline['f1'],
            'event_f1_delta':metric['event_f1']-baseline['event_f1'],
            'weak_episode_recall':weak_fault_mean_from_metric(metric),
            'weak_episode_recall_delta':weak_fault_mean_from_metric(metric)-weak_fault_mean_from_metric(baseline),
        })
    return {
        'score_col':score_col,'threshold':threshold,'min_points':min_points,'max_gap_minutes':max_gap,
        'rows':rows,'min_precision':min(row['precision'] for row in rows),
        'max_false_alarm':max(row['false_alarm_episodes_per_station_day'] for row in rows),
        'min_point_f1_delta':min(row['point_f1_delta'] for row in rows),
        'mean_point_f1_delta':float(np.mean([row['point_f1_delta'] for row in rows])),
        'min_event_f1_delta':min(row['event_f1_delta'] for row in rows),
        'mean_event_f1_delta':float(np.mean([row['event_f1_delta'] for row in rows])),
        'mean_weak_recall_delta':float(np.mean([row['weak_episode_recall_delta'] for row in rows])),
    }

weak6_candidates=[]
for score_col in ['weak6_min','weak6_geom']:
  for threshold in [.10,.20,.30,.40,.50,.60,.70,.80]:
    for min_points in [2,3,4,6]:
      for max_gap in [90,180,360]:
        weak6_candidates.append(evaluate_weak6_candidate(score_col,threshold,min_points,max_gap))

def weak6_discovery_pass(row):
    return (row['min_precision']>=.75 and row['max_false_alarm']<=.02 and
            row['min_point_f1_delta']>=0 and row['min_event_f1_delta']>=-.01 and
            row['mean_point_f1_delta']>0 and row['mean_event_f1_delta']>=0 and
            row['mean_weak_recall_delta']>0)

weak6_frontier=pd.DataFrame([{key:value for key,value in row.items() if key!='rows'} for row in weak6_candidates])
weak6_frontier['passes_discovery']=weak6_frontier.apply(lambda row:weak6_discovery_pass(row.to_dict()),axis=1)
weak6_frontier.to_csv(ITER6_ROOT/'iteration6_weak_policy_frontier.csv',index=False)
weak6_feasible=[row for row in weak6_candidates if weak6_discovery_pass(row)]
proposed_weak6=(sorted(weak6_feasible,key=lambda row:(row['mean_weak_recall_delta'],
                                                       row['mean_point_f1_delta'],row['mean_event_f1_delta']),
                       reverse=True)[0] if weak6_feasible else None)

def weak6_confirmation_scope(mask,policy,scope):
    rescue=weak6_run_cache[(policy['score_col'],policy['threshold'],policy['max_gap_minutes'])].ge(policy['min_points'])
    rescue&=~dev.weather6_prediction
    part=dev.loc[mask].copy()
    part['baseline']=dev.loc[mask,'iteration5_reference'].to_numpy(bool)
    part['candidate']=(dev.loc[mask,'iteration5_reference']|rescue.loc[mask]).to_numpy(bool)
    baseline=evaluate(part,'base_score','baseline'); metric=evaluate(part,'base_score','candidate')
    return {
        'scope':scope,'precision':metric['precision'],
        'false_alarm_episodes_per_station_day':metric['false_alarm_episodes_per_station_day'],
        'point_f1':metric['f1'],'point_f1_delta':metric['f1']-baseline['f1'],
        'event_f1':metric['event_f1'],'event_f1_delta':metric['event_f1']-baseline['event_f1'],
        'weak_episode_recall':weak_fault_mean_from_metric(metric),
        'weak_episode_recall_delta':weak_fault_mean_from_metric(metric)-weak_fault_mean_from_metric(baseline),
    }

weak6_confirmation=[]
if proposed_weak6:
    weak6_confirmation.append(weak6_confirmation_scope(
        discovery&dev.dev_split.eq('block_oct_dec'),proposed_weak6,'oct_dec_discovery'))
    weak6_confirmation.append(weak6_confirmation_scope(
        pseudo&dev.dev_split.isin(POLICY_BLOCKS),proposed_weak6,'pseudo_unseen_all_2023'))
    weak6_confirmation_pass=all(
        row['precision']>=.75 and row['false_alarm_episodes_per_station_day']<=.02 and
        row['point_f1_delta']>=0 and row['event_f1_delta']>=-.01 and
        row['weak_episode_recall_delta']>=0 for row in weak6_confirmation)
else:
    weak6_confirmation_pass=False

if proposed_weak6 and weak6_confirmation_pass:
    WEAK6_STATUS='station_transfer_weak_rescue_confirmed'
    SELECTED_WEAK6={key:proposed_weak6[key] for key in ['score_col','threshold','min_points','max_gap_minutes']}
else:
    WEAK6_STATUS='no_station_transfer_gain_keep_iteration5_candidate'
    SELECTED_WEAK6={'score_col':'weak6_min','threshold':1.10,'min_points':999,'max_gap_minutes':180}

weak6_confirmation=pd.DataFrame(weak6_confirmation)
weak6_confirmation.to_csv(ITER6_ROOT/'iteration6_weak_confirmation.csv',index=False)
print('Weak transfer status:',WEAK6_STATUS,SELECTED_WEAK6)
display(weak6_frontier.sort_values(['passes_discovery','mean_weak_recall_delta','mean_point_f1_delta'],ascending=False).head(15))
display(weak6_confirmation)
"""),
    md(r"""## 26. Three-block ablation and result package

The final development candidate is materialized only when both discovery and confirmation gates pass. Failed experiments remain in the frontier files and do not silently alter the detector.
"""),
    code(r"""if int(SELECTED_WEAK6['min_points'])<100:
    selected_weak6_rescue=weak6_run_cache[(SELECTED_WEAK6['score_col'],SELECTED_WEAK6['threshold'],
                                           SELECTED_WEAK6['max_gap_minutes'])].ge(SELECTED_WEAK6['min_points'])
    selected_weak6_rescue&=~dev.weather6_prediction
else:
    selected_weak6_rescue=pd.Series(False,index=dev.index)

dev['iteration6_candidate']=dev.iteration5_reference|selected_weak6_rescue
iteration6_rows=[]
for block in POLICY_BLOCKS:
    mask=dev.dev_split.eq(block)&dev.available_to_detector.eq(1)
    part=dev.loc[mask].copy()
    part['iteration5']=dev.loc[mask,'iteration5_reference'].to_numpy(bool)
    part['iteration6']=dev.loc[mask,'iteration6_candidate'].to_numpy(bool)
    for variant,pred_col in [('Iteration5 candidate','iteration5'),('Iteration6 candidate','iteration6')]:
        metric=evaluate(part,'base_score',pred_col)
        iteration6_rows.append({'block':block,'variant':variant,**metric,
                                'weak_episode_recall':weak_fault_mean_from_metric(metric)})

iteration6_ablation=pd.DataFrame(iteration6_rows)
iteration6_ablation.to_csv(ITER6_ROOT/'iteration6_multiblock_ablation.csv',index=False)
display(iteration6_ablation[['block','variant','precision','recall','f1','event_precision','event_recall',
                             'event_f1','weak_episode_recall','false_alarm_episodes_per_station_day']])

result6={
    'iteration':'06_communication_safety_weather_station_transfer',
    'device':DEVICE,'gpu':torch.cuda.get_device_name(0),
    'blind_2025_opened':False,'former_final_tests_opened':False,
    'development_years':[2022,2023],
    'pseudo_unseen_stations':PSEUDO_HOLDOUT_STATIONS,
    'communication':{
        'status':GAP_POLICY_STATUS,'selected_policy':SELECTED_GAP_POLICY,
        'safe_automatic_candidates':int(len(safe_gap_candidates)),
        'best_gap_policy':gap_frontier.iloc[0].to_dict(),
        'confirmation':gap_confirmation.to_dict('records'),
        'stream_action_used_by_detector':False,
    },
    'weather':{
        'status':WEATHER6_STATUS,'selected_policy':SELECTED_WEATHER6,
        'feature_count':len(WEATHER_INV_FEATURES),'model_history':weather6_history,
        'discovery_feasible_candidates':int(len(feasible_weather)),
        'confirmation':weather6_confirmation.to_dict('records'),
    },
    'weak_fault_transfer':{
        'status':WEAK6_STATUS,'selected_policy':SELECTED_WEAK6,
        'feature_count':len(WEAK6_FEATURES),'model_history':weak6_history,
        'discovery_feasible_candidates':int(len(weak6_feasible)),
        'confirmation':weak6_confirmation.to_dict('records'),
    },
    'selected_ablation':iteration6_ablation.drop(columns=['per_fault_episode_recall'],errors='ignore').to_dict('records'),
    'promotion_rule':'No change unless discovery, October, pseudo-unseen, precision, false-alarm, point-F1 and event-F1 gates pass.',
}
(ITER6_ROOT/'iteration6_result_block.json').write_text(json.dumps(result6,indent=2,default=float))
(ITER6_ROOT/'iteration6_feature_contract.json').write_text(json.dumps({
    'weather_features':WEATHER_INV_FEATURES,'weak_features':WEAK6_FEATURES,
    'detector_observation_inputs':['temperature','pressure','relative_humidity'],
    'communication_metadata':['station_id','arrival_timestamp','optional_expected_cadence'],
    'forbidden':['dew_point','future_observation','blind_2025_labels'],
},indent=2))

print(json.dumps(result6,indent=2,default=float))
print('\nSEND BACK THESE ITERATION 6 FILES:')
for filename in [
    'iteration6_result_block.json','iteration6_communication_frontier.csv',
    'iteration6_communication_confirmation.csv',
    'iteration6_weather_policy_frontier.csv','iteration6_weather_confirmation.csv',
    'iteration6_weak_policy_frontier.csv','iteration6_weak_confirmation.csv',
    'iteration6_multiblock_ablation.csv','iteration6_feature_contract.json',
]: print(ITER6_ROOT/filename)
"""),
    md(r"""## Iteration 6 decision

Do not reopen the 2025 benchmark. If a challenger passes every development and pseudo-unseen gate, freeze it and create a new later benchmark before production promotion. If it fails, retain the prior detector and use the frontier evidence to decide whether the next development phase needs broader weather simulation or additional weak-fault episodes.
"""),
])

notebook.setdefault("metadata", {}).setdefault("colab", {})["name"] = OUTPUT.name
OUTPUT.write_text(json.dumps(notebook, indent=1, ensure_ascii=False), encoding="utf-8")
print(OUTPUT)
