"""Extend the validated Iteration 2 notebook with frozen-rule and replay ablations."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "notebooks" / "SkyGuard_AI_GPU_Iteration_02_Weak_Fault_Rescue_Colab.ipynb"
OUTPUT = ROOT / "notebooks" / "SkyGuard_AI_GPU_Iteration_03_Frozen_and_Communication_Colab.ipynb"


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": text.splitlines(keepends=True)}


notebook = json.loads(SOURCE.read_text(encoding="utf-8"))
notebook["cells"][0] = md(r"""# SkyGuard AI — GPU Iteration 3

## Sensor-specific frozen detection and communication replay

Iteration 2 proved that the two-tier CatBoost policy improves incident performance across all three 2023 blocks, but its learned frozen/bias/drift specialists are not stable enough to claim generalization. This notebook reproduces Iteration 2 from saved Drive checkpoints and then makes one controlled addition:

1. Evaluate conservative, sensor-specific frozen rules using causal run length plus neighbour disagreement.
2. Keep a rule only if the complete detector still meets precision and false-alarm constraints in every block.
3. Evaluate duplicate packets in an actual replay simulation. Static feature rows contain `stream_action='duplicate'`; they are not physically duplicated until replay, so a static duplicate-key test is scientifically invalid.

The 2024 final tests remain sealed.
""")

notebook["cells"].extend([
md(r"""# Iteration 3 controlled experiment

Everything above reconstructs Iteration 2 and reuses its saved models. The cells below write only to `iteration_03_frozen_communication`.
"""),
code(r"""ITER3_ROOT=DRIVE_ROOT/'experiments'/'iteration_03_frozen_communication'
ITER3_ROOT.mkdir(parents=True,exist_ok=True)
print('Iteration 3 artifacts:',ITER3_ROOT)
"""),
md(r"""## 11. Sensor-specific frozen rules

Natural quantization differs strongly by sensor. Therefore a single frozen threshold is inappropriate. Candidate rules require both a constant-value run and disagreement from currently available neighbouring stations.
"""),
code(r"""FROZEN_CANDIDATES={
 'temperature':[None,(4,5.0),(8,4.0),(12,3.0)],
 'pressure':[None,(12,5.0),(16,3.0),(20,2.0)],
 'humidity':[None,(16,10.0),(12,10.0),(20,5.0)],
}

def sensor_frozen_rule(frame,sensor,config):
    if config is None: return pd.Series(False,index=frame.index)
    run_threshold,residual_threshold=config
    return (frame[f'{sensor}_frozen_run_length'].ge(run_threshold)&
            frame[f'neighbor_{sensor}_count'].ge(1)&
            frame[f'neighbor_{sensor}_residual'].abs().ge(residual_threshold))

def frozen_rule(frame,configs):
    result=pd.Series(False,index=frame.index)
    for sensor,config in configs.items(): result|=sensor_frozen_rule(frame,sensor,config)
    return result

def evaluate_frozen_configuration(configs):
    rows=[]
    for block in POLICY_BLOCKS:
        part=dev.loc[dev.dev_split.eq(block)].copy()
        part['iteration2_pred']=apply_two_tier(part,selected.base_start,selected.base_continue,
                                               selected.rescue_threshold,int(selected.min_points))
        part['frozen_rule']=frozen_rule(part,configs)
        part['candidate_pred']=part.iteration2_pred|part.frozen_rule
        reference=evaluate(part,'base_score','iteration2_pred')
        metric=evaluate(part,'base_score','candidate_pred')
        rows.append({'block':block,**metric,
                     'event_f1_delta':metric['event_f1']-reference['event_f1'],
                     'point_f1_delta':metric['f1']-reference['f1']})
    valid_frozen=[row['per_fault_episode_recall'].get('frozen_sensor') for row in rows
                  if row['per_fault_episode_recall'].get('frozen_sensor') is not None]
    return {
        'temperature':str(configs['temperature']),'pressure':str(configs['pressure']),
        'humidity':str(configs['humidity']),'rows':rows,
        'min_precision':min(row['precision'] for row in rows),
        'max_false_alarm':max(row['false_alarm_episodes_per_station_day'] for row in rows),
        'min_event_recall':min(row['event_recall'] for row in rows),
        'mean_event_f1':float(np.mean([row['event_f1'] for row in rows])),
        'min_event_f1_delta':min(row['event_f1_delta'] for row in rows),
        'mean_event_f1_delta':float(np.mean([row['event_f1_delta'] for row in rows])),
        'min_frozen_recall':min(valid_frozen) if valid_frozen else 0.0,
        'mean_frozen_recall':float(np.mean(valid_frozen)) if valid_frozen else 0.0,
    }

