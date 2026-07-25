"""0C batch_001 STEP-1 (greenlit): (A) per-anchor score-residual专项 — fast dsl.evaluate vs my slow
reference, per-anchor rank-order agreement (benign scale vs rank bug); (B) inc-IC ref-vs-ledger align;
(C) A-group mutual corr (cluster?); (D) B-group pred-corr vs the 4-leg book. Writes /tmp/0c_b1_step1.json.
"""
import json, sys, numpy as np, pandas as pd
from scipy.stats import rankdata
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/factory")
import dsl, pipeline as P
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
LEDGER = MA + "/exports/eda/factory_ledger.jsonl"
A = {101: "neg(mul(xsec_z(lturnover_24h), xsec_z(max_ret_24h)))", 104: "neg(xsec_z(ts_max(abs(ret_1h), 24)))",
     107: "neg(xsec_z(power(ret_24h, 3)))", 120: "neg(xsec_z(ts_max(rvol_6h, 42)))"}
B = {109: "where(gt(xsec_z(rvol_24h), xsec_z(rvol_72h)), s2, king)",
     114: "where(gt(xsec_z(mom_72h), xsec_z(mom_24h)), s2, king)",
     115: "where(gt(xsec_z(dvol_24h), xsec_z(dvol_72h)), king, s2)"}


def ref_xsec_z(Arr, mem, CL):
    out = np.full_like(Arr, np.nan)
    for t in range(Arr.shape[0]):
        b = np.where(mem[t] & CL[t] & np.isfinite(Arr[t]))[0]
        if b.size >= 3:
            x = Arr[t, b]; sd = x.std(); out[t, b] = (x - x.mean()) / sd if sd > 1e-9 else np.nan
    return out


