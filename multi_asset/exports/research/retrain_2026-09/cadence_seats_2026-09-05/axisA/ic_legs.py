"""ic_legs.py (axis A; copied from rolling_king/pod_king_ic_legs.py, only OUT/KING_PATHS/KINGS changed) — STEP 1 IC tables + STEP 2 leg-level + msharpe seat (PREREG_rolling_king_monthly_2026-09-05).
Kings: pinned (/workspace/shadow_bundle_v3/slow_pred_pinned.npy), rollm, rollq (rolling_king/). Read-only inputs.
IC   = Spearman(prediction, target) over meta members with finite target (>=30 pairs; exporter sp()), mean over anchors;
       anchor set = anchors >= 2024-01-01 where EVERY king source has a finite IC (identical anchor set across sources);
       targets: raw y4 (meta, Σ5m simple [E,E+47]) and dlw y4s (Π(1+r5)-1 over [E+1,E+48], aligned by E_ts).
Leg  = production definition (pod_export_bundle_v3.py L102-109 == device legs()): z = nan_to_num(xz(score)); z = where(ok, z, 0);
       z -= mean(z[ok]); leg = Σ (z/|z|₁)·y ×1e4 (bps per unit gross), members = meta members, ok = isfinite(y), anchors with a panel row.
Seat = production msharpe (exporter L113-119): 900 previous anchors, shp = mean/(std+1e-9) clipped >= 0, normalised (3 legs);
       plus LEGS=101 mask (device w3_at L170-173): rev24 zeroed and renormalised = deployed combo seat.
"""
import os, sys, json, time, calendar, hashlib
import numpy as np
from scipy.stats import rankdata, spearmanr
OUT = "/workspace/review_scratch/cadence_seats/axisA"
KING_PATHS = {"pinned": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy", "rollm": "/workspace/review_scratch/rolling_king/slow_pred_rollm.npy", "rollm1": f"{OUT}/slow_pred_rollm1.npy", "rollw1": f"{OUT}/slow_pred_rollw1.npy"}
KINGS = [k for k in ("pinned", "rollm", "rollm1", "rollw1") if os.path.exists(KING_PATHS[k])]
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
t00 = time.time()
print("CONFIG " + json.dumps({"kings": {k: {"path": KING_PATHS[k], "sha256": sha(KING_PATHS[k])} for k in KINGS}, "self_sha256": sha(__file__),
                              "meta": "/workspace/data/wide_fea_v2ext_meta.npz", "panel": "/workspace/data/wide_panel_4h_v2ext.npz", "dlw": "/workspace/data/dlw_targets.npz"}), flush=True)
MT = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; nA = len(E_ts); NW = 829
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
CUT = calendar.timegm((2026, 8, 10, 20, 0, 0))
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
PW = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True)
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]; R24 = PW["f_rev_24h"]; FE = PW["f_fund_ema_v1"]
DT = np.load("/workspace/data/dlw_targets.npz", allow_pickle=True)
assert [str(s) for s in DT["symbols"]] == [str(s) for s in PW["symbols"]], "dlw symbols != panel symbols"
dts = DT["E_ts"].astype(np.int64); y4s_src = DT["y4s"]
dmap = {int(t): k for k, t in enumerate(dts)}
Y4S = np.full((nA, NW), np.nan, np.float32); has_dlw = np.zeros(nA, bool)
for i in range(nA):
    k = dmap.get(int(E_ts[i]))
    if k is not None: Y4S[i] = y4s_src[k]; has_dlw[i] = True
_miss = np.where(~has_dlw)[0]
print(f"DLW align: meta anchors {nA}, with dlw row {int(has_dlw.sum())}, missing {len(_miss)} "
      f"(first missing {iso(E_ts[_miss[0]]) if len(_miss) else '-'}, last missing {iso(E_ts[_miss[-1]]) if len(_miss) else '-'}; missing >=2024: {int((yrs[_miss] >= 2024).sum())})", flush=True)
