"""Fair Ridge baseline FAST version: only fold 0, 200 train days, with progress prints.

Apples-to-apples vs V5 singh fold 0 (P=+0.058 S=+0.072) using same input dimensions
that V5 sees: X[t=-1] (64) + X_raw[t=-1].flatten() (100) = 164 features.
"""
from __future__ import annotations
import os, pathlib, sys, json, time
import numpy as np
from scipy.stats import pearsonr, spearmanr
from sklearn.linear_model import Ridge

NPZ_DIR = pathlib.Path("data/npz_v4")
TRAIN_DAYS = 200  # subset (vs V5's 700) for speed
N_LEVELS = 25


def load_features(days, include_raw=True, label="?"):
    Xs, ys, ms, tss = [], [], [], []
    t0 = time.time()
    for i, day in enumerate(days):
        path = NPZ_DIR / f"{day}.npz"
        if not path.exists():
            continue
        try:
            d = np.load(path, allow_pickle=True)
            X = d["X"]; y = d["y_600"]; m = d["y_mask_600"]
            ts = d["timestamps"] if "timestamps" in d.files else np.zeros(len(y), dtype=np.int64)
            X_last = X[:, -1, :].astype(np.float32)  # (N, 64)
            if include_raw:
                X_raw = d["X_raw"]
                L = X_raw.shape[2]
                if L >= N_LEVELS:
                    X_raw_use = X_raw[:, -1, :N_LEVELS, :].astype(np.float32)
                else:
                    pad = np.zeros((X_raw.shape[0], N_LEVELS - L, 4), dtype=np.float32)
                    X_raw_use = np.concatenate([X_raw[:, -1, :, :].astype(np.float32), pad], axis=1)
                X_combined = np.concatenate([X_last, X_raw_use.reshape(X_last.shape[0], -1)], axis=1)
            else:
                X_combined = X_last
            Xs.append(X_combined); ys.append(y); ms.append(m); tss.append(ts)
        except Exception as e:
            print(f"  skip {day}: {e}", flush=True)
            continue
        if (i + 1) % 50 == 0:
            print(f"  [{label}] loaded {i+1}/{len(days)} days, {time.time()-t0:.1f}s", flush=True)
    return (
        np.concatenate(Xs).astype(np.float32),
        np.concatenate(ys).astype(np.float32),
        np.concatenate(ms).astype(np.float32),
        np.concatenate(tss).astype(np.int64),
    )


def main():
    all_days = sorted(p.stem for p in NPZ_DIR.glob("20??-??-??.npz"))
    test_start_idx = all_days.index("2025-02-09")
    test = all_days[test_start_idx:test_start_idx + 90]
    val_end_idx = test_start_idx - 1
    val_start_idx = val_end_idx - 60
    val = all_days[val_start_idx:val_end_idx]
    train_end_idx = val_start_idx - 1
    train_start_idx = max(0, train_end_idx - TRAIN_DAYS)
    train = all_days[train_start_idx:train_end_idx]
    print(f"Fold 0 splits:")
    print(f"  train ({len(train)}d): {train[0]}..{train[-1]}")
    print(f"  val   ({len(val)}d): {val[0]}..{val[-1]}")
    print(f"  test  ({len(test)}d): {test[0]}..{test[-1]}", flush=True)

    out_path = pathlib.Path("experiments/baselines_fair_ridge_y600/fold0_results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    results = {}

    for variant_name, include_raw in [("Ridge_X_only_64dim", False), ("Ridge_X_LOB_164dim", True)]:
        print(f"\n=== {variant_name} (include_raw={include_raw}) ===", flush=True)
        t0 = time.time()
        X_train, y_train, m_train, _ = load_features(train, include_raw=include_raw, label=f"{variant_name}-train")
        print(f"  train load done, {time.time()-t0:.1f}s, X shape {X_train.shape}", flush=True)

        # Normalize y
        valid = m_train.astype(bool)
        y_med = float(np.median(y_train[valid]))
        y_sigma = float(np.median(np.abs(y_train[valid] - y_med)) * 1.4826)
        y_sigma = max(y_sigma, 1e-9)
        y_train_z = np.clip((y_train - y_med) / y_sigma, -10, 10).astype(np.float32)

        X_train_use = X_train[valid]
        y_train_use = y_train_z[valid]
        # Standardize features
        x_mean = X_train_use.mean(axis=0)
        x_std = X_train_use.std(axis=0)
        x_std = np.where(x_std < 1e-9, 1.0, x_std)
        X_train_norm = ((X_train_use - x_mean) / x_std).astype(np.float32)

        print(f"  fitting Ridge α=1.0 on n={len(X_train_use)} F={X_train.shape[1]}...", flush=True)
        t1 = time.time()
        ridge = Ridge(alpha=1.0)
        ridge.fit(X_train_norm, y_train_use)
        print(f"  fit done in {time.time()-t1:.1f}s", flush=True)

        # Test
        t2 = time.time()
        X_test, y_test, m_test, _ = load_features(test, include_raw=include_raw, label=f"{variant_name}-test")
        print(f"  test load done, {time.time()-t2:.1f}s", flush=True)
        test_valid = m_test.astype(bool)
        X_test_norm = ((X_test - x_mean) / x_std).astype(np.float32)
        q_z = ridge.predict(X_test_norm)
        q_bps = (q_z * y_sigma + y_med) * 1e4
        y_bps = y_test * 1e4
        qm, ym = q_bps[test_valid], y_bps[test_valid]
        p = float(pearsonr(qm, ym)[0])
        s = float(spearmanr(qm, ym).correlation)
        sq, sy = qm.std(), ym.std()
        beta = float(np.cov(qm, ym)[0, 1] / max(sq**2, 1e-12))
        bias = float(qm.mean() - ym.mean())
        print(f"  TEST FOLD 0: P={p:+.4f} S={s:+.4f} β={beta:+.3f} σŷ/σy={sq/sy:.3f} bias={bias:+.3f}bps n={len(qm)}", flush=True)
        results[variant_name] = {"P": p, "S": s, "beta": beta, "sigma_ratio": float(sq/sy), "bias_bps": bias, "n": int(len(qm))}

    # Compare
    print(f"\n=== Fold 0 comparison ===", flush=True)
    if "Ridge_X_only_64dim" in results and "Ridge_X_LOB_164dim" in results:
        r64 = results["Ridge_X_only_64dim"]
        r164 = results["Ridge_X_LOB_164dim"]
        print(f"  Ridge_X_only_64dim:    P={r64['P']:+.4f} S={r64['S']:+.4f}")
        print(f"  Ridge_X_LOB_164dim:    P={r164['P']:+.4f} S={r164['S']:+.4f}")
        print(f"  ΔP from adding LOB:    {r164['P']-r64['P']:+.4f} ({(r164['P']-r64['P'])/abs(r64['P'])*100 if r64['P'] != 0 else 0:.0f}%)")
        print(f"  ΔS from adding LOB:    {r164['S']-r64['S']:+.4f}")
    print(f"  V5 singh fold 0 BEST:  P=+0.0583 S=+0.0723", flush=True)

    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=float)
    print(f"\n→ {out_path}")


if __name__ == "__main__":
    main()
