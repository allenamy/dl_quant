"""3-seed ensemble: V5 prod (s42) + Track A (s42 DAQH+TV) + Track A2 (s7 DAQH+TV).

Live-calibrated value-blend at fold level.
Sweeps weights to find best (P+S)/2 maximizer.

Outputs production CSV in same format as V5 prod live CSV.
"""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import itertools
import numpy as np
import pathlib
from scipy.stats import pearsonr, spearmanr

EMA_ALPHA = 0.01
WARMUP = 50


def demean(q):
    n = len(q); ema = np.zeros(n); cur = 0.0
    for i in range(n):
        if i > 0:
            cur = EMA_ALPHA * q[i - 1] + (1 - EMA_ALPHA) * cur
        ema[i] = cur
    out = q.copy()
    out -= ema
    out[:WARMUP] = 0.0
    return out, ema


def load_fold(npz_path):
    z = np.load(npz_path, allow_pickle=True)
    pred = z["predictions"]; y = z["targets"].reshape(-1); m = z["mask"].reshape(-1).astype(bool); ts = z["timestamps"]
    sy = float(z["y_sigma"]); ymed = float(z["y_median"])
    q10 = pred[:, 0] * sy + ymed
    q50 = pred[:, 1] * sy + ymed
    q90 = pred[:, 2] * sy + ymed
    order = np.argsort(ts)
    return {
        "ts": ts[order], "q10": q10[order], "q50": q50[order], "q90": q90[order],
        "y": (y * sy + ymed)[order], "mask": m[order],
        "y_sigma": sy, "y_median": ymed,
    }


def load_3fold_live(dir_pattern):
    folds = []
    for f in range(3):
        # Try several layouts
        candidates = [
            pathlib.Path(dir_pattern.format(f)),
            pathlib.Path(dir_pattern.format(f)) / "test_preds.npz",
        ]
        path = next((p for p in candidates if p.exists()), None)
        if path is None:
            raise FileNotFoundError(f"fold {f}: tried {candidates}")
        d = load_fold(path)
        q50_bps = d["q50"] * 1e4
        q50_live, ema = demean(q50_bps)
        folds.append({
            "ts": d["ts"], "q50_live": q50_live, "ema": ema, "q50_raw_bps": q50_bps,
            "q10": d["q10"], "q90": d["q90"],
            "y_bps": d["y"] * 1e4, "y_logret": d["y"],
            "mask": d["mask"], "y_sigma_bps": d["y_sigma"] * 1e4,
        })
    return folds