PRED = {k: np.load(KING_PATHS[k]) for k in KINGS}
for k in KINGS:
    assert PRED[k].shape == (nA, NW) and PRED[k].dtype == np.float32, (k, PRED[k].shape, PRED[k].dtype)
    fa = np.isfinite(PRED[k]).any(1)
    print(f"KING {k}: finite anchors {int(fa.sum())} first {iso(E_ts[np.where(fa)[0][0]])} last {iso(E_ts[np.where(fa)[0][-1]])} pre2024_all_nan {bool(not fa[yrs < 2024].any())} "
          f"finite_mask_equal_pinned {bool(np.array_equal(np.isfinite(PRED[k]), np.isfinite(PRED['pinned'])))}", flush=True)
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 10: out[ok] = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
    return out

# ───────── IC tables ─────────
ic = {("raw", k): np.full(nA, np.nan) for k in KINGS}; ic.update({("y4s", k): np.full(nA, np.nan) for k in KINGS})
for i in range(nA):
    if yrs[i] < 2024: continue
    m = members[i]; yv = y4[i, m]; ys = Y4S[i, m]
    for k in KINGS:
        p = PRED[k][i, m]
        ic[("raw", k)][i] = sp(p, yv); ic[("y4s", k)][i] = sp(p, ys)
WIN = {"2024": yrs == 2024, "2025": yrs == 2025, "2026<=08-10": (yrs == 2026) & (E_ts <= CUT), "2026->08-30": yrs == 2026,
       "2024->26": yrs >= 2024, "2025->26": yrs >= 2025}
res_ic = {}
for tgt in ("raw", "y4s"):
    common = np.ones(nA, bool)
    for k in KINGS: common &= np.isfinite(ic[(tgt, k)])
    print(f"\nIC TABLE target={tgt} ({'raw y4 = Σ5m simple [E,E+47]' if tgt == 'raw' else 'dlw y4s = Π(1+r5)-1 over [E+1,E+48]'}); anchors = 2024+ with finite IC for all of {KINGS}; mean rank-IC over anchors")
    hdr = f"{'window':12s} {'n':>6s} " + " ".join(f"{k:>9s}" for k in KINGS) + ("  " + " ".join(f"{'Δ'+k+'-pin':>12s}" for k in KINGS if k != "pinned"))
    print(hdr)
    for w, msk in WIN.items():
        mm = msk & common; n = int(mm.sum())
        vals = {k: float(np.mean(ic[(tgt, k)][mm])) if n else np.nan for k in KINGS}
        dl = {}
        for k in KINGS:
            if k == "pinned": continue
            d = ic[(tgt, k)][mm] - ic[(tgt, "pinned")][mm]
            dl[k] = (float(d.mean()), float(d.std(ddof=1) / np.sqrt(max(n, 1))))
        res_ic[f"{tgt}/{w}"] = {"n": n, **{k: round(vals[k], 5) for k in KINGS}, **{f"d_{k}": [round(dl[k][0], 5), round(dl[k][1], 5)] for k in dl}}
        print(f"{w:12s} {n:6d} " + " ".join(f"{vals[k]:+9.4f}" for k in KINGS) + "  " + " ".join(f"{dl[k][0]:+8.4f}±{dl[k][1]:.4f}" for k in dl))
# per-month IC (raw) for rollm vs pinned (auxiliary)
ym = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in E_ts])
common_raw = np.ones(nA, bool)
for k in KINGS: common_raw &= np.isfinite(ic[("raw", k)])
print(f"\nIC BY MONTH (raw y4; n anchors; " + " / ".join(KINGS) + ")")
row = []
for key in sorted(set(ym[yrs >= 2024].tolist())):
    mm = (ym == key) & common_raw
    row.append(f"{key}:{int(mm.sum())} " + "/".join(f"{np.mean(ic[('raw', k)][mm]):+.3f}" for k in KINGS))
for a in range(0, len(row), 4): print("  " + " | ".join(row[a:a + 4]))

# ───────── leg-level ─────────
def legs_for(SLOW, Ymat):
    LR = {"king": [], "rev24": [], "fund": []}; idx = []
    for i in range(nA):
        j = pw_row.get(int(E_ts[i]))
        if j is None: continue
        m = members[i]; ok = np.isfinite(Ymat[i, m])
        sc = {"king": SLOW[i, m], "rev24": -R24[j, m], "fund": FE[j, m]}
        for leg in LR:
            z = np.nan_to_num(xz(sc[leg])); z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0
            g = np.abs(z).sum()
            LR[leg].append(float((z / g * np.nan_to_num(Ymat[i, m], nan=0.0)).sum() * 1e4) if g > 1e-9 else 0.0)
        idx.append(i)
    return {k: np.array(v) for k, v in LR.items()}, np.array(idx)
