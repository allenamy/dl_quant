"""0C batch_002 STEP-1: equivalence (independent slow ref: explicit recursive ema + rolling ts_std over
FULL history; xsec_z over member&CL — matching the fixed dsl) vs ledger inc-IC + fast-vs-ref rank agreement;
low-vol cluster {248,250,251} mutual corr (1 leg or 3?); capacity probe (large vs small DVOL half) for all 4.
Writes /tmp/0c_b2_step1.json."""
import os
import json, sys, numpy as np, pandas as pd
from scipy.stats import rankdata
sys.path.insert(0, MA)
sys.path.insert(0, MA + "/factory")
import dsl, pipeline as P
MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
LEDGER = MA + "/exports/eda/factory_ledger.jsonl"
CAND = {247: "xsec_z(mul(ema(ret_4h, 24), neg(rvol_6h)))", 248: "neg(xsec_z(ts_std(ret_4h, 168)))",
        250: "neg(xsec_z(ema(rvol_72h, 168)))", 251: "neg(xsec_z(ema(abs(ret_24h), 168)))"}
LOWVOL = [248, 250, 251]


def ref_ema(A, span):  # recursive, adjust=False, min_periods=1, vectorized over coins
    a = 2.0 / (span + 1); out = np.full_like(A, np.nan); s = np.full(A.shape[1], np.nan)
    for t in range(A.shape[0]):
        x = A[t]; fin = np.isfinite(x)
        s_new = np.where(np.isfinite(s), a * x + (1 - a) * s, x)
        s = np.where(fin, s_new, s); out[t] = s
    return out


