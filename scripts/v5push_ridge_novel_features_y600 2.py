"""V5-push Phase 1A: Ridge walk-forward gate for novel book-derived features.

Baseline: V5's 64 hand-crafted features (X[:, -1, :]).
Candidate: baseline + ~15 novel book-derived features computed from X_raw[:, :, :, :].

Novel features (book-only, computable from X_raw alone; trade-derived deferred):
  queue_depletion: inside (L0) size vs 60s rolling median, EWMA 60s/300s
  entropy_skew: Shannon entropy of 10-level depth, bid vs ask gap + EWMA
  energy_skew: distance-weighted depth E_bid - E_ask
  temp_imb: (RV / depth) imbalance
  dva_L5, dva_L10: bid_var - ask_var over 60s
  mom_overextended_60s: |mom_60s| > 2 sigma_1h
  low_liq_state: spread_bps > 2 * spread_med_1h (need spread reconstruction from L0 deltas)

Gate (per anti-pattern feedback): Δ pool Pearson ≥ +0.005 AND ≥ 2 of 3 folds positive Δ.

Runs 3-fold walk-forward matching V5 singh splits.
"""
from __future__ import annotations
import argparse
import json
import math
import pathlib
import time
from typing import List, Tuple

import numpy as np
from scipy.stats import pearsonr, spearmanr
from sklearn.linear_model import Ridge

NPZ_DIR = pathlib.Path("data/npz_v4")
N_LEVELS = 25
EPS = 1e-12


# -------- novel-feature computation from X_raw (N, T, L, 4) --------
# X_raw channels: [0]=bid_delta_bps, [1]=bid_log_amt, [2]=ask_delta_bps, [3]=ask_log_amt

