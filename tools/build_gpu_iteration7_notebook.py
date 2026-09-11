"""Build SkyGuard GPU Iteration 7: calibrated weather transfer and causal TCN consensus."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "notebooks" / "SkyGuard_AI_GPU_Iteration_06_Communication_Weather_Transfer_Colab.ipynb"
OUTPUT = ROOT / "notebooks" / "SkyGuard_AI_GPU_Iteration_07_Climate_Calibration_Causal_TCN_Colab.ipynb"


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
            "SEND BACK THESE ITERATION 6 FILES:",
            "HISTORICAL ITERATION 6 FILES — continue running; do not return these yet:",
        )
    elif cell.get("cell_type") == "markdown":
        source = source.replace("## Iteration 6 decision", "## Historical Iteration 6 decision — continue to Iteration 7")
    cell["source"] = source.splitlines(keepends=True)

notebook["cells"][0] = md(r"""# SkyGuard AI — GPU Iteration 7

## Climate-calibrated weather transfer and causal TCN consensus

Iteration 6 correctly refused three unsafe promotions. It established that unknown-cadence archive gaps must remain advisory, found a weather challenger that missed the station-macro gate by a small margin, and showed that a point-level weak-fault rescue did not transfer to October or pseudo-unseen stations.

Iteration 7 therefore changes the representation rather than relaxing any gate:

1. Freeze the heartbeat-contract communication policy.
2. Convert station-invariant weather scores to climate-cluster percentiles and train sparse L1/L2 meta-calibrators.
3. Train a small causal temporal convolutional network on relative, causal sequences only.
4. Require tree–TCN consensus and incident persistence for weak-fault rescue.
5. Promote nothing unless May–September discovery, October confirmation, and pseudo-unseen station confirmation all pass.

The 2024 and 2025 benchmark files remain sealed. All earlier sections are reconstruction checkpoints and must be run in order.
""")

notebook["cells"][1] = md(r"""## Run instructions

1. Keep `SkyGuard_GPU_Data_Bundle.zip` in `/content/drive/MyDrive/SkyGuard_AI_GPU/`.
2. In Colab select **Runtime → Change runtime type → T4 GPU**.
3. Run the notebook from the first cell through the final Iteration 7 cell without skipping historical reconstruction cells.
4. Keep `UNLOCK_FINAL_TESTS=False` and `REUSE_SAVED_MODELS=True`.
5. Expected runtime is approximately 45–100 minutes when prior CatBoost/LightGBM models already exist; rebuilding all historical models can take longer.
6. Return only the twelve Iteration 7 files printed by the final cell. Do not send or use any 2025 label file for tuning.
""")

notebook["cells"].extend([
    md(r"""# Iteration 7 controlled development phase

The only model-observation inputs remain temperature, atmospheric pressure, and relative humidity. Station identifier, cluster, timestamps and neighbour metadata are routing/context metadata, not additional meteorological measurements. No future row, dew point, 2024 label or 2025 label is permitted.
"""),
    code(r"""from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from torch import nn
from torch.utils.data import Dataset,DataLoader
import torch.nn.functional as F

ITER7_ROOT=DRIVE_ROOT/'experiments'/'iteration_07_climate_calibration_causal_tcn'
ITER7_ROOT.mkdir(parents=True,exist_ok=True)
assert UNLOCK_FINAL_TESTS is False,'Iteration 7 must keep all former final tests locked.'
assert 'blind_2025' not in str(ITER7_ROOT).lower()
assert result6['blind_2025_opened'] is False and result6['former_final_tests_opened'] is False
assert result6['weather']['status']=='no_confirmed_weather_gain_keep_iteration5_weather'
assert result6['weak_fault_transfer']['status']=='no_station_transfer_gain_keep_iteration5_candidate'

ITER7_DISCOVERY_BLOCKS=['block_may_jun','block_jul_sep']
ITER7_CONFIRMATION_SCOPES={
    'oct_dec_discovery':discovery&dev.dev_split.eq('block_oct_dec'),
    'pseudo_unseen_all_2023':pseudo&dev.dev_split.isin(POLICY_BLOCKS),
}
dev['iteration7_reference']=dev.iteration5_reference.astype(bool)
print('Iteration 7 root:',ITER7_ROOT)
print('Discovery stations:',len(DISCOVERY_STATIONS),'| pseudo-unseen:',PSEUDO_HOLDOUT_STATIONS)
"""),
    md(r"""## 27. Freeze the communication safety contract

An unknown-cadence silence is not identifiable as a station failure from archive timestamps alone. Iteration 7 carries the validated policy forward unchanged and emits a machine-readable adapter contract for the API/dashboard phase.
"""),
    code(r"""ITER7_COMMUNICATION_CONTRACT={
    'version':'1.0',
    'automatic_duplicate_detection':True,
    'automatic_dropout_alert_requires':{
        'expected_cadence_seconds':'positive integer supplied by source adapter',
        'heartbeat_sla_seconds':'positive integer supplied by source adapter',
        'source_contract_verified':True,
    },
    'unknown_cadence_status':'unverified_data_gap_advisory',
    'unknown_cadence_is_sensor_fault':False,
    'maintenance_ticket_from_unknown_gap':False,
    'detector_observation_inputs':['temperature','pressure','relative_humidity'],
    'communication_metadata':['station_id','arrival_timestamp','expected_cadence_seconds','heartbeat_sla_seconds'],
}
assert SELECTED_GAP_POLICY['automatic_fault_alert_without_contract'] is False
(ITER7_ROOT/'iteration7_communication_contract.json').write_text(
    json.dumps(ITER7_COMMUNICATION_CONTRACT,indent=2))