candidate_rows=[]
for temperature in FROZEN_CANDIDATES['temperature']:
 for pressure in FROZEN_CANDIDATES['pressure']:
  for humidity in FROZEN_CANDIDATES['humidity']:
    candidate_rows.append(evaluate_frozen_configuration({
        'temperature':temperature,'pressure':pressure,'humidity':humidity}))

frontier=pd.DataFrame([{k:v for k,v in row.items() if k!='rows'} for row in candidate_rows])
baseline_frozen=float(frontier.loc[
    frontier[['temperature','pressure','humidity']].eq('None').all(axis=1),'mean_frozen_recall'].iloc[0])
feasible=frontier.loc[(frontier.min_precision>=.75)&(frontier.max_false_alarm<=.02)&
                      (frontier.min_event_f1_delta>=-.01)&(frontier.mean_event_f1_delta>=0)]
if len(feasible):
    frozen_selected=feasible.sort_values(
        ['min_frozen_recall','mean_frozen_recall','mean_event_f1_delta','min_event_recall'],ascending=False).iloc[0]
    FROZEN_STATUS='constraints_met_all_blocks'
else:
    frontier['violation']=np.maximum(0,.75-frontier.min_precision)/.75+np.maximum(0,frontier.max_false_alarm-.02)/.02
    frozen_selected=frontier.sort_values(['violation','min_frozen_recall','mean_event_f1'],ascending=[True,False,False]).iloc[0]
    FROZEN_STATUS='pareto_fallback'

def parse_config(value):
    if value=='None': return None
    left,right=value.strip('()').split(','); return (int(left),float(right))

SELECTED_FROZEN_CONFIG={sensor:parse_config(frozen_selected[sensor]) for sensor in ['temperature','pressure','humidity']}
if float(frozen_selected.mean_frozen_recall)<=baseline_frozen:
    SELECTED_FROZEN_CONFIG={sensor:None for sensor in ['temperature','pressure','humidity']}
    FROZEN_STATUS='no_generalizable_gain_keep_iteration2'
frontier.to_csv(ITER3_ROOT/'iteration3_frozen_frontier.csv',index=False)
display(frozen_selected.to_frame('selected')); print(FROZEN_STATUS,SELECTED_FROZEN_CONFIG)
"""),
md("## 12. Clean contribution ablation"),
code(r"""rows=[]; combined=[]
for block in POLICY_BLOCKS:
    part=dev.loc[dev.dev_split.eq(block)].copy()
    part['cat_base']=hysteresis(part,'base_score',base_policy['threshold'],max(0,base_policy['threshold']-.08))
    part['cat_hard']=part.cat_base|part.hard_rule
    part['iteration2']=apply_two_tier(part,selected.base_start,selected.base_continue,
                                      selected.rescue_threshold,int(selected.min_points))
    part['frozen_only']=part.cat_hard|frozen_rule(part,SELECTED_FROZEN_CONFIG)
    part['iteration3']=part.iteration2|frozen_rule(part,SELECTED_FROZEN_CONFIG)
    for variant,pred in [('CatBoost base','cat_base'),('CatBoost + hard rules','cat_hard'),
                         ('Iteration2 learned rescue','iteration2'),('CatBoost + frozen rule','frozen_only'),
                         ('Iteration3 combined','iteration3')]:
        rows.append({'block':block,'variant':variant,**evaluate(part,'base_score',pred)})
    combined.append(part)

ablation3=pd.DataFrame(rows)
ablation3.to_csv(ITER3_ROOT/'iteration3_multiblock_ablation.csv',index=False)
display(ablation3[['block','variant','precision','recall','f1','event_precision','event_recall','event_f1',
                   'false_alarm_episodes_per_station_day','delay_mean_min','delay_p90_min']])

combined=pd.concat(combined,ignore_index=True); combined['pred']=combined.iteration3
fault_recall3=pd.Series(event_metrics(combined,'pred')['per_fault_episode_recall'],name='episode_recall').sort_values().to_frame()
fault_recall3.to_csv(ITER3_ROOT/'iteration3_fault_episode_recall.csv')
display(fault_recall3)
"""),
md(r"""## 13. Correct duplicate-packet evaluation through replay