def compute_novel_features(X_raw: np.ndarray) -> Tuple[np.ndarray, List[str]]:
    """X_raw: (N, T=600, L_raw, 4). Returns (N, F_novel), feat_names."""
    N, T, Lraw, _ = X_raw.shape
    L = min(Lraw, N_LEVELS)
    bid_amt = X_raw[:, :, :L, 1].astype(np.float64)  # log_amt
    ask_amt = X_raw[:, :, :L, 3].astype(np.float64)
    bid_dbps = X_raw[:, :, :L, 0].astype(np.float64)
    ask_dbps = X_raw[:, :, :L, 2].astype(np.float64)

    novel = []
    names = []

    # --- queue_depletion: inside (L0) bid/ask exp(log_amt) size vs 60s rolling median ratio ---
    # ratio_bid[t] = bid_size[t] / median(bid_size[t-60:t])
    bid_size_inside = np.exp(bid_amt[:, :, 0]) - 1.0  # (N, T) un-logamt back to size
    ask_size_inside = np.exp(ask_amt[:, :, 0]) - 1.0
    # 60s rolling median at last step
    win = 60
    last_60_bid = bid_size_inside[:, -win:]
    last_60_ask = ask_size_inside[:, -win:]
    bid_size_t = bid_size_inside[:, -1]
    ask_size_t = ask_size_inside[:, -1]
    med_bid_60 = np.median(last_60_bid, axis=1) + EPS
    med_ask_60 = np.median(last_60_ask, axis=1) + EPS
    qd_bid_ratio = bid_size_t / med_bid_60  # <1 means thin → SELL pressure
    qd_ask_ratio = ask_size_t / med_ask_60  # <1 means thin → BUY pressure
    qd_imb = (qd_ask_ratio - qd_bid_ratio) / (qd_ask_ratio + qd_bid_ratio + EPS)
    qd_severity_buy = np.clip(1.0 - qd_ask_ratio, 0.0, 1.0)
    qd_severity_sell = np.clip(1.0 - qd_bid_ratio, 0.0, 1.0)
    qd_severity_net = qd_severity_buy - qd_severity_sell
    novel.append(qd_bid_ratio); names.append("qd_bid_ratio_60s")
    novel.append(qd_ask_ratio); names.append("qd_ask_ratio_60s")
    novel.append(qd_imb); names.append("qd_imb_60s")
    novel.append(qd_severity_net); names.append("qd_severity_net_60s")

    # --- entropy_skew: Shannon entropy of 10-level depth distribution ---
    L10 = min(L, 10)
    bid_q10 = np.exp(bid_amt[:, -1, :L10]) - 1.0  # (N, L10) at last timestep
    ask_q10 = np.exp(ask_amt[:, -1, :L10]) - 1.0
    bid_q10 = np.clip(bid_q10, 0.0, None)
    ask_q10 = np.clip(ask_q10, 0.0, None)
    def normalized_entropy(Q):
        s = Q.sum(axis=1, keepdims=True) + EPS
        p = np.clip(Q / s, EPS, 1.0)
        H = -(p * np.log(p)).sum(axis=1)
        Hn = H / math.log(L10)
        return np.clip(Hn, 0.0, 1.0)
    ent_bid = normalized_entropy(bid_q10)
    ent_ask = normalized_entropy(ask_q10)
    ent_gap = ent_ask - ent_bid
    ent_both = 0.5 * (ent_bid + ent_ask)
    novel.append(ent_bid); names.append("ent_bid_10L")
    novel.append(ent_ask); names.append("ent_ask_10L")
    novel.append(ent_gap); names.append("ent_gap_10L")
    novel.append(ent_both); names.append("ent_both_10L")

    # --- energy_skew: distance-weighted depth (in bps from mid) ---
    decay_bps = 10.0
    w_bid = np.exp(-np.abs(bid_dbps[:, -1, :]) / decay_bps)
    w_ask = np.exp(-np.abs(ask_dbps[:, -1, :]) / decay_bps)
    bid_q = np.exp(bid_amt[:, -1, :]) - 1.0
    ask_q = np.exp(ask_amt[:, -1, :]) - 1.0
    E_bid = (bid_q * w_bid).sum(axis=1)
    E_ask = (ask_q * w_ask).sum(axis=1)
    V_bid = bid_q.sum(axis=1) + EPS
    V_ask = ask_q.sum(axis=1) + EPS
    E_bar_bid = E_bid / V_bid
    E_bar_ask = E_ask / V_ask
    energy_skew = E_bar_ask - E_bar_bid
    novel.append(energy_skew); names.append("energy_skew")

    # delta_energy_skew (over 30s): need step t-30 vs t
    if T >= 31:
        w_bid_p = np.exp(-np.abs(bid_dbps[:, -31, :]) / decay_bps)
        w_ask_p = np.exp(-np.abs(ask_dbps[:, -31, :]) / decay_bps)
        bid_q_p = np.exp(bid_amt[:, -31, :]) - 1.0
        ask_q_p = np.exp(ask_amt[:, -31, :]) - 1.0
        E_bar_bid_p = (bid_q_p * w_bid_p).sum(axis=1) / (bid_q_p.sum(axis=1) + EPS)
        E_bar_ask_p = (ask_q_p * w_ask_p).sum(axis=1) / (ask_q_p.sum(axis=1) + EPS)
        d_energy_skew = (E_bar_ask - E_bar_bid) - (E_bar_ask_p - E_bar_bid_p)
        novel.append(d_energy_skew); names.append("delta_energy_skew_30s")

    # --- DVA: bid var - ask var over 60s on inside-5 levels ---
    for K in (5, 10):
        Kuse = min(L, K)
        bid_q_60 = np.exp(bid_amt[:, -win:, :Kuse]) - 1.0  # (N, 60, K)
        ask_q_60 = np.exp(ask_amt[:, -win:, :Kuse]) - 1.0
        bid_var = bid_q_60.var(axis=1).sum(axis=1)  # sum var across levels
        ask_var = ask_q_60.var(axis=1).sum(axis=1)
        dva = (bid_var - ask_var) / (bid_var + ask_var + EPS)
        novel.append(dva); names.append(f"dva_L{K}_60s")

    # NOTE: spread/momentum features dropped — X_raw L0 is microprice-tight (spread ≈ 0.001 bps
    # not real) and per-step mid normalization makes mid_delta degenerate. V5's X already has
    # spread_bps, log_returns, realized_vol, microprice_dev — no need to reconstruct.

    # --- Trend in ent_gap over 60s (rate of regime change in book asymmetry) ---
    # bid_amt / ask_amt shape (N, T, L10), recompute ent at t-60 vs t for delta
    if T >= 61:
        bid_q10_p = np.exp(bid_amt[:, -61, :L10]) - 1.0
        ask_q10_p = np.exp(ask_amt[:, -61, :L10]) - 1.0
        bid_q10_p = np.clip(bid_q10_p, 0.0, None)
        ask_q10_p = np.clip(ask_q10_p, 0.0, None)
        ent_bid_p = normalized_entropy(bid_q10_p)
        ent_ask_p = normalized_entropy(ask_q10_p)
        ent_gap_p = ent_ask_p - ent_bid_p
        d_ent_gap = (ent_ask - ent_bid) - ent_gap_p
        novel.append(d_ent_gap); names.append("delta_ent_gap_60s")

    # --- Cross-level concentration vs L0 ratio ---
    # bid_q[:, -1, 0] / bid_q[:, -1, :5].sum()  — how much inside dominates
    bid_total_5 = bid_q10[:, :5].sum(axis=1) + EPS
    ask_total_5 = ask_q10[:, :5].sum(axis=1) + EPS
    bid_L0_frac = bid_q10[:, 0] / bid_total_5
    ask_L0_frac = ask_q10[:, 0] / ask_total_5
    L0_frac_gap = ask_L0_frac - bid_L0_frac
    novel.append(bid_L0_frac); names.append("bid_L0_frac_L5")
    novel.append(ask_L0_frac); names.append("ask_L0_frac_L5")
    novel.append(L0_frac_gap); names.append("L0_frac_gap")

    out = np.stack(novel, axis=1).astype(np.float32)  # (N, F_novel)
    return out, names