display(pd.Series(ITER7_COMMUNICATION_CONTRACT,name='contract').to_frame())
"""),
    md(r"""## 28. Climate-cluster percentile calibration

The Iteration 6 weather models improved average F1 but shifted score distributions between stations. A fixed global threshold therefore helped some stations and hurt others. The calibrator below learns empirical score distributions from clean discovery-station history and maps each score to a climate-cluster percentile. Pseudo-unseen stations receive only their cluster reference; no station-specific label or threshold is fitted.
"""),
    code(r"""WEATHER7_SCORE_COLUMNS=['weather6_cat','weather6_lgb','weather6_mean','weather6_geom']
WEATHER7_CONTEXT_CANDIDATES=[
    'regional_agreement_mean','regional_agreement_min','regional_agreeing_sensor_count',
    'regional_standardized_disagreement_max','regional_trend_disagreement_mean',
    'neighbor_temperature_agreement_fraction','neighbor_pressure_agreement_fraction',
    'neighbor_humidity_agreement_fraction','temperature_slope_3h','temperature_slope_6h',
    'pressure_slope_3h','pressure_slope_6h','humidity_slope_3h','humidity_slope_6h',
    'temperature_neighbor_residual_slope_3h','pressure_neighbor_residual_slope_3h',
    'humidity_neighbor_residual_slope_3h','temperature_robust_z_24h','pressure_robust_z_24h',
    'humidity_robust_z_24h',
]
WEATHER7_CONTEXT_FEATURES=[feature for feature in WEATHER7_CONTEXT_CANDIDATES if feature in dev.columns]
assert len(WEATHER7_CONTEXT_FEATURES)>=15

weather7_reference_mask=(
    discovery&dev.dev_split.eq('tune_model')&dev.is_weather_event.eq(0)&dev.is_anomaly.eq(0))

def fit_cluster_ecdf(frame,mask,score_columns):
    references={'cluster':{},'global':{}}
    for score_col in score_columns:
        global_values=np.sort(frame.loc[mask,score_col].dropna().to_numpy(float))
        assert len(global_values)>=100
        references['global'][score_col]=global_values
    for cluster,group in frame.loc[mask].groupby('cluster'):
        references['cluster'][str(cluster)]={}
        for score_col in score_columns:
            values=np.sort(group[score_col].dropna().to_numpy(float))
            references['cluster'][str(cluster)][score_col]=values
    return references

def apply_cluster_ecdf(frame,references,score_col):
    result=np.zeros(len(frame),dtype=float)
    for cluster,positions in frame.groupby('cluster',sort=False).indices.items():
        cluster_ref=references['cluster'].get(str(cluster),{}).get(score_col)
        reference=cluster_ref if cluster_ref is not None and len(cluster_ref)>=50 else references['global'][score_col]
        values=frame.iloc[positions][score_col].fillna(-np.inf).to_numpy(float)
        result[np.asarray(positions,dtype=int)]=np.searchsorted(reference,values,side='right')/max(len(reference),1)
    return np.clip(result,0,1)

weather7_ecdf=fit_cluster_ecdf(dev,weather7_reference_mask,WEATHER7_SCORE_COLUMNS)
for score_col in WEATHER7_SCORE_COLUMNS:
    dev[f'{score_col}_cluster_pct']=apply_cluster_ecdf(dev,weather7_ecdf,score_col)

WEATHER7_META_FEATURES=(
    [f'{score_col}_cluster_pct' for score_col in WEATHER7_SCORE_COLUMNS]+WEATHER7_CONTEXT_FEATURES)
assert not ({'temperature_value','pressure_value','humidity_value','station_id'}&set(WEATHER7_META_FEATURES))
print('Weather meta features:',len(WEATHER7_META_FEATURES))
"""),
    code(r"""weather7_fit=discovery&dev.dev_split.eq('tune_model')
weather7_y=dev.is_weather_event.astype(int)
assert int(weather7_y.loc[weather7_fit].sum())>=20
weather7_weights=station_episode_balanced_weights(
    dev.loc[weather7_fit],weather7_y.loc[weather7_fit].to_numpy(bool))

def weather7_pipeline(penalty,C):
    return Pipeline([
        ('imputer',SimpleImputer(strategy='median',add_indicator=True)),
        ('scale',StandardScaler()),
        ('lr',LogisticRegression(
            penalty=penalty,C=C,solver='liblinear',class_weight=None,
            max_iter=2000,random_state=17)),
    ])

weather7_models={
    'weather7_l1':weather7_pipeline('l1',.30),
    'weather7_l2':weather7_pipeline('l2',.30),
}
for name,model in weather7_models.items():
    model.fit(dev.loc[weather7_fit,WEATHER7_META_FEATURES],weather7_y.loc[weather7_fit],
              lr__sample_weight=weather7_weights)
    dev[name]=model.predict_proba(dev[WEATHER7_META_FEATURES])[:,1]
    joblib.dump(model,ITER7_ROOT/f'{name}.joblib')

dev['weather7_blend']=(dev.weather7_l1+dev.weather7_l2)/2
weather7_nonzero={name:int(np.count_nonzero(model.named_steps['lr'].coef_))
                  for name,model in weather7_models.items()}
print('Weather calibrator non-zero coefficients:',weather7_nonzero)
"""),
    code(r"""WEATHER7_SCORE_OPTIONS=['weather7_l1','weather7_l2','weather7_blend']