def ref_ts_std(A, n):  # trailing std ddof=1, min_periods=max(2,n//2)
    mp = max(2, n // 2); out = np.full_like(A, np.nan)
    for t in range(A.shape[0]):
        w = A[max(0, t - n + 1):t + 1]; cnt = np.isfinite(w).sum(0)
        out[t] = np.where(cnt >= mp, np.nanstd(w, axis=0, ddof=1), np.nan)
    return out


def ref_xsec_z(A, uni):  # z over member&CL universe only (matches fixed dsl)
    B = np.where(uni, A, np.nan); out = np.full_like(A, np.nan)
    for t in range(A.shape[0]):
        b = np.where(np.isfinite(B[t]))[0]
        if b.size >= 3:
            x = B[t, b]; sd = x.std(); out[t, b] = (x - x.mean()) / sd if sd > 1e-9 else np.nan
    return out


C = P.load_context(horizon=4, subsample=1)
ctx, mem, CL, rows, tgt, year, day = C["ctx"], C["member"], C["CL"], C["rows"], C["target"], C["year"], C["day"]
uni = ctx["__universe__"]
raw = {c: np.load(MA + "/exports/wide_dl_full.npz", allow_pickle=True)["CH"][:, :, i].astype(np.float64)
       for i, c in enumerate([str(x) for x in np.load(MA + "/exports/wide_dl_full.npz", allow_pickle=True)["ch_names"]])
       if c in ("ret_4h", "rvol_6h", "rvol_72h", "ret_24h", "size_dvol")}
Y4 = np.load(MA + "/exports/wide_dl_full.npz", allow_pickle=True)["Y4"].astype(np.float64)


def ref_build(fid):
    if fid == 247: return ref_xsec_z(ref_ema(raw["ret_4h"], 24) * (-raw["rvol_6h"]), uni)
    if fid == 248: return -ref_xsec_z(ref_ts_std(raw["ret_4h"], 168), uni)
    if fid == 250: return -ref_xsec_z(ref_ema(raw["rvol_72h"], 168), uni)
    if fid == 251: return -ref_xsec_z(ref_ema(np.abs(raw["ret_24h"]), 168), uni)


def incic(fac, target, rows):
    ics = []
    for t in rows:
        b = np.where(mem[t] & CL[t] & np.isfinite(target[t]) & np.isfinite(fac[t]))[0]
        if b.size >= 8 and np.std(fac[t, b]) > 1e-12 and np.std(target[t, b]) > 1e-12:
            ics.append(np.corrcoef(rankdata(fac[t, b]), rankdata(target[t, b]))[0, 1])
    return float(np.mean(ics)), len(ics)


led = {r["eval_id"]: r for r in (json.loads(l) for l in open(LEDGER) if l.strip())}
OUT = {}; facs = {}
for fid in CAND:
    ref = ref_build(fid); facs[fid] = ref
    fast = dsl.evaluate(dsl.parse(CAND[fid]), ctx)
    sp = []
    for t in rows:
        b = np.where(mem[t] & CL[t] & np.isfinite(fast[t]) & np.isfinite(ref[t]))[0]
        if b.size >= 8 and np.std(fast[t, b]) > 1e-12 and np.std(ref[t, b]) > 1e-12:
            sp.append(np.corrcoef(rankdata(fast[t, b]), rankdata(ref[t, b]))[0, 1])
    ic, n = incic(ref, tgt, rows); lic = led[fid]["stage1_stats"]["inc_ic"]
    OUT[f"c{fid}"] = dict(formula=CAND[fid], inc_ic_ref=round(ic, 5), inc_ic_ledger=lic, diff=round(abs(ic - lic), 6),
                          rankorder_spearman_min=round(float(np.min(sp)), 6), match=bool(abs(ic - lic) < 6e-4))
    print(f"c{fid}: ref {ic:.5f} vs led {lic} diff {abs(ic-lic):.6f} rankSpear {np.min(sp):.5f} {'MATCH' if abs(ic-lic)<6e-4 else 'MISMATCH'}", flush=True)

# cluster mutual corr {248,250,251}
mut = {}
for i in range(len(LOWVOL)):
    for j in range(i + 1, len(LOWVOL)):
        cc = [abs(np.corrcoef(rankdata(facs[LOWVOL[i]][t, b]), rankdata(facs[LOWVOL[j]][t, b]))[0, 1])
              for t in rows for b in [np.where(mem[t] & CL[t] & np.isfinite(facs[LOWVOL[i]][t]) & np.isfinite(facs[LOWVOL[j]][t]))[0]] if b.size >= 8]
        mut[f"{LOWVOL[i]}x{LOWVOL[j]}"] = round(float(np.mean(cc)), 3)
OUT["_lowvol_mutual_corr"] = mut
# I15 vs cluster (is bullseye distinct?)
OUT["_I15(247)_vs_cluster"] = {f"247x{fid}": round(float(np.mean(
    [abs(np.corrcoef(rankdata(facs[247][t, b]), rankdata(facs[fid][t, b]))[0, 1])
     for t in rows for b in [np.where(mem[t] & CL[t] & np.isfinite(facs[247][t]) & np.isfinite(facs[fid][t]))[0]] if b.size >= 8])), 3) for fid in LOWVOL}
print("lowvol mutual:", mut, "| I15 vs cluster:", OUT["_I15(247)_vs_cluster"], flush=True)

# capacity probe (large vs small DVOL half) for all 4
cap = {}
for fid in CAND:
    small, large = [], []
    for t in rows:
        b = np.where(mem[t] & CL[t] & np.isfinite(Y4[t]) & np.isfinite(facs[fid][t]) & np.isfinite(raw["size_dvol"][t]))[0]
        if b.size >= 20:
            md = np.median(raw["size_dvol"][t, b]); sm = b[raw["size_dvol"][t, b] <= md]; lg = b[raw["size_dvol"][t, b] > md]
            if sm.size >= 8 and np.std(facs[fid][t, sm]) > 1e-9: small.append(np.corrcoef(rankdata(facs[fid][t, sm]), rankdata(Y4[t, sm]))[0, 1])
            if lg.size >= 8 and np.std(facs[fid][t, lg]) > 1e-9: large.append(np.corrcoef(rankdata(facs[fid][t, lg]), rankdata(Y4[t, lg]))[0, 1])
    cap[f"c{fid}"] = dict(ic_small=round(float(np.mean(small)), 4), ic_large=round(float(np.mean(large)), 4),
                          large_over_small=round(float(np.mean(large) / (np.mean(small) + 1e-9)), 2))
    print(f"capacity c{fid}: small {np.mean(small):.4f} large {np.mean(large):.4f}", flush=True)
OUT["_capacity"] = cap
json.dump(OUT, open("/tmp/0c_b2_step1.json", "w"), indent=1, default=str)
print("SAVED", flush=True)