def eval_pool(q, y, mask, warmup_mask=None):
    """Eval pooled IC where mask=1, warmup_mask handles per-fold warmup."""
    if warmup_mask is None:
        v = mask
    else:
        v = mask & warmup_mask
    q = q[v]; y = y[v]
    P = pearsonr(q, y)[0]; S = spearmanr(q, y).correlation
    sq, sy = q.std(), y.std()
    beta = np.cov(q, y)[0, 1] / max(sq ** 2, 1e-12)
    da = float(np.mean(np.sign(q) == np.sign(y)))
    hy = np.abs(y) > sy
    da_hy = float(np.mean(np.sign(q[hy]) == np.sign(y[hy])))
    abs_thr = np.percentile(np.abs(q), 90)
    top_mask = np.abs(q) >= abs_thr
    top_spread = float((np.sign(q[top_mask]) * y[top_mask]).mean())
    return {"P": P, "S": S, "beta": beta, "sigma_r": sq/sy, "DA": da, "DA_hy": da_hy, "topspread": top_spread, "n": int(len(q))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v5-prod-dir", default="experiments/v5_final/singleh_alpha0_huber")
    ap.add_argument("--track-a-dir", default="/tmp/track_a_preds")
    ap.add_argument("--track-a2-dir", default="experiments/v5push/singh_daqh_tv_seed7")
    ap.add_argument("--out-csv", required=True)
    ap.add_argument("--remote-track-a2", action="store_true",
                    help="If true, fetch track-a2 from remote via scp before eval")
    args = ap.parse_args()

    if args.remote_track_a2:
        import subprocess
        local_dir = pathlib.Path("/tmp/track_a2_preds")
        local_dir.mkdir(exist_ok=True)
        for f in range(3):
            subprocess.run([
                "scp", "-P", "31999", "-o", "StrictHostKeyChecking=no",
                f"root@212.50.244.62:/mnt/storage/private/work_hsy/quant_research/experiments/v5push/singh_daqh_tv_seed7/fold_{f}/test_preds.npz",
                str(local_dir / f"fold_{f}.npz"),
            ], check=True, capture_output=True)
        track_a2_dir = "/tmp/track_a2_preds/fold_{}.npz"
    else:
        track_a2_dir = args.track_a2_dir + "/fold_{}"

    # Load all 3 model sets
    print("Loading V5 prod...")
    v5_folds = load_3fold_live(args.v5_prod_dir + "/fold_{}")
    print("Loading Track A...")
    a_folds = load_3fold_live(args.track_a_dir + "/fold_{}.npz")
    print("Loading Track A2...")
    a2_folds = load_3fold_live(track_a2_dir)

    # Pool predictions, aligned by fold
    pool_q5 = []  # V5 prod
    pool_qa = []  # Track A
    pool_qa2 = []  # Track A2
    pool_y = []
    pool_mask = []
    pool_warmup = []
    pool_fold = []
    pool_ts = []
    pool_q10s = {"v5":[], "a":[], "a2":[]}
    pool_q90s = {"v5":[], "a":[], "a2":[]}
    pool_ema = {"v5":[], "a":[], "a2":[]}

    for f in range(3):
        v = v5_folds[f]; a = a_folds[f]; a2 = a2_folds[f]
        # Assert alignment
        assert len(v["ts"]) == len(a["ts"]) == len(a2["ts"]), f"fold {f} length mismatch"
        assert np.array_equal(v["ts"], a["ts"]) and np.array_equal(v["ts"], a2["ts"]), f"fold {f} ts mismatch"
        n = len(v["ts"])
        pool_q5.append(v["q50_live"]); pool_qa.append(a["q50_live"]); pool_qa2.append(a2["q50_live"])
        pool_y.append(v["y_bps"]); pool_mask.append(v["mask"])
        pool_warmup.append(np.arange(n) < WARMUP)
        pool_fold.append(np.full(n, f, dtype=np.int8))
        pool_ts.append(v["ts"])
        for k, src in [("v5", v), ("a", a), ("a2", a2)]:
            pool_q10s[k].append(src["q10"]); pool_q90s[k].append(src["q90"]); pool_ema[k].append(src["ema"])

    Q5 = np.concatenate(pool_q5); QA = np.concatenate(pool_qa); QA2 = np.concatenate(pool_qa2)
    Y = np.concatenate(pool_y); MASK = np.concatenate(pool_mask)
    WARMUP_MASK = ~np.concatenate(pool_warmup)
    eligible = MASK & WARMUP_MASK
    print(f"\nTotal eligible: {eligible.sum():,}")

    # Single model eval
    print("\n=== Single-model pooled (live-cal) ===")
    for label, Q in [("V5 prod", Q5), ("Track A (s42)", QA), ("Track A2 (s7)", QA2)]:
        m = eval_pool(Q, Y, eligible)
        print(f"  {label:18s}: P={m['P']:+.4f} S={m['S']:+.4f} β={m['beta']:+.3f} σŷ/σy={m['sigma_r']:.3f} DA={m['DA']:.4f} DA_|y|>σ={m['DA_hy']:.4f} top={m['topspread']:+.3f}")

    # Pred-pred correlations
    Qv = Q5[eligible]; Qa = QA[eligible]; Qa2 = QA2[eligible]
    print(f"\ncorr(V5,A)={pearsonr(Qv,Qa)[0]:.3f}, corr(V5,A2)={pearsonr(Qv,Qa2)[0]:.3f}, corr(A,A2)={pearsonr(Qa,Qa2)[0]:.3f}")

    # Sweep weights
    print("\n=== 3-seed ensemble weight sweep ===")
    best = None
    for w5 in np.arange(0.2, 0.81, 0.1):
        for wa in np.arange(0.1, 0.81 - w5 + 1e-9, 0.1):
            wa2 = 1 - w5 - wa
            if wa2 < 0.05 or wa2 > 0.7:
                continue
            QE = w5*Q5 + wa*QA + wa2*QA2
            m = eval_pool(QE, Y, eligible)
            score = 0.5*m["P"] + 0.5*m["S"]
            if best is None or score > best[0]:
                best = (score, w5, wa, wa2, m)
    print(f"  Best: w_V5={best[1]:.2f} w_A={best[2]:.2f} w_A2={best[3]:.2f}")
    print(f"   P={best[4]['P']:+.4f} S={best[4]['S']:+.4f} β={best[4]['beta']:+.3f} σŷ/σy={best[4]['sigma_r']:.3f}")
    print(f"   DA={best[4]['DA']:.4f} DA_|y|>σ={best[4]['DA_hy']:.4f} TopSpread={best[4]['topspread']:+.3f}bps")

    # 2-seed reference (V5 + Track A at w=0.4 from prior)
    QE_2seed = 0.6 * Q5 + 0.4 * QA
    m2 = eval_pool(QE_2seed, Y, eligible)
    print(f"  2-seed (V5 60%, A 40%): P={m2['P']:+.4f} S={m2['S']:+.4f} DA={m2['DA']:.4f}")

    # Write production CSV using best weights
    w5, wa, wa2 = best[1], best[2], best[3]
    print(f"\nWriting CSV with weights V5={w5:.2f}, A={wa:.2f}, A2={wa2:.2f}...")
    rows = []
    for f in range(3):
        v = v5_folds[f]; a = a_folds[f]; a2 = a2_folds[f]
        n = len(v["ts"])
        for i in range(n):
            ts_us = int(v["ts"][i])
            dts = dt.datetime.fromtimestamp(ts_us / 1e6, tz=dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            warm = i < WARMUP
            q50_logret = w5 * v["q50"][i] + wa * a["q50"][i] + wa2 * a2["q50"][i]
            q10_logret = w5 * v["q10"][i] + wa * a["q10"][i] + wa2 * a2["q10"][i]
            q90_logret = w5 * v["q90"][i] + wa * a["q90"][i] + wa2 * a2["q90"][i]
            q50_live = w5 * v["q50_live"][i] + wa * a["q50_live"][i] + wa2 * a2["q50_live"][i]
            ema_state = w5 * v["ema"][i] + wa * a["ema"][i] + wa2 * a2["ema"][i]
            rows.append({
                "timestamp_us": ts_us, "datetime_utc": dts,
                "fold": f, "horizon_sec": 600,
                "mask": int(v["mask"][i]),
                "y_true_logret": float(v["y_logret"][i]),
                "y_true_bps": float(v["y_bps"][i]),
                "y_pred_q10_logret": float(q10_logret),
                "y_pred_q50_logret": float(q50_logret),
                "y_pred_q90_logret": float(q90_logret),
                "y_pred_q50_bps": float(q50_logret * 1e4),
                "y_pred_q50_bps_live": 0.0 if warm else float(q50_live),
                "y_pred_q50_bps_live_ema_state": float(ema_state),
                "y_sigma_train_bps": v["y_sigma_bps"],
                "warmup": warm,
                "ensemble_w_v5prod": w5,
                "ensemble_w_track_a": wa,
                "ensemble_w_track_a2": wa2,
            })

    out_path = pathlib.Path(args.out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"Wrote {len(rows):,} rows to {out_path}")


if __name__ == "__main__":
    main()