def weather7_candidate_summary(score_col,threshold):
    rows=[]
    for block in ITER7_DISCOVERY_BLOCKS:
        part=dev.loc[discovery&dev.dev_split.eq(block)].copy()
        part['baseline_pred']=part.cat_weather_mean.ge(float(WEATHER_GUARD_THRESHOLD))
        part['candidate_pred']=part[score_col].ge(float(threshold))
        baseline=weather_quality(part,'baseline_pred','cat_weather_mean')
        candidate=weather_quality(part,'candidate_pred',score_col)
        rows.append({
            'scope':block,**candidate,
            'f1_delta':candidate['weather_f1']-baseline['weather_f1'],
            'macro_delta':candidate['positive_station_macro_f1']-baseline['positive_station_macro_f1'],
        })
    return {
        'score_col':score_col,'threshold':float(threshold),'rows':rows,
        'min_f1_delta':float(min(row['f1_delta'] for row in rows)),
        'mean_f1_delta':float(np.mean([row['f1_delta'] for row in rows])),
        'min_macro_delta':float(min(row['macro_delta'] for row in rows)),
        'max_fault_to_weather':float(max(row['fault_to_weather_rate'] for row in rows)),
        'mean_weather_f1':float(np.mean([row['weather_f1'] for row in rows])),
    }

def weather7_discovery_pass(row):
    return (
        row['min_f1_delta']>=0 and row['mean_f1_delta']>0 and
        row['min_macro_delta']>=-.02 and row['max_fault_to_weather']<=.01)

weather7_candidates=[]
for score_col in WEATHER7_SCORE_OPTIONS:
    for threshold in np.linspace(.05,.95,37):
        weather7_candidates.append(weather7_candidate_summary(score_col,threshold))

weather7_frontier=pd.DataFrame([
    {key:value for key,value in row.items() if key!='rows'} for row in weather7_candidates])
weather7_frontier['passes_discovery']=weather7_frontier.apply(
    lambda row:weather7_discovery_pass(row.to_dict()),axis=1)
weather7_frontier.to_csv(ITER7_ROOT/'iteration7_weather_policy_frontier.csv',index=False)

weather7_feasible=[row for row in weather7_candidates if weather7_discovery_pass(row)]
proposed_weather7=(sorted(
    weather7_feasible,
    key=lambda row:(row['min_macro_delta'],row['mean_weather_f1'],row['mean_f1_delta']),
    reverse=True)[0] if weather7_feasible else None)
print('Weather discovery-feasible:',len(weather7_feasible),'of',len(weather7_candidates))
display(weather7_frontier.sort_values(
    ['passes_discovery','min_macro_delta','mean_weather_f1'],ascending=False).head(15))
"""),
    code(r"""WEATHER7_CONFIRM_COLUMNS=[
    'scope','current_weather_precision','current_weather_recall','current_weather_f1',
    'current_weather_auprc','current_positive_station_macro_f1','current_fault_to_weather_rate',
    'candidate_weather_precision','candidate_weather_recall','candidate_weather_f1',
    'candidate_weather_auprc','candidate_positive_station_macro_f1','candidate_fault_to_weather_rate',
    'f1_delta','macro_delta']

weather7_confirmation=[]
if proposed_weather7:
    for scope,mask in ITER7_CONFIRMATION_SCOPES.items():
        weather7_confirmation.append(compare_weather_scope(
            mask,proposed_weather7['score_col'],proposed_weather7['threshold'],scope))

weather7_confirmation_frame=pd.DataFrame(weather7_confirmation,columns=WEATHER7_CONFIRM_COLUMNS)
weather7_confirmation_pass=(len(weather7_confirmation_frame)==2 and all(
    row['f1_delta']>=0 and row['macro_delta']>=-.02 and
    row['candidate_fault_to_weather_rate']<=.01
    for row in weather7_confirmation))

if proposed_weather7 and weather7_confirmation_pass:
    WEATHER7_STATUS='climate_calibrated_weather_confirmed'
    SELECTED_WEATHER7={
        'score_col':proposed_weather7['score_col'],
        'threshold':proposed_weather7['threshold']}
else:
    WEATHER7_STATUS='no_confirmed_weather_gain_keep_iteration5_weather'
    SELECTED_WEATHER7={'score_col':'cat_weather_mean','threshold':float(WEATHER_GUARD_THRESHOLD)}

weather7_confirmation_frame.to_csv(ITER7_ROOT/'iteration7_weather_confirmation.csv',index=False)
dev['weather7_prediction']=dev[SELECTED_WEATHER7['score_col']].ge(float(SELECTED_WEATHER7['threshold']))
print('Weather status:',WEATHER7_STATUS,SELECTED_WEATHER7)
display(weather7_confirmation_frame)
"""),
    code(r"""weather7_station_rows=[]
for scope,mask in {
    **{block:discovery&dev.dev_split.eq(block) for block in ITER7_DISCOVERY_BLOCKS},
    **ITER7_CONFIRMATION_SCOPES,
}.items():
    for station,group in dev.loc[mask].groupby('station_id'):
        if group.is_weather_event.sum()==0:
            continue
        baseline=group.cat_weather_mean.ge(float(WEATHER_GUARD_THRESHOLD))
        candidate=group[SELECTED_WEATHER7['score_col']].ge(float(SELECTED_WEATHER7['threshold']))
        weather7_station_rows.append({
            'scope':scope,'station_id':str(station),'cluster':str(group.cluster.iloc[0]),
            'weather_rows':int(group.is_weather_event.sum()),
            'baseline_f1':float(f1_score(group.is_weather_event,baseline,zero_division=0)),
            'candidate_f1':float(f1_score(group.is_weather_event,candidate,zero_division=0)),
        })
