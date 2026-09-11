"""Extend Iteration 3 with a causal incident-state coverage experiment."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "notebooks" / "SkyGuard_AI_GPU_Iteration_03_Frozen_and_Communication_Colab.ipynb"
OUTPUT = ROOT / "notebooks" / "SkyGuard_AI_GPU_Iteration_04_Causal_Incident_State_Colab.ipynb"


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": text.splitlines(keepends=True)}


notebook = json.loads(SOURCE.read_text(encoding="utf-8"))
notebook["cells"][0] = md(r"""# SkyGuard AI — GPU Iteration 4

## Causal incident-state coverage

Iteration 3 correctly rejected non-generalizing frozen thresholds and validated duplicate-packet detection through full-stream replay. The remaining point-level weakness is concentrated inside long, already-detected incidents. This notebook tests a causal finite-state alert controller that can maintain an active incident while weak supporting evidence continues.

The controller:

1. Starts only from the validated Iteration 2/3 detector trigger.
2. Uses only present and past observations.
3. Never opens a new incident from weak support alone.
4. Is promoted only if every development block preserves precision, false-alarm, event-F1, and point-F1 safeguards.
5. Leaves the 2024 final tests sealed.
""")

notebook["cells"].extend([
md(r"""# Iteration 4 controlled experiment

Everything above reconstructs Iterations 2 and 3 from saved Drive checkpoints. The cells below write only to `iteration_04_causal_incident_state`.
"""),
code(r"""ITER4_ROOT=DRIVE_ROOT/'experiments'/'iteration_04_causal_incident_state'
ITER4_ROOT.mkdir(parents=True,exist_ok=True)
print('Iteration 4 artifacts:',ITER4_ROOT)
"""),
md(r"""## 15. Causal incident-state controller

`grace_minutes` allows a live alert to remain active briefly after its latest strong or supporting observation. `support_threshold` is applied to the maximum calibrated CatBoost/specialist score and cannot start an incident. `max_duration_minutes` prevents an alert from remaining active indefinitely.
"""),
code(r"""def causal_incident_state(frame,trigger_col,grace_minutes,support_threshold,max_duration_minutes):
    result=pd.Series(False,index=frame.index)
    for _,g in frame.groupby('station_id',sort=False):
        g=g.sort_values('emitted_timestamp_utc')
        times=g.emitted_timestamp_utc.tolist()
        triggers=g[trigger_col].fillna(False).to_numpy(bool)
        support=np.maximum(g.base_score.fillna(0).to_numpy(float),g.rescue_score.fillna(0).to_numpy(float))
        out=np.zeros(len(g),bool); active=False; start=None; last_evidence=None
        for pos,(timestamp,trigger,score) in enumerate(zip(times,triggers,support)):
            if trigger:
                if not active: start=timestamp
                active=True; last_evidence=timestamp; out[pos]=True
                continue
            if not active: continue
            elapsed=(timestamp-start).total_seconds()/60
            since_evidence=(timestamp-last_evidence).total_seconds()/60
            if elapsed>max_duration_minutes:
                active=False; start=None; last_evidence=None; continue
            if score>=support_threshold:
                last_evidence=timestamp; out[pos]=True
            elif since_evidence<=grace_minutes:
                out[pos]=True
            else:
                active=False; start=None; last_evidence=None
        result.loc[g.index]=out
    return result

STATE_CANDIDATES={
    'grace_minutes':[0,60,180,360],
    'support_threshold':[.10,.20,.30,1.10],
    'max_duration_minutes':[720,1440],
}

STATE_REFERENCE={}
for block in POLICY_BLOCKS:
    part=dev.loc[dev.dev_split.eq(block)].copy()
    part['iteration3_trigger']=apply_two_tier(part,selected.base_start,selected.base_continue,
                                              selected.rescue_threshold,int(selected.min_points))
    part['iteration3_trigger']|=frozen_rule(part,SELECTED_FROZEN_CONFIG)
    STATE_REFERENCE[block]=evaluate(part,'base_score','iteration3_trigger')

