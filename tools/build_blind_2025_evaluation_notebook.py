"""Build the sealed one-time 2025 blind comparison notebook.

The notebook reconstructs the accepted development pipeline from Iteration 5,
verifies the frozen artifacts and development results, and only then allows an
explicit one-time evaluation on the separately packaged 2025 benchmark.
"""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "notebooks" / "SkyGuard_AI_GPU_Iteration_05_Weak_Fault_Consensus_Colab.ipynb"
OUTPUT = ROOT / "notebooks" / "SkyGuard_AI_GPU_Blind_2025_Final_Comparison_Colab.ipynb"


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

# The source notebook contains historical hand-off text from Iterations 1–5.
# In a combined final runner those messages look like stop instructions, so
# relabel them as checkpoints before appending the one-time blind phase.
for cell in notebook["cells"]:
    source = "".join(cell.get("source", []))
    if cell.get("cell_type") == "code":
        source = source.replace(
            "SEND BACK THESE FILES:",
            "HISTORICAL CHECKPOINT FILES — do not stop or send these; continue running:",
        )
    elif cell.get("cell_type") == "markdown":
        if "## Return to Codex" in source:
            source = source.replace("## Return to Codex", "## Historical checkpoint — continue running")
            source = source.replace(
                "Send the four files listed above.",
                "Do not return the intermediate files in this combined notebook.",
            )
        if source.startswith("## 10. Final-test seal"):
            source = source.replace(
                "## 10. Final-test seal",
                "## 10. Historical Iteration 2 seal — continue to Iteration 3",
            )
        if source.startswith("## Promotion decision"):
            source = source.replace(
                "## Promotion decision",
                "## Historical Iteration 5 development decision — continue to the blind phase",
            )
    cell["source"] = source.splitlines(keepends=True)

notebook["cells"][0] = md(r"""# SkyGuard AI — Final 2025 blind evaluation

## Frozen Iteration 3 versus Iteration 5 comparison

This notebook first reconstructs the complete accepted development pipeline. It then verifies the exact Iteration 5 model files, policy, and development confusion matrices before it can open a separately sealed NOAA/NCEI 2025 benchmark.

The blind section has **no threshold search, model fitting, calibration, feature selection, or policy selection**. It evaluates the frozen Iteration 3 reference and Iteration 5 weak-fault consensus once on:

- a later-time test using the 20 development-station identities;
- a later-time test using four stations never used for model training;
- injected sensor/data faults, genuine regional weather events, and operational communication replay.

Keep `UNLOCK_BLIND_2025 = False` until all earlier cells complete and the development-lock cell passes. Then change that single flag to `True` and run the blind section once.

> **Important:** Iteration 1–5 sections are historical reconstruction checkpoints inside this combined notebook. Do not stop at them and do not return their intermediate files. Continue until **Section 23 — DEVELOPMENT LOCK**.
""")

