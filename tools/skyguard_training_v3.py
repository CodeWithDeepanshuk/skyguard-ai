"""Reproducible historical-proxy training shared by CLI and Colab.

No live model is overwritten. NOAA SLP is the pressure contract; aviation
altimeter values stay in raw columns and are not silently treated as SLP.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

SENSORS = {'t': 'temperature_c', 'p': 'pressure_hpa', 'rh': 'relative_humidity_pct'}
FLOORS = {'t': 0.5, 'p': 0.8, 'rh': 3.0}
FAULTS = ['spike', 'bias', 'drift', 'freeze']
CLASSES = [f'{s}_{f}' for s in SENSORS for f in FAULTS]
FEATURES = ['gap_hours', 'hour_sin', 'hour_cos', 'doy_sin', 'doy_cos'] + [
    f'{s}_{name}' for s in SENSORS for name in
    ['value', 'missing', 'delta', 'rate', 'z', 'ewma', 'cusum_pos', 'cusum_neg',
     'flat_hours', 'flat_count', 'peer_count', 'peer_residual', 'buddy_z',
     'peer_age', 'peer_agreement', 'physical_violation']]


def save_json(path, value):
    def clean(x):
        if isinstance(x, dict): return {str(k): clean(v) for k, v in x.items()}
        if isinstance(x, (list, tuple)): return [clean(v) for v in x]
        if isinstance(x, (np.integer,)): return int(x)
        if isinstance(x, (float, np.floating)): return float(x) if np.isfinite(x) else None
        if isinstance(x, (np.bool_,)): return bool(x)
        if isinstance(x, (pd.Timestamp, Path)): return str(x)
        return x
    Path(path).write_text(json.dumps(clean(value), indent=2), encoding='utf-8')


def load_history(path):
    d = pd.read_csv(path, dtype={'station_id': str}, low_memory=False)
    required = {'station_id', 'timestamp_utc', 'evaluation_role', 'latitude', 'longitude',
                'elevation_m', 'pressure_source', *SENSORS.values()}
    if required - set(d): raise ValueError(f'Missing fields: {required - set(d)}')
    d['timestamp_utc'] = pd.to_datetime(d.timestamp_utc, utc=True, errors='raise')
    if not d.timestamp_utc.dt.year.isin([2022, 2023, 2024]).all():
        raise ValueError('Only 2022–2024 observations allowed')
    if d.duplicated(['station_id', 'timestamp_utc']).any():
        raise ValueError('Resolve duplicate station timestamps explicitly')
    d = d.sort_values(['station_id', 'timestamp_utc']).reset_index(drop=True)
    for c in [*SENSORS.values(), 'latitude', 'longitude', 'elevation_m']:
        d[c] = pd.to_numeric(d[c], errors='coerce').replace([np.inf, -np.inf], np.nan)
    source = d.pressure_source.fillna('').str.lower().str.strip()
    if not source.isin(['', 'slp', 'ma1_altimeter']).all():
        raise ValueError('Unrecognized pressure semantics')
    d['pressure_hpa_raw'] = d.pressure_hpa
    d['pressure_source_raw'] = source
    d['pressure_hpa'] = d.pressure_hpa.where(source.eq('slp'))
    d['pressure_type'] = 'mean_sea_level_pressure'
    d['fault_label'] = 0
    d['fault_class'] = -1
    d['episode_id'] = ''
    t = d.timestamp_utc
    held = d.evaluation_role.eq('station_holdout')
    d['split'] = 'excluded'
    for name, start, end in [
        ('fit', '2022-01-01', '2023-01-01'),
        ('select', '2023-01-01', '2023-04-01'),
        ('calibrate', '2023-04-01', '2023-07-01'),
        ('policy', '2023-07-01', '2024-01-01'),
        ('temporal', '2024-01-01', '2025-01-01')]:
        d.loc[~held & t.ge(start) & t.lt(end), 'split'] = name
    d.loc[held & t.ge('2024-01-01'), 'split'] = 'spatial'
    return d


def features(frame, radius_km=300.0, max_age_hours=3.0):
    """Causal features. Peers are distinct other stations, matched backward."""
    z = frame.sort_values(['station_id', 'timestamp_utc']).reset_index(drop=True).copy()
    groups = z.groupby('station_id', sort=False)
    z['gap_hours'] = groups.timestamp_utc.diff().dt.total_seconds() / 3600
    hour = z.timestamp_utc.dt.hour + z.timestamp_utc.dt.minute / 60
    z['hour_sin'], z['hour_cos'] = np.sin(hour * np.pi / 12), np.cos(hour * np.pi / 12)
    day = z.timestamp_utc.dt.dayofyear
    z['doy_sin'], z['doy_cos'] = np.sin(day * 2*np.pi/365.25), np.cos(day * 2*np.pi/365.25)
    bounds = {'t': (-90, 60), 'p': (850, 1100), 'rh': (0, 100)}
    for s, col in SENSORS.items():
        z[f'{s}_value'] = z[col]
        # Semantic exclusion of altimeter values is not a pressure dropout.
        z[f'{s}_missing'] = (z.pressure_hpa_raw.isna() if s == 'p' else z[col].isna()).astype(float)
        for name in ['delta', 'rate', 'z', 'ewma', 'cusum_pos', 'cusum_neg', 'flat_hours', 'flat_count']:
            z[f'{s}_{name}'] = np.nan
        for _, g in groups:
            segments = (g.gap_hours.gt(6) | g.gap_hours.isna()).cumsum()
            for _, chunk in g.groupby(segments):
                v = chunk[col]
                prior = v.shift(1)
                baseline = prior.rolling(16, min_periods=4).median()
                mad = (prior-baseline).abs().rolling(16, min_periods=4).median()
                rz = (v-baseline) / (1.4826*mad).clip(lower=FLOORS[s])
                z.loc[chunk.index, f'{s}_delta'] = v.diff()
                z.loc[chunk.index, f'{s}_rate'] = v.diff() / chunk.gap_hours.where(chunk.gap_hours.gt(0))
                z.loc[chunk.index, f'{s}_z'] = rz
                z.loc[chunk.index, f'{s}_ewma'] = v-prior.ewm(span=12, adjust=False).mean()
                pos, neg, flat, hours = [], [], [], []
                cp = cn = run = duration = 0.0
                values, gaps = v.to_numpy(), chunk.gap_hours.to_numpy()
                for j, r in enumerate(rz.to_numpy()):
                    if not np.isfinite(r): cp = cn = 0.0
                    else:
                        cp = min(100, max(0, cp+np.clip(r, -10, 10)-0.5))
                        cn = min(100, max(0, cn-np.clip(r, -10, 10)-0.5))
                    same = j > 0 and np.isfinite(values[j]) and np.isfinite(values[j-1]) and abs(values[j]-values[j-1]) <= 0.01
                    run = run+1 if same else 0
                    duration = duration+gaps[j] if same and np.isfinite(gaps[j]) else 0
                    pos.append(cp); neg.append(cn); flat.append(run); hours.append(duration)
                for name, vals in [('cusum_pos',pos),('cusum_neg',neg),('flat_count',flat),('flat_hours',hours)]:
                    z.loc[chunk.index, f'{s}_{name}'] = vals
        lo, hi = bounds[s]
        z[f'{s}_physical_violation'] = ((z[col] < lo) | (z[col] > hi)).astype(float)
        for name in ['peer_count', 'peer_residual', 'buddy_z', 'peer_age', 'peer_agreement', 'peer_median', 'peer_scale']:
            z[f'{s}_{name}'] = np.nan
    station_frames = {sid: g for sid, g in z.groupby('station_id', sort=False)}
    metadata = z.groupby('station_id')[['latitude', 'longitude', 'elevation_m']].first()
    for sid, target in station_frames.items():
        a = metadata.loc[sid]
        lat1, lat2 = np.radians(a.latitude), np.radians(metadata.latitude.to_numpy())
        dlat = lat2-lat1
        dlon = np.radians(metadata.longitude.to_numpy()-a.longitude)
        distance = 6371*2*np.arcsin(np.sqrt(np.clip(np.sin(dlat/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2,0,1)))
        peers = metadata.index[(distance <= radius_km) & (metadata.index != sid)]
        for s, col in SENSORS.items():
            vals, ages = [], []
            for other in peers:
                # Temperature peers must also have comparable elevation. SLP needs no elevation reduction.
                if s == 't' and abs(metadata.loc[other, 'elevation_m']-a.elevation_m) > 300: continue
                peer = station_frames[other].loc[:, ['timestamp_utc', col]].rename(columns={'timestamp_utc':'peer_time', col:'peer_value'})
                matched = pd.merge_asof(target[['timestamp_utc']], peer,
                    left_on='timestamp_utc', right_on='peer_time', direction='backward',
                    tolerance=pd.Timedelta(hours=max_age_hours))
                vals.append(matched.peer_value.to_numpy())
                ages.append((matched.timestamp_utc-matched.peer_time).dt.total_seconds().to_numpy()/3600)
            if not vals:
                z.loc[target.index, f'{s}_peer_count'] = 0
                continue
            matrix = np.column_stack(vals)
            valid = np.isfinite(matrix)
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', RuntimeWarning)
                median = np.nanmedian(matrix, axis=1)
                scale = np.maximum(1.4826*np.nanmedian(abs(matrix-median[:,None]), axis=1), FLOORS[s])
                age = np.nanmax(np.where(valid, np.column_stack(ages), np.nan), axis=1)
            count = valid.sum(axis=1)
            residual = target[col].to_numpy()-median
            buddy = np.where(count >= 2, residual/scale, np.nan)
            agree = np.where(count >= 2, (valid & (abs(matrix-target[col].to_numpy()[:,None]) <= 2.5*FLOORS[s])).sum(axis=1)/np.maximum(count,1), np.nan)
            for name, value in [('peer_count',count),('peer_residual',residual),('buddy_z',buddy),('peer_age',age),('peer_agreement',agree),('peer_median',median),('peer_scale',scale)]:
                z.loc[target.index, f'{s}_{name}'] = value
    return z


def inject(frame, seed, repeats=3):
    """Balanced sensor × signature curriculum; no overlapping episodes."""
    out = frame.copy().reset_index(drop=True)
    rng = np.random.default_rng(seed)
    magnitude = {'t': (2, 8), 'p': (3, 15), 'rh': (10, 35)}
    for sid, ids in out.groupby('station_id').groups.items():
        ids = np.asarray(ids)
        occupied = np.zeros(len(ids), bool)
        for repeat in range(repeats):
            for class_id in rng.permutation(len(CLASSES)):
                sensor, kind = CLASSES[class_id].split('_', 1)
                col = SENSORS[sensor]
                length = 1 if kind == 'spike' else int(rng.integers(5, 17))
                for attempt in range(200):
                    if len(ids) < length+50: break
                    start = int(rng.integers(24, len(ids)-length-24))
                    loc = ids[start:start+length]
                    raw = out.loc[loc, col].to_numpy(copy=True)
                    gaps = out.loc[loc, 'timestamp_utc'].diff().dt.total_seconds()/3600
                    if occupied[max(0,start-12):start+length+12].any() or not np.isfinite(raw).all() or gaps.gt(6).any(): continue
                    if kind == 'freeze' and np.ptp(raw) < FLOORS[sensor]: continue
                    amount = rng.uniform(*magnitude[sensor])*rng.choice([-1,1])
                    if kind in ['spike','bias']: corrupted = raw+amount
                    elif kind == 'drift': corrupted = raw+np.linspace(0.1*amount,amount,length)
                    else: corrupted = np.full(length,raw[0])
                    if sensor == 'rh' and ((corrupted < 0).any() or (corrupted > 100).any()): continue
                    out.loc[loc, col] = corrupted
                    out.loc[loc, ['fault_label','fault_class','episode_id']] = [1,int(class_id),f'{seed}-{sid}-{repeat}-{class_id}']
                    occupied[max(0,start-12):start+length+12] = True
                    break
    return out


def verify_causality(frame):
    """Appending future observations cannot change past features."""
    sample = frame[frame.timestamp_utc.lt(frame.timestamp_utc.min()+pd.Timedelta(days=5))].copy()
    cutoff = sample.timestamp_utc.min()+pd.Timedelta(days=3)
    before = features(sample[sample.timestamp_utc.le(cutoff)])
    after = features(sample)
    joined = before.merge(after, on=['station_id','timestamp_utc'], suffixes=('_before','_after'))
    for c in FEATURES:
        np.testing.assert_allclose(joined[c+'_before'], joined[c+'_after'], equal_nan=True, rtol=1e-6)
    return {'passed': True, 'rows': len(joined), 'features': len(FEATURES)}


def build_tcn(width):
    import torch
    from torch import nn
    class Network(nn.Module):
        def __init__(self):
            super().__init__()
            self.project = nn.Conv1d(width, 32, 1)
            self.layers = nn.ModuleList([nn.Conv1d(32,32,3,dilation=d) for d in [1,2,4]])
            self.head = nn.Linear(32,1)
        def forward(self,x):
            h = self.project(x.transpose(1,2))
            for layer, dilation in zip(self.layers,[1,2,4]):
                h = h+torch.relu(layer(nn.functional.pad(h,(2*dilation,0))))
            return self.head(h[:,:,-1]).squeeze(-1)
    return Network()


def sequence_loader(frame, matrix, batch_size, shuffle=False):
    import torch
    from torch.utils.data import Dataset, DataLoader
    # Only indices are materialized, not N × length × feature tensors.
    lengths = np.zeros(len(frame),dtype=np.int64)
    for _, g in frame.groupby('station_id',sort=False):
        run = 0
        for idx, gap in zip(g.index,g.gap_hours):
            run = 1 if not np.isfinite(gap) or gap > 6 else run+1
            lengths[idx] = min(run,12)
    class Windows(Dataset):
        def __len__(self): return len(frame)
        def __getitem__(self,i):
            size = lengths[i]
            x = np.zeros((12,matrix.shape[1]+1),np.float32)
            x[-size:,:-1] = matrix[i-size+1:i+1]
            x[-size:,-1] = 1
            return torch.from_numpy(x), torch.tensor(float(frame.fault_label.iloc[i]))
    return DataLoader(Windows(), batch_size=batch_size, shuffle=shuffle,num_workers=0,
                      pin_memory=torch.cuda.is_available())


def neural_predict(model, loader, device):
    import torch
    model.eval()
    values = []
    with torch.inference_mode():
        for x,_ in loader:
            values.append(torch.sigmoid(model(x.to(device))).cpu().numpy())
    return np.concatenate(values)


def policy_events(frame, score, cfg):
    events = []
    for sid,g in frame.groupby('station_id',sort=False):
        hits = pd.Series(score[g.index] >= cfg['threshold'], index=g.index)
        segments = (g.gap_hours.isna() | g.gap_hours.gt(6)).cumsum()
        persistent = hits.groupby(segments).transform(lambda s:s.rolling(cfg['n'], min_periods=cfg['n']).sum().ge(cfg['k']))
        # Allow severe isolated spikes; persistence alone cannot detect a one-row spike.
        trigger = persistent | (score[g.index] >= cfg['urgent'])
        stamps = g.loc[trigger,'timestamp_utc']
        event_ids = stamps.diff().gt(pd.Timedelta(minutes=cfg['cooldown'])).cumsum()
        for _, times in stamps.groupby(event_ids):
            events.append({'station_id':sid,'start':times.min(),'end':times.max()})
    return pd.DataFrame(events,columns=['station_id','start','end'])


def evaluate(frame, score, cfg):
    predicted = policy_events(frame,score,cfg)
    truth = frame[frame.fault_label.eq(1)].groupby(['station_id','episode_id']).agg(
        start=('timestamp_utc','min'),end=('timestamp_utc','max'),fault_class=('fault_class','first')).reset_index()
    used = set(); matches = []; delays = []
    for _,event in truth.sort_values('start').iterrows():
        # Match alert onset, not a pre-existing alert overlapping a later injection.
        eligible = predicted[(predicted.station_id == event.station_id) &
            predicted.start.ge(event.start) & predicted.start.le(event.end+pd.Timedelta(hours=3))]
        choices = [i for i in eligible.index if i not in used]
        hit = bool(choices)
        if hit:
            chosen = choices[0]; used.add(chosen)
            delays.append((predicted.loc[chosen,'start']-event.start).total_seconds()/60)
        matches.append({'station_id':event.station_id,'episode_id':event.episode_id,
                        'fault_class':CLASSES[int(event.fault_class)],'detected':hit})
    tp = len(used); precision = tp/max(len(predicted),1); recall = tp/max(len(truth),1)
    # Observed reporting days exclude long unobserved outages from the denominator.
    days = frame[['station_id','timestamp_utc']].assign(day=frame.timestamp_utc.dt.floor('D')).drop_duplicates(['station_id','day']).groupby('station_id').size()
    counts = predicted.groupby('station_id').size().reindex(days.index,fill_value=0)
    metrics = {'events':len(predicted),'truth_events':len(truth),'precision':precision,'recall':recall,
               'f1':2*precision*recall/max(precision+recall,1e-12),
               'alerts_per_reporting_station_day':len(predicted)/max(int(days.sum()),1),
               'median_delay_minutes':float(np.median(delays)) if delays else None}
    station_summary = pd.DataFrame({'days':days,'alerts':counts})
    return metrics, pd.DataFrame(matches), station_summary


def run(data_path, output, epochs=100, trials=100, seeds=(17,41,67), evaluate_tests=True):
    import joblib
    import lightgbm as lgb
    import sklearn
    import torch
    from sklearn.ensemble import IsolationForest
    from sklearn.isotonic import IsotonicRegression
    from sklearn.metrics import average_precision_score, classification_report, brier_score_loss
    from sklearn.preprocessing import RobustScaler
    from torch import nn

    output = Path(output)
    output.mkdir(parents=True,exist_ok=False)
    random.seed(26073); np.random.seed(26073); torch.manual_seed(26073)
    torch.set_num_threads(min(8,torch.get_num_threads()))
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    log_path = output/'progress.jsonl'
    def log(stage,**values):
        record = {'utc':datetime.now(timezone.utc).isoformat(),'stage':stage,**values}
        with log_path.open('a',encoding='utf-8') as stream: stream.write(json.dumps(record,default=str)+'\n')
        print(json.dumps(record,default=str),flush=True)
    log('start',device=device,epochs=epochs,policy_trials=trials,seeds=list(seeds))
    d = load_history(data_path)
    source_hash = hashlib.sha256(Path(data_path).read_bytes()).hexdigest()
    save_json(output/'data_contract.json',{'sha256':source_hash,'rows':len(d),'stations':d.station_id.nunique(),
        'pressure':'native NOAA SLP only','excluded_altimeter_rows':int(d.pressure_source_raw.eq('ma1_altimeter').sum()),
        'provider':'NOAA/NCEI Indian surface-station proxy; not direct IMD AWS API',
        'labels':'controlled injections; no confirmed field failures',
        'splits':d.groupby('split').agg(rows=('station_id','size'),stations=('station_id','nunique')).reset_index().to_dict('records')})
    save_json(output/'causality_check.json',verify_causality(d[d.split.eq('fit')]))
    log('causality_passed',feature_count=len(FEATURES))
    clean = {}; injected = {}
    for split,seed in [('fit',1701),('select',4101),('calibrate',6701),('policy',8901)]:
        raw = d[d.split.eq(split)].copy()
        clean[split] = features(raw)
        injected[split] = features(inject(raw,seed,repeats=6 if split=='fit' else 3))
        log('features_ready',split=split,rows=len(raw),injected_rows=int(injected[split].fault_label.sum()))
    fit, selection = injected['fit'], injected['select']
    medians = fit[FEATURES].median().fillna(0)
    def matrix(frame): return frame[FEATURES].replace([np.inf,-np.inf],np.nan).fillna(medians).astype(np.float32)
    X, V = matrix(fit),matrix(selection)
    y, vy = fit.fault_label.to_numpy(dtype=int),selection.fault_label.to_numpy(dtype=int)
    positive_weight = min(30,(len(y)-y.sum())/max(y.sum(),1))
    trees = []
    for seed in seeds:
        model = lgb.LGBMClassifier(n_estimators=1800,learning_rate=.035,num_leaves=31,
            min_child_samples=60,reg_lambda=4,reg_alpha=.5,subsample=.8,subsample_freq=1,
            colsample_bytree=.85,random_state=seed,n_jobs=8,verbosity=-1)
        model.fit(X,y,sample_weight=np.where(y,positive_weight,1),eval_set=[(V,vy)],eval_metric='average_precision',
                  callbacks=[lgb.early_stopping(100,verbose=False)])
        trees.append(model)
        joblib.dump(model,output/f'lightgbm_{seed}.joblib')
        log('tree_trained',seed=seed,iterations=model.best_iteration_,selection_auprc=average_precision_score(vy,model.predict_proba(V)[:,1]))
    iso = IsolationForest(n_estimators=200,contamination='auto',random_state=26073,n_jobs=8)
    iso.fit(matrix(clean['fit']))
    iso_reference = np.sort(-iso.score_samples(matrix(clean['fit'])))
    scaler = RobustScaler().fit(X)
    def normalized(frame): return np.clip(scaler.transform(matrix(frame)),-20,20).astype(np.float32)
    net = build_tcn(len(FEATURES)+1).to(device)
    optimizer = torch.optim.AdamW(net.parameters(),lr=8e-4,weight_decay=1e-4)
    loss_function = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(positive_weight,device=device))
    train_loader = sequence_loader(fit,normalized(fit),512,shuffle=True)
    val_loader = sequence_loader(selection,normalized(selection),1024)
    history = []; best = -1; wait = 0
    for epoch in range(1,epochs+1):
        net.train(); losses = []
        for xb,yb in train_loader:
            optimizer.zero_grad(set_to_none=True)
            loss = loss_function(net(xb.to(device)),yb.to(device))
            loss.backward(); nn.utils.clip_grad_norm_(net.parameters(),2); optimizer.step()
            losses.append(float(loss.detach().cpu()))
        prediction = neural_predict(net,val_loader,device)
        ap = average_precision_score(vy,prediction)
        row = {'epoch':epoch,'loss':float(np.mean(losses)),'selection_auprc':float(ap)}
        history.append(row); log('neural_epoch',**row)
        pd.DataFrame(history).to_csv(output/'neural_history.csv',index=False)
        if ap > best+1e-4:
            best=ap; wait=0
            torch.save(net.state_dict(),output/'causal_tcn_best.pt')
        else: wait+=1
        if wait>=10: break
    net.load_state_dict(torch.load(output/'causal_tcn_best.pt',map_location=device,weights_only=True))
    # Twelve sensor/signature classes are hypotheses, not physical root-cause labels.
    positive = fit.fault_label.eq(1)
    if set(fit.loc[positive,'fault_class']) != set(range(12)):
        raise RuntimeError('Training curriculum lacks one or more of the 12 classes')
    diagnosis = lgb.LGBMClassifier(n_estimators=600,num_leaves=15,learning_rate=.035,
        min_child_samples=15,reg_lambda=4,random_state=26073,n_jobs=8,verbosity=-1)
    diagnosis.fit(X.loc[positive],fit.loc[positive,'fault_class'].astype(int))
    def raw_scores(frame):
        xx = matrix(frame)
        tree = np.mean([m.predict_proba(xx)[:,1] for m in trees],axis=0)
        neural = neural_predict(net,sequence_loader(frame,normalized(frame),1024),device)
        isolation = np.searchsorted(iso_reference,-iso.score_samples(xx),side='right')/len(iso_reference)
        return np.column_stack([tree,neural,isolation])
    cal_raw = raw_scores(injected['calibrate'])
    calibrators = [IsotonicRegression(out_of_bounds='clip').fit(cal_raw[:,i],injected['calibrate'].fault_label) for i in range(3)]
    def scores(frame):
        raw = raw_scores(frame)
        return np.column_stack([calibrators[i].predict(raw[:,i]) for i in range(3)])
    policy_clean = scores(clean['policy']); policy_fault = scores(injected['policy'])
    rng = np.random.default_rng(26073); search = []
    for trial in range(trials):
        weights = np.eye(3)[trial] if trial < 3 else rng.dirichlet([3,2,1])
        n = int(rng.choice([1,2,3,4,5])); k = int(rng.integers(1,n+1))
        cfg = {'threshold':float(rng.uniform(.1,.95)), 'urgent':float(rng.choice([.98,.995,1.01])),
               'n':n,'k':k,'cooldown':int(rng.choice([60,180,360])), 'weights':weights.tolist()}
        cm,_,_ = evaluate(clean['policy'],policy_clean@weights,cfg)
        fm,_,_ = evaluate(injected['policy'],policy_fault@weights,cfg)
        feasible = cm['alerts_per_reporting_station_day'] <= .02
        search.append({'trial':trial,'config':cfg,'clean':cm,'injected':fm,'feasible':feasible})
        if trial%10==0: log('policy_search',trial=trial,feasible=feasible,f1=fm['f1'])
    eligible = [r for r in search if r['feasible']]
    selected = max(eligible or search,key=lambda r:(r['feasible'],r['injected']['f1'],r['injected']['recall'],-r['clean']['alerts_per_reporting_station_day']))
    cfg = selected['config']; weights = np.asarray(cfg['weights'])
    save_json(output/'policy_search.json',search); save_json(output/'frozen_policy.json',cfg)
    bundle = {'trees':trees,'isolation':iso,'isolation_reference':iso_reference,'calibrators':calibrators,
              'scaler':scaler,'medians':medians,'diagnosis':diagnosis,'features':FEATURES,'classes':CLASSES,'policy':cfg}
    joblib.dump(bundle,output/'candidate_bundle.joblib')
    reloaded = joblib.load(output/'candidate_bundle.joblib')
    np.testing.assert_allclose(trees[0].predict_proba(V.head(64)),reloaded['trees'][0].predict_proba(V.head(64)))
    # Built-in TreeSHAP contributions, with additive-logit reconstruction checked.
    contributions = trees[0].booster_.predict(V.head(32),pred_contrib=True)
    np.testing.assert_allclose(contributions.sum(axis=1),trees[0].booster_.predict(V.head(32),raw_score=True),rtol=1e-5,atol=1e-6)
    pd.DataFrame(contributions,columns=FEATURES+['bias']).to_csv(output/'tree_shap_examples.csv',index=False)
    save_json(output/'runtime_versions.json',{'python':__import__('sys').version,'torch':torch.__version__,
        'lightgbm':lgb.__version__,'sklearn':sklearn.__version__,'pandas':pd.__version__,'numpy':np.__version__})
    log('development_complete',selected_trial=selected['trial'],feasible=selected['feasible'])
    results = []
    if evaluate_tests:
        # All thresholds, weights and fitted transforms are frozen before 2024 scoring.
        for split in ['temporal','spatial']:
            raw = d[d.split.eq(split)].copy()
            real = features(raw); real_score = scores(real)@weights
            cm,_,by_station = evaluate(real,real_score,cfg)
            by_station.to_csv(output/f'{split}_reporting_days_alerts.csv')
            # Station block resampling preserves complete trajectories and event grouping.
            rates=[]
            for _ in range(100):
                sample=by_station.iloc[rng.integers(0,len(by_station),len(by_station))]
                rates.append(float(sample.alerts.sum()/sample.days.sum()))
            for seed in [111,222,333]:
                faulty = features(inject(raw,seed,3)); fault_score=scores(faulty)@weights
                fm,matches,_=evaluate(faulty,fault_score,cfg)
                matches.to_csv(output/f'{split}_{seed}_episode_matches.csv',index=False)
                pos=faulty.fault_label.eq(1)
                report=classification_report(faulty.loc[pos,'fault_class'].astype(int),
                    diagnosis.predict(matrix(faulty).loc[pos]),labels=list(range(12)),
                    target_names=CLASSES,output_dict=True,zero_division=0)
                save_json(output/f'{split}_{seed}_diagnosis.json',report)
                bins=np.minimum((fault_score*10).astype(int),9)
                labels=faulty.fault_label.to_numpy()
                ece=sum(float((bins==b).mean())*abs(float(labels[bins==b].mean()-fault_score[bins==b].mean())) for b in range(10) if (bins==b).any())
                result={'split':split,'seed':seed,'clean_alert_burden':cm,
                    'clean_alert_rate_station_bootstrap_95pct':np.quantile(rates,[.025,.975]).tolist(),
                    'injected':fm,'synthetic_ece':ece,'synthetic_brier':brier_score_loss(labels,fault_score),
                    'diagnosis_macro_f1':report['macro avg']['f1-score'],
                    'diagnosis_accuracy':float((diagnosis.predict(matrix(faulty).loc[pos])==faulty.loc[pos,'fault_class']).mean())}
                results.append(result); save_json(output/'holdout_results.json',results)
                log('holdout_evaluated',split=split,seed=seed,**fm)
    save_json(output/'status.json',{'status':'RESEARCH_CANDIDATE','training_complete':True,
        'heldout_evaluation_complete':bool(evaluate_tests),'data_sha256':source_hash,
        'features':len(FEATURES),'model_seeds':list(seeds),'epochs_run':len(history),
        'policy_trials':trials,'field_fault_probability_validated':False,
        'unverified_claims':['real IMD domain transfer','maintenance-confirmed hardware causes',
            'DWD weather gates','calibrated advisory repair coverage','backend parity and deployment'],
        'note':'No automatic live promotion; synthetic labels do not establish real fault accuracy.'})
    log('finished',output=str(output))
    return output


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--data',type=Path,default=Path('data/archive/legacy_noaa_aws/aws_observations_2022_2024.csv.gz'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--epochs',type=int,default=100)
    parser.add_argument('--trials',type=int,default=100)
    parser.add_argument('--development-only',action='store_true')
    args=parser.parse_args()
    run(args.data,args.output,args.epochs,args.trials,evaluate_tests=not args.development_only)


if __name__ == '__main__':
    main()
