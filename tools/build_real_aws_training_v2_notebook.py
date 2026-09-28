"""Build the audited SkyGuard historical-training V2 Colab notebook.

The generated notebook deliberately keeps promotion fail-closed. It uses 100
policy-search trials and 100 station-day bootstrap replications; it never
duplicates observations to inflate the sample size.
"""
from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks" / "SkyGuard_Real_AWS_Training_2022_2024_V2_Audited.ipynb"


def md(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": dedent(source).strip() + "\n"}


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": dedent(source).strip() + "\n",
    }


cells = [
    md(r"""
    # SkyGuard AI - Audited Historical Training V2

    This notebook repairs the scientific and operational weaknesses found in
    `SkyGuard_Real_AWS_Training_2022_2024.ipynb`.

    **What it does differently**

    - never repeats rows to create fake sample size;
    - performs 100 reproducible policy-search trials on development data only;
    - performs 100 station-day block bootstrap replications for uncertainty;
    - separates model fitting, calibration, policy selection, temporal test and
      unseen-station test;
    - evaluates alert burden on untouched genuine observations and sensitivity
      on reproducibly injected evaluation copies;
    - requires causal persistence and cooldown before creating incidents;
    - creates a deployable promoted bundle only when every frozen gate passes.

    **Data limitation:** the bundled 2022-2024 archive is NOAA/NCEI Global
    Hourly Indian surface-station data exchanged through WMO channels. It is a
    24-station historical proxy. It is **not** a direct export from the new IMD
    AWS API and must never be presented as 1,153 live IMD AWS stations.

    **Label limitation:** public maintenance-confirmed hardware-fault labels are
    unavailable. Injected faults are controlled benchmark scenarios, not real
    field failures. Therefore, alert-burden and injected-recovery metrics are
    promotion evidence, but not a claim of real-world fault probability.
    """),
    md("""
    ## 1. Runtime and reproducibility

    Use a Colab GPU runtime. LightGBM runs on CPU; the causal TCN uses CUDA when
    available. All random sources and exported contracts are versioned.
    """),
    code(r"""
    import os, sys, json, math, time, random, hashlib, shutil, subprocess, warnings
    from pathlib import Path
    from datetime import datetime, timezone

    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-q",
        "lightgbm>=4.3", "scikit-learn>=1.4", "pandas>=2.1",
        "numpy>=1.26", "matplotlib>=3.8", "joblib>=1.3", "torch>=2.1"
    ])

    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    import joblib
    import lightgbm as lgb
    import torch
    import torch.nn as nn
    from torch.utils.data import Dataset, DataLoader
    from sklearn.metrics import (
        average_precision_score, brier_score_loss, precision_recall_fscore_support,
        roc_auc_score
    )
    from sklearn.isotonic import IsotonicRegression
    from sklearn.preprocessing import RobustScaler

    warnings.filterwarnings("ignore", category=FutureWarning)
    SEED = 26073
    POLICY_TRIALS = 100
    BOOTSTRAP_REPEATS = 100
    MODEL_SEEDS = [17, 41, 67, 89, 113]
    FALSE_ALERT_LIMIT = 0.05
    MIN_INJECTED_EVENT_RECALL = 0.80
    MIN_INJECTED_EVENT_PRECISION = 0.70
    MAX_MEDIAN_DELAY_MIN = 180.0
    MAX_SYNTHETIC_ECE = 0.10
    RUN_TCN = True

    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(SEED)
    torch.use_deterministic_algorithms(False)
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print({"device": str(DEVICE), "torch": torch.__version__, "policy_trials": POLICY_TRIALS,
           "bootstrap_repeats": BOOTSTRAP_REPEATS})
    """),
    md("""
    ## 2. Repository, immutable experiment folder and dataset receipt

    The notebook clones the canonical repository only when needed. An experiment
    folder is created in Google Drive when available so Colab disconnects do not
    destroy artifacts.
    """),
    code(r"""
    IN_COLAB = "google.colab" in sys.modules
    if IN_COLAB:
        from google.colab import drive
        drive.mount("/content/drive", force_remount=False)
        if not Path("/content/skyguard-ai").exists():
            subprocess.check_call(["git", "clone", "https://github.com/CodeWithDeepanshuk/skyguard-ai.git", "/content/skyguard-ai"])
        os.chdir("/content/skyguard-ai")

    ROOT = Path.cwd().resolve()
    if not (ROOT / "data").exists() and (ROOT.parent / "data").exists():
        ROOT = ROOT.parent
        os.chdir(ROOT)

    if IN_COLAB:
        EXPERIMENT_ROOT = Path("/content/drive/MyDrive/SkyGuard/experiments/real_aws_v2_audited")
    else:
        EXPERIMENT_ROOT = ROOT / "artifacts" / "real_aws_v2_audited"
    CANDIDATE_DIR = EXPERIMENT_ROOT / "candidate"
    PROMOTED_DIR = EXPERIMENT_ROOT / "promoted"
    REPORT_DIR = EXPERIMENT_ROOT / "reports"
    for directory in [CANDIDATE_DIR, PROMOTED_DIR, REPORT_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

    DATA_CANDIDATES = [
        ROOT / "data/archive/legacy_noaa_aws/aws_observations_2022_2024.csv.gz",
        ROOT / "data/archive/legacy_noaa_aws/aws_observations_2022_2024.csv",
    ]
    DATA_PATH = next((p for p in DATA_CANDIDATES if p.exists()), None)
    if DATA_PATH is None:
        raise FileNotFoundError("Historical archive not found. Do not silently download or substitute another provider.")

    def sha256_file(path, block=1024 * 1024):
        digest = hashlib.sha256()
        with Path(path).open("rb") as stream:
            for chunk in iter(lambda: stream.read(block), b""):
                digest.update(chunk)
        return digest.hexdigest()

    DATA_SHA256 = sha256_file(DATA_PATH)
    print({"dataset": str(DATA_PATH), "sha256": DATA_SHA256, "bytes": DATA_PATH.stat().st_size})
    """),
    md("""
    ## 3. Load and verify the observation contract

    Pressure semantics are retained explicitly. The legacy archive contains a
    row-wise mixture of NOAA sea-level pressure (`slp`) and MA1 aviation
    altimeter/QNH values. The live IMD field is documented as MSLP, so this
    notebook preserves the original pressure and source for audit but admits
    **only native SLP rows** to the deployable pressure feature. It does not
    guess a conversion or apply a second elevation reduction.
    """),
    code(r"""
    REQUIRED = {
        "station_id", "timestamp_utc", "station_name", "latitude", "longitude",
        "elevation_m", "temperature_c", "relative_humidity_pct", "pressure_hpa",
        "pressure_source", "temperature_quality", "pressure_quality", "cluster",
        "evaluation_role", "source"
    }
    df = pd.read_csv(DATA_PATH, low_memory=False)
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError(f"Dataset contract missing columns: {sorted(missing)}")
    df["station_id"] = df["station_id"].astype(str)
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True, errors="raise")
    for c in ["temperature_c", "pressure_hpa", "relative_humidity_pct", "latitude", "longitude", "elevation_m"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.sort_values(["station_id", "timestamp_utc"]).reset_index(drop=True)

    # Preserve the source values, then create a fail-closed MSLP-compatible
    # pressure channel. MA1 altimeter/QNH is useful aviation evidence but is
    # not silently relabelled as IMD MSLP.
    df["pressure_hpa_raw"] = df["pressure_hpa"]
    df["pressure_source_raw"] = df["pressure_source"].fillna("").astype(str).str.strip().str.lower()
    known_pressure_sources = {"", "slp", "ma1_altimeter"}
    unknown_pressure_sources = sorted(set(df.pressure_source_raw) - known_pressure_sources)
    if unknown_pressure_sources:
        raise ValueError(f"Unknown pressure sources require review: {unknown_pressure_sources}")
    slp_mask = df.pressure_source_raw.eq("slp") & df.pressure_hpa_raw.notna()
    df["pressure_hpa"] = df.pressure_hpa_raw.where(slp_mask)
    df["pressure_source"] = np.where(slp_mask, "slp", "")

    audit = {
        "rows": int(len(df)), "stations": int(df.station_id.nunique()),
        "start": df.timestamp_utc.min().isoformat(), "end": df.timestamp_utc.max().isoformat(),
        "duplicates": int(df.duplicated(["station_id", "timestamp_utc"]).sum()),
        "negative_gaps": int((df.groupby("station_id").timestamp_utc.diff().dt.total_seconds() < 0).sum()),
        "raw_pressure_sources": df.pressure_source_raw.replace("", "MISSING").value_counts().to_dict(),
        "normalization_contract": "native NOAA SLP only; MA1 altimeter retained in pressure_hpa_raw and excluded from MSLP model input",
        "eligible_slp_rows": int(slp_mask.sum()),
        "eligible_slp_stations": int(df.loc[slp_mask, "station_id"].nunique()),
        "sources": df.source.fillna("MISSING").value_counts().to_dict(),
    }
    print(json.dumps(audit, indent=2, default=str))
    assert audit["duplicates"] == 0 and audit["negative_gaps"] == 0
    assert audit["eligible_slp_rows"] > 0 and audit["eligible_slp_stations"] > 0
    """),
    md("""
    ## 4. Frozen partitions

    - model fit: development stations, 2022 through March 2023;
    - calibration: development stations, April through June 2023;
    - policy selection: development stations, July through December 2023;
    - temporal test: development stations, all of 2024;
    - spatial test: stations marked `station_holdout`, all of 2024.

    Neither 2024 partition is read during model, calibration or policy fitting.
    """),
    code(r"""
    is_holdout = df.evaluation_role.astype(str).eq("station_holdout")
    t = df.timestamp_utc
    df["split"] = "excluded"
    df.loc[(~is_holdout) & (t < "2023-04-01"), "split"] = "model_fit"
    df.loc[(~is_holdout) & t.between("2023-04-01", "2023-06-30 23:59:59+00:00"), "split"] = "calibration"
    df.loc[(~is_holdout) & t.between("2023-07-01", "2023-12-31 23:59:59+00:00"), "split"] = "policy_select"
    df.loc[(~is_holdout) & t.between("2024-01-01", "2024-12-31 23:59:59+00:00"), "split"] = "test_temporal"
    df.loc[is_holdout & t.between("2024-01-01", "2024-12-31 23:59:59+00:00"), "split"] = "test_spatial"
    split_table = df.groupby("split").agg(rows=("station_id", "size"), stations=("station_id", "nunique"),
                                           start=("timestamp_utc", "min"), end=("timestamp_utc", "max"))
    display(split_table)
    assert (df.loc[df.split.eq("model_fit"), "timestamp_utc"].max() <
            df.loc[df.split.eq("calibration"), "timestamp_utc"].min())
    assert not set(df.loc[df.split.eq("model_fit"), "station_id"]) & set(df.loc[df.split.eq("test_spatial"), "station_id"])
    """),
    md("""
    ## 5. Causal temporal and contemporaneous regional features

    Rolling baselines use `shift(1)`, so the current reading never contributes
    to its own reference. Regional consensus uses only same-cluster readings in
    the same three-hour time bucket and leaves the target station out.
    """),
    code(r"""
    PARAMS = ["temperature_c", "pressure_hpa", "relative_humidity_pct"]

    def engineer_features(frame):
        z = frame.sort_values(["station_id", "timestamp_utc"]).copy()
        group = z.groupby("station_id", sort=False, group_keys=False)
        z["gap_hours"] = group.timestamp_utc.diff().dt.total_seconds().div(3600)
        for col, short in [("temperature_c", "t"), ("pressure_hpa", "p"), ("relative_humidity_pct", "rh")]:
            z[f"{short}_delta"] = group[col].diff()
            z[f"{short}_rate"] = z[f"{short}_delta"].div(z.gap_hours.where(z.gap_hours.between(.25, 6)))
            prior = group[col].shift(1)
            roll_med = prior.groupby(z.station_id).transform(lambda s: s.rolling(16, min_periods=5).median())
            abs_dev = (prior - roll_med).abs()
            roll_mad = abs_dev.groupby(z.station_id).transform(lambda s: s.rolling(16, min_periods=5).median())
            floor = {"t": .5, "p": .6, "rh": 3.0}[short]
            z[f"{short}_robust_z"] = (z[col] - roll_med) / np.maximum(1.4826 * roll_mad, floor)
            z[f"{short}_ewm_residual"] = z[col] - prior.groupby(z.station_id).transform(lambda s: s.ewm(span=12, adjust=False).mean())

        z["hour_sin"] = np.sin(2 * np.pi * z.timestamp_utc.dt.hour / 24)
        z["hour_cos"] = np.cos(2 * np.pi * z.timestamp_utc.dt.hour / 24)
        z["doy_sin"] = np.sin(2 * np.pi * z.timestamp_utc.dt.dayofyear / 365.25)
        z["doy_cos"] = np.cos(2 * np.pi * z.timestamp_utc.dt.dayofyear / 365.25)
        z["bucket_3h"] = z.timestamp_utc.dt.floor("3h")

        # Exact leave-one-station-out regional mean. Pressure is already SLP;
        # applying a barometric elevation reduction again would be invalid.
        keys = ["cluster", "bucket_3h"]
        for col, short in [("temperature_c", "t"), ("pressure_hpa", "p"), ("relative_humidity_pct", "rh")]:
            valid = z[col].notna().astype(int)
            total = z[col].fillna(0).groupby([z[k] for k in keys]).transform("sum")
            count = valid.groupby([z[k] for k in keys]).transform("sum")
            z[f"{short}_peer_count"] = count - valid
            consensus = (total - z[col].fillna(0)).div((count - valid).replace(0, np.nan))
            z[f"{short}_regional_residual"] = z[col] - consensus
        z["min_peer_count"] = z[["t_peer_count", "p_peer_count", "rh_peer_count"]].min(axis=1)
        return z

    df = engineer_features(df)
    print("Feature rows:", len(df), "minimum/median peers:", df.min_peer_count.min(), df.min_peer_count.median())
    """),
    md("""
    ## 6. Controlled causal fault curriculum

    Faults are injected only into copies. Raw historical observations remain
    unchanged. Each episode has an ID, type, sensor, start and end. The same
    injection function is used with different frozen seeds for fit,
    calibration, policy and final-test copies.
    """),
    code(r"""
    def inject_fault_episodes(base, seed, episodes_per_station=12):
        rng = np.random.default_rng(seed)
        out = base[[c for c in base.columns if not c.endswith(("_delta", "_rate", "_robust_z", "_ewm_residual", "_regional_residual", "_peer_count"))
                    and c not in {"min_peer_count", "bucket_3h"}]].copy()
        out["fault_label"] = 0
        out["episode_id"] = ""
        out["fault_type"] = "normal"
        out["fault_sensor"] = ""
        choices = ["spike", "step_bias", "drift", "freeze"]
        sensor_specs = {
            "temperature_c": (3.0, 9.0), "pressure_hpa": (5.0, 18.0),
            "relative_humidity_pct": (12.0, 35.0)
        }
        for station, idx in out.groupby("station_id", sort=False).groups.items():
            idx = np.asarray(list(idx), dtype=int)
            if len(idx) < 100:
                continue
            eligible = idx[24:-24]
            starts = rng.choice(eligible, size=min(episodes_per_station, max(1, len(eligible)//40)), replace=False)
            for number, start in enumerate(np.sort(starts)):
                kind = rng.choice(choices)
                length = 1 if kind == "spike" else int(rng.integers(3, 9))
                loc = idx[np.searchsorted(idx, start):np.searchsorted(idx, start)+length]
                if not len(loc):
                    continue
                eligible_sensors = [name for name in sensor_specs if out.loc[loc, name].notna().all()]
                if not eligible_sensors:
                    continue
                sensor = rng.choice(eligible_sensors)
                low, high = sensor_specs[sensor]
                magnitude = float(rng.uniform(low, high) * rng.choice([-1, 1]))
                original = out.loc[loc, sensor].copy()
                if kind == "spike":
                    out.loc[loc, sensor] = original + magnitude
                elif kind == "step_bias":
                    out.loc[loc, sensor] = original + magnitude
                elif kind == "drift":
                    out.loc[loc, sensor] = original + np.linspace(magnitude/len(loc), magnitude, len(loc))
                else:
                    out.loc[loc, sensor] = original.iloc[0]
                eid = f"inj-{seed}-{station}-{number:03d}"
                out.loc[loc, ["fault_label", "episode_id", "fault_type", "fault_sensor"]] = [1, eid, kind, sensor]
        # Recompute every causal feature from corrupted values.
        return engineer_features(out)

    fit_clean = df[df.split.eq("model_fit")].copy()
    cal_clean = df[df.split.eq("calibration")].copy()
    policy_clean = df[df.split.eq("policy_select")].copy()
    fit_injected = inject_fault_episodes(fit_clean, 1701, 14)
    cal_injected = inject_fault_episodes(cal_clean, 4101, 10)
    policy_injected = inject_fault_episodes(policy_clean, 6701, 12)
    print({"fit_fault_rows": int(fit_injected.fault_label.sum()),
           "calibration_fault_rows": int(cal_injected.fault_label.sum()),
           "policy_fault_rows": int(policy_injected.fault_label.sum())})
    """),
    md("""
    ## 7. Five-seed LightGBM ensemble

    Normal rows are sampled by station and month to control imbalance. Training
    labels come only from the documented injection curriculum, never from raw
    NOAA source flags interpreted as hardware faults.
    """),
    code(r"""
    FEATURES = [
        "temperature_c", "pressure_hpa", "relative_humidity_pct", "gap_hours",
        "t_delta", "p_delta", "rh_delta", "t_rate", "p_rate", "rh_rate",
        "t_robust_z", "p_robust_z", "rh_robust_z",
        "t_ewm_residual", "p_ewm_residual", "rh_ewm_residual",
        "t_regional_residual", "p_regional_residual", "rh_regional_residual",
        "t_peer_count", "p_peer_count", "rh_peer_count", "min_peer_count",
        "hour_sin", "hour_cos", "doy_sin", "doy_cos"
    ]
    assert all(c in fit_injected for c in FEATURES)

    positive = fit_injected[fit_injected.fault_label.eq(1)]
    normal_pool = fit_injected[fit_injected.fault_label.eq(0)].copy()
    normal_pool["month"] = normal_pool.timestamp_utc.dt.to_period("M").astype(str)
    normal = (normal_pool.groupby(["station_id", "month"], group_keys=False)
              .apply(lambda g: g.sample(min(len(g), 1000), random_state=SEED)))
    train = pd.concat([normal, positive], ignore_index=True).sample(frac=1, random_state=SEED)
    X_train = train[FEATURES].replace([np.inf, -np.inf], np.nan)
    medians = X_train.median()
    X_train = X_train.fillna(medians)
    y_train = train.fault_label.astype(int)

    models = []
    cal_raw = []
    X_cal = cal_injected[FEATURES].replace([np.inf, -np.inf], np.nan).fillna(medians)
    for seed in MODEL_SEEDS:
        model = lgb.LGBMClassifier(
            objective="binary", n_estimators=1800, learning_rate=.025,
            num_leaves=31, max_depth=-1, min_child_samples=80,
            subsample=.8, colsample_bytree=.8, reg_lambda=4.0,
            reg_alpha=.5, random_state=seed, n_jobs=-1, verbosity=-1
        )
        model.fit(X_train, y_train, callbacks=[lgb.log_evaluation(0)])
        models.append(model)
        cal_raw.append(model.predict_proba(X_cal)[:, 1])
    cal_tree_raw = np.mean(cal_raw, axis=0)
    calibrator = IsotonicRegression(out_of_bounds="clip").fit(cal_tree_raw, cal_injected.fault_label)
    cal_tree = calibrator.predict(cal_tree_raw)
    print("Calibration injected AUPRC:", average_precision_score(cal_injected.fault_label, cal_tree))
    """),
    md("""
    ## 8. Causal TCN ablation

    The TCN is optional and advisory. Sequences never cross station boundaries.
    Its score is admitted into fusion only if development policy search assigns
    it weight and the final frozen gates still pass.
    """),
    code(r"""
    SEQ_FEATURES = [
        "t_robust_z", "p_robust_z", "rh_robust_z", "t_rate", "p_rate", "rh_rate",
        "t_regional_residual", "p_regional_residual", "rh_regional_residual"
    ]
    SEQ_LEN = 12
    scaler = RobustScaler().fit(train[SEQ_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0))

    def make_sequences(frame, stride=1):
        X, y, row_indices = [], [], []
        for _, g in frame.sort_values(["station_id", "timestamp_utc"]).groupby("station_id", sort=False):
            values = scaler.transform(g[SEQ_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0))
            labels = g.fault_label.to_numpy(dtype=np.float32) if "fault_label" in g else np.zeros(len(g), dtype=np.float32)
            indices = g.index.to_numpy()
            for end in range(SEQ_LEN - 1, len(g), stride):
                X.append(values[end-SEQ_LEN+1:end+1]); y.append(labels[end]); row_indices.append(indices[end])
        return np.asarray(X, np.float32), np.asarray(y, np.float32), np.asarray(row_indices)

    class CausalTCN(nn.Module):
        def __init__(self, n_features):
            super().__init__()
            self.net = nn.Sequential(
                nn.Conv1d(n_features, 32, 3, padding=2, dilation=1), nn.ReLU(),
                nn.Conv1d(32, 32, 3, padding=4, dilation=2), nn.ReLU(),
                nn.Conv1d(32, 32, 3, padding=8, dilation=4), nn.ReLU(),
            )
            self.head = nn.Linear(32, 1)
        def forward(self, x):
            h = self.net(x.transpose(1, 2))
            # Convolutions contain right padding; use the original final-time position.
            return self.head(h[:, :, x.shape[1]-1]).squeeze(1)

    tcn = CausalTCN(len(SEQ_FEATURES)).to(DEVICE)
    tcn_history = []
    if RUN_TCN:
        X_seq, y_seq, _ = make_sequences(fit_injected, stride=2)
        X_val_seq, y_val_seq, _ = make_sequences(cal_injected, stride=1)
        train_loader = DataLoader(list(zip(torch.from_numpy(X_seq), torch.from_numpy(y_seq))), batch_size=1024,
                                  shuffle=True, num_workers=0, pin_memory=torch.cuda.is_available())
        optimizer = torch.optim.AdamW(tcn.parameters(), lr=8e-4, weight_decay=1e-4)
        criterion = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([(len(y_seq)-y_seq.sum())/max(y_seq.sum(),1)], device=DEVICE))
        best_state, best_auprc, patience = None, -1.0, 0
        for epoch in range(1, 31):
            tcn.train(); losses = []
            for xb, yb in train_loader:
                xb, yb = xb.to(DEVICE), yb.to(DEVICE)
                optimizer.zero_grad(set_to_none=True)
                loss = criterion(tcn(xb), yb); loss.backward()
                torch.nn.utils.clip_grad_norm_(tcn.parameters(), 2.0)
                optimizer.step(); losses.append(float(loss.detach().cpu()))
            tcn.eval()
            with torch.no_grad():
                logits = tcn(torch.from_numpy(X_val_seq).to(DEVICE)).cpu().numpy()
            probs = 1/(1+np.exp(-np.clip(logits, -30, 30)))
            auprc = average_precision_score(y_val_seq, probs)
            tcn_history.append({"epoch": epoch, "loss": np.mean(losses), "calibration_auprc": auprc})
            if auprc > best_auprc + 1e-4:
                best_auprc, best_state, patience = auprc, {k:v.detach().cpu().clone() for k,v in tcn.state_dict().items()}, 0
            else:
                patience += 1
            if patience >= 5:
                break
        tcn.load_state_dict(best_state); tcn.to(DEVICE).eval()
    print({"tcn_enabled": RUN_TCN, "best_calibration_auprc": best_auprc, "epochs": len(tcn_history)})
    """),
    md("""
    ## 9. Score all development rows

    Missing sequence prefixes remain unavailable rather than receiving invented
    neural scores. The tree ensemble and TCN outputs are kept separate for
    ablation and traceability.
    """),
    code(r"""
    def score_frame(frame):
        out = frame.copy()
        X = out[FEATURES].replace([np.inf, -np.inf], np.nan).fillna(medians)
        raw = np.mean([m.predict_proba(X)[:,1] for m in models], axis=0)
        out["tree_score"] = calibrator.predict(raw)
        out["tcn_score"] = np.nan
        if RUN_TCN:
            seq, _, indices = make_sequences(out, stride=1)
            with torch.no_grad():
                logits = tcn(torch.from_numpy(seq).to(DEVICE)).cpu().numpy()
            probs = 1/(1+np.exp(-np.clip(logits, -30, 30)))
            out.loc[indices, "tcn_score"] = probs
        out["spatial_evidence"] = np.nanmax(np.column_stack([
            out.t_regional_residual.abs().div(3.0),
            out.p_regional_residual.abs().div(4.0),
            out.rh_regional_residual.abs().div(15.0)
        ]), axis=1)
        out["spatial_evidence"] = 1 - np.exp(-out.spatial_evidence.clip(lower=0).fillna(0))
        return out

    cal_scored = score_frame(cal_injected)
    policy_clean_scored = score_frame(policy_clean.assign(fault_label=0, episode_id="", fault_type="normal", fault_sensor=""))
    policy_injected_scored = score_frame(policy_injected)
    """),
    md("""
    ## 10. Incident policy and metrics

    A row score does not automatically become an incident. A station must meet a
    causal `k`-of-`n` persistence rule, and repeated alerts are grouped with a
    cooldown. Missing peers can be required to abstain.
    """),
    code(r"""
    def apply_policy(frame, cfg):
        z = frame.sort_values(["station_id", "timestamp_utc"]).copy()
        tcn_score = z.tcn_score.fillna(z.tree_score)
        z["fusion_score"] = (cfg["tree_weight"] * z.tree_score +
                             cfg["tcn_weight"] * tcn_score +
                             cfg["spatial_weight"] * z.spatial_evidence)
        z["candidate"] = z.fusion_score.ge(cfg["threshold"])
        if cfg["min_peers"] > 0:
            z["candidate"] &= z.min_peer_count.ge(cfg["min_peers"])
        z["alert"] = False
        for _, g in z.groupby("station_id", sort=False):
            rolling = g.candidate.astype(int).rolling(cfg["n"], min_periods=cfg["n"]).sum()
            z.loc[g.index, "alert"] = rolling.ge(cfg["k"]).to_numpy()
        return z

    def incident_table(scored, cfg):
        z = apply_policy(scored, cfg)
        rows = []
        gap = pd.Timedelta(minutes=cfg["cooldown_min"])
        for station, g in z[z.alert].groupby("station_id", sort=False):
            g = g.sort_values("timestamp_utc")
            event_no = (g.timestamp_utc.diff().gt(gap)).cumsum()
            for _, event in g.groupby(event_no):
                rows.append({"station_id": station, "start": event.timestamp_utc.min(),
                             "end": event.timestamp_utc.max(), "max_score": event.fusion_score.max()})
        return pd.DataFrame(rows, columns=["station_id", "start", "end", "max_score"]), z

    def station_days(frame):
        total = 0.0
        for _, g in frame.groupby("station_id"):
            total += max((g.timestamp_utc.max() - g.timestamp_utc.min()).total_seconds()/86400, 1/24)
        return total

    def evaluate_policy(clean, injected, cfg):
        clean_events, _ = incident_table(clean, cfg)
        predicted, scored = incident_table(injected, cfg)
        truth = (injected[injected.fault_label.eq(1) & injected.episode_id.ne("")]
                 .groupby(["station_id", "episode_id"], as_index=False)
                 .agg(start=("timestamp_utc", "min"), end=("timestamp_utc", "max")))
        matched_pred, matched_truth, delays = set(), set(), []
        for ti, true in truth.iterrows():
            candidates = predicted[(predicted.station_id.eq(true.station_id)) &
                                   (predicted.end.ge(true.start)) & (predicted.start.le(true.end + pd.Timedelta(hours=3)))]
            for pi, pred in candidates.iterrows():
                if pi not in matched_pred:
                    matched_pred.add(pi); matched_truth.add(ti)
                    delays.append(max(0, (pred.start-true.start).total_seconds()/60)); break
        tp, fp, fn = len(matched_truth), len(predicted)-len(matched_pred), len(truth)-len(matched_truth)
        precision = tp/max(tp+fp,1); recall = tp/max(tp+fn,1)
        return {
            "clean_alerts_per_station_day": len(clean_events)/max(station_days(clean), 1e-9),
            "event_precision": precision, "event_recall": recall,
            "event_f1": 2*precision*recall/max(precision+recall, 1e-9),
            "median_delay_min": float(np.median(delays)) if delays else float("inf"),
            "clean_events": len(clean_events), "injected_predicted_events": len(predicted),
            "injected_truth_events": len(truth)
        }
    """),
    md("""
    ## 11. One hundred policy-search trials

    These are 100 distinct configurations evaluated on development data. The
    objective first enforces the false-alert budget, then maximizes injected
    event F1 and recall while minimizing delay. Test data remains unopened.
    """),
    code(r"""
    rng = np.random.default_rng(SEED)
    rows = []
    for trial in range(POLICY_TRIALS):
        weights = rng.dirichlet([3.0, 1.5 if RUN_TCN else .001, 2.0])
        cfg = {
            "trial": trial,
            "tree_weight": float(weights[0]), "tcn_weight": float(weights[1] if RUN_TCN else 0),
            "spatial_weight": float(weights[2]),
            "threshold": float(rng.uniform(.45, .98)),
            "n": int(rng.choice([2, 3, 4, 5])),
            "k": 0, "cooldown_min": int(rng.choice([60, 120, 180, 360])),
            "min_peers": int(rng.choice([0, 1, 2, 3]))
        }
        cfg["k"] = int(rng.integers(2, cfg["n"]+1))
        metrics = evaluate_policy(policy_clean_scored, policy_injected_scored, cfg)
        feasible = metrics["clean_alerts_per_station_day"] <= FALSE_ALERT_LIMIT
        objective = (0 if feasible else -1000 * metrics["clean_alerts_per_station_day"])
        objective += 4*metrics["event_f1"] + 2*metrics["event_recall"] - min(metrics["median_delay_min"], 1440)/1440
        rows.append({**cfg, **metrics, "feasible": feasible, "objective": objective})
    policy_search = pd.DataFrame(rows).sort_values(["feasible", "objective"], ascending=[False, False])
    display(policy_search.head(15))
    if not policy_search.feasible.any():
        raise RuntimeError("No development policy satisfies the alert budget. Promotion must fail; revise features/model, not gates.")
    selected = policy_search[policy_search.feasible].iloc[0].to_dict()
    POLICY_KEYS = ["tree_weight", "tcn_weight", "spatial_weight", "threshold", "n", "k", "cooldown_min", "min_peers"]
    FROZEN_POLICY = {k: (int(selected[k]) if k in {"n", "k", "cooldown_min", "min_peers"} else float(selected[k])) for k in POLICY_KEYS}
    print("FROZEN POLICY", json.dumps(FROZEN_POLICY, indent=2))
    policy_search.to_csv(REPORT_DIR / "policy_search_100_trials.csv", index=False)
    """),
    md("""
    ## 12. Synthetic calibration audit

    Calibration is measured only against injected labels and is explicitly
    named synthetic-benchmark calibration. It must not be displayed as a real
    probability of hardware failure on the public website.
    """),
    code(r"""
    def expected_calibration_error(y, p, bins=10):
        y, p = np.asarray(y), np.asarray(p)
        edges = np.linspace(0, 1, bins+1); total = 0.0
        for lo, hi in zip(edges[:-1], edges[1:]):
            mask = (p >= lo) & (p < hi if hi < 1 else p <= hi)
            if mask.any(): total += mask.mean() * abs(y[mask].mean() - p[mask].mean())
        return float(total)
    synthetic_ece = expected_calibration_error(cal_injected.fault_label, cal_tree)
    calibration_report = {
        "scope": "controlled injected benchmark only; not field-fault probability",
        "brier": float(brier_score_loss(cal_injected.fault_label, cal_tree)),
        "ece_10bin": synthetic_ece,
        "auprc": float(average_precision_score(cal_injected.fault_label, cal_tree)),
    }
    print(json.dumps(calibration_report, indent=2))
    """),
    md("""
    ## 13. Open the frozen 2024 temporal and unseen-station tests exactly once

    Clean observations measure operational alert burden. Separate injected
    copies measure controlled fault sensitivity. Thresholds and persistence are
    already frozen and are never adjusted from these results.
    """),
    code(r"""
    temporal_clean = df[df.split.eq("test_temporal")].copy().assign(fault_label=0, episode_id="", fault_type="normal", fault_sensor="")
    spatial_clean = df[df.split.eq("test_spatial")].copy().assign(fault_label=0, episode_id="", fault_type="normal", fault_sensor="")
    temporal_injected = inject_fault_episodes(temporal_clean, 8901, 10)
    spatial_injected = inject_fault_episodes(spatial_clean, 11301, 14)

    temporal_clean_scored = score_frame(temporal_clean)
    spatial_clean_scored = score_frame(spatial_clean)
    temporal_injected_scored = score_frame(temporal_injected)
    spatial_injected_scored = score_frame(spatial_injected)

    temporal_metrics = evaluate_policy(temporal_clean_scored, temporal_injected_scored, FROZEN_POLICY)
    spatial_metrics = evaluate_policy(spatial_clean_scored, spatial_injected_scored, FROZEN_POLICY)
    frozen_results = pd.DataFrame([
        {"test": "2024_temporal_seen_stations", **temporal_metrics},
        {"test": "2024_unseen_stations", **spatial_metrics},
    ])
    display(frozen_results)
    """),
    md("""
    ## 14. One hundred station-day block bootstrap replications

    Whole station-days are resampled so temporally adjacent rows stay together.
    This quantifies uncertainty without pretending individual rows are
    independent.
    """),
    code(r"""
    def block_bootstrap(clean, injected, cfg, repeats=100, seed=SEED):
        rng = np.random.default_rng(seed)
        clean = clean.copy(); injected = injected.copy()
        clean["block"] = clean.station_id + "|" + clean.timestamp_utc.dt.strftime("%Y-%m-%d")
        injected["block"] = injected.station_id + "|" + injected.timestamp_utc.dt.strftime("%Y-%m-%d")
        blocks = clean.block.unique(); records = []
        for repeat in range(repeats):
            sampled = rng.choice(blocks, size=len(blocks), replace=True)
            counts = pd.Series(sampled).value_counts()
            cparts, iparts = [], []
            for block, count in counts.items():
                for copy_no in range(int(count)):
                    c = clean[clean.block.eq(block)].copy(); i = injected[injected.block.eq(block)].copy()
                    suffix = f"|boot{repeat}|copy{copy_no}"
                    c["station_id"] += suffix; i["station_id"] += suffix
                    if "episode_id" in i: i["episode_id"] = i.episode_id.where(i.episode_id.eq(""), i.episode_id + suffix)
                    cparts.append(c); iparts.append(i)
            m = evaluate_policy(pd.concat(cparts, ignore_index=True), pd.concat(iparts, ignore_index=True), cfg)
            records.append({"repeat": repeat, **m})
        return pd.DataFrame(records)

    boot_temporal = block_bootstrap(temporal_clean_scored, temporal_injected_scored, FROZEN_POLICY, BOOTSTRAP_REPEATS, 26073)
    boot_spatial = block_bootstrap(spatial_clean_scored, spatial_injected_scored, FROZEN_POLICY, BOOTSTRAP_REPEATS, 26074)
    bootstrap = pd.concat([boot_temporal.assign(test="temporal"), boot_spatial.assign(test="spatial")], ignore_index=True)
    ci = bootstrap.groupby("test")[["clean_alerts_per_station_day", "event_precision", "event_recall", "event_f1", "median_delay_min"]].quantile([.025, .5, .975])
    display(ci)
    bootstrap.to_csv(REPORT_DIR / "station_day_bootstrap_100.csv", index=False)
    """),
    md("""
    ## 15. Fail-closed promotion gates

    Gates are fixed before inspecting test results. No gate is weakened or
    removed to force promotion. A failed model remains a research candidate.
    """),
    code(r"""
    gates = [
        ("dataset_hash_recorded", bool(DATA_SHA256)),
        ("no_duplicate_station_timestamps", audit["duplicates"] == 0),
        ("chronological_split", df.loc[df.split.eq("model_fit"), "timestamp_utc"].max() < df.loc[df.split.eq("calibration"), "timestamp_utc"].min()),
        ("station_holdout_isolation", not set(df.loc[df.split.eq("model_fit"), "station_id"]) & set(df.loc[df.split.eq("test_spatial"), "station_id"])),
        ("pressure_sources_recognized", not unknown_pressure_sources),
        ("pressure_normalized_to_native_slp_only", bool((df.loc[df.pressure_hpa.notna(), "pressure_source"] == "slp").all())),
        ("pressure_slp_coverage_sufficient", audit["eligible_slp_rows"] >= 100000 and audit["eligible_slp_stations"] >= 15),
        ("development_policy_feasible", bool(policy_search.feasible.any())),
        ("synthetic_calibration_ece", synthetic_ece <= MAX_SYNTHETIC_ECE),
        ("temporal_alert_budget", temporal_metrics["clean_alerts_per_station_day"] <= FALSE_ALERT_LIMIT),
        ("spatial_alert_budget", spatial_metrics["clean_alerts_per_station_day"] <= FALSE_ALERT_LIMIT),
        ("temporal_injected_precision", temporal_metrics["event_precision"] >= MIN_INJECTED_EVENT_PRECISION),
        ("spatial_injected_precision", spatial_metrics["event_precision"] >= MIN_INJECTED_EVENT_PRECISION),
        ("temporal_injected_recall", temporal_metrics["event_recall"] >= MIN_INJECTED_EVENT_RECALL),
        ("spatial_injected_recall", spatial_metrics["event_recall"] >= MIN_INJECTED_EVENT_RECALL),
        ("temporal_delay", temporal_metrics["median_delay_min"] <= MAX_MEDIAN_DELAY_MIN),
        ("spatial_delay", spatial_metrics["median_delay_min"] <= MAX_MEDIAN_DELAY_MIN),
        ("bootstrap_complete", len(boot_temporal) == BOOTSTRAP_REPEATS and len(boot_spatial) == BOOTSTRAP_REPEATS),
    ]
    gate_table = pd.DataFrame(gates, columns=["gate", "passed"])
    PROMOTED = bool(gate_table.passed.all())
    display(gate_table)
    print("PROMOTION STATUS:", "PROMOTED" if PROMOTED else "RESEARCH_CANDIDATE_NOT_PROMOTED")
    gate_table.to_csv(REPORT_DIR / "promotion_gates.csv", index=False)
    """),
    md("""
    ## 16. Artifact packaging and deployment contract

    Candidate artifacts are always retained for audit. The `promoted/` bundle is
    written only after every gate passes. The website must still label its
    output as an uncalibrated/benchmark score until real field-fault calibration
    evidence exists.
    """),
    code(r"""
    def json_safe(value):
        if isinstance(value, dict): return {str(k): json_safe(v) for k,v in value.items()}
        if isinstance(value, (list, tuple)): return [json_safe(v) for v in value]
        if isinstance(value, (np.integer,)): return int(value)
        if isinstance(value, (np.floating,)): return None if not np.isfinite(value) else float(value)
        if isinstance(value, pd.Timestamp): return value.isoformat()
        return value

    manifest = {
        "model_name": "skyguard_historical_proxy_v2",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "promotion_status": "PROMOTED" if PROMOTED else "RESEARCH_CANDIDATE_NOT_PROMOTED",
        "dataset": {
            "provider": "NOAA/NCEI Global Hourly Indian surface-station historical proxy",
            "direct_imd_aws_api": False, "station_count": int(df.station_id.nunique()),
            "sha256": DATA_SHA256, "pressure_type": "mean_sea_level_pressure",
            "pressure_normalization": {
                "model_input": "native NOAA SLP rows only",
                "raw_sources_preserved": audit["raw_pressure_sources"],
                "eligible_rows": audit["eligible_slp_rows"],
                "eligible_stations": audit["eligible_slp_stations"],
                "ma1_altimeter_policy": "retained for audit; excluded from pressure_hpa model feature"
            }
        },
        "label_scope": "controlled injected benchmark; no public maintenance-confirmed field-fault labels",
        "feature_order": FEATURES, "sequence_features": SEQ_FEATURES,
        "policy": FROZEN_POLICY, "model_seeds": MODEL_SEEDS,
        "thresholds": {
            "false_alerts_per_station_day": FALSE_ALERT_LIMIT,
            "minimum_injected_event_precision": MIN_INJECTED_EVENT_PRECISION,
            "minimum_injected_event_recall": MIN_INJECTED_EVENT_RECALL,
            "maximum_median_delay_minutes": MAX_MEDIAN_DELAY_MIN,
            "maximum_synthetic_ece": MAX_SYNTHETIC_ECE,
        },
        "frozen_test_results": frozen_results.to_dict("records"),
        "gates": gate_table.to_dict("records"),
        "public_probability_allowed": False,
        "required_live_input": ["temperature_c", "pressure_hpa", "relative_humidity_pct", "pressure_type",
                                "station_id", "timestamp_utc", "latitude", "longitude"],
    }

    joblib.dump({"models": models, "calibrator": calibrator, "medians": medians,
                 "features": FEATURES}, CANDIDATE_DIR / "tree_ensemble.joblib")
    joblib.dump(scaler, CANDIDATE_DIR / "sequence_scaler.joblib")
    torch.save({"state_dict": {k:v.detach().cpu() for k,v in tcn.state_dict().items()},
                "sequence_features": SEQ_FEATURES, "sequence_length": SEQ_LEN},
               CANDIDATE_DIR / "causal_tcn.pt")
    (CANDIDATE_DIR / "manifest.json").write_text(json.dumps(json_safe(manifest), indent=2), encoding="utf-8")

    if PROMOTED:
        if PROMOTED_DIR.exists(): shutil.rmtree(PROMOTED_DIR)
        shutil.copytree(CANDIDATE_DIR, PROMOTED_DIR)
        print("Promoted deployment bundle:", PROMOTED_DIR)
    else:
        print("No promoted bundle written. Failed gates must be resolved with new evidence/model changes.")
    """),
    md("""
    ## 17. Round-trip verification and final report

    Reload every serialized component and compare scores before any backend
    integration. Deployment is a separate reviewed change; this notebook never
    pushes directly to Render or `main`.
    """),
    code(r"""
    reloaded = joblib.load(CANDIDATE_DIR / "tree_ensemble.joblib")
    sample = temporal_clean_scored.head(256)
    sample_x = sample[FEATURES].replace([np.inf, -np.inf], np.nan).fillna(reloaded["medians"])
    before = np.mean([m.predict_proba(sample_x)[:,1] for m in models], axis=0)
    after = np.mean([m.predict_proba(sample_x)[:,1] for m in reloaded["models"]], axis=0)
    np.testing.assert_allclose(before, after, rtol=1e-10, atol=1e-12)

    final_report = {
        "status": manifest["promotion_status"], "dataset_sha256": DATA_SHA256,
        "rows": int(len(df)), "stations": int(df.station_id.nunique()),
        "policy_trials": POLICY_TRIALS, "bootstrap_repeats_per_test": BOOTSTRAP_REPEATS,
        "frozen_policy": FROZEN_POLICY,
        "temporal_test": temporal_metrics, "spatial_test": spatial_metrics,
        "failed_gates": gate_table.loc[~gate_table.passed, "gate"].tolist(),
        "artifact_roundtrip": "PASS",
        "deployment_warning": "Do not deploy unless status is PROMOTED; do not display benchmark scores as real fault probabilities."
    }
    (REPORT_DIR / "final_result_block.json").write_text(json.dumps(json_safe(final_report), indent=2), encoding="utf-8")
    print(json.dumps(json_safe(final_report), indent=2))
    """),
    md("""
    ## Interpretation

    A `PROMOTED` result means this candidate met the predefined operational
    proxy gates on the available 24-station NOAA/NCEI archive and controlled
    fault curriculum. It does **not** establish performance for the 1,153-station
    IMD AWS network. Before live deployment, verify the IMD API schema, units,
    pressure semantics, cadence, missing codes and station identifiers, then
    run domain-shift monitoring. Thirty or more days of genuine IMD history is
    a reasonable first pilot window, not proof of field-fault accuracy.
    """),
]


notebook = {
    "cells": cells,
    "metadata": {
        "accelerator": "GPU",
        "colab": {"name": OUTPUT.name, "provenance": []},
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

OUTPUT.write_text(json.dumps(notebook, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"Wrote {OUTPUT} ({len(cells)} cells)")