# -------- fold setup matching V5 singh production --------
def get_v5_folds(npz_dir: pathlib.Path,
                 test_starts=("2025-02-09", "2025-04-10", "2025-06-11"),
                 train_days_n=700, val_days_n=60, test_days_n=90, embargo=1) -> List[dict]:
    all_days = sorted(p.stem for p in npz_dir.glob("20??-??-??.npz"))
    folds = []
    for ts_str in test_starts:
        if ts_str not in all_days:
            raise RuntimeError(f"test start {ts_str} not in NPZ dir")
        ts_idx = all_days.index(ts_str)
        test = all_days[ts_idx:ts_idx + test_days_n]
        val_end = ts_idx - embargo
        val_start = val_end - val_days_n
        val = all_days[val_start:val_end]
        train_end = val_start - embargo
        train_start = max(0, train_end - train_days_n)
        train = all_days[train_start:train_end]
        folds.append({"train": train, "val": val, "test": test, "ts": ts_str})
    return folds


def load_fold(days, include_novel=True, label="?"):
    Xs, Xs_novel, ys, ms, novel_names_local = [], [], [], [], None
    t0 = time.time()
    for i, day in enumerate(days):
        p = NPZ_DIR / f"{day}.npz"
        if not p.exists():
            continue
        z = np.load(p, allow_pickle=True)
        X = z["X"]
        y = z["y_600"]
        m = z["y_mask_600"]
        # last-timestep 64 features
        X_last = X[:, -1, :].astype(np.float32)
        Xs.append(X_last)
        ys.append(y)
        ms.append(m)
        if include_novel:
            Xr = z["X_raw"]
            xn, names = compute_novel_features(Xr)
            Xs_novel.append(xn)
            if novel_names_local is None:
                novel_names_local = names
        if (i + 1) % 100 == 0:
            print(f"  [{label}] {i+1}/{len(days)} days loaded ({time.time()-t0:.0f}s)", flush=True)
    X_arr = np.concatenate(Xs).astype(np.float32)
    y_arr = np.concatenate(ys).astype(np.float32)
    m_arr = np.concatenate(ms).astype(np.float32)
    X_novel = np.concatenate(Xs_novel).astype(np.float32) if include_novel else None
    return X_arr, X_novel, y_arr, m_arr, novel_names_local


