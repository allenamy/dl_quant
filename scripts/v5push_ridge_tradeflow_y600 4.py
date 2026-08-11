"""Phase 1A-trade quick test: Ridge with existing tradeflow overlay (5 cols)
already built at data/npz_v4_tradeflow/<date>.npz. NOT in V5 production.

Compare 3 variants on 3-fold walk-forward:
  A. baseline 64
  B. baseline 64 + tradeflow 5 (= 69)
  C. baseline 64 + tradeflow 5 + book novel 16 (= 85)

Gate: pool ΔP ≥ +0.005 (one or both directions).

Reuses get_v5_folds + compute_novel_features from v5push_ridge_novel_features_y600.py.
"""
from __future__ import annotations
import argparse, json, pathlib, time, sys
import numpy as np
from scipy.stats import pearsonr, spearmanr
from sklearn.linear_model import Ridge

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from v5push_ridge_novel_features_y600 import get_v5_folds, compute_novel_features

NPZ_DIR = pathlib.Path("data/npz_v4")
TF_DIR = pathlib.Path("data/npz_v4_tradeflow")


def load_fold(days, include_novel=True, include_tradeflow=True, label="?"):
    Xs, Xnov, Xtf, ys, ms, nov_names = [], [], [], [], [], None
    skip = 0
    t0 = time.time()
    for i, day in enumerate(days):
        base = NPZ_DIR / f"{day}.npz"
        tf_path = TF_DIR / f"{day}.npz"
        if not base.exists():
            skip += 1; continue
        if include_tradeflow and not tf_path.exists():
            skip += 1; continue
        z = np.load(base, allow_pickle=True)
        N = z["X"].shape[0]
        Xs.append(z["X"][:, -1, :].astype(np.float32))
        ys.append(z["y_600"]); ms.append(z["y_mask_600"])
        if include_novel:
            xn, names = compute_novel_features(z["X_raw"])
            Xnov.append(xn)
            if nov_names is None: nov_names = names
        if include_tradeflow:
            tz = np.load(tf_path, allow_pickle=True)
            tf = tz["trade_feats"].astype(np.float32)
            if tf.shape[0] != N:
                # Length mismatch — pad/truncate to align
                if tf.shape[0] < N:
                    tf = np.vstack([tf, np.zeros((N - tf.shape[0], tf.shape[1]), dtype=np.float32)])
                else:
                    tf = tf[:N]
            Xtf.append(tf)
        if (i+1) % 100 == 0:
            print(f"  [{label}] {i+1}/{len(days)} loaded ({time.time()-t0:.0f}s) skip={skip}", flush=True)
    return (np.concatenate(Xs).astype(np.float32),
            np.concatenate(Xnov).astype(np.float32) if include_novel and Xnov else None,
            np.concatenate(Xtf).astype(np.float32) if include_tradeflow and Xtf else None,
            np.concatenate(ys).astype(np.float32),
            np.concatenate(ms).astype(np.float32),
            nov_names)