def evaluate_state_configuration(grace_minutes,support_threshold,max_duration_minutes):
    rows=[]
    for block in POLICY_BLOCKS:
        part=dev.loc[dev.dev_split.eq(block)].copy()
        part['iteration3_trigger']=apply_two_tier(part,selected.base_start,selected.base_continue,
                                                  selected.rescue_threshold,int(selected.min_points))
        part['iteration3_trigger']|=frozen_rule(part,SELECTED_FROZEN_CONFIG)
        part['candidate_pred']=causal_incident_state(part,'iteration3_trigger',grace_minutes,
                                                     support_threshold,max_duration_minutes)
        metric=evaluate(part,'base_score','candidate_pred'); reference=STATE_REFERENCE[block]
        rows.append({'block':block,**metric,
                     'point_f1_delta':metric['f1']-reference['f1'],
                     'event_f1_delta':metric['event_f1']-reference['event_f1']})
    return {
        'grace_minutes':grace_minutes,'support_threshold':support_threshold,
        'max_duration_minutes':max_duration_minutes,'rows':rows,
        'min_precision':min(row['precision'] for row in rows),
        'max_false_alarm':max(row['false_alarm_episodes_per_station_day'] for row in rows),
        'min_point_f1':min(row['f1'] for row in rows),
        'mean_point_f1':float(np.mean([row['f1'] for row in rows])),
        'min_point_f1_delta':min(row['point_f1_delta'] for row in rows),
        'mean_point_f1_delta':float(np.mean([row['point_f1_delta'] for row in rows])),
        'min_event_recall':min(row['event_recall'] for row in rows),
        'min_event_f1_delta':min(row['event_f1_delta'] for row in rows),
        'mean_event_f1_delta':float(np.mean([row['event_f1_delta'] for row in rows])),
    }

state_candidates=[]
for grace in STATE_CANDIDATES['grace_minutes']:
 for support in STATE_CANDIDATES['support_threshold']:
  for maximum in STATE_CANDIDATES['max_duration_minutes']:
    state_candidates.append(evaluate_state_configuration(grace,support,maximum))

state_frontier=pd.DataFrame([{k:v for k,v in row.items() if k!='rows'} for row in state_candidates])
feasible=state_frontier.loc[(state_frontier.min_precision>=.75)&
                            (state_frontier.max_false_alarm<=.02)&
                            (state_frontier.min_point_f1_delta>=0)&
                            (state_frontier.min_event_f1_delta>=-.01)&
                            (state_frontier.mean_event_f1_delta>=0)]
if len(feasible):
    state_selected=feasible.sort_values(
        ['min_point_f1','mean_point_f1','min_event_recall','mean_event_f1_delta'],ascending=False).iloc[0]
    STATE_STATUS='constraints_met_all_blocks'
    safe_selection=True
else:
    state_selected=state_frontier.sort_values(
        ['min_point_f1_delta','mean_point_f1_delta','mean_event_f1_delta'],ascending=False).iloc[0]
    STATE_STATUS='no_safe_candidate_keep_iteration3'
    safe_selection=False

if not safe_selection:
    SELECTED_STATE={'grace_minutes':0,'support_threshold':1.10,'max_duration_minutes':720}
elif float(state_selected.mean_point_f1_delta)<=0:
    STATE_STATUS='no_generalizable_gain_keep_iteration3'
    SELECTED_STATE={'grace_minutes':0,'support_threshold':1.10,'max_duration_minutes':720}
else:
    SELECTED_STATE={k:(int(state_selected[k]) if k!='support_threshold' else float(state_selected[k]))
                    for k in ['grace_minutes','support_threshold','max_duration_minutes']}

state_frontier.to_csv(ITER4_ROOT/'iteration4_state_frontier.csv',index=False)
display(state_selected.to_frame('selected')); print(STATE_STATUS,SELECTED_STATE)
"""),
md("## 16. Multiblock ablation and fault coverage"),
code(r"""rows=[]; combined=[]
for block in POLICY_BLOCKS:
    part=dev.loc[dev.dev_split.eq(block)].copy()
    part['iteration3']=apply_two_tier(part,selected.base_start,selected.base_continue,
                                      selected.rescue_threshold,int(selected.min_points))
    part['iteration3']|=frozen_rule(part,SELECTED_FROZEN_CONFIG)
    part['iteration4']=causal_incident_state(part,'iteration3',**SELECTED_STATE)
    for variant,pred in [('Iteration3 trigger','iteration3'),('Iteration4 causal state','iteration4')]:
        rows.append({'block':block,'variant':variant,**evaluate(part,'base_score',pred)})
    combined.append(part)

