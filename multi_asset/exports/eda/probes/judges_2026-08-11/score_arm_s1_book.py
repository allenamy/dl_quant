"""0C — ARM-S1 follow-up: small-weight king-merge (boost) IC vs YR4 + S1 standalone Sharpe + 5-leg
improve-rule vs the existing 4-leg book. CPU-only. Appends to arm_s1_score.json."""
import sys, numpy as np, pandas as pd, json, glob
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
from scipy.stats import rankdata
from multi_asset.data.megacap_funding_replay import build_panel, HOUR_MS
TR = "multi_asset/exports/train/"; EDA = "multi_asset/exports/eda/"; WPF = "multi_asset/exports/wide_panel_full.npz"
S1 = TR + "wideA_s1_yr4k_c1"; RNG = np.random.default_rng(0); ANN = np.sqrt(365.0)


def dms(ts):
    return pd.to_datetime(np.asarray(ts).astype(np.int64), unit="ms", utc=True).floor("D")


def rw(sc):
    r = sc.argsort().argsort().astype(np.float64); r -= r.mean(); s = np.abs(r).sum(); return r / s * 2.0 if s > 0 else r


def cp(scores, member, CL, YR):
    T, N, K = scores.shape; C = np.full((T, N), np.nan)
    for t in np.where((member & CL & np.isfinite(YR)).any(1))[0]:
        base = np.where(member[t] & CL[t] & np.isfinite(YR[t]))[0]
        if base.size < 5:
            continue
        comp = np.zeros(base.size); nk = 0
        for k in range(K):
            col = scores[t, base, k]
            if np.isfinite(col).all() and col.std() > 1e-12:
                comp += (col - col.mean()) / col.std(); nk += 1
        if nk:
            C[t, base] = comp / nk
    return C


def sh(s):
    s = np.asarray(s); return float(s.mean() / s.std() * ANN) if s.std() > 0 else np.nan


pr = np.load(S1 + "/panel_ref.npz", allow_pickle=True)
member, CL, YR4K, Yraw = pr["member"].astype(bool), pr["CL"].astype(bool), pr["YR"].astype(np.float64), pr["Yraw"].astype(np.float64)
ts = pr["ts"].astype(np.int64); N = Yraw.shape[1]
kp = np.load(EDA + "king_pred_panel.npz", allow_pickle=True); king = kp["king_pred"].astype(np.float64); YR4 = kp["YR"].astype(np.float64)
T = Yraw.shape[0]; Sc = np.full((T, N), np.nan)
for f in sorted(glob.glob(S1 + "/fold_*_head_scores.npz")):
    C = cp(np.load(f)["scores"], member, CL, YR4K); m = np.isfinite(C); Sc[m] = C[m]
rows = np.sort(np.where(np.isfinite(Sc).any(1))[0])
day = pr["day"]

# small-weight king-merge: king + w*S1 IC vs YR4
print("=== king-merge boost (IC vs YR4) ===")
merge = {}
for w in (0.05, 0.1, 0.2, 0.3):
    d = []; days = []
    for t in rows:
        b = np.where(member[t] & CL[t] & np.isfinite(YR4[t]) & np.isfinite(Sc[t]) & np.isfinite(king[t]))[0]
        if b.size < 8:
            continue
        k = king[t, b]; s = Sc[t, b]
        zk = (k - k.mean()) / (k.std() + 1e-12); zs = (s - s.mean()) / (s.std() + 1e-12)
        kic = np.corrcoef(rankdata(k), rankdata(YR4[t, b]))[0, 1]
        bic = np.corrcoef(rankdata(zk + w * zs), rankdata(YR4[t, b]))[0, 1]
        d.append(bic - kic); days.append(int(day[t]))
    d = np.array(d); days = np.array(days); ud = np.unique(days); d2 = {u: np.where(days == u)[0] for u in ud}
    bt = np.array([d[np.concatenate([d2[u] for u in RNG.choice(ud, len(ud), True)])].mean() for _ in range(2000)])
    merge[str(w)] = dict(uplift=round(float(d.mean()), 4), ci=[round(float(np.percentile(bt, 2.5)), 4), round(float(np.percentile(bt, 97.5)), 4)], sig=bool(np.percentile(bt, 2.5) > 0))
    print(f"  w={w}: uplift {d.mean():+.4f} CI{merge[str(w)]['ci']} sig{merge[str(w)]['sig']}", flush=True)

# 5-leg: build the 4 existing legs + S1, improve-rule
def bookd(P, Yr, mem, cl, tss, cost):
    dd = dms(tss); rws = np.sort(np.where(np.isfinite(P).any(1))[0]); prev = np.zeros(P.shape[1]); ds = {}
    for t in rws:
        v = np.where(mem[t] & cl[t] & np.isfinite(P[t]) & np.isfinite(Yr[t]))[0]
        if v.size < 10:
            continue
        w = np.zeros(P.shape[1]); w[v] = rw(P[t, v]); g = float((w * np.nan_to_num(Yr[t])).sum()); tn = np.abs(w - prev).sum()
        ds[dd[t]] = ds.get(dd[t], 0.0) + g - tn * cost * 1e-4; prev = w
    return pd.Series(ds).sort_index()


# reuse funding/size from build_4leg logic (import functions)
import importlib.util
spec = importlib.util.spec_from_file_location("b4", EDA + "build_4leg.py"); b4 = importlib.util.module_from_spec(spec); spec.loader.exec_module(b4)
funding = b4.leg_funding(); size = b4.leg_size()
king_b = b4.leg_dl_or_s2(None, None, True, 5.0)
s2_b = b4.leg_dl_or_s2(None, TR + "wideA_s2_y24_5yr", False, 5.0)
s1_b = bookd(Sc, Yraw, member, CL, ts, 5.0)
J = pd.concat([funding, king_b, size, s2_b, s1_b], axis=1, join="inner").dropna(); J.columns = ["funding", "king", "size", "s2", "s1"]
Jn = J / J.std()
four = (Jn["funding"] + Jn["king"] + Jn["size"]) / 3 * 0.9 + Jn["s2"] * 0.1  # 4-leg at v3 weights approx
five = four * 0.9 + Jn["s1"] * 0.1
corr_s1 = {c: round(float(J["s1"].corr(J[c])), 3) for c in ["funding", "king", "size", "s2"]}
print(f"\n5-leg: s1 corr {corr_s1} | 4-leg Sh {sh(four):.2f} -> +s1(0.1) Sh {sh(five):.2f} (Δ {sh(five)-sh(four):+.2f})", flush=True)

r = json.load(open(EDA + "arm_s1_score.json"))
r["king_merge_boost"] = merge
r["s1_leg_corr"] = corr_s1
r["five_leg"] = dict(four_leg_sharpe=round(sh(four), 2), five_leg_sharpe=round(sh(five), 2), delta=round(sh(five) - sh(four), 2))
json.dump(r, open(EDA + "arm_s1_score.json", "w"), indent=2, default=str)
print("SAVED", flush=True)