The detector never reads `stream_action`. The simulator reads it and emits an identical packet twice. The operational rule then detects the second packet by a station/timestamp/value fingerprint. This mirrors the actual streaming engine.
"""),
code(r"""validation_full=load_table('validation')
replay_packets=[]
for _,row in validation_full.iterrows():
    packet={'station_id':row.station_id,'timestamp':row.emitted_timestamp_utc,
            'temperature':row.temperature_value,'pressure':row.pressure_value,'humidity':row.humidity_value,
            'episode_id':row.episode_id,'injected_duplicate':False}
    replay_packets.append(packet)
    if row.stream_action=='duplicate':
        duplicate=packet.copy(); duplicate['injected_duplicate']=True; replay_packets.append(duplicate)

def packet_fingerprint(packet):
    clean=lambda value: None if pd.isna(value) else value
    return (packet['station_id'],packet['timestamp'],clean(packet['temperature']),
            clean(packet['pressure']),clean(packet['humidity']))

seen=set(); tp=fp=fn=0; detected_episodes=set(); true_episodes=set()
for packet in replay_packets:
    fingerprint=packet_fingerprint(packet)
    prediction=fingerprint in seen; seen.add(fingerprint)
    truth=bool(packet['injected_duplicate'])
    tp+=int(prediction and truth); fp+=int(prediction and not truth); fn+=int(not prediction and truth)
    if truth and packet['episode_id']: true_episodes.add(packet['episode_id'])
    if prediction and truth and packet['episode_id']: detected_episodes.add(packet['episode_id'])

communication_result={
    'simulated_input_rows':int(len(validation_full)),
    'emitted_packets':int(len(replay_packets)),
    'duplicate_packet_tp':tp,'duplicate_packet_fp':fp,'duplicate_packet_fn':fn,
    'duplicate_packet_precision':tp/max(tp+fp,1),
    'duplicate_packet_recall':tp/max(tp+fn,1),
    'true_duplicate_episodes':len(true_episodes),
    'detected_duplicate_episodes':len(true_episodes&detected_episodes),
    'duplicate_episode_recall':len(true_episodes&detected_episodes)/max(len(true_episodes),1),
    'detector_inputs':['station_id','timestamp','temperature','pressure','humidity'],
    'stream_action_used_by_detector':False,
}
pd.DataFrame([communication_result]).to_csv(ITER3_ROOT/'iteration3_communication_replay.csv',index=False)
display(pd.Series(communication_result,name='replay'))
"""),
md("## 14. Save Iteration 3 result block"),
code(r"""iteration3_rows=ablation3.loc[ablation3.variant.eq('Iteration3 combined')]
result3={
 'iteration':'03_frozen_communication','device':DEVICE,'gpu':torch.cuda.get_device_name(0),
 'final_tests_opened':False,'frozen_policy_status':FROZEN_STATUS,
 'selected_frozen_config':SELECTED_FROZEN_CONFIG,
 'iteration3_blocks':iteration3_rows.drop(columns=['per_fault_episode_recall'],errors='ignore').to_dict('records'),
 'fault_episode_recall':fault_recall3.episode_recall.to_dict(),
 'communication_replay':communication_result,
 'weather_policy_unchanged':{'score':weather_selected.score,'threshold':float(weather_selected.threshold)},
}
(ITER3_ROOT/'iteration3_result_block.json').write_text(json.dumps(result3,indent=2,default=float))
print(json.dumps(result3,indent=2,default=float))
print('\nSEND BACK THESE FILES:')
for name in ['iteration3_result_block.json','iteration3_multiblock_ablation.csv',
             'iteration3_fault_episode_recall.csv','iteration3_communication_replay.csv']:
    print(ITER3_ROOT/name)
"""),
md(r"""## Decision rule

Promote the frozen rule only if it raises frozen episode recall while all three blocks retain precision ≥75% and false-alarm episodes ≤0.02/station-day. Duplicate-packet replay must reach 100% episode recall. The final 2024 evaluation remains a separate, one-time notebook after this result is reviewed.
"""),
])

notebook["metadata"]["colab"]["name"] = OUTPUT.name
OUTPUT.write_text(json.dumps(notebook, indent=1, ensure_ascii=False), encoding="utf-8")
print(OUTPUT)