ablation4=pd.DataFrame(rows)
ablation4.to_csv(ITER4_ROOT/'iteration4_multiblock_ablation.csv',index=False)
display(ablation4[['block','variant','precision','recall','f1','event_precision','event_recall','event_f1',
                   'false_alarm_episodes_per_station_day','delay_mean_min','delay_p90_min']])

combined=pd.concat(combined,ignore_index=True); combined['pred']=combined.iteration4
fault_recall4=pd.Series(event_metrics(combined,'pred')['per_fault_episode_recall'],name='episode_recall').sort_values().to_frame()
fault_recall4.to_csv(ITER4_ROOT/'iteration4_fault_episode_recall.csv')

fault_rows=combined.loc[combined.is_anomaly.eq(1)]
point_fault_recall4=(fault_rows.groupby('anomaly_type').pred.mean().rename('point_recall').sort_values().to_frame())
point_fault_recall4.to_csv(ITER4_ROOT/'iteration4_point_fault_recall.csv')
display(fault_recall4); display(point_fault_recall4)
"""),
md(r"""## 17. Operational communication coverage

Duplicate packets are evaluated through replay, not static feature rows. Therefore the operational coverage table replaces the static duplicate value with the validated replay result while retaining both values for auditability.
"""),
code(r"""operational_fault_recall=fault_recall4.episode_recall.to_dict()
static_duplicate_recall=float(operational_fault_recall.get('duplicate_packet',0.0))
operational_fault_recall['duplicate_packet']=float(communication_result['duplicate_episode_recall'])
communication_coverage={
    'static_duplicate_recall_not_operational':static_duplicate_recall,
    'replay_duplicate_packet_precision':float(communication_result['duplicate_packet_precision']),
    'replay_duplicate_packet_recall':float(communication_result['duplicate_packet_recall']),
    'replay_duplicate_episode_recall':float(communication_result['duplicate_episode_recall']),
}
display(pd.Series(communication_coverage,name='communication'))
"""),
md("## 18. Save Iteration 4 result block"),
code(r"""iteration4_rows=ablation4.loc[ablation4.variant.eq('Iteration4 causal state')]
result4={
 'iteration':'04_causal_incident_state','device':DEVICE,'gpu':torch.cuda.get_device_name(0),
 'final_tests_opened':False,'state_policy_status':STATE_STATUS,'selected_state':SELECTED_STATE,
 'iteration4_blocks':iteration4_rows.drop(columns=['per_fault_episode_recall'],errors='ignore').to_dict('records'),
 'fault_episode_recall_static':fault_recall4.episode_recall.to_dict(),
 'fault_episode_recall_operational':operational_fault_recall,
 'point_fault_recall':point_fault_recall4.point_recall.to_dict(),
 'communication_coverage':communication_coverage,
 'frozen_rule_promoted':any(value is not None for value in SELECTED_FROZEN_CONFIG.values()),
}
(ITER4_ROOT/'iteration4_result_block.json').write_text(json.dumps(result4,indent=2,default=float))
print(json.dumps(result4,indent=2,default=float))
print('\nSEND BACK THESE FILES:')
for name in ['iteration4_result_block.json','iteration4_state_frontier.csv',
             'iteration4_multiblock_ablation.csv','iteration4_fault_episode_recall.csv',
             'iteration4_point_fault_recall.csv']:
    print(ITER4_ROOT/name)
"""),
md(r"""## Decision rule

Promote the causal state only if every development block preserves at least 75% precision, at most 0.02 false-alarm episodes per station-day, non-decreasing point F1, no more than 0.01 event-F1 loss in any block, non-decreasing mean event F1, and a positive mean point-F1 gain. Otherwise keep the Iteration 3/2 detector unchanged.

This experiment changes alert persistence only. It does not claim to improve previously missed frozen, drift, or bias episodes, and it does not access the 2024 final tests.
"""),
])

notebook.setdefault("metadata", {}).setdefault("colab", {})["name"] = OUTPUT.name
OUTPUT.write_text(json.dumps(notebook, indent=1, ensure_ascii=False), encoding="utf-8")
print(OUTPUT)