weather7_station_metrics=pd.DataFrame(weather7_station_rows)
if len(weather7_station_metrics):
    weather7_station_metrics['f1_delta']=weather7_station_metrics.candidate_f1-weather7_station_metrics.baseline_f1
weather7_station_metrics.to_csv(ITER7_ROOT/'iteration7_weather_station_metrics.csv',index=False)
display(weather7_station_metrics.sort_values(['scope','f1_delta']).head(20))
"""),
    md(r"""## 29. Causal TCN for weak-fault sequence evidence

The tree models see a feature row at a time. Bias and drift are weak sequence phenomena, so Iteration 7 adds a compact causal TCN. Every window ends at the current observation; left padding is used at the start of a station history, and no future observation enters a window.

Raw temperature, raw pressure, raw humidity, calendar encodings and dew point are excluded. The TCN sees relative residuals, slopes, CUSUM, frozen runs, timing gaps and neighbour disagreement only.
"""),
    code(r"""WEAK7_SEQUENCE_CANDIDATES=[
    'time_since_previous_minutes','gap_ratio','primary_missing_count','out_of_order_indicator',
    'temperature_delta1','temperature_rate_per_hour','temperature_rolling_mad_24h',
    'temperature_robust_z_24h','temperature_ewma_residual','temperature_frozen_run_length',
    'pressure_delta1','pressure_rate_per_hour','pressure_rolling_mad_24h',
    'pressure_robust_z_24h','pressure_ewma_residual','pressure_frozen_run_length',
    'humidity_delta1','humidity_rate_per_hour','humidity_rolling_mad_24h',
    'humidity_robust_z_24h','humidity_ewma_residual','humidity_frozen_run_length',
    'neighbor_temperature_residual','neighbor_pressure_residual','neighbor_humidity_residual',
    'temperature_slope_3h','temperature_slope_6h','temperature_slope_12h',
    'pressure_slope_3h','pressure_slope_6h','pressure_slope_12h',
    'humidity_slope_3h','humidity_slope_6h','humidity_slope_12h',
    'temperature_neighbor_residual_slope_3h','pressure_neighbor_residual_slope_3h',
    'humidity_neighbor_residual_slope_3h','temperature_cusum_positive','temperature_cusum_negative',
    'pressure_cusum_positive','pressure_cusum_negative','humidity_cusum_positive','humidity_cusum_negative',
    'temperature_monotonic_run','pressure_monotonic_run','humidity_monotonic_run',
    'regional_agreement_mean','regional_agreement_min','regional_standardized_disagreement_max',
    'regional_trend_disagreement_mean',
]
WEAK7_SEQUENCE_FEATURES=[feature for feature in WEAK7_SEQUENCE_CANDIDATES if feature in dev.columns]
assert len(WEAK7_SEQUENCE_FEATURES)>=40
assert not ({'temperature_value','pressure_value','humidity_value','temperature_lag1',
             'pressure_lag1','humidity_lag1','temperature_dewpoint_spread_c'}&set(WEAK7_SEQUENCE_FEATURES))

weak7_train_mask=discovery&dev.dev_split.eq('train')
weak7_tune_mask=discovery&dev.dev_split.eq('tune_model')
weak7_y=dev.anomaly_type.isin(WEAK_TYPES).astype(np.float32)

normalizer_source=dev.loc[weak7_train_mask,WEAK7_SEQUENCE_FEATURES].replace([np.inf,-np.inf],np.nan)
weak7_median=normalizer_source.median().fillna(0)
weak7_iqr=(normalizer_source.quantile(.75)-normalizer_source.quantile(.25)).replace(0,1).fillna(1)
weak7_matrix=((dev[WEAK7_SEQUENCE_FEATURES].replace([np.inf,-np.inf],np.nan)-weak7_median)/weak7_iqr)
weak7_matrix=weak7_matrix.clip(-20,20).fillna(0).to_numpy(np.float32)

WEAK7_WINDOW=24
weak7_station_arrays={}; weak7_row_station=np.empty(len(dev),dtype=object); weak7_row_position=np.zeros(len(dev),dtype=np.int32)
for station,group in dev.sort_values(['station_id','emitted_timestamp_utc']).groupby('station_id',sort=False):
    rows=group.index.to_numpy(int)
    weak7_station_arrays[str(station)]=weak7_matrix[rows]
    weak7_row_station[rows]=str(station)
    weak7_row_position[rows]=np.arange(len(rows),dtype=np.int32)

weak7_global_weights=np.ones(len(dev),dtype=np.float32)
train_rows_all=np.flatnonzero(weak7_train_mask.to_numpy(bool))
balanced_result=station_episode_balanced_weights(
    dev.loc[weak7_train_mask],weak7_y.loc[weak7_train_mask].to_numpy(bool))