notebook["cells"].extend([
    md(r"""# Final phase — sealed 2025 blind benchmark

The benchmark was built from official NOAA/NCEI Global Hourly station files for 1 January through 24 August 2025. Its source files, normalized rows, injected episodes, features, and hashes are isolated from all development folders. Neither Iteration 3 nor Iteration 5 was executed while the benchmark was built.

This phase answers the question left open by Iteration 5: does its small development gain survive both future time and unseen stations?
"""),
    code(r"""import hashlib, zipfile
from datetime import datetime, timezone

BLIND_BUNDLE_ZIP=DRIVE_ROOT/'SkyGuard_Blind_2025_Bundle.zip'
BLIND_ROOT=DRIVE_ROOT/'SkyGuard_Blind_2025_Bundle'
BLIND_OUTPUT_ROOT=DRIVE_ROOT/'experiments'/'blind_2025_final_comparison'
BLIND_OUTPUT_ROOT.mkdir(parents=True,exist_ok=True)

EXPECTED_BLIND_BUNDLE_SHA256='5f8bbad22342295f62c97d9b47628800eaa43df7aec5650ea91b814c6854d859'
UNLOCK_BLIND_2025=False  # Change only this value to True after the development lock passes.

EXPECTED_ITER5_POLICY={
    'score_col':'weak_consensus_min','threshold':0.35,'min_points':4,
    'max_gap_minutes':180,'weather_guard':True,
}
EXPECTED_ITER5_MODEL_HASHES={
    'weak_union_lightgbm_seed17.joblib':'45a9b0fb90951ea122e6015d285917001ed33ad9da6395bb6e42196adb65bc61',
    'weak_union_lightgbm_seed41.joblib':'d9c75bd0be21722a45f32c15e1022af61869a8a4a907255f97310ac22a4f7ce2',
    'weak_union_lightgbm_seed67.joblib':'96a3eb01e64423f50f2d7f8a97705443de9c5376587fea3d76d5bed30b1bafcd',
    'weak_union_catboost_seed17.cbm':'1651cca3a20e6fea1bbb038a5d397e65b463775d08f51df116b2e668d463ebc3',
    'weak_union_catboost_seed41.cbm':'6d60c53a24ad27f9b8553671634d6ec0555f968ccb20a57b1d11e313dabccd75',
    'weak_union_catboost_seed67.cbm':'3569e4a82ba387072dec09a76a52fa512f963b81488afe9ad632830ea5e5b45c',
}

def file_sha256(path,chunk_size=1024*1024):
    digest=hashlib.sha256()
    with open(path,'rb') as handle:
        for chunk in iter(lambda:handle.read(chunk_size),b''):
            digest.update(chunk)
    return digest.hexdigest()

print('Blind archive expected at:',BLIND_BUNDLE_ZIP)
print('Results will be written to:',BLIND_OUTPUT_ROOT)
print('Current blind lock:',UNLOCK_BLIND_2025)
"""),
    md(r"""## 23. Freeze and reproduce the development result

This is the last step before opening the blind archive. It checks the six exact saved Iteration 5 experts, the policy selected on development data, and every Iteration 3/5 development confusion matrix. A mismatch stops the run.
"""),
    code(r"""assert ITER5_STATUS=='constraints_met_with_confirmation',ITER5_STATUS
assert SELECTED_WEAK_POLICY==EXPECTED_ITER5_POLICY,(SELECTED_WEAK_POLICY,EXPECTED_ITER5_POLICY)
assert abs(float(WEATHER_GUARD_THRESHOLD)-0.24)<1e-12,WEATHER_GUARD_THRESHOLD
assert len(FEATURES)==108
assert not ({'hour_sin','hour_cos','day_of_year_sin','day_of_year_cos','temperature_dewpoint_spread_c'}&set(FEATURES))

for filename,expected_hash in EXPECTED_ITER5_MODEL_HASHES.items():
    path=ITER5_ROOT/filename
    assert path.exists(),f'Missing frozen model: {path}'
    actual_hash=file_sha256(path)
    assert actual_hash==expected_hash,f'Frozen model hash mismatch for {filename}: {actual_hash}'

EXPECTED_DEV_COUNTS={
 ('block_may_jun','Iteration3 reference'):(108,27,135,28742),
 ('block_may_jun','Iteration5 weak consensus'):(109,27,134,28742),
 ('block_jul_sep','Iteration3 reference'):(70,9,305,46419),
 ('block_jul_sep','Iteration5 weak consensus'):(72,9,303,46419),
 ('block_oct_dec','Iteration3 reference'):(194,39,277,47089),
 ('block_oct_dec','Iteration5 weak consensus'):(194,39,277,47089),
}
for key,expected in EXPECTED_DEV_COUNTS.items():
    block,variant=key
    observed=ablation5.loc[(ablation5.block==block)&(ablation5.variant==variant)]
    assert len(observed)==1,f'Missing development row: {key}'
    observed_counts=tuple(int(observed.iloc[0][name]) for name in ['tp','fp','fn','tn'])
    assert observed_counts==expected,f'Development result mismatch for {key}: {observed_counts}'

development_lock={
    'status':'PASS',
    'checked_at_utc':datetime.now(timezone.utc).isoformat(),
    'feature_count':len(FEATURES),
    'iteration5_policy':EXPECTED_ITER5_POLICY,
    'weather_threshold':float(WEATHER_GUARD_THRESHOLD),
    'model_sha256':EXPECTED_ITER5_MODEL_HASHES,
    'development_confusion_matrices':{
        f'{block}|{variant}':{'tp':v[0],'fp':v[1],'fn':v[2],'tn':v[3]}
        for (block,variant),v in EXPECTED_DEV_COUNTS.items()
    },
}
(BLIND_OUTPUT_ROOT/'development_lock.json').write_text(json.dumps(development_lock,indent=2))
print('DEVELOPMENT LOCK: PASS')
print('No blind feature or label file has been read.')
"""),
    md(r"""## 24. Explicit one-time unlock, integrity verification, and receipt

Upload `SkyGuard_Blind_2025_Bundle.zip` directly into `MyDrive/SkyGuard_AI_GPU/`. Change `UNLOCK_BLIND_2025` to `True` in the configuration cell, then run from that cell onward. The archive hash and every internal file hash must match before scoring.

If a completed result already exists, the notebook refuses to score again. This prevents repeated inspection and threshold tuning on the blind benchmark.
"""),
    code(r"""assert UNLOCK_BLIND_2025 is True,(
    'Blind benchmark remains sealed. After DEVELOPMENT LOCK: PASS, change '
    'UNLOCK_BLIND_2025 to True and run this section once.'
)
assert BLIND_BUNDLE_ZIP.exists(),f'Upload the blind bundle to {BLIND_BUNDLE_ZIP}'
assert file_sha256(BLIND_BUNDLE_ZIP)==EXPECTED_BLIND_BUNDLE_SHA256,'Blind archive hash mismatch.'

FINAL_RESULT_PATH=BLIND_OUTPUT_ROOT/'blind_2025_result_block.json'
assert not FINAL_RESULT_PATH.exists(),(
    f'A completed blind result already exists at {FINAL_RESULT_PATH}. '
    'Do not rerun or tune against the blind benchmark.'
)

if not BLIND_ROOT.exists():
    with zipfile.ZipFile(BLIND_BUNDLE_ZIP) as archive:
        archive.extractall(DRIVE_ROOT)

MANIFEST_PATH=BLIND_ROOT/'data'/'blind_2025'/'manifest'/'sealed_benchmark_files.csv'
assert MANIFEST_PATH.exists(),f'Missing manifest: {MANIFEST_PATH}'
sealed_manifest=pd.read_csv(MANIFEST_PATH)
for row in sealed_manifest.itertuples(index=False):
    path=BLIND_ROOT/row.relative_path
    assert path.exists(),f'Missing sealed file: {row.relative_path}'
    assert int(path.stat().st_size)==int(row.bytes),f'Byte-size mismatch: {row.relative_path}'
    assert file_sha256(path)==row.sha256,f'SHA-256 mismatch: {row.relative_path}'

PROTOCOL_PATH=BLIND_ROOT/'data'/'blind_2025'/'blind_protocol.json'
protocol=json.loads(PROTOCOL_PATH.read_text())
assert protocol['status']=='SEALED_NOT_SCORED'
assert protocol['frozen_comparison']==['Iteration 3/2 detector','Iteration 5 weak-fault consensus']

receipt_path=BLIND_OUTPUT_ROOT/'blind_2025_open_receipt.json'
receipt={
    'opened_at_utc':datetime.now(timezone.utc).isoformat(),
    'archive_sha256':EXPECTED_BLIND_BUNDLE_SHA256,
    'manifest_rows':int(len(sealed_manifest)),
    'frozen_iteration5_policy':EXPECTED_ITER5_POLICY,
    'weather_threshold':float(WEATHER_GUARD_THRESHOLD),
    'feature_count':len(FEATURES),
    'no_tuning_attestation':(
        'No blind threshold search, model fitting, calibration, feature selection, '
        'or policy selection is performed by this notebook.'
    ),
}
if receipt_path.exists():
    previous=json.loads(receipt_path.read_text())
    assert previous['archive_sha256']==receipt['archive_sha256']
    assert previous['frozen_iteration5_policy']==receipt['frozen_iteration5_policy']
    receipt=previous
else:
    receipt_path.write_text(json.dumps(receipt,indent=2))

print('BLIND ARCHIVE INTEGRITY: PASS')
print('One-time open receipt:',receipt_path)
"""),
    md(r"""## 25. Frozen scoring and operational communication replay

The scoring path below uses the same 108 causal features, CatBoost base/weather ensembles, calibrated weak-fault specialists, hard rules, and frozen Iteration 5 CatBoost–LightGBM consensus used in development. It does not inspect labels to produce predictions.

Dropout and duplicate packets are also replayed as stream operations. `stream_action` is used by the simulator/evaluator to omit or repeat packets, never as a detector input.
"""),
    code(r"""BLIND_DATA_ROOT=BLIND_ROOT/'data'/'blind_2025'
BLIND_FEATURE_PATHS={
    'blind_time':BLIND_DATA_ROOT/'features_phase10'/'blind_time_features.csv.gz',
    'blind_station':BLIND_DATA_ROOT/'features_phase10'/'blind_station_features.csv.gz',
}
BLIND_LABEL_PATHS={
    'blind_time':BLIND_DATA_ROOT/'labelled'/'blind_time.csv',
    'blind_station':BLIND_DATA_ROOT/'labelled'/'blind_station.csv',
}

def load_blind_features(test_name):
    frame=pd.read_csv(BLIND_FEATURE_PATHS[test_name],dtype={'station_id':str,'episode_id':str})
    frame['station_id']=frame.station_id.astype(str).str.zfill(11)
    frame['episode_id']=frame.episode_id.fillna('').astype(str)
    for column in ['timestamp_utc','emitted_timestamp_utc','original_timestamp_utc']:
        frame[column]=pd.to_datetime(frame[column],utc=True,errors='coerce')
    assert frame.emitted_timestamp_utc.notna().all()
    assert set(FEATURES).issubset(frame.columns)
    assert frame.evaluation_role.nunique()==1
    visible=frame.loc[frame.available_to_detector.eq(1)].copy()
    visible=visible.sort_values(['station_id','emitted_timestamp_utc','row_id']).reset_index(drop=True)
    return visible

def score_frozen_detectors(frame):
    scored=add_hard_rules(frame.copy())
    X_blind=scored[FEATURES]

    scored['cat_fault_mean']=np.mean(
        [model.predict_proba(X_blind)[:,1] for model in fault_models],axis=0)
    scored['cat_weather_mean']=np.mean(
        [model.predict_proba(X_blind)[:,1] for model in weather_models],axis=0)
    scored['base_score']=apply_platt(base_calibrator,scored.cat_fault_mean)

    specialist_score_columns=[]
    for fault,features in SPECIALIST_FEATURES.items():
        raw=np.mean([model.predict_proba(scored[features])[:,1]
                     for model in specialist_models[fault]],axis=0)
        score_column=f'{fault}_score'
        scored[score_column]=apply_platt(calibrators[fault],raw)
        specialist_score_columns.append(score_column)
    scored['rescue_score']=scored[specialist_score_columns].max(axis=1)

    scored['weak_cat_score']=np.mean(
        [model.predict_proba(scored[WEAK_FEATURES])[:,1] for model in weak_cat_models],axis=0)
    scored['weak_lgb_score']=np.mean(
        [model.predict_proba(scored[WEAK_FEATURES])[:,1] for model in weak_lgb_models],axis=0)
    scored['weak_consensus_min']=np.minimum(scored.weak_cat_score,scored.weak_lgb_score)
    scored['weak_consensus_geom']=np.sqrt(
        np.clip(scored.weak_cat_score,0,1)*np.clip(scored.weak_lgb_score,0,1))

    iteration3=apply_two_tier(
        scored,float(selected.base_start),float(selected.base_continue),
        float(selected.rescue_threshold),int(selected.min_points))
    iteration3|=frozen_rule(scored,SELECTED_FROZEN_CONFIG)
    scored['iteration3']=iteration3.to_numpy(bool)
    scored['iteration5_rescue']=materialize_weak_rescue(scored,EXPECTED_ITER5_POLICY).to_numpy(bool)
    scored['iteration5']=scored.iteration3|scored.iteration5_rescue
    scored['weather_prediction']=scored.cat_weather_mean.ge(float(WEATHER_GUARD_THRESHOLD))
    return scored

def enriched_detection_metrics(frame,pred_col):
    metrics=evaluate(frame,'base_score',pred_col)
    total=metrics['tp']+metrics['fp']+metrics['fn']+metrics['tn']
    metrics['accuracy']=(metrics['tp']+metrics['tn'])/max(total,1)
    metrics['specificity']=metrics['tn']/max(metrics['tn']+metrics['fp'],1)
    metrics['balanced_accuracy']=0.5*(metrics['recall']+metrics['specificity'])
    return metrics

def weather_metrics_fixed(frame,pred_col):
    truth=frame.is_weather_event.astype(int).to_numpy()
    weather_prediction=frame.weather_prediction.astype(bool).to_numpy()
    fault_prediction=frame[pred_col].astype(bool).to_numpy()
    return {
        'weather_rows':int(truth.sum()),
        'weather_precision':float(precision_score(truth,weather_prediction,zero_division=0)),
        'weather_recall':float(recall_score(truth,weather_prediction,zero_division=0)),
        'weather_f1':float(f1_score(truth,weather_prediction,zero_division=0)),
        'weather_auprc':float(average_precision_score(truth,frame.cat_weather_mean)),
        'weather_to_fault_rate':float(fault_prediction[truth.astype(bool)].mean()) if truth.sum() else 0.0,
    }

def packet_fingerprint_blind(packet):
    clean=lambda value:None if pd.isna(value) else value
    return (packet['station_id'],packet['timestamp'],clean(packet['temperature']),
            clean(packet['pressure']),clean(packet['humidity']))

def replay_duplicates(source):
    packets=[]
    for row in source.itertuples(index=False):
        packet={
            'station_id':row.station_id,'timestamp':row.timestamp_utc,
            'temperature':row.temperature_c,'pressure':row.pressure_hpa,
            'humidity':row.relative_humidity_pct,'episode_id':row.episode_id,
            'injected_duplicate':False,
        }
        packets.append(packet)
        if row.stream_action=='duplicate':
            duplicate=packet.copy(); duplicate['injected_duplicate']=True; packets.append(duplicate)
    seen=set(); tp=fp=fn=0; true_episodes=set(); detected_episodes=set()
    for packet in packets:
        fingerprint=packet_fingerprint_blind(packet)
        prediction=fingerprint in seen; seen.add(fingerprint)
        truth=bool(packet['injected_duplicate'])
        tp+=int(prediction and truth); fp+=int(prediction and not truth); fn+=int(not prediction and truth)
        if truth and packet['episode_id']: true_episodes.add(packet['episode_id'])
        if prediction and truth and packet['episode_id']: detected_episodes.add(packet['episode_id'])
    return {
        'duplicate_packet_tp':tp,'duplicate_packet_fp':fp,'duplicate_packet_fn':fn,
        'duplicate_packet_precision':tp/max(tp+fp,1),
        'duplicate_packet_recall':tp/max(tp+fn,1),
        'true_duplicate_episodes':len(true_episodes),
        'detected_duplicate_episodes':len(true_episodes&detected_episodes),
        'duplicate_episode_recall':len(true_episodes&detected_episodes)/max(len(true_episodes),1),
    }

def modal_cadence_minutes(times):
    diff=pd.Series(times).sort_values().diff().dt.total_seconds().div(60)
    plausible=diff[(diff>0)&(diff<=180)].round().astype(int)
    return float(plausible.mode().iloc[0]) if len(plausible) else 60.0

def replay_dropouts(source):
    predictions=[]; truths=[]; cadence_by_station={}
    for station,group in source.groupby('station_id',sort=False):
        group=group.sort_values('timestamp_utc')
        observed=group.loc[group.stream_action.ne('drop')].sort_values('timestamp_utc')
        cadence=modal_cadence_minutes(observed.timestamp_utc)
        cadence_by_station[station]=cadence
        times=observed.timestamp_utc.dropna().drop_duplicates().sort_values().tolist()
        for previous,current in zip(times[:-1],times[1:]):
            gap=(current-previous).total_seconds()/60
            if gap>2.5*cadence:
                predictions.append((station,previous+pd.Timedelta(minutes=cadence),
                                    current-pd.Timedelta(minutes=cadence)))
        dropped=group.loc[group.stream_action.eq('drop')&group.episode_id.ne('')]
        for episode,episode_rows in dropped.groupby('episode_id'):
            truths.append((station,episode,episode_rows.timestamp_utc.min(),episode_rows.timestamp_utc.max()))
    used=set(); detected=[]
    for station,episode,start,end in truths:
        candidates=[(index,prediction) for index,prediction in enumerate(predictions)
                    if index not in used and prediction[0]==station and
                    prediction[1]<=end and prediction[2]>=start]
        if candidates:
            index,_=min(candidates,key=lambda item:item[1][1]); used.add(index); detected.append(episode)
    tp=len(detected); fp=len(predictions)-len(used); fn=len(truths)-tp
    return {
        'dropout_event_tp':tp,'dropout_event_fp':fp,'dropout_event_fn':fn,
        'dropout_event_precision':tp/max(tp+fp,1),
        'dropout_event_recall':tp/max(tp+fn,1),
        'true_dropout_episodes':len(truths),
        'detector_uses_only_arrival_timestamps':True,
        'cadence_minutes_by_station':cadence_by_station,
    }

def load_blind_labels(test_name):
    source=pd.read_csv(BLIND_LABEL_PATHS[test_name],dtype={'station_id':str,'episode_id':str})
    source['station_id']=source.station_id.astype(str).str.zfill(11)
    source['episode_id']=source.episode_id.fillna('').astype(str)
    source['timestamp_utc']=pd.to_datetime(source.timestamp_utc,utc=True,errors='coerce')
    return source

print('Frozen scoring and communication replay functions loaded.')
"""),
    md(r"""## 26. Execute the one-time blind comparison

Both detectors receive exactly the same rows. Iteration 5 is accepted over Iteration 3 only if it avoids point- and event-F1 regression on both blind tests and stays inside the precision/false-alarm safety budget. The stricter SIH readiness target is reported separately; it is not used to alter the detector.
"""),
    code(r"""comparison_rows=[]; weather_rows=[]; fault_episode_rows=[]; point_fault_rows=[]; communication_rows=[]
scored_blind={}

for test_name in ['blind_time','blind_station']:
    source=load_blind_labels(test_name)
    frame=score_frozen_detectors(load_blind_features(test_name))
    scored_blind[test_name]=frame

    duplicate_result=replay_duplicates(source)
    dropout_result=replay_dropouts(source)
    communication={
        'test':test_name,
        **{key:value for key,value in duplicate_result.items()},
        **{key:value for key,value in dropout_result.items() if key!='cadence_minutes_by_station'},
        'stream_action_used_by_detector':False,
        'detector_inputs':['station_id','arrival_timestamp','temperature','pressure','humidity'],
    }
    communication_rows.append(communication)

    truth_counts=(source.loc[source.is_anomaly.eq(1)&source.episode_id.ne('')]
                  .groupby('anomaly_type').episode_id.nunique().to_dict())
    station_days=sum(max((group.emitted_timestamp_utc.max()-group.emitted_timestamp_utc.min()).total_seconds()/86400,1/24)
                     for _,group in frame.groupby('station_id'))

    for variant,pred_col in [('Iteration3 reference','iteration3'),('Iteration5 weak consensus','iteration5')]:
        metrics=enriched_detection_metrics(frame,pred_col)
        weather=weather_metrics_fixed(frame,pred_col)

        reported_fault_recall={}
        for fault,count in sorted(truth_counts.items()):
            static_recall=metrics['per_fault_episode_recall'].get(fault,0.0)
            if fault=='duplicate_packet':
                reported=float(duplicate_result['duplicate_episode_recall']); mode='operational_replay'
            elif fault=='dropout':
                reported=float(dropout_result['dropout_event_recall']); mode='operational_replay'
            else:
                reported=float(static_recall); mode='static_causal_stream'
            reported_fault_recall[fault]=reported
            fault_episode_rows.append({
                'test':test_name,'variant':variant,'anomaly_type':fault,
                'true_episodes':int(count),'episode_recall':reported,'evaluation_mode':mode,
            })

        total_fault_episodes=sum(truth_counts.values())
        operational_event_recall=sum(truth_counts[fault]*reported_fault_recall[fault]
                                     for fault in truth_counts)/max(total_fault_episodes,1)
        communication_fp=duplicate_result['duplicate_packet_fp']+dropout_result['dropout_event_fp']
        operational_false_alarm_rate=(
            metrics['false_alarm_episodes_per_station_day']+communication_fp/max(station_days,1e-12))

        clean_metrics={key:value for key,value in metrics.items() if key!='per_fault_episode_recall'}
        comparison_rows.append({
            'test':test_name,'variant':variant,'rows':int(len(frame)),
            'stations':int(frame.station_id.nunique()),**clean_metrics,
            'operational_episode_recall':float(operational_event_recall),
            'operational_false_alarm_episodes_per_station_day':float(operational_false_alarm_rate),
            'weather_f1':weather['weather_f1'],
            'weather_to_fault_rate':weather['weather_to_fault_rate'],
        })
        weather_rows.append({'test':test_name,'variant':variant,**weather})

        anomaly_rows=frame.loc[frame.is_anomaly.eq(1)]
        point_recall=anomaly_rows.groupby('anomaly_type')[pred_col].mean().to_dict()
        for fault,count in sorted(truth_counts.items()):
            if fault=='duplicate_packet':
                recall=float(duplicate_result['duplicate_packet_recall']); mode='operational_replay'
            elif fault=='dropout':
                recall=np.nan; mode='not_point_evaluable_packet_absence'
            else:
                recall=float(point_recall.get(fault,0.0)); mode='static_causal_stream'
            point_fault_rows.append({
                'test':test_name,'variant':variant,'anomaly_type':fault,
                'point_recall':recall,'evaluation_mode':mode,
            })

comparison=pd.DataFrame(comparison_rows)
weather_table=pd.DataFrame(weather_rows)
fault_episode_table=pd.DataFrame(fault_episode_rows)
point_fault_table=pd.DataFrame(point_fault_rows)
communication_table=pd.DataFrame(communication_rows)

targets=protocol['promotion_target']
relative_checks=[]; readiness_checks=[]
for test_name in ['blind_time','blind_station']:
    old=comparison.loc[(comparison.test==test_name)&(comparison.variant=='Iteration3 reference')].iloc[0]
    new=comparison.loc[(comparison.test==test_name)&(comparison.variant=='Iteration5 weak consensus')].iloc[0]
    relative_checks.extend([
        {'test':test_name,'criterion':'no_point_f1_regression','passed':bool(new.f1+1e-12>=old.f1)},
        {'test':test_name,'criterion':'no_event_f1_regression','passed':bool(new.event_f1+1e-12>=old.event_f1)},
        {'test':test_name,'criterion':'precision_safety_0.75','passed':bool(new.precision>=.75)},
        {'test':test_name,'criterion':'false_alarm_safety_0.02','passed':bool(new.operational_false_alarm_episodes_per_station_day<=.02)},
    ])
    readiness_checks.extend([
        {'test':test_name,'criterion':'precision','actual':float(new.precision),'target':float(targets['minimum_precision_each_test']),'passed':bool(new.precision>=targets['minimum_precision_each_test'])},
        {'test':test_name,'criterion':'point_f1','actual':float(new.f1),'target':float(targets['minimum_point_f1_each_test']),'passed':bool(new.f1>=targets['minimum_point_f1_each_test'])},
        {'test':test_name,'criterion':'operational_episode_recall','actual':float(new.operational_episode_recall),'target':float(targets['minimum_episode_recall_each_test']),'passed':bool(new.operational_episode_recall>=targets['minimum_episode_recall_each_test'])},
        {'test':test_name,'criterion':'operational_false_alarm_rate','actual':float(new.operational_false_alarm_episodes_per_station_day),'target':float(targets['maximum_false_alarm_episodes_per_station_day']),'passed':bool(new.operational_false_alarm_episodes_per_station_day<=targets['maximum_false_alarm_episodes_per_station_day'])},
        {'test':test_name,'criterion':'weather_f1','actual':float(new.weather_f1),'target':float(targets['minimum_weather_f1_each_test']),'passed':bool(new.weather_f1>=targets['minimum_weather_f1_each_test'])},
        {'test':test_name,'criterion':'weather_to_fault_rate','actual':float(new.weather_to_fault_rate),'target':float(targets['weather_to_fault_rate_maximum']),'passed':bool(new.weather_to_fault_rate<=targets['weather_to_fault_rate_maximum'])},
    ])

relative_table=pd.DataFrame(relative_checks)
readiness_table=pd.DataFrame(readiness_checks)
iteration5_relative_pass=bool(relative_table.passed.all())
sih_readiness_pass=bool(readiness_table.passed.all())

comparison.to_csv(BLIND_OUTPUT_ROOT/'blind_2025_comparison.csv',index=False)
fault_episode_table.to_csv(BLIND_OUTPUT_ROOT/'blind_2025_fault_episode_recall.csv',index=False)
point_fault_table.to_csv(BLIND_OUTPUT_ROOT/'blind_2025_point_fault_recall.csv',index=False)
weather_table.to_csv(BLIND_OUTPUT_ROOT/'blind_2025_weather_metrics.csv',index=False)
communication_table.to_csv(BLIND_OUTPUT_ROOT/'blind_2025_communication_replay.csv',index=False)
readiness_table.to_csv(BLIND_OUTPUT_ROOT/'blind_2025_readiness_checks.csv',index=False)

result={
    'phase':'fresh_2025_blind_time_and_station_evaluation',
    'evaluated_at_utc':datetime.now(timezone.utc).isoformat(),
    'archive_sha256':EXPECTED_BLIND_BUNDLE_SHA256,
    'source':protocol['official_source'],
    'frozen_iteration5_policy':EXPECTED_ITER5_POLICY,
    'weather_threshold':float(WEATHER_GUARD_THRESHOLD),
    'feature_count':len(FEATURES),
    'model_sha256':EXPECTED_ITER5_MODEL_HASHES,
    'no_tuning_attestation':receipt['no_tuning_attestation'],
    'comparison':comparison.replace({np.nan:None}).to_dict('records'),
    'weather_metrics':weather_table.replace({np.nan:None}).to_dict('records'),
    'communication_replay':communication_table.replace({np.nan:None}).to_dict('records'),
    'relative_promotion_checks':relative_table.to_dict('records'),
    'sih_readiness_checks':readiness_table.to_dict('records'),
    'decision':{
        'iteration5_relative_promotion_gate_passed':iteration5_relative_pass,
        'sih_readiness_targets_all_passed':sih_readiness_pass,
        'recommended_detector':('Iteration5 candidate for reviewed promotion' if iteration5_relative_pass else 'Keep Iteration3 reference'),
        'automatic_production_change_made':False,
    },
}
FINAL_RESULT_PATH.write_text(json.dumps(result,indent=2,default=float,allow_nan=False))

display(comparison[['test','variant','precision','recall','f1','event_precision','event_recall','event_f1',
                    'operational_episode_recall','operational_false_alarm_episodes_per_station_day',
                    'weather_f1','weather_to_fault_rate']].round(4))
display(readiness_table)
display(communication_table.drop(columns=['detector_inputs'],errors='ignore'))
print('Iteration 5 relative promotion gate:',iteration5_relative_pass)
print('All strict SIH readiness targets:',sih_readiness_pass)
print('Final result:',FINAL_RESULT_PATH)
"""),
    md(r"""## 27. Visual comparison and files to return

The chart is descriptive only; it does not influence policy selection. Return the JSON result plus all six CSV files so the next review can identify whether the limiting issue is weak-fault recall, future-time transfer, unseen-station transfer, genuine-weather separation, or communication replay.
"""),
    code(r"""import matplotlib.pyplot as plt

plot_table=comparison.pivot(index='test',columns='variant',values=['f1','event_f1','operational_episode_recall'])
axes=plot_table.plot(kind='bar',figsize=(13,5),ylim=(0,1),rot=0)
axes.axhline(.65,color='tab:blue',linestyle='--',linewidth=1,label='point-F1 target')
axes.axhline(.85,color='tab:green',linestyle=':',linewidth=1,label='episode-recall target')
axes.set_title('Frozen SkyGuard blind evaluation — no blind tuning')
axes.set_ylabel('Score')
axes.grid(axis='y',alpha=.25)
plt.tight_layout(); plt.show()

print('SEND BACK THESE FILES:')
for filename in [
    'blind_2025_result_block.json','blind_2025_comparison.csv',
    'blind_2025_fault_episode_recall.csv','blind_2025_point_fault_recall.csv',
    'blind_2025_weather_metrics.csv','blind_2025_communication_replay.csv',
    'blind_2025_readiness_checks.csv','blind_2025_open_receipt.json',
]:
    print(BLIND_OUTPUT_ROOT/filename)
"""),
    md(r"""## Decision rule after this notebook

- If the relative promotion gate fails on either test, keep Iteration 3 and diagnose the failed fault families. Do not tune on this 2025 benchmark.
- If the relative gate passes but strict SIH readiness fails, Iteration 5 is a valid research improvement but the complete detector still needs another development-only improvement cycle and a new future blind test.
- If both pass, package Iteration 5 for integration into the API/dashboard, retain advisory correction behavior, and run CPU latency/load testing as the final deployment gate.

The result is a measurement, not permission to retune against these labels.
"""),
])

notebook.setdefault("metadata", {}).setdefault("colab", {})["name"] = OUTPUT.name
OUTPUT.write_text(json.dumps(notebook, indent=1, ensure_ascii=False), encoding="utf-8")
print(OUTPUT)
