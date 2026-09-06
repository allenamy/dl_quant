#!/usr/bin/env python3
"""rebuild_overlap.py — read-only: after a stop trips and the book is flattened, how different is the book we
would REBUILD k anchors later from the book we were holding at the trip? Answers "仓位结构全变了吗".
Device: health_check M1_UPIT_prod_s{42,2027}_ccal.npz — the artifact stores per-anchor full-width weights W.
Metrics per trip event and k: L1 overlap = 1 - 0.5*Σ|w_k - w_trip| / (0.5*(Σ|w_k|+Σ|w_trip|)); cosine; sign agreement
on names held in both; and the turnover the rebuild costs (Σ|w_k| from flat = 1.0 by construction)."""
import json, time, calendar, hashlib
import numpy as np
H = "/workspace/review_scratch/health_check/dev_alt/probe_artifacts"
COLS = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C = {k: i for i, k in enumerate(COLS)}; L = 2.0
KS = [1, 2, 3, 6, 12, 24, 48]
THRS = {"-4.0%": -0.040, "-2.68%": -0.0268}
out = {"metric": "L1 overlap of normalised weight vectors; cosine; sign agreement", "caveat": "replay weights = the device's own book; the live rebuild targets the producer's target, whose EMA state is independent of our positions", "seeds": {}}
for seed in (42, 2027):
    p = f"{H}/w10_ablation_series_M1_UPIT_prod_s{seed}_ccal.npz"
    z = np.load(p, allow_pickle=True)
    Wk = [k for k in z.files if k.endswith("_W")]
    R = np.asarray(z["d30_n2_c42_rec"], float); ts = R[:, C["ts"]].astype(np.int64)
    g = R[:, C["net_ex"]] / R[:, C["gross_total"]]; r = L * g / 1e4
    Wname = "d30_n2_c42_W" if "d30_n2_c42_W" in z.files else (Wk[0] if Wk else None)
    if Wname is None: out["seeds"][f"s{seed}"] = {"error": f"no W array; files {z.files[:10]}"}; continue
    W = np.asarray(z[Wname], float)
    res = {"artifact": p, "sha16": hashlib.sha256(open(p,"rb").read()).hexdigest()[:16], "W": Wname, "W_shape": list(W.shape), "tiers": {}}
    days = ts // 86400
    for tname, thr in THRS.items():
        trips = []
        for d in np.unique(days):
            idx = np.where(days == d)[0]; cum = np.cumprod(1 + r[idx]) - 1; hit = np.where(cum <= thr)[0]
            if len(hit): trips.append(int(idx[hit[0]]))
        per = {}
        for k in KS:
            ov, cs, sg = [], [], []
            for t in trips:
                if t + k >= len(W): continue
                a, b = W[t], W[t+k]
                na, nb = np.abs(a).sum(), np.abs(b).sum()
                if na < 1e-9 or nb < 1e-9: continue
                a, b = a/na, b/nb
                ov.append(1.0 - 0.5*np.abs(b-a).sum())
                cs.append(float(a@b/(np.linalg.norm(a)*np.linalg.norm(b)+1e-12)))
                m = (np.abs(a) > 1e-6) & (np.abs(b) > 1e-6)
                sg.append(float((np.sign(a[m]) == np.sign(b[m])).mean()) if m.sum() else np.nan)
            per[str(k)] = {"n": len(ov), "L1_overlap_mean": float(np.mean(ov)) if ov else None,
                           "cosine_mean": float(np.mean(cs)) if cs else None,
                           "sign_agree_mean": float(np.nanmean(sg)) if sg else None}
        # baseline: same metrics for a random (non-trip) anchor, same k
        rng = np.random.default_rng(20260905); base = {}
        rnd = rng.choice(np.arange(200, len(W)-60), size=300, replace=False)
        for k in KS:
            ov = []
            for t in rnd:
                a, b = W[t], W[t+k]; na, nb = np.abs(a).sum(), np.abs(b).sum()
                if na < 1e-9 or nb < 1e-9: continue
                ov.append(1.0 - 0.5*np.abs(b/nb - a/na).sum())
            base[str(k)] = float(np.mean(ov)) if ov else None
        res["tiers"][tname] = {"n_trips": len(trips), "by_k": per, "baseline_random_anchor_L1_overlap": base}
    out["seeds"][f"s{seed}"] = res
json.dump(out, open("/workspace/review_scratch/health_check/rebuild_overlap.json", "w"), indent=1, default=float)
for s, res in out["seeds"].items():
    if "error" in res: print(s, res["error"]); continue
    print(f"\n===== {s}  W={res['W']} {res['W_shape']}")
    for tname, t in res["tiers"].items():
        print(f"-- {tname}  n_trips={t['n_trips']}")
        print("   k(锚) | 触发时 vs 复场时 权重 L1 重叠 | 余弦 | 同号率 | 同 k 的随机锚基线重叠")
        for k in KS:
            v = t["by_k"][str(k)]; b = t["baseline_random_anchor_L1_overlap"][str(k)]
            f = lambda x: f"{x:.3f}" if x is not None else " n/a "
            print(f"     {k:>3} |  {f(v['L1_overlap_mean'])}  | {f(v['cosine_mean'])} | {f(v['sign_agree_mean'])} |  {f(b)}   (n {v['n']})")
print("\nREBUILD_OVERLAP_DONE")
