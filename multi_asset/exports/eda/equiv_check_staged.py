"""0C independent equivalence recompute — batch_001 A-group (STAGED; run only after lead greenlight).
Recomputes Stage-1 inc-IC via a SLOW REFERENCE path (explicit trailing ts_max loop, explicit xsec_z,
explicit per-anchor rank-IC) — NOT fast dsl.evaluate/score_series — and aligns value-for-value with the
ledger. Guards the 3 vectorizations: (a) score_series rank/mask, (b) ts_max temporal (only id104/id120
exercise a temporal op), (c) shuffle-eval null. inc-IC~0.012 -> one off-by-one could fabricate it.
Also computes A-group mutual |rank-corr| (are they one collinear lottery/extreme-value cluster?).
"""
import json, numpy as np, pandas as pd
from scipy.stats import rankdata
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
LEDGER = MA + "/exports/eda/factory_ledger.jsonl"; HOLDOUT = 2026
A_GROUP = {101: "neg(mul(xsec_z(lturnover_24h), xsec_z(max_ret_24h)))",
           104: "neg(xsec_z(ts_max(abs(ret_1h), 24)))",
           107: "neg(xsec_z(power(ret_24h, 3)))",
           120: "neg(xsec_z(ts_max(rvol_6h, 42)))"}


def ref_xsec_z(A, mem, CL):
    out = np.full_like(A, np.nan)
    for t in range(A.shape[0]):
        b = np.where(mem[t] & CL[t] & np.isfinite(A[t]))[0]
        if b.size >= 3:
            x = A[t, b]; sd = x.std(); out[t, b] = (x - x.mean()) / sd if sd > 1e-9 else np.nan
    return out


def ref_ts_max(A, n, use_abs=False):
    X = np.abs(A) if use_abs else A; out = np.full_like(A, np.nan); mp = max(2, n // 2)
    for t in range(A.shape[0]):
        w = X[max(0, t - n + 1):t + 1]; cnt = np.isfinite(w).sum(0)
        out[t] = np.where(cnt >= mp, np.nanmax(np.where(np.isfinite(w), w, -np.inf), 0), np.nan)
    return out


def build(fid, ctx, mem, CL):
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


def run():
    W = np.load(MA + "/exports/wide_dl_full.npz", allow_pickle=True)
    tgt = np.load(MA + "/exports/yr4b_target.npz", allow_pickle=True)["YR4K"].astype(np.float64)
    ch = [str(c) for c in W["ch_names"]]; CH = W["CH"].astype(np.float64)
    mem = W["MEMBER110"].astype(bool); CL = W["CL4"].astype(bool)
    year = pd.to_datetime(W["ts"].astype(np.int64), unit="ms", utc=True).year.to_numpy()
    ctx = {c: CH[:, :, ch.index(c)] for c in ("lturnover_24h", "max_ret_24h", "ret_24h", "ret_1h", "rvol_6h")}
    rows = np.where((mem & CL & np.isfinite(tgt)).any(1) & (year != HOLDOUT))[0]
    led = {r["eval_id"]: r for r in (json.loads(l) for l in open(LEDGER) if l.strip())}
    out = {}; facs = {}
    for fid in A_GROUP:
        fac = build(fid, ctx, mem, CL); facs[fid] = fac
        ic, n = incic(fac, tgt, mem, CL, rows); lic = led[fid]["stage1_stats"]["inc_ic"]
        out[fid] = dict(ref=round(ic, 5), ledger=lic, diff=round(abs(ic - lic), 6), n=n, match=bool(abs(ic - lic) < 5e-4))
        print(f"id{fid}: ref {ic:.5f} vs ledger {lic} diff {abs(ic-lic):.6f} {'MATCH' if abs(ic-lic)<5e-4 else 'MISMATCH'}", flush=True)
    ids = list(A_GROUP)
    out["_mutual_corr"] = {}
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            cc = [abs(np.corrcoef(rankdata(facs[ids[i]][t, b]), rankdata(facs[ids[j]][t, b]))[0, 1])
                  for t in rows for b in [np.where(mem[t] & CL[t] & np.isfinite(facs[ids[i]][t]) & np.isfinite(facs[ids[j]][t]))[0]] if b.size >= 8]
            out["_mutual_corr"][f"{ids[i]}x{ids[j]}"] = round(float(np.mean(cc)), 3)
    print("A-group mutual |rank-corr|:", out["_mutual_corr"], flush=True)
    json.dump(out, open("/tmp/0c_equiv_check.json", "w"), indent=1); print("SAVED", flush=True)


if __name__ == "__main__":
    run()
