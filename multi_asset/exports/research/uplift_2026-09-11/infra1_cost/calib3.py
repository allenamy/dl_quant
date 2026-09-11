#!/usr/bin/env python3
"""INFRA-1 step 2: calibrate a liquidity-dependent replay cost model from live fills.
Sign: positive = cost. Outputs tier statistics + regressions; writes calib_receipt.json."""
import json, time, sys, numpy as np
from collections import defaultdict
BASE = "/workspace/uplift_2026-09-11/infra1_cost"
R = json.load(open(f"{BASE}/fill_cost_rows.json")); rows = R["rows"]
P = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True)
M = np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz", allow_pickle=True)
psym = [str(s) for s in P["symbols"]]; sidx = {s: i for i, s in enumerate(psym)}
E = M["E_ts"].astype(np.int64); qvk = M["qvk"]; erow = {int(t): i for i, t in enumerate(E)}
pts = P["ts"].astype(np.int64); prow = {int(t): i for i, t in enumerate(pts)}
VOL = np.asarray(P["f_vol_7d"], float)
QV = np.expm1(np.clip(qvk, 0, 30)) * 48.0           # (nA,829) 4h quote volume USDT
LAST = np.full(len(psym), np.nan)                    # last finite qv4h per symbol (panel end) for carry-forward
for c in range(len(psym)):
    v = QV[:, c]; f = np.where(np.isfinite(v))[0]
    if len(f): LAST[c] = np.nanmedian(v[max(0, len(v) - 42):][np.isfinite(v[max(0, len(v) - 42):])]) if np.isfinite(v[-42:]).any() else v[f[-1]]
g4 = lambda ts: int(np.floor(ts / 14400.0) * 14400)
nex = 0
for r in rows:
    k = g4(r["anchor_ts"]); r["g4"] = k
    c = sidx.get(r["symbol"]); j = erow.get(k); pj = prow.get(k)
    r["qv4h"] = None; r["qv_src"] = None; r["vol7d"] = None
    if c is None: continue
    if j is not None and np.isfinite(QV[j, c]): r["qv4h"] = float(QV[j, c]); r["qv_src"] = "panel"
    elif np.isfinite(LAST[c]): r["qv4h"] = float(LAST[c]); r["qv_src"] = "carryfwd"; nex += 1
    if pj is not None and np.isfinite(VOL[pj, c]): r["vol7d"] = float(VOL[pj, c])
print(f"rows {len(rows)}  carry-forward qv4h rows {nex}")

def tier(q): return 0 if q >= 5e6 else (1 if q >= 1e6 else 2)
TN = ["tier0_qv4h>=5e6", "tier1_qv4h>=1e6", "tier2_rest"]