# Iteration 6 returns the weight array directly. Keep tuple compatibility so this
# continuation also works if an older reconstruction helper returns (weights, audit).
balanced=balanced_result[0] if isinstance(balanced_result,tuple) else balanced_result
weak7_global_weights[train_rows_all]=balanced.astype(np.float32)
print('TCN sequence features:',len(WEAK7_SEQUENCE_FEATURES),'| window:',WEAK7_WINDOW)
"""),
    code(r"""class Weak7WindowDataset(Dataset):
    def __init__(self,rows,include_weight=True):
        self.rows=np.asarray(rows,dtype=np.int64); self.include_weight=include_weight
    def __len__(self): return len(self.rows)
    def __getitem__(self,index):
        row=int(self.rows[index]); station=weak7_row_station[row]; position=int(weak7_row_position[row])
        source=weak7_station_arrays[station]
        start=max(0,position-WEAK7_WINDOW+1); window=source[start:position+1]
        if len(window)<WEAK7_WINDOW:
            window=np.pad(window,((WEAK7_WINDOW-len(window),0),(0,0)),mode='constant')
        x=torch.from_numpy(window.T.copy())
        y=torch.tensor(weak7_y.iloc[row],dtype=torch.float32)
        weight=torch.tensor(weak7_global_weights[row] if self.include_weight else 1.0,dtype=torch.float32)
        return x,y,weight

class CausalConvBlock(nn.Module):
    def __init__(self,channels,kernel,dilation,dropout):
        super().__init__()
        self.left=(kernel-1)*dilation
        self.conv=nn.Conv1d(channels,channels,kernel,dilation=dilation)
        self.norm=nn.GroupNorm(1,channels)
        self.drop=nn.Dropout(dropout)
    def forward(self,x):
        residual=x
        x=self.conv(F.pad(x,(self.left,0)))
        x=self.drop(F.gelu(self.norm(x)))
        return x+residual

class Weak7TCN(nn.Module):
    def __init__(self,input_channels,channels=48):
        super().__init__()
        self.input=nn.Conv1d(input_channels,channels,1)
        self.blocks=nn.Sequential(
            CausalConvBlock(channels,3,1,.10),
            CausalConvBlock(channels,3,2,.10),
            CausalConvBlock(channels,3,4,.10),
            CausalConvBlock(channels,3,8,.10),
        )
        self.head=nn.Sequential(nn.Linear(channels,24),nn.GELU(),nn.Dropout(.10),nn.Linear(24,1))
    def forward(self,x):
        z=self.blocks(self.input(x))
        return self.head(z[:,:,-1]).squeeze(1)

def weak7_training_rows(seed):
    rng=np.random.default_rng(seed)
    train_mask=weak7_train_mask.to_numpy(bool); positive=weak7_y.to_numpy(bool)
    positive_rows=np.flatnonzero(train_mask&positive)
    negative_rows=np.flatnonzero(train_mask&~positive)
    hard=(dev.is_anomaly.eq(1)|dev.is_weather_event.eq(1)|
          dev.weak6_geom.ge(dev.loc[weak7_train_mask,'weak6_geom'].quantile(.90))).to_numpy(bool)
    hard_rows=np.flatnonzero(train_mask&~positive&hard)
    random_pool=np.setdiff1d(negative_rows,hard_rows,assume_unique=False)
    random_count=min(len(random_pool),max(4*len(positive_rows),20000))
    random_rows=rng.choice(random_pool,size=random_count,replace=False)
    return np.unique(np.concatenate([positive_rows,hard_rows,random_rows]))

def predict_weak7_tcn(model,rows,batch_size=2048):
    loader=DataLoader(Weak7WindowDataset(rows,include_weight=False),batch_size=batch_size,
                      shuffle=False,num_workers=0,pin_memory=True)
    output=[]; model.eval()
    with torch.no_grad():
        for x,_,_ in loader:
            output.append(torch.sigmoid(model(x.to(DEVICE,non_blocking=True))).cpu().numpy())
    return np.concatenate(output)
"""),
    code(r"""def train_weak7_tcn(seed,max_epochs=20,patience=4):
    torch.manual_seed(seed); np.random.seed(seed)
    train_rows=weak7_training_rows(seed)
    tune_rows=np.flatnonzero(weak7_tune_mask.to_numpy(bool))
    train_loader=DataLoader(Weak7WindowDataset(train_rows),batch_size=512,shuffle=True,
                            num_workers=0,pin_memory=True)
    model=Weak7TCN(len(WEAK7_SEQUENCE_FEATURES)).to(DEVICE)
    optimizer=torch.optim.AdamW(model.parameters(),lr=8e-4,weight_decay=2e-4)
    best_state=None; best_auprc=-1; wait=0; history=[]
    for epoch in range(1,max_epochs+1):
        model.train(); losses=[]
        for x,y,weight in train_loader:
            x=x.to(DEVICE,non_blocking=True); y=y.to(DEVICE); weight=weight.to(DEVICE)
            optimizer.zero_grad(set_to_none=True)
            logits=model(x)
            raw=F.binary_cross_entropy_with_logits(logits,y,reduction='none')
            probability=torch.sigmoid(logits)
            pt=torch.where(y.gt(.5),probability,1-probability)
            loss=((1-pt).pow(1.5)*raw*weight).mean()
            loss.backward(); nn.utils.clip_grad_norm_(model.parameters(),2.0); optimizer.step()
            losses.append(float(loss.detach().cpu()))
        tune_score=predict_weak7_tcn(model,tune_rows)
        tune_auprc=float(average_precision_score(weak7_y.iloc[tune_rows],tune_score))
        history.append({'seed':seed,'epoch':epoch,'loss':float(np.mean(losses)),'tune_auprc':tune_auprc})
        print(f'seed={seed} epoch={epoch} loss={np.mean(losses):.5f} tune_auprc={tune_auprc:.5f}')
        if tune_auprc>best_auprc+1e-4:
            best_auprc=tune_auprc; wait=0
            best_state={key:value.detach().cpu().clone() for key,value in model.state_dict().items()}
        else:
            wait+=1
            if wait>=patience: break
    model.load_state_dict(best_state); model.to(DEVICE).eval()
    torch.save({'state_dict':best_state,'features':WEAK7_SEQUENCE_FEATURES,'window':WEAK7_WINDOW,
                'median':weak7_median.to_dict(),'iqr':weak7_iqr.to_dict(),'seed':seed},
               ITER7_ROOT/f'weak7_causal_tcn_seed{seed}.pt')
    return model,history,best_auprc