def ref_ts_max(Arr, n, use_abs=False):
    X = np.abs(Arr) if use_abs else Arr; out = np.full_like(Arr, np.nan); mp = max(2, n // 2)
    for t in range(Arr.shape[0]):
        w = X[max(0, t - n + 1):t + 1]; cnt = np.isfinite(w).sum(0)
        out[t] = np.where(cnt >= mp, np.nanmax(np.where(np.isfinite(w), w, -np.inf), 0), np.nan)
    return out


def ref_build(fid, ctx, mem, CL):
    if fid == 101: return -(ref_xsec_z(ctx["lturnover_24h"], mem, CL) * ref_xsec_z(ctx["max_ret_24h"], mem, CL))
    if fid == 107: return -ref_xsec_z(np.sign(ctx["ret_24h"]) * np.abs(ctx["ret_24h"]) ** 3.0, mem, CL)
    if fid == 104: return -ref_xsec_z(ref_ts_max(ctx["ret_1h"], 24, True), mem, CL)
    if fid == 120: return -ref_xsec_z(ref_ts_max(ctx["rvol_6h"], 42), mem, CL)


def incic(fac, tgt, mem, CL, rows):
    ics = []
    for t in rows:
        b = np.where(mem[t] & CL[t] & np.isfinite(tgt[t]) & np.isfinite(fac[t]))[0]
        if b.size >= 8 and np.std(fac[t, b]) > 1e-12 and np.std(tgt[t, b]) > 1e-12:
            ics.append(np.corrcoef(rankdata(fac[t, b]), rankdata(tgt[t, b]))[0, 1])
    return float(np.mean(ics)), len(ics)


C = P.load_context(horizon=4, subsample=1)
ctx, mem, CL, rows, tgt = C["ctx"], C["member"], C["CL"], C["rows"], C["target"]
led = {r["eval_id"]: r for r in (json.loads(l) for l in open(LEDGER) if l.strip())}
OUT = {}; facs = {}

# ---- (A) residual专项 + (B) inc-IC align (A-group) ----
for fid, f in A.items():
    fast = dsl.evaluate(dsl.parse(f), ctx)
    ref = ref_build(fid, ctx, mem, CL); facs[fid] = ref
    # per-anchor rank-order agreement (over scored member&CL&finite) between fast & ref
    sp, flips, valmax = [], 0, 0.0
    for t in rows:
        b = np.where(mem[t] & CL[t] & np.isfinite(fast[t]) & np.isfinite(ref[t]))[0]
        if b.size >= 8 and np.std(fast[t, b]) > 1e-12 and np.std(ref[t, b]) > 1e-12:
            s = np.corrcoef(rankdata(fast[t, b]), rankdata(ref[t, b]))[0, 1]
            sp.append(s); flips += (s < 0.99999)
            valmax = max(valmax, float(np.nanmax(np.abs(fast[t, b] - ref[t, b]))))
    ic_ref, n = incic(ref, tgt, mem, CL, rows); ic_led = led[fid]["stage1_stats"]["inc_ic"]
    OUT[f"A{fid}"] = dict(formula=f, rankorder_spearman_min=round(float(np.min(sp)), 6),
                          rankorder_spearman_mean=round(float(np.mean(sp)), 6),
                          anchors_with_rankflip=int(flips), n_anchors=len(sp),
                          perAnchorMaxValDiff=round(valmax, 4),
                          inc_ic_ref=round(ic_ref, 5), inc_ic_ledger=ic_led,
                          inc_ic_diff=round(abs(ic_ref - ic_led), 6),
                          inc_ic_match=bool(abs(ic_ref - ic_led) < 5e-4))
    print(f"A{fid}: rankSpear min {np.min(sp):.6f} flips {flips}/{len(sp)} | valDiff {valmax:.4f} | "
          f"incIC ref {ic_ref:.5f} vs led {ic_led} {'MATCH' if abs(ic_ref-ic_led)<5e-4 else 'MISMATCH'}", flush=True)

# ---- (C) A-group mutual |rank-corr| ----
ids = list(A); mut = {}
for i in range(len(ids)):
    for j in range(i + 1, len(ids)):
        cc = []
        for t in rows:
            b = np.where(mem[t] & CL[t] & np.isfinite(facs[ids[i]][t]) & np.isfinite(facs[ids[j]][t]))[0]
            if b.size >= 8: cc.append(abs(np.corrcoef(rankdata(facs[ids[i]][t, b]), rankdata(facs[ids[j]][t, b]))[0, 1]))
        mut[f"{ids[i]}x{ids[j]}"] = round(float(np.mean(cc)), 3)
OUT["_A_mutual_corr"] = mut
print("A-group mutual |rank-corr|:", mut, flush=True)

# ---- (D) B-group pred-corr vs the 4-leg book (combined) ----
wts = {"king": 0.30, "s2": 0.10, "funding_leg": 0.30, "size_leg": 0.30}
def zc(A_, mem, CL, t, b):
    v = A_[t, b]; return (v - v.mean()) / (v.std() + 1e-9) if v.std() > 1e-9 else np.zeros_like(v)
Bout = {}
for fid, f in B.items():
    fast = dsl.evaluate(dsl.parse(f), ctx)
    cc_book, cc_king = [], []
    for t in rows:
        b = np.where(mem[t] & CL[t] & np.isfinite(fast[t]) & np.isfinite(ctx["king"][t]) & np.isfinite(ctx["s2"][t]))[0]
        if b.size >= 8:
            book = sum(wts[k] * zc(ctx[k], mem, CL, t, b) for k in wts)
            if np.std(book) > 1e-9 and np.std(fast[t, b]) > 1e-9:
                cc_book.append(abs(np.corrcoef(rankdata(fast[t, b]), rankdata(book))[0, 1]))
                cc_king.append(abs(np.corrcoef(rankdata(fast[t, b]), rankdata(ctx["king"][t, b]))[0, 1]))
    Bout[f"B{fid}"] = dict(formula=f, predcorr_vs_4leg_book=round(float(np.mean(cc_book)), 3),
                           predcorr_vs_king=round(float(np.mean(cc_king)), 3),
                           ledger_predcorr_king=led[fid]["stage1_stats"]["pred_corr"]["king"])
    print(f"B{fid}: predcorr vs book {np.mean(cc_book):.3f} vs king {np.mean(cc_king):.3f} (led king {led[fid]['stage1_stats']['pred_corr']['king']})", flush=True)
OUT["_B_predcorr"] = Bout
json.dump(OUT, open("/tmp/0c_b1_step1.json", "w"), indent=1, default=str)
print("SAVED /tmp/0c_b1_step1.json", flush=True)
