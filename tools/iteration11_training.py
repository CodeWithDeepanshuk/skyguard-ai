"""Bounded-memory, causal research baselines for the Iteration 11 data rebuild.

NOT operational IMD validation. Fault/weather labels below are synthetic and
presumed-normal source-QC labels are imperfect. No promotion to live models.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, brier_score_loss,
                             confusion_matrix, f1_score, precision_score, recall_score)

from iteration11_data import PRIMARY, VERSION, atomic_replace, digest, write_json

FEATURES = ["gap_minutes", "missing_count"]
for prefix in ["temperature", "pressure", "humidity"]:
    FEATURES += [f"{prefix}_{suffix}" for suffix in [
        "delta", "rate", "z24", "iqr24", "frozen_minutes", "slope3h", "slope6h", "slope24h",
        "buddy_count", "buddy_residual", "buddy_spread", "buddy_age_minutes", "buddy_trend_residual"]]
FEATURES += ["hour_sin", "hour_cos", "year_sin", "year_cos"]
SPATIAL_FEATURES = [x for x in FEATURES if "buddy_" in x]
FAULT_TYPES = ["spike", "bias", "drift", "frozen", "noise", "missing_value"]


class RobustQC:
    """Non-learning temporal QC comparator; output is a score until calibrated."""
    def predict_proba(self, frame):
        z = frame[[f"{p}_z24" for p in ["temperature", "pressure", "humidity"]]].abs().max(axis=1).fillna(0)
        score = np.maximum(z.to_numpy(), frame.missing_count.to_numpy() * 10)
        p = 1 / (1 + np.exp(-np.clip(score - 6, -30, 30)))
        return np.column_stack([1-p, p])


def seed_for(text, seed):
    return int(hashlib.sha256(f"{seed}:{text}".encode()).hexdigest()[:8], 16)


def inject(frame, seed=111):
    """New episodes, not inherited old benchmark labels. Injection BEFORE features.

    All buddies get the SAME deterministic simulator, including their faults;
    no clean-reference/oracle neighbor stream. Holdout labels are simulator-only.
    """
    f = frame.sort_values("timestamp_utc").reset_index(drop=True).copy()
    f["y"] = np.where(f.qc_screened_proxy, 0, -1)
    f["fault_type"] = ""
    f["episode_id"] = ""
    f["weather_challenge"] = False
    if f.empty:
        return f
    sid = f.station_id.iloc[0]
    # Coherent, smooth 24h T/P/RH perturbations for same geographic block.
    # Synthetic challenges, NOT verified cyclones/fronts or meteorological labels.
    for year in sorted(f.timestamp_utc.dt.year.unique()):
        block_rng = np.random.default_rng(seed_for(f"weather:{f.geographic_block.iloc[0]}:{year}", seed))
        for month in [2, 5, 8, 11]:
            start = pd.Timestamp(year=int(year), month=month, day=int(block_rng.integers(8, 15)), tz="UTC")
            phase = (f.timestamp_utc - start).dt.total_seconds() / 86400
            mask = phase.between(0, 1) & f.y.eq(0)
            bump = np.sin(np.pi * phase[mask]) ** 2
            for column, size in zip(PRIMARY, [-4.0, -5.0, 12.0]):
                f.loc[mask, column] += size * bump
            f.loc[mask, "relative_humidity_pct"] = f.loc[mask, "relative_humidity_pct"].clip(0, 100)
            f.loc[mask, "weather_challenge"] = True
    for year in sorted(f.timestamp_utc.dt.year.unique()):
        rng = np.random.default_rng(seed_for(f"fault:{sid}:{year}", seed))
        for month in range(1, 13):
            # Two episodes / month, rotating faults; keep real cadence and gaps.
            for slot in range(2):
                kind = FAULT_TYPES[(month * 2 + slot) % len(FAULT_TYPES)]
                possible = f.index[(f.timestamp_utc.dt.year == year) & (f.timestamp_utc.dt.month == month)
                                   & f.y.eq(0) & ~f.weather_challenge & f.episode_id.eq("")]
                if len(possible) < 20:
                    continue
                begin = int(rng.choice(possible[3:-3]))
                hours = 0 if kind == "spike" else float(rng.choice([3, 6, 12, 24]))
                until = f.timestamp_utc.iloc[begin] + pd.Timedelta(hours=hours)
                ids = f.index[(f.index >= begin) & (f.timestamp_utc <= until) & f.y.eq(0)
                              & ~f.weather_challenge & f.episode_id.eq("")]
                if not len(ids):
                    continue
                # Do not join an injected episode across long natural reporting gaps.
                gap = f.loc[ids, "timestamp_utc"].diff().dt.total_seconds().gt(6 * 3600)
                if gap.any():
                    ids = ids[:int(np.flatnonzero(gap)[0])]
                if len(ids) < 2 and kind not in {"spike", "missing_value"}:
                    continue
                col_index = int(rng.integers(0, 3))
                col = PRIMARY[col_index]
                amp = [3.0, 5.0, 12.0][col_index] * float(rng.uniform(.5, 2)) * rng.choice([-1, 1])
                if kind == "spike":
                    f.loc[ids, col] += amp * 2
                elif kind == "bias":
                    f.loc[ids, col] += amp
                elif kind == "drift":
                    f.loc[ids, col] += np.linspace(amp * .1, amp, len(ids))
                elif kind == "frozen":
                    value = f.loc[max(0, begin - 1), col]
                    if not np.isfinite(value) or np.allclose(f.loc[ids, col], value):
                        continue
                    f.loc[ids, col] = value
                elif kind == "noise":
                    f.loc[ids, col] += rng.normal(0, abs(amp), len(ids))
                elif kind == "missing_value":
                    f.loc[ids, col] = np.nan
                f.loc[ids, "y"] = 1
                f.loc[ids, "fault_type"] = kind
                f.loc[ids, "episode_id"] = f"{seed}:{sid}:{year}:{month}:{slot}"
    return f


def temporal(frame):
    f = frame.sort_values("timestamp_utc").reset_index(drop=True)
    out = pd.DataFrame(index=f.index)
    stamps = pd.DatetimeIndex(f.timestamp_utc)
    minutes = f.timestamp_utc.diff().dt.total_seconds().div(60)
    out["gap_minutes"] = minutes
    out["missing_count"] = f[PRIMARY].isna().sum(axis=1)
    # All rolling baselines closed='left': current/future values never enter.
    hours = pd.Series((stamps - stamps[0]).total_seconds() / 3600, index=stamps)
    for col, prefix, floor in zip(PRIMARY, ["temperature", "pressure", "humidity"], [.3, .5, 2.0]):
        s = pd.Series(f[col].to_numpy(float), index=stamps)
        roll = s.rolling("24h", closed="left", min_periods=4)
        med = roll.median()
        spread = (roll.quantile(.75) - roll.quantile(.25)).clip(lower=floor)
        out[prefix + "_delta"] = s.diff().to_numpy()
        out[prefix + "_rate"] = (s.diff().to_numpy() / minutes.clip(lower=1).to_numpy() * 60)
        out[prefix + "_z24"] = ((s - med) / spread).to_numpy()
        out[prefix + "_iqr24"] = spread.to_numpy()
        changes = f[col].ne(f[col].shift()) | minutes.gt(360) | f[col].isna()
        run_start = f.timestamp_utc.groupby(changes.cumsum()).transform("first")
        out[prefix + "_frozen_minutes"] = (f.timestamp_utc - run_start).dt.total_seconds().div(60)
        for window in [3, 6, 24]:
            valid_hours = hours.where(s.notna())
            k = dict(window=f"{window}h", closed="left", min_periods=3)
            cov = (valid_hours * s).rolling(**k).mean() - valid_hours.rolling(**k).mean() * s.rolling(**k).mean()
            var = (valid_hours ** 2).rolling(**k).mean() - valid_hours.rolling(**k).mean() ** 2
            out[f"{prefix}_slope{window}h"] = (cov / var.where(var > 1e-6)).to_numpy()
    hr = stamps.hour + stamps.minute / 60
    out["hour_sin"], out["hour_cos"] = np.sin(2*np.pi*hr/24), np.cos(2*np.pi*hr/24)
    out["year_sin"], out["year_cos"] = np.sin(2*np.pi*stamps.dayofyear/365.25), np.cos(2*np.pi*stamps.dayofyear/365.25)
    return out.replace([np.inf, -np.inf], np.nan)


def spatial(frame, temp, buddies, max_age_minutes=90):
    """Past-only matches. Pressure compared only within compatible datums.

    Differences are temporal residuals, not absolute raw pressure across heights.
    Scores abstain (NaN) with fewer than two independent valid buddies.
    """
    f = frame.sort_values("timestamp_utc").reset_index(drop=True)
    result = temp.copy()
    for prefix in ["temperature", "pressure", "humidity"]:
        vals, trends, ages = [], [], []
        for other, features, compatible in buddies:
            if prefix == "pressure" and not compatible:
                continue
            right = pd.DataFrame({"neighbor_time": other.timestamp_utc.to_numpy(),
                                  "z": features[prefix + "_z24"].to_numpy(),
                                  "trend": features[prefix + "_slope6h"].to_numpy()}).sort_values("neighbor_time")
            matched = pd.merge_asof(f[["timestamp_utc"]], right, left_on="timestamp_utc", right_on="neighbor_time",
                                    direction="backward", tolerance=pd.Timedelta(minutes=max_age_minutes))
            vals.append(matched.z)
            trends.append(matched.trend)
            ages.append((matched.timestamp_utc - matched.neighbor_time).dt.total_seconds().div(60).where(matched.z.notna()))
        if vals:
            v = pd.concat(vals, axis=1)
            t = pd.concat(trends, axis=1)
            a = pd.concat(ages, axis=1)
            count = v.notna().sum(axis=1)
            center = v.median(axis=1)
            supported = count.ge(2)
            result[prefix + "_buddy_count"] = count
            result[prefix + "_buddy_residual"] = (temp[prefix + "_z24"] - center).where(supported)
            result[prefix + "_buddy_spread"] = v.sub(center, axis=0).abs().median(axis=1).where(supported)
            result[prefix + "_buddy_age_minutes"] = a.max(axis=1).where(supported)
            result[prefix + "_buddy_trend_residual"] = (temp[prefix + "_slope6h"] - t.median(axis=1)).where(t.notna().sum(axis=1).ge(2))
        else:
            for suffix in ["count", "residual", "spread", "age_minutes", "trend_residual"]:
                result[f"{prefix}_buddy_{suffix}"] = 0 if suffix == "count" else np.nan
    return result[FEATURES].replace([np.inf, -np.inf], np.nan).astype(np.float32)


def split_roles(times, station_role):
    t = pd.to_datetime(times, utc=True)
    year = t.dt.year
    split = pd.Series("unused", index=t.index)
    if station_role == "spatial_holdout":
        split.loc[year.eq(2023)] = "spatial_confirmation"
        return split
    split.loc[year.le(2021)] = "train"
    split.loc[year.eq(2022) & t.dt.month.le(4)] = "early_stop"
    split.loc[year.eq(2022) & t.dt.month.between(5, 8)] = "calibration"
    split.loc[year.eq(2022) & t.dt.month.ge(9)] = "policy"
    split.loc[year.eq(2023)] = "temporal_confirmation"
    return split


def build_features(root, seed=111, min_ready=True):
    root = Path(root)
    readiness = json.loads((root / "data_readiness.json").read_text())
    if min_ready and not readiness["ready_for_expanded_training"]:
        raise RuntimeError("Data gate failed: need >=50 eligible stations, >=25 outside legacy24. Download/profile first.")
    quality = pd.read_csv(root / "station_quality.csv", dtype={"station_id": str})
    ready = quality.loc[quality.training_eligible].set_index("station_id")
    graph = pd.read_csv(root / "neighbor_graph.csv", dtype={"station_id": str, "neighbor_id": str})
    target = root / f"features_seed{seed}"
    target.mkdir(exist_ok=True)
    contract = {"version": VERSION, "source_sha256": digest(Path(__file__)), "data_hash": readiness["all_data_hash"],
                "seed": seed, "features": FEATURES, "no_future_neighbors": True,
                "training_neighbors": "development stations only; no spatial holdout contamination",
                "confirmation_neighbors": "all eligible contemporaneous streams, with faults injected; not clean oracles",
                "labels": "synthetic faults and coherent perturbations on QC-screened presumed-normal proxy",
                "2023": "development confirmation, previously used elsewhere; NOT a new blind test"}
    contract_path = target / "contract.json"
    if contract_path.exists() and json.loads(contract_path.read_text()) != contract:
        raise RuntimeError("Feature contract changed: use a new root/version; stale caches will not be reused")
    write_json(contract_path, contract)
    @lru_cache(maxsize=10)
    def stream(sid):
        path = root / f"processed/{sid}.parquet"
        if digest(path) != ready.loc[sid, "processed_sha256"]:
            raise ValueError(f"Processed hash mismatch: {sid}")
        raw = pd.read_parquet(path)
        # per-year feature boundaries intentionally reset, no next-year influence
        f = inject(raw, seed)
        pieces = [temporal(g.reset_index(drop=True)) for _, g in f.groupby(f.timestamp_utc.dt.year, sort=True)]
        return f, pd.concat(pieces, ignore_index=True)
    for sid in ready.index:
        dest = target / f"{sid}.parquet"
        receipt_path = dest.with_name(dest.name + ".json")
        if dest.exists() and receipt_path.exists() and digest(dest) == json.loads(receipt_path.read_text())["sha256"]:
            continue
        frame, temp = stream(sid)
        parts = []
        for year, group in frame.groupby(frame.timestamp_utc.dt.year, sort=True):
            take = group.index
            own = group.reset_index(drop=True)
            own_temp = temp.loc[take].reset_index(drop=True)
            neighbours = []
            for edge in graph.loc[graph.station_id.eq(sid)].to_dict("records"):
                if year <= 2022 and edge["neighbor_role"] != "development":
                    continue
                neighbor, nf = stream(edge["neighbor_id"])
                ids = neighbor.index[neighbor.timestamp_utc.dt.year.eq(year)]
                if len(ids):
                    neighbours.append((neighbor.loc[ids].reset_index(drop=True), nf.loc[ids].reset_index(drop=True), bool(edge["pressure_compatible"])))
            feats = spatial(own, own_temp, neighbours)
            for col in ["station_id", "timestamp_utc", "y", "fault_type", "episode_id", "weather_challenge", "geographic_block"]:
                feats[col] = own[col].to_numpy()
            feats["split"] = split_roles(own.timestamp_utc, ready.loc[sid, "station_role"]).to_numpy()
            feats["legacy_24_station"] = bool(ready.loc[sid, "legacy_24_station"])
            parts.append(feats)
        combined = pd.concat(parts, ignore_index=True)
        tmp = dest.with_suffix(".partial.parquet")
        combined.to_parquet(tmp, index=False)
        atomic_replace(tmp, dest)
        write_json(receipt_path, {"sha256": digest(dest), "rows": len(combined)})
        print(f"Features: {sid}, {len(combined):,} rows", flush=True)
    stream.cache_clear()
    return target


def load_partition(directory, split, negative_cap=1500, seed=11, legacy_only=False):
    """Per-station deterministic negative subsampling; never samples final metrics."""
    rows = []
    for path in sorted(Path(directory).glob("*.parquet")):
        f = pd.read_parquet(path)
        f = f.loc[f.split.eq(split) & f.y.ge(0)]
        if legacy_only:
            f = f.loc[f.legacy_24_station]
        if negative_cap is not None:
            pos = f.loc[f.y.eq(1) | f.weather_challenge]
            neg = f.loc[f.y.eq(0) & ~f.weather_challenge]
            if len(neg) > negative_cap:
                neg = neg.sample(negative_cap, random_state=seed_for(str(path.name), seed))
            f = pd.concat([pos, neg])
        rows.append(f)
    if not rows:
        raise ValueError("Feature directory is empty")
    return pd.concat(rows, ignore_index=True)


def weights(frame):
    # Equal station mass, with capped episode weighting inside each station.
    w = 1 / frame.station_id.map(frame.station_id.value_counts()).to_numpy(float)
    positive = frame.y.eq(1).to_numpy()
    if positive.any():
        ep = frame.loc[positive, "episode_id"]
        w[positive] /= np.sqrt(ep.map(ep.value_counts()).to_numpy(float))
    return w / w.mean()


def metrics(frame, probability, threshold):
    y = frame.y.to_numpy(int)
    pred = np.asarray(probability) >= threshold
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    day = frame.timestamp_utc.dt.strftime("%Y-%m-%d")
    station_days = (frame.station_id + ":" + day).nunique()
    episodic = pd.DataFrame({"ep": frame.episode_id.to_numpy(), "hit": pred})
    episodic = episodic.loc[episodic.ep.ne("")].groupby("ep").hit.max()
    weather = frame.weather_challenge.to_numpy(bool) & (y == 0)
    return {"rows": len(y), "positives": int(y.sum()), "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
            "precision": float(precision_score(y, pred, zero_division=0)), "recall": float(recall_score(y, pred, zero_division=0)),
            "f1": float(f1_score(y, pred, zero_division=0)), "accuracy": float(accuracy_score(y, pred)),
            "pr_auc_ap": float(average_precision_score(y, probability)) if y.sum() else None,
            "brier": float(brier_score_loss(y, probability)),
            "fault_episode_recall": float(episodic.mean()) if len(episodic) else None,
            "false_positive_rows_per_observed_station_day": float(fp / max(station_days, 1)),
            "synthetic_weather_false_alarm_fraction": float(pred[weather].mean()) if weather.any() else None}


def calibrated(model, x, calibrator):
    p = np.clip(model.predict_proba(x)[:, 1], 1e-6, 1-1e-6)
    return calibrator.predict_proba(np.log(p/(1-p)).reshape(-1, 1))[:, 1]


def score_partition(directory, split, model, features, calibrator=None):
    """Keep only labels/timestamps/probabilities in RAM for full-prevalence scoring."""
    rows = []
    for path in sorted(Path(directory).glob("*.parquet")):
        f = pd.read_parquet(path)
        f = f.loc[f.split.eq(split) & f.y.ge(0)]
        if f.empty:
            continue
        p = (calibrated(model, f[features], calibrator) if calibrator is not None
             else model.predict_proba(f[features])[:, 1])
        slim = f[["station_id", "timestamp_utc", "y", "episode_id", "weather_challenge", "fault_type"]].copy()
        slim["probability"] = p
        rows.append(slim)
    if not rows:
        raise RuntimeError(f"No observations in {split}")
    return pd.concat(rows, ignore_index=True)


def train_research(root, seed=111, use_catboost=False, gpu=True, smoke=False):
    from lightgbm import LGBMClassifier, early_stopping, log_evaluation
    root = Path(root)
    features_dir = root / f"features_seed{seed}"
    output = root / f"research_seed{seed}"
    if (output / "frozen_policies.json").exists():
        return output  # no implicit repeated model selection or overwriting frozen candidates
    output.mkdir(exist_ok=True)
    fit = load_partition(features_dir, "train", negative_cap=2500)
    early = load_partition(features_dir, "early_stop", negative_cap=1500)
    if set(fit.y.unique()) != {0, 1} or set(early.y.unique()) != {0, 1}:
        raise RuntimeError("Both classes required in fit and early-stop periods")
    candidates = [("lightgbm_temporal", [x for x in FEATURES if x not in SPATIAL_FEATURES], False),
                  ("lightgbm_spatial", FEATURES, False)]
    if fit.loc[fit.legacy_24_station, "station_id"].nunique() >= 5:
        candidates.append(("lightgbm_legacy24_retrained", FEATURES, True))
    if use_catboost:
        candidates.append(("catboost_spatial", FEATURES, False))
    models = [("robust_qc", RobustQC(), FEATURES, False)]
    for name, feats, legacy in candidates:
        sub = fit.loc[fit.legacy_24_station] if legacy else fit
        if name.startswith("catboost"):
            from catboost import CatBoostClassifier
            model = CatBoostClassifier(iterations=60 if smoke else 1400, depth=6, learning_rate=.045,
                                       loss_function="Logloss", eval_metric="AUC", l2_leaf_reg=12,
                                       random_seed=seed, task_type="GPU" if gpu else "CPU", verbose=False,
                                       allow_writing_files=False, thread_count=4)
            model.fit(sub[feats], sub.y, sample_weight=weights(sub), eval_set=(early[feats], early.y),
                      early_stopping_rounds=100, verbose=False)
        else:
            model = LGBMClassifier(n_estimators=60 if smoke else 1400, num_leaves=31, max_depth=-1,
                                  learning_rate=.04, min_child_samples=120, reg_alpha=1, reg_lambda=12,
                                  colsample_bytree=.85, subsample=.85, subsample_freq=1,
                                  random_state=seed, n_jobs=4, verbosity=-1, force_col_wise=True,
                                  metric="average_precision")
            model.fit(sub[feats], sub.y, sample_weight=weights(sub), eval_set=[(early[feats], early.y)],
                      eval_metric="average_precision", callbacks=[early_stopping(100, first_metric_only=True, verbose=False), log_evaluation(0)])
        models.append((name, model, feats, legacy))
        print("Trained", name, "on", len(sub), "sampled rows from", sub.station_id.nunique(), "stations", flush=True)
    del fit, early
    # Full-prevalence calibration and policy sets, distinct four-month blocks.
    # If the full sets exceed RAM, score streaming by station instead of subsampling negatives.
    bundles = []
    for name, model, feats, legacy in models:
        cal = score_partition(features_dir, "calibration", model, feats)
        if set(cal.y.unique()) != {0, 1}:
            raise RuntimeError("Calibration block needs both classes")
        p = np.clip(cal.probability.to_numpy(), 1e-6, 1-1e-6)
        calibrator = LogisticRegression(C=1, solver="lbfgs", max_iter=500)
        calibrator.fit(np.log(p/(1-p)).reshape(-1, 1), cal.y)
        bundles.append({"name": name, "model": model, "features": feats, "calibrator": calibrator,
                        "legacy_retrained": legacy, "research_only": True})
    del cal
    frontier, decisions = [], []
    for bundle in bundles:
        policy = score_partition(features_dir, "policy", bundle["model"], bundle["features"], bundle["calibrator"])
        if policy.y.sum() == 0:
            raise RuntimeError("Policy period has no injected positives")
        p = policy.probability.to_numpy()
        rows = []
        for th in sorted(set([1.000001, *np.geomspace(.0001, .1, 24), *np.linspace(.1, .99, 35)])):
            item = {"model": bundle["name"], "threshold": float(th), **metrics(policy, p, th)}
            item["meets_development_budget"] = bool(item["precision"] >= .8 and item["false_positive_rows_per_observed_station_day"] <= .05)
            rows.append(item)
        acceptable = [x for x in rows if x["meets_development_budget"]]
        # No gate passing != operationally acceptable. Freeze a descriptive best-F1 comparator only.
        chosen = max(acceptable or rows, key=lambda x: x["f1"])
        bundle["threshold"] = chosen["threshold"]
        bundle["policy_gate_passed"] = bool(acceptable)
        model_path = output / (bundle["name"] + ".joblib")
        joblib.dump(bundle, model_path)
        decisions.append({**chosen, "path": model_path.name, "sha256": digest(model_path)})
        frontier.extend(rows)
    pd.DataFrame(frontier).to_csv(output / "policy_frontier.csv", index=False)
    write_json(output / "frozen_policies.json", {"version": VERSION, "seed": seed, "smoke_test_only": smoke,
        "feature_contract_sha256": digest(features_dir / "contract.json"), "policies": decisions,
        "warning": "Not promoted; 2023 confirmation is NOT fresh blind evidence; thresholds must not be retuned there",
        "versions": {p: importlib.metadata.version(p) for p in ["numpy", "pandas", "scikit-learn", "lightgbm", "joblib"]}})
    return output


def confirm_research(root, seed=111):
    root = Path(root)
    output = root / f"research_seed{seed}"
    result_path = output / "iteration11_result_block.json"
    if result_path.exists():
        return json.loads(result_path.read_text())
    lock = json.loads((output / "frozen_policies.json").read_text())
    if digest(root / f"features_seed{seed}/contract.json") != lock["feature_contract_sha256"]:
        raise RuntimeError("Feature contract differs from frozen training input")
    comparison, per_station, fault_rows = [], [], []
    # Read only station partitions, so full network scoring has bounded memory.
    for item in lock["policies"]:
        path = output / item["path"]
        if digest(path) != item["sha256"]:
            raise RuntimeError("Model hash mismatch")
        bundle = joblib.load(path)  # only artifacts generated by this pipeline
        grouped = {"temporal_confirmation": [], "spatial_confirmation": []}
        for part in sorted((root / f"features_seed{seed}").glob("*.parquet")):
            f = pd.read_parquet(part)
            f = f.loc[f.split.isin(grouped) & f.y.ge(0)]
            if f.empty:
                continue
            prob = calibrated(bundle["model"], f[bundle["features"]], bundle["calibrator"])
            slim = f[["station_id", "timestamp_utc", "y", "fault_type", "episode_id", "weather_challenge", "split"]].copy()
            slim["probability"] = prob
            for scope, g in slim.groupby("split"):
                grouped[scope].append(g)
                per_station.append({"model": bundle["name"], "split": scope, "station_id": part.stem,
                                    **metrics(g, g.probability, bundle["threshold"])})
        for scope, frames in grouped.items():
            if not frames:
                continue
            frame = pd.concat(frames, ignore_index=True)
            comparison.append({"model": bundle["name"], "split": scope, **metrics(frame, frame.probability, bundle["threshold"])})
            for kind, g in frame.loc[frame.y.eq(1)].groupby("fault_type"):
                pred = g.probability.ge(bundle["threshold"])
                eps = pd.DataFrame({"id": g.episode_id, "hit": pred}).groupby("id").hit.max()
                fault_rows.append({"model": bundle["name"], "split": scope, "fault": kind,
                                   "point_recall": float(pred.mean()), "episode_recall": float(eps.mean()),
                                   "positive_rows": len(g), "episodes": len(eps)})
    pd.DataFrame(comparison).to_csv(output / "iteration11_comparison.csv", index=False)
    pd.DataFrame(per_station).to_csv(output / "iteration11_station_metrics.csv", index=False)
    pd.DataFrame(fault_rows).to_csv(output / "iteration11_fault_recall.csv", index=False)
    result = {"version": VERSION, "seed": seed, "smoke_test_only": lock["smoke_test_only"],
              "data_readiness": json.loads((root / "data_readiness.json").read_text()), "comparison": comparison,
              "live_model_changed": False, "real_sensor_fault_accuracy": "unknown: no verified field fault labels",
              "unimplemented_in_this_baseline": ["packet loss detection without heartbeat contract", "validated maintenance prediction",
                                                 "root cause classification", "automatic correction", "IMD authorization/telemetry adapter"],
              "status": "Research data-expansion comparison; requires review, event bootstrap uncertainty and external AWS validation before promotion"}
    write_json(result_path, result)
    return result