WEAK7_TCN_SEEDS=[17,41]
weak7_tcn_models=[]; weak7_training_history=[]; weak7_best_auprc=[]
for seed in WEAK7_TCN_SEEDS:
    model,history,best=train_weak7_tcn(seed)
    weak7_tcn_models.append(model); weak7_training_history.extend(history); weak7_best_auprc.append(best)

all_rows=np.arange(len(dev),dtype=np.int64)
dev['weak7_tcn_raw']=np.mean([predict_weak7_tcn(model,all_rows) for model in weak7_tcn_models],axis=0)
pd.DataFrame(weak7_training_history).to_csv(ITER7_ROOT/'iteration7_tcn_training_history.csv',index=False)
print('TCN best tune AUPRC:',weak7_best_auprc)
"""),
    code(r"""weak7_platt=LogisticRegression(C=.5,solver='lbfgs',class_weight='balanced',max_iter=1000,random_state=17)
weak7_platt.fit(dev.loc[weak7_tune_mask,['weak7_tcn_raw']],weak7_y.loc[weak7_tune_mask])
dev['weak7_tcn']=weak7_platt.predict_proba(dev[['weak7_tcn_raw']])[:,1]
joblib.dump(weak7_platt,ITER7_ROOT/'weak7_tcn_platt.joblib')

dev['weak7_tree']=np.sqrt(np.clip(dev.weak6_cat,0,1)*np.clip(dev.weak6_lgb,0,1))
dev['weak7_min']=np.minimum(dev.weak7_tree,dev.weak7_tcn)
dev['weak7_geom']=np.sqrt(np.clip(dev.weak7_tree,0,1)*np.clip(dev.weak7_tcn,0,1))
dev['weak7_blend']=.65*dev.weak7_tree+.35*dev.weak7_tcn
print(dev[['weak7_tree','weak7_tcn','weak7_min','weak7_geom','weak7_blend']].describe().T)
"""),
    md(r"""## 30. Incident-level consensus policy

A weak-fault rescue is allowed only when its score persists across multiple causal observations and the selected weather gate does not identify a coherent meteorological event. Thresholds are discovered on May–September only. October and pseudo-unseen stations are never searched.
"""),
    code(r"""WEAK7_SCORE_OPTIONS=['weak7_min','weak7_geom','weak7_blend']
WEAK7_THRESHOLDS=[.10,.15,.20,.25,.30,.35,.40,.50,.60,.70,.80]
WEAK7_MIN_POINTS=[2,3,4,6]
WEAK7_MAX_GAPS=[90,180]
weak7_run_cache={}
for score_col in WEAK7_SCORE_OPTIONS:
    for threshold in WEAK7_THRESHOLDS:
        for max_gap in WEAK7_MAX_GAPS:
            weak7_run_cache[(score_col,threshold,max_gap)]=gap_aware_run_length(
                dev,score_col,threshold,max_gap)