LEGS = {}
for cal, Ymat in (("raw", y4), ("y4s", Y4S)):
    for k in KINGS:
        LEGS[(cal, k)], idx = legs_for(PRED[k], Ymat)
print(f"\nLEGS computed: anchors with panel row {len(idx)} first {iso(E_ts[idx[0]])} last {iso(E_ts[idx[-1]])} ({time.time()-t00:.0f}s)", flush=True)
its = E_ts[idx]; iyr = yrs[idx]
pos = {int(i): p for p, i in enumerate(idx)}
p_cut = pos[int(np.where(E_ts == CUT)[0][0])]
LW0 = {"2024": iyr == 2024, "2025": iyr == 2025, "2026<=08-10": (iyr == 2026) & (its <= CUT), "2026->08-30": iyr == 2026, "2024->26": iyr >= 2024, "2025->26": iyr >= 2025}
hasd = has_dlw[idx]
w900_pre = np.zeros(len(idx), bool); w900_pre[p_cut - 900:p_cut] = True          # the seat window at 2026-08-10 20:00Z
w900_last = np.zeros(len(idx), bool); w900_last[-900:] = True                   # last 900 anchors of the file (raw caliber)
w900_last_d = np.zeros(len(idx), bool); w900_last_d[np.where(hasd)[0][-900:]] = True   # last 900 anchors WITH a dlw row (y4s caliber; dlw ends 2026-08-10 20:00Z)
def sh(x): return float(x.mean() / (x.std(ddof=1) + 1e-12))
res_leg = {}
for cal in ("raw", "y4s"):
    LW = LW0 if cal == "raw" else {w: (m & hasd) for w, m in LW0.items()}   # y4s: only anchors with a dlw row (2026->08-30 == 2026<=08-10 there)
    if cal == "y4s": w900_last = w900_last_d
    print(f"\nLEG TABLE caliber={cal} (bps per unit gross per anchor; production leg definition; king leg per source, rev24/fund identical across sources"
          + ("; windows restricted to anchors with a dlw row, i.e. <= 2026-08-10 20:00Z)" if cal == "y4s" else ")"))
    print(f"{'leg':14s} " + " ".join(f"{w:>18s}" for w in LW) + f" {'S/anchor 900pre0810':>20s} {'S/anchor last900':>18s}")
    rows = [("king", k) for k in KINGS] + [("rev24", "pinned"), ("fund", "pinned")]
    for leg, k in rows:
        x = LEGS[(cal, k)][leg]; name = f"{leg}[{k}]" if leg == "king" else leg
        cells = {w: (float(x[m].mean()), sh(x[m]), int(m.sum())) for w, m in LW.items()}
        s_pre = sh(x[w900_pre]); s_last = sh(x[w900_last])
        res_leg[f"{cal}/{name}"] = {**{w: [round(c[0], 4), round(c[1], 4), c[2]] for w, c in cells.items()}, "S900pre": round(s_pre, 4), "S900last": round(s_last, 4),
                                    "mean900pre": round(float(x[w900_pre].mean()), 4), "mean900last": round(float(x[w900_last].mean()), 4)}
        print(f"{name:14s} " + " ".join(f"{cells[w][0]:+8.3f} S{cells[w][1]:+.3f}".rjust(18) for w in LW) + f" {s_pre:+20.4f} {s_last:+18.4f}")
    for k in KINGS:
        if k == "pinned": continue
        d = LEGS[(cal, k)]["king"] - LEGS[(cal, "pinned")]["king"]
        print(f"  Δking[{k}-pinned]: " + " ".join(f"{w}={d[m].mean():+.3f}(n{int(m.sum())})" for w, m in LW.items()) + f" | 900pre {d[w900_pre].mean():+.3f} last900 {d[w900_last].mean():+.3f}")
    print(f"  (window sizes: " + ", ".join(f"{w}={int(m.sum())}" for w, m in LW.items()) + f"; 900pre window {iso(its[p_cut-900])}..{iso(its[p_cut-1])}; last900 {iso(its[np.where(w900_last)[0][0]])}..{iso(its[np.where(w900_last)[0][-1]])})")