def fit_eval(Xtr, ytrZ, Xte, yte, mte, ymed, ysig, alpha=1.0):
    xm, xs = Xtr.mean(0), Xtr.std(0)
    xs = np.where(xs < 1e-9, 1.0, xs)
    Xtn = ((Xtr - xm) / xs).astype(np.float32)
    Xen = ((Xte - xm) / xs).astype(np.float32)
    Xtn = np.nan_to_num(Xtn, nan=0.0, posinf=0.0, neginf=0.0)
    Xen = np.nan_to_num(Xen, nan=0.0, posinf=0.0, neginf=0.0)
    r = Ridge(alpha=alpha).fit(Xtn, ytrZ)
    qz = r.predict(Xen)
    qbps = (qz * ysig + ymed) * 1e4
    ybps = yte * 1e4
    v = mte.astype(bool)
    qm, ym = qbps[v], ybps[v]
    P = float(pearsonr(qm, ym)[0])
    S = float(spearmanr(qm, ym).correlation)
    sq, sy = qm.std(), ym.std()
    beta = float(np.cov(qm, ym)[0,1] / max(sq**2, 1e-12))
    return {"P": P, "S": S, "beta": beta, "sigma_ratio": float(sq/sy), "n": int(v.sum()), "qm": qm, "ym": ym, "coef": r.coef_}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="experiments/v5push_phase1a_trade/ridge_results.json")
    ap.add_argument("--alpha", type=float, default=1.0)
    ap.add_argument("--folds", default="0,1,2")
    args = ap.parse_args()
    fold_ids = [int(x) for x in args.folds.split(",")]
    folds = get_v5_folds(NPZ_DIR)

    out = pathlib.Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    results = {"variants": {"A_base64": [], "B_64tf5": [], "C_64tf5nov16": []},
                "novel_names": None}
    pool = {k: ([], []) for k in results["variants"]}

    for fi in fold_ids:
        fold = folds[fi]
        print(f"\n=== fold {fi} ({fold['ts']}) ===", flush=True)
        Xb_tr, Xn_tr, Xtf_tr, ytr, mtr, nov_names = load_fold(fold["train"], label=f"f{fi}-tr")
        Xb_te, Xn_te, Xtf_te, yte, mte, _ = load_fold(fold["test"], label=f"f{fi}-te")
        if results["novel_names"] is None:
            results["novel_names"] = nov_names
        print(f"  train n={len(Xb_tr):,} test n={len(Xb_te):,}", flush=True)

        # Sanitize
        for arr in (Xb_tr, Xb_te, Xn_tr, Xn_te, Xtf_tr, Xtf_te):
            if arr is not None:
                np.nan_to_num(arr, copy=False, nan=0.0, posinf=0.0, neginf=0.0)

        vtr = mtr.astype(bool)
        ymed = float(np.median(ytr[vtr]))
        ysig = max(float(np.median(np.abs(ytr[vtr]-ymed))*1.4826), 1e-9)
        ytrZ = np.clip((ytr-ymed)/ysig, -10, 10).astype(np.float32)

        # A: base 64
        rA = fit_eval(Xb_tr[vtr], ytrZ[vtr], Xb_te, yte, mte, ymed, ysig, alpha=args.alpha)
        print(f"  A 64-feat:           P={rA['P']:+.4f} S={rA['S']:+.4f} β={rA['beta']:+.3f} σŷ/σy={rA['sigma_ratio']:.3f}", flush=True)
        # B: base + tradeflow
        Xtr_B = np.concatenate([Xb_tr[vtr], Xtf_tr[vtr]], axis=1)
        Xte_B = np.concatenate([Xb_te, Xtf_te], axis=1)
        rB = fit_eval(Xtr_B, ytrZ[vtr], Xte_B, yte, mte, ymed, ysig, alpha=args.alpha)
        print(f"  B 64+tf5:           P={rB['P']:+.4f} S={rB['S']:+.4f} β={rB['beta']:+.3f} σŷ/σy={rB['sigma_ratio']:.3f}  ΔP={rB['P']-rA['P']:+.4f} ΔS={rB['S']-rA['S']:+.4f}", flush=True)
        # C: base + tradeflow + novel book
        Xtr_C = np.concatenate([Xb_tr[vtr], Xtf_tr[vtr], Xn_tr[vtr]], axis=1)
        Xte_C = np.concatenate([Xb_te, Xtf_te, Xn_te], axis=1)
        rC = fit_eval(Xtr_C, ytrZ[vtr], Xte_C, yte, mte, ymed, ysig, alpha=args.alpha)
        print(f"  C 64+tf5+nov16:    P={rC['P']:+.4f} S={rC['S']:+.4f} β={rC['beta']:+.3f} σŷ/σy={rC['sigma_ratio']:.3f}  ΔP={rC['P']-rA['P']:+.4f} ΔS={rC['S']-rA['S']:+.4f}", flush=True)
        # Top 5 |coef| for variant B (tradeflow features should appear here if useful)
        idx_top5_B = np.argsort(-np.abs(rB["coef"]))[:8]
        print(f"  Variant B top-8 |coef|:")
        for j in idx_top5_B:
            tag = "★tf  " if 64 <= j < 69 else "  base"
            name = f"X{j}" if j < 64 else (f"tf{j-64}" if j < 69 else f"nov{j-69}")
            print(f"    {tag} {name:8s} coef={rB['coef'][j]:+.4f}")

        for tag, r in (("A_base64", rA), ("B_64tf5", rB), ("C_64tf5nov16", rC)):
            results["variants"][tag].append({k:v for k,v in r.items() if k not in ('qm','ym','coef')})
            pool[tag][0].append(r["qm"]); pool[tag][1].append(r["ym"])

    print(f"\n=== POOL ({len(fold_ids)} folds) ===")
    for tag in results["variants"]:
        Q = np.concatenate(pool[tag][0]); Y = np.concatenate(pool[tag][1])
        P = float(pearsonr(Q, Y)[0]); S = float(spearmanr(Q, Y).correlation)
        sq, sy = Q.std(), Y.std()
        beta = float(np.cov(Q, Y)[0,1] / max(sq**2, 1e-12))
        stdP = float(np.std([r["P"] for r in results["variants"][tag]]))
        print(f"  {tag:15s}: P={P:+.4f} S={S:+.4f} β={beta:+.3f} σŷ/σy={sq/sy:.3f} per-fold P-std={stdP:.4f}")
        results[f"{tag}_pool"] = {"P": P, "S": S, "beta": beta, "sigma_ratio": float(sq/sy), "n": int(len(Q)), "per_fold_P_std": stdP}

    # Gates
    PA, PB, PC = (results[f"{tag}_pool"]["P"] for tag in ("A_base64","B_64tf5","C_64tf5nov16"))
    SA, SB, SC = (results[f"{tag}_pool"]["S"] for tag in ("A_base64","B_64tf5","C_64tf5nov16"))
    print(f"\n=== Gate ===")
    print(f"  B vs A (tradeflow only):       ΔP={PB-PA:+.4f} ΔS={SB-SA:+.4f}  gate={'PASS' if (PB-PA)>=0.005 else 'FAIL'}")
    print(f"  C vs A (tradeflow + novel):    ΔP={PC-PA:+.4f} ΔS={SC-SA:+.4f}  gate={'PASS' if (PC-PA)>=0.005 else 'FAIL'}")
    print(f"  C vs B (novel adds over tf):   ΔP={PC-PB:+.4f} ΔS={SC-SB:+.4f}  gate={'PASS' if (PC-PB)>=0.005 else 'FAIL'}")
    results["gates"] = {"B_vs_A_dP": PB-PA, "C_vs_A_dP": PC-PA, "C_vs_B_dP": PC-PB,
                          "B_vs_A_dS": SB-SA, "C_vs_A_dS": SC-SA, "C_vs_B_dS": SC-SB}

    with open(out, "w") as f:
        json.dump(results, f, indent=2, default=float)
    print(f"\n→ {out}")


if __name__ == "__main__":
    main()