def fit_eval_ridge(X_train, y_train_z, X_test, y_test, m_test,
                    y_med, y_sigma, alpha=1.0):
    x_mean = X_train.mean(axis=0)
    x_std = X_train.std(axis=0)
    x_std = np.where(x_std < 1e-9, 1.0, x_std)
    Xtn = ((X_train - x_mean) / x_std).astype(np.float32)
    Xen = ((X_test - x_mean) / x_std).astype(np.float32)
    ridge = Ridge(alpha=alpha)
    ridge.fit(Xtn, y_train_z)
    q_z = ridge.predict(Xen)
    q_bps = (q_z * y_sigma + y_med) * 1e4
    y_bps = y_test * 1e4
    v = m_test.astype(bool)
    qm, ym = q_bps[v], y_bps[v]
    P = float(pearsonr(qm, ym)[0])
    S = float(spearmanr(qm, ym).correlation)
    sq, sy = qm.std(), ym.std()
    beta = float(np.cov(qm, ym)[0, 1] / max(sq**2, 1e-12))
    bias = float(qm.mean() - ym.mean())
    return {"P": P, "S": S, "beta": beta, "sigma_ratio": float(sq/sy),
            "bias_bps": bias, "n": int(v.sum()),
            "qm": qm, "ym": ym, "coef": ridge.coef_}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="experiments/v5push_phase1a/ridge_results.json")
    ap.add_argument("--alpha", type=float, default=1.0)
    ap.add_argument("--folds", default="0,1,2")
    args = ap.parse_args()
    fold_ids = [int(x) for x in args.folds.split(",")]

    folds = get_v5_folds(NPZ_DIR)
    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    results = {"baseline_64": [], "with_novel": [], "novel_names": None, "alpha": args.alpha}
    pool = {"baseline_64": ([], []), "with_novel": ([], [])}

    for fi in fold_ids:
        fold = folds[fi]
        print(f"\n=== fold {fi} (test start {fold['ts']}) ===", flush=True)
        print(f"  train ({len(fold['train'])}d): {fold['train'][0]}..{fold['train'][-1]}")
        print(f"  test  ({len(fold['test'])}d): {fold['test'][0]}..{fold['test'][-1]}", flush=True)

        # Load
        Xtr_base, Xtr_novel, ytr, mtr, novel_names = load_fold(fold["train"], include_novel=True, label=f"f{fi}-train")
        Xte_base, Xte_novel, yte, mte, _ = load_fold(fold["test"], include_novel=True, label=f"f{fi}-test")
        if results["novel_names"] is None:
            results["novel_names"] = novel_names
        print(f"  train n={len(Xtr_base):,} test n={len(Xte_base):,} F_base={Xtr_base.shape[1]} F_novel={Xtr_novel.shape[1]}")

        # NaN scrub
        Xtr_base = np.nan_to_num(Xtr_base, nan=0.0, posinf=0.0, neginf=0.0)
        Xte_base = np.nan_to_num(Xte_base, nan=0.0, posinf=0.0, neginf=0.0)
        Xtr_novel = np.nan_to_num(Xtr_novel, nan=0.0, posinf=0.0, neginf=0.0)
        Xte_novel = np.nan_to_num(Xte_novel, nan=0.0, posinf=0.0, neginf=0.0)

        # y normalize (MAD-σ, per-fold)
        v_tr = mtr.astype(bool)
        y_med = float(np.median(ytr[v_tr]))
        y_sigma = float(np.median(np.abs(ytr[v_tr] - y_med)) * 1.4826)
        y_sigma = max(y_sigma, 1e-9)
        ytr_z = np.clip((ytr - y_med) / y_sigma, -10, 10).astype(np.float32)
        Xtr_b = Xtr_base[v_tr]; ytr_b = ytr_z[v_tr]

        # Run 1: baseline 64
        r1 = fit_eval_ridge(Xtr_b, ytr_b, Xte_base, yte, mte, y_med, y_sigma, alpha=args.alpha)
        print(f"  Ridge 64-feat:        P={r1['P']:+.4f} S={r1['S']:+.4f} β={r1['beta']:+.3f} σŷ/σy={r1['sigma_ratio']:.3f}", flush=True)
        results["baseline_64"].append({k: v for k, v in r1.items() if k not in ("qm", "ym", "coef")})
        pool["baseline_64"][0].append(r1["qm"]); pool["baseline_64"][1].append(r1["ym"])

        # Run 2: baseline + novel
        Xtr_all = np.concatenate([Xtr_b, Xtr_novel[v_tr]], axis=1)
        Xte_all = np.concatenate([Xte_base, Xte_novel], axis=1)
        r2 = fit_eval_ridge(Xtr_all, ytr_b, Xte_all, yte, mte, y_med, y_sigma, alpha=args.alpha)
        print(f"  Ridge 64+novel({Xtr_novel.shape[1]}):  P={r2['P']:+.4f} S={r2['S']:+.4f} β={r2['beta']:+.3f} σŷ/σy={r2['sigma_ratio']:.3f}  "
              f"ΔP={r2['P']-r1['P']:+.4f} ΔS={r2['S']-r1['S']:+.4f}", flush=True)
        # Feature importance from coef
        feat_names_all = [f"X{i}" for i in range(Xtr_base.shape[1])] + novel_names
        coef = r2["coef"]
        top_idx = np.argsort(-np.abs(coef))[:10]
        print(f"  Top-10 |coef|:")
        for j in top_idx:
            tag = "★novel" if j >= Xtr_base.shape[1] else "  base"
            print(f"    {tag} {feat_names_all[j]:30s} coef={coef[j]:+.4f}")
        results["with_novel"].append({k: v for k, v in r2.items() if k not in ("qm", "ym", "coef")})
        pool["with_novel"][0].append(r2["qm"]); pool["with_novel"][1].append(r2["ym"])

    # Pool
    print(f"\n=== POOL ({len(fold_ids)} folds) ===")
    for tag in ("baseline_64", "with_novel"):
        Q = np.concatenate(pool[tag][0]); Y = np.concatenate(pool[tag][1])
        P = float(pearsonr(Q, Y)[0]); S = float(spearmanr(Q, Y).correlation)
        sq, sy = Q.std(), Y.std()
        beta = float(np.cov(Q, Y)[0,1] / max(sq**2, 1e-12))
        bias = float(Q.mean() - Y.mean())
        std_P = float(np.std([r["P"] for r in results[tag]]))
        results[f"{tag}_pool"] = {"P": P, "S": S, "beta": beta, "sigma_ratio": float(sq/sy),
                                   "bias_bps": bias, "n": int(len(Q)), "per_fold_P_std": std_P}
        print(f"  {tag:14s}: P={P:+.4f} S={S:+.4f} β={beta:+.3f} σŷ/σy={sq/sy:.3f} per-fold P-std={std_P:.4f}")

    P_base = results["baseline_64_pool"]["P"]; P_novel = results["with_novel_pool"]["P"]
    S_base = results["baseline_64_pool"]["S"]; S_novel = results["with_novel_pool"]["S"]
    dP = P_novel - P_base; dS = S_novel - S_base
    print(f"\n=== Gate ===")
    print(f"  Δ pool Pearson  = {dP:+.4f}  (gate ≥ +0.0050 → {'PASS' if dP >= 0.005 else 'FAIL'})")
    print(f"  Δ pool Spearman = {dS:+.4f}")
    n_pos_folds = sum(1 for i in range(len(fold_ids)) if results['with_novel'][i]['P'] > results['baseline_64'][i]['P'])
    print(f"  Per-fold positive ΔP: {n_pos_folds} / {len(fold_ids)} (gate ≥ 2/3)")
    overall_pass = (dP >= 0.005) and (n_pos_folds >= 2)
    print(f"  OVERALL GATE: {'PASS' if overall_pass else 'FAIL'}")
    results["gate_pass"] = overall_pass
    results["dP"] = dP; results["dS"] = dS

    with open(out_path, "w") as f:
        json.dump({k: v for k, v in results.items() if not k.startswith("_")}, f, indent=2, default=float)
    print(f"\n→ {out_path}")


if __name__ == "__main__":
    main()