# ───────── msharpe seat ─────────
def msharpe_w(LRa, p, look=900):
    sl = slice(p - look, p)
    r = np.stack([LRa["king"][sl], LRa["rev24"][sl], LRa["fund"][sl]])
    mu = r.mean(1); sd = r.std(1); shp = mu / (sd + 1e-9); shp = np.maximum(shp, 0.0)
    w = shp / shp.sum() if shp.sum() > 0 else np.array([1 / 3] * 3)
    msk = np.array([1.0, 0.0, 1.0]); w101 = w * msk; w101 = w101 / w101.sum() if w101.sum() > 1e-12 else msk / msk.sum()
    return w, w101, shp, mu, sd
res_seat = {}
print(f"\nSEAT at {iso(CUT)} (production msharpe LOOK=900 over the 900 anchors {iso(its[p_cut-900])}..{iso(its[p_cut-1])}; w3 = king/rev24/fund; w101 = LEGS=101 mask = deployed combo)")
for cal in ("raw", "y4s"):
    for k in KINGS:
        w, w101, shp, mu, sd = msharpe_w(LEGS[(cal, k)], p_cut)
        res_seat[f"{cal}/{k}"] = {"w3": [round(float(v), 4) for v in w], "w101": [round(float(v), 4) for v in w101], "shp": [round(float(v), 4) for v in shp], "mu": [round(float(v), 4) for v in mu], "sd": [round(float(v), 4) for v in sd]}
        print(f"  cal={cal:4s} king={k:7s} shp(king/rev24/fund)={shp[0]:+.4f}/{shp[1]:+.4f}/{shp[2]:+.4f}  w3={w[0]:.3f}/{w[1]:.3f}/{w[2]:.3f}  w101(king/fund)={w101[0]:.3f}/{w101[2]:.3f}  [mu {mu[0]:+.3f}/{mu[1]:+.3f}/{mu[2]:+.3f} sd {sd[0]:.2f}/{sd[1]:.2f}/{sd[2]:.2f}]")
# seat trajectory (raw caliber): first anchor of each quarter 2024Q3..2026Q3 (>= 900 anchors of 2024+ legs needed for a window free of the pre-2024 NaN-king zeros), and CUT
print("\nSEAT TRAJECTORY (raw y4 caliber, w101 king weight at first anchor of each quarter; note pinned/roll king leg = 0 before 2024 -> windows before ~2024-06 contain zero-return king anchors)")
traj = []
for (yy, mo) in [(2024, 1), (2024, 4), (2024, 7), (2024, 10), (2025, 1), (2025, 4), (2025, 7), (2025, 10), (2026, 1), (2026, 4), (2026, 7)]:
    t = calendar.timegm((yy, mo, 1, 0, 0, 0)); ii = np.where(its >= t)[0][0]
    traj.append(f"{iso(its[ii])[:10]}: " + " ".join(f"{k}={msharpe_w(LEGS[('raw', k)], ii)[1][0]:.3f}" for k in KINGS))
traj.append(f"{iso(CUT)[:10]}: " + " ".join(f"{k}={msharpe_w(LEGS[('raw', k)], p_cut)[1][0]:.3f}" for k in KINGS))
for a in range(0, len(traj), 3): print("  " + " | ".join(traj[a:a + 3]))
json.dump({"ic": res_ic, "legs": res_leg, "seat": res_seat, "kings": {k: KING_PATHS[k] for k in KINGS}}, open(f"{OUT}/ic_legs_seat.json", "w"), indent=1)
np.savez_compressed(f"{OUT}/legs_by_king.npz", ts=its, **{f"{cal}_{k}_{leg}": LEGS[(cal, k)][leg] for cal in ("raw", "y4s") for k in KINGS for leg in ("king", "rev24", "fund")})
print(f"\nDONE {time.time()-t00:.0f}s -> {OUT}/ic_legs_seat.json, legs_by_king.npz", flush=True)