def evaluate_weak7_candidate(score_col,threshold,min_points,max_gap):
    rescue=weak7_run_cache[(score_col,threshold,max_gap)].ge(min_points)&~dev.weather7_prediction
    candidate=dev.iteration7_reference|rescue
    rows=[]
    for block in ITER7_DISCOVERY_BLOCKS:
        mask=discovery&dev.dev_split.eq(block)
        part=dev.loc[mask].copy()
        part['baseline']=dev.loc[mask,'iteration7_reference'].to_numpy(bool)
        part['candidate']=candidate.loc[mask].to_numpy(bool)
        baseline=evaluate(part,'base_score','baseline'); metric=evaluate(part,'base_score','candidate')
        rows.append({
            'scope':block,**metric,
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
        'min_weak_recall_delta':min(row['weak_episode_recall_delta'] for row in rows),
        'mean_weak_recall_delta':float(np.mean([row['weak_episode_recall_delta'] for row in rows])),
    }

def weak7_discovery_pass(row):
    return (
        row['min_precision']>=.75 and row['max_false_alarm']<=.02 and
        row['min_point_f1_delta']>=0 and row['min_event_f1_delta']>=-.01 and
        row['mean_point_f1_delta']>0 and row['mean_event_f1_delta']>=0 and
        row['min_weak_recall_delta']>=0 and row['mean_weak_recall_delta']>0)

weak7_candidates=[]
for score_col in WEAK7_SCORE_OPTIONS:
  for threshold in WEAK7_THRESHOLDS:
    for min_points in WEAK7_MIN_POINTS:
      for max_gap in WEAK7_MAX_GAPS:
        weak7_candidates.append(evaluate_weak7_candidate(score_col,threshold,min_points,max_gap))

weak7_frontier=pd.DataFrame([
    {key:value for key,value in row.items() if key!='rows'} for row in weak7_candidates])
weak7_frontier['passes_discovery']=weak7_frontier.apply(
    lambda row:weak7_discovery_pass(row.to_dict()),axis=1)
weak7_frontier.to_csv(ITER7_ROOT/'iteration7_weak_policy_frontier.csv',index=False)
weak7_feasible=[row for row in weak7_candidates if weak7_discovery_pass(row)]
proposed_weak7=(sorted(
    weak7_feasible,
    key=lambda row:(row['mean_weak_recall_delta'],row['mean_point_f1_delta'],row['mean_event_f1_delta']),
    reverse=True)[0] if weak7_feasible else None)
print('Weak discovery-feasible:',len(weak7_feasible),'of',len(weak7_candidates))
display(weak7_frontier.sort_values(
    ['passes_discovery','mean_weak_recall_delta','mean_point_f1_delta'],ascending=False).head(15))
"""),
    code(r"""def weak7_confirmation_scope(mask,policy,scope):
    rescue=weak7_run_cache[(policy['score_col'],policy['threshold'],policy['max_gap_minutes'])].ge(policy['min_points'])
    rescue&=~dev.weather7_prediction
    part=dev.loc[mask].copy()
    part['baseline']=dev.loc[mask,'iteration7_reference'].to_numpy(bool)
    part['candidate']=(dev.loc[mask,'iteration7_reference']|rescue.loc[mask]).to_numpy(bool)
    baseline=evaluate(part,'base_score','baseline'); metric=evaluate(part,'base_score','candidate')
    return {
        'scope':scope,'precision':metric['precision'],
        'false_alarm_episodes_per_station_day':metric['false_alarm_episodes_per_station_day'],
        'point_f1':metric['f1'],'point_f1_delta':metric['f1']-baseline['f1'],
        'event_f1':metric['event_f1'],'event_f1_delta':metric['event_f1']-baseline['event_f1'],
        'weak_episode_recall':weak_fault_mean_from_metric(metric),
        'weak_episode_recall_delta':weak_fault_mean_from_metric(metric)-weak_fault_mean_from_metric(baseline),
    }

WEAK7_CONFIRM_COLUMNS=[
    'scope','precision','false_alarm_episodes_per_station_day','point_f1','point_f1_delta',
    'event_f1','event_f1_delta','weak_episode_recall','weak_episode_recall_delta']
weak7_confirmation=[]
if proposed_weak7:
    for scope,mask in ITER7_CONFIRMATION_SCOPES.items():
        weak7_confirmation.append(weak7_confirmation_scope(mask,proposed_weak7,scope))

weak7_confirmation_frame=pd.DataFrame(weak7_confirmation,columns=WEAK7_CONFIRM_COLUMNS)
weak7_confirmation_pass=(len(weak7_confirmation_frame)==2 and all(
    row['precision']>=.75 and row['false_alarm_episodes_per_station_day']<=.02 and
    row['point_f1_delta']>=0 and row['event_f1_delta']>=-.01 and
    row['weak_episode_recall_delta']>=0 for row in weak7_confirmation) and
    next(row for row in weak7_confirmation if row['scope']=='pseudo_unseen_all_2023')['weak_episode_recall_delta']>0)

if proposed_weak7 and weak7_confirmation_pass:
    WEAK7_STATUS='causal_tcn_consensus_confirmed'
    SELECTED_WEAK7={key:proposed_weak7[key] for key in ['score_col','threshold','min_points','max_gap_minutes']}
else:
    WEAK7_STATUS='no_confirmed_tcn_transfer_keep_iteration5_candidate'
    SELECTED_WEAK7={'score_col':'weak7_min','threshold':1.10,'min_points':999,'max_gap_minutes':180}

weak7_confirmation_frame.to_csv(ITER7_ROOT/'iteration7_weak_confirmation.csv',index=False)
print('Weak status:',WEAK7_STATUS,SELECTED_WEAK7)
display(weak7_confirmation_frame)
"""),
    md(r"""## 31. Final development ablation, fault coverage and integrity receipt

The selected candidate is materialized only after every confirmation gate passes. Otherwise the no-op policy preserves the Iteration 5 development reference exactly. A new external blind benchmark may be opened only after this notebook has been reviewed and the candidate frozen.
"""),
    code(r"""if int(SELECTED_WEAK7['min_points'])<100:
    selected_weak7_rescue=weak7_run_cache[(
        SELECTED_WEAK7['score_col'],SELECTED_WEAK7['threshold'],SELECTED_WEAK7['max_gap_minutes'])].ge(
            SELECTED_WEAK7['min_points'])&~dev.weather7_prediction
else:
    selected_weak7_rescue=pd.Series(False,index=dev.index)

dev['iteration7_candidate']=dev.iteration7_reference|selected_weak7_rescue
iteration7_rows=[]; iteration7_combined=[]
for block in POLICY_BLOCKS:
    mask=dev.dev_split.eq(block)&dev.available_to_detector.eq(1)
    part=dev.loc[mask].copy()
    part['reference']=dev.loc[mask,'iteration7_reference'].to_numpy(bool)
    part['candidate']=dev.loc[mask,'iteration7_candidate'].to_numpy(bool)
    for variant,pred_col in [('Iteration5 reference','reference'),('Iteration7 candidate','candidate')]:
        metric=evaluate(part,'base_score',pred_col)
        iteration7_rows.append({
            'block':block,'variant':variant,**metric,
            'weak_episode_recall':weak_fault_mean_from_metric(metric)})
    iteration7_combined.append(part)

iteration7_ablation=pd.DataFrame(iteration7_rows)
iteration7_ablation.to_csv(ITER7_ROOT/'iteration7_multiblock_ablation.csv',index=False)
display(iteration7_ablation[['block','variant','precision','recall','f1','event_precision','event_recall',
                             'event_f1','weak_episode_recall','false_alarm_episodes_per_station_day']])

iteration7_all=pd.concat(iteration7_combined,ignore_index=True)
iteration7_all['pred']=iteration7_all.candidate
iteration7_fault_recall=(pd.Series(
    event_metrics(iteration7_all,'pred')['per_fault_episode_recall'],name='episode_recall')
    .sort_values().rename_axis('anomaly_type').reset_index())
iteration7_fault_recall.to_csv(ITER7_ROOT/'iteration7_fault_episode_recall.csv',index=False)
display(iteration7_fault_recall)
"""),
    code(r"""iteration7_feature_contract={
    'detector_observation_inputs':['temperature','pressure','relative_humidity'],
    'routing_metadata':['station_id','timestamp','cluster','latitude','longitude'],
    'communication_metadata':['arrival_timestamp','optional_expected_cadence','optional_heartbeat_sla'],
    'weather_meta_features':WEATHER7_META_FEATURES,
    'weak_sequence_features':WEAK7_SEQUENCE_FEATURES,
    'sequence_window_observations':WEAK7_WINDOW,
    'causal_window':'current and previous observations only; left padded; no future rows',
    'forbidden':['dew_point','future_observation','2024_labels','blind_2025_labels'],
}
(ITER7_ROOT/'iteration7_feature_contract.json').write_text(
    json.dumps(iteration7_feature_contract,indent=2))

result7={
    'iteration':'07_climate_calibration_causal_tcn',
    'device':DEVICE,'gpu':torch.cuda.get_device_name(0),
    'blind_2025_opened':False,'former_final_tests_opened':False,
    'development_years':[2022,2023],
    'pseudo_unseen_stations':PSEUDO_HOLDOUT_STATIONS,
    'communication':{
        'status':'heartbeat_contract_frozen','contract':ITER7_COMMUNICATION_CONTRACT},
    'weather':{
        'status':WEATHER7_STATUS,'selected_policy':SELECTED_WEATHER7,
        'meta_feature_count':len(WEATHER7_META_FEATURES),
        'regularization_nonzero_coefficients':weather7_nonzero,
        'discovery_feasible_candidates':int(len(weather7_feasible)),
        'confirmation':weather7_confirmation_frame.to_dict('records')},
    'weak_fault_transfer':{
        'status':WEAK7_STATUS,'selected_policy':SELECTED_WEAK7,
        'sequence_feature_count':len(WEAK7_SEQUENCE_FEATURES),'window':WEAK7_WINDOW,
        'tcn_seeds':WEAK7_TCN_SEEDS,'best_tune_auprc':weak7_best_auprc,
        'discovery_feasible_candidates':int(len(weak7_feasible)),
        'confirmation':weak7_confirmation_frame.to_dict('records')},
    'selected_ablation':iteration7_ablation.drop(
        columns=['per_fault_episode_recall'],errors='ignore').to_dict('records'),
    'promotion_rule':(
        'No change unless discovery, October, pseudo-unseen, precision, false-alarm, '
        'point-F1, event-F1, station-macro and pseudo-unseen weak-recall gates pass.'),
}
(ITER7_ROOT/'iteration7_result_block.json').write_text(
    json.dumps(result7,indent=2,default=float))

integrity7={
    'blind_2025_opened':False,'former_final_tests_opened':False,
    'development_partitions':['2022 train','2023 tune/discovery/confirmation'],
    'pseudo_unseen_stations':PSEUDO_HOLDOUT_STATIONS,
    'future_features_used':False,'dew_point_used':False,
    'communication_stream_action_used_by_detector':False,
    'result_sha256':hashlib.sha256((ITER7_ROOT/'iteration7_result_block.json').read_bytes()).hexdigest(),
    'feature_contract_sha256':hashlib.sha256((ITER7_ROOT/'iteration7_feature_contract.json').read_bytes()).hexdigest(),
}
(ITER7_ROOT/'iteration7_integrity_receipt.json').write_text(
    json.dumps(integrity7,indent=2))

print(json.dumps(result7,indent=2,default=float))
print('\nSEND BACK THESE ITERATION 7 FILES:')
for filename in [
    'iteration7_result_block.json','iteration7_integrity_receipt.json',
    'iteration7_communication_contract.json','iteration7_weather_policy_frontier.csv',
    'iteration7_weather_confirmation.csv','iteration7_weather_station_metrics.csv',
    'iteration7_tcn_training_history.csv','iteration7_weak_policy_frontier.csv',
    'iteration7_weak_confirmation.csv','iteration7_multiblock_ablation.csv',
    'iteration7_fault_episode_recall.csv','iteration7_feature_contract.json',
]: print(ITER7_ROOT/filename)
"""),
    md(r"""## Iteration 7 stop rule

Return the twelve files printed above. Do not open or tune against the 2025 benchmark. We will first audit discovery-versus-confirmation transfer, per-station weather stability, weak-fault event recall, false alarms, TCN convergence and the integrity receipt. Only a fully confirmed candidate will be frozen for a genuinely new blind evaluation.
"""),
])

notebook.setdefault("metadata", {}).setdefault("colab", {})["name"] = OUTPUT.name
OUTPUT.write_text(json.dumps(notebook, indent=1, ensure_ascii=False), encoding="utf-8")
print(OUTPUT)