def agg(sel, label):
    A = [defaultdict(float) for _ in range(3)]
    for r in rows:
        if r.get("qv4h") is None or not sel(r): continue
        t = tier(r["qv4h"]); a = A[t]
        a["intent_a1"] += r["intent_a1"]; a["intent_all"] += r["intended"]; a["skipped"] += r["skipped"]
        a["n_rows"] += 1
        for tag in ("mk", "tk", "pf"):
            nz = r[f"{tag}_nz"]; a[f"{tag}_nz"] += nz; a[f"{tag}_fee"] += r[f"{tag}_fee"]; a[f"{tag}_n"] += r[f"{tag}_n"]
            if r[f"{tag}_slip_cov"] > 0:
                a[f"{tag}_slipw"] += r[f"{tag}_slip_bps"] * r[f"{tag}_slip_cov"]; a[f"{tag}_slipn"] += r[f"{tag}_slip_cov"]
            if r[f"{tag}_mo_cov"] > 0:
                a[f"{tag}_mow"] += r[f"{tag}_mo_bps"] * r[f"{tag}_mo_cov"]; a[f"{tag}_mon"] += r[f"{tag}_mo_cov"]
        if r.get("spread_bps") is not None and r["intent_a1"] > 0:
            a["spw"] += r["spread_bps"] * r["intent_a1"]; a["spn"] += r["intent_a1"]
        if r["intent_a1"] > 0: a["part_w"] += (r["intent_a1"] / r["qv4h"]) * r["intent_a1"]
    out = []
    for t in range(3):
        a = A[t]
        f = lambda k: a[k]
        filled = a["mk_nz"] + a["tk_nz"] + a["pf_nz"]
        d = dict(tier=TN[t], n_rows=int(a["n_rows"]), n_fills=int(a["mk_n"] + a["tk_n"] + a["pf_n"]),
                 intent_a1=a["intent_a1"], intent_all=a["intent_all"], skipped=a["skipped"], filled=filled)
        for tag in ("mk", "tk", "pf"):
            nz = a[f"{tag}_nz"]
            d[f"{tag}_nz"] = nz
            d[f"{tag}_fee_bps"] = (a[f"{tag}_fee"] / nz * 1e4) if nz > 0 else None
            d[f"{tag}_slip_bps"] = (a[f"{tag}_slipw"] / a[f"{tag}_slipn"]) if a[f"{tag}_slipn"] > 0 else None
            d[f"{tag}_slip_cov"] = (a[f"{tag}_slipn"] / nz) if nz > 0 else None
            d[f"{tag}_mo_bps"] = (a[f"{tag}_mow"] / a[f"{tag}_mon"]) if a[f"{tag}_mon"] > 0 else None
        d["maker_share_filled"] = a["mk_nz"] / filled if filled > 0 else None
        d["fill_rate_vs_intent_a1"] = filled / a["intent_a1"] if a["intent_a1"] > 0 else None
        d["maker_fill_rate_vs_intent_a1"] = a["mk_nz"] / a["intent_a1"] if a["intent_a1"] > 0 else None
        d["spread_bps"] = (a["spw"] / a["spn"]) if a["spn"] > 0 else None
        d["participation_wavg"] = (a["part_w"] / a["intent_a1"]) if a["intent_a1"] > 0 else None
        out.append(d)
    print(f"\n===== {label} =====")
    for d in out:
        print(f"{d['tier']:<18} rows{d['n_rows']:>7} fills{d['n_fills']:>7} intentA1 {d['intent_a1']:>11.0f} filled {d['filled']:>11.0f}"
              f" fillrate {d['fill_rate_vs_intent_a1'] if d['fill_rate_vs_intent_a1'] is None else round(d['fill_rate_vs_intent_a1'],4)}")
        print(f"   fee bps mk {d['mk_fee_bps'] and round(d['mk_fee_bps'],4)} tk {d['tk_fee_bps'] and round(d['tk_fee_bps'],4)} pf {d['pf_fee_bps'] and round(d['pf_fee_bps'],4)}"
              f" | maker_share_filled {d['maker_share_filled'] and round(d['maker_share_filled'],4)}")
        print(f"   slip_vs_anchor bps mk {d['mk_slip_bps'] and round(d['mk_slip_bps'],3)} (cov {d['mk_slip_cov'] and round(d['mk_slip_cov'],2)})"
              f" tk {d['tk_slip_bps'] and round(d['tk_slip_bps'],3)} pf {d['pf_slip_bps'] and round(d['pf_slip_bps'],3)}")
        print(f"   markout60 cost bps mk {d['mk_mo_bps'] and round(d['mk_mo_bps'],3)} tk {d['tk_mo_bps'] and round(d['tk_mo_bps'],3)}"
              f" | spread@submit {d['spread_bps'] and round(d['spread_bps'],3)} | participation {d['participation_wavg'] and round(d['participation_wavg'],7)}")
    return out

allr = agg(lambda r: True, "ALL 2026-08-01 -> 09-11 (243 anchors; Sept qv4h carried forward)")
panel = agg(lambda r: r["qv_src"] == "panel", "PANEL-JOINED ONLY 2026-08-01 -> 08-31 (no extrapolation)")
combo = agg(lambda r: r["anchor_ts"] >= 1787716800.0, "COMBO ERA 2026-08-26 04Z ->")
json.dump(dict(all=allr, panel_only=panel, combo=combo, n_dedup=R["n_dedup"], n_raw=R["n_raw"]),
          open(f"{BASE}/tier_stats.json", "w"), indent=1)
print("\nWROTE tier_stats.json")
