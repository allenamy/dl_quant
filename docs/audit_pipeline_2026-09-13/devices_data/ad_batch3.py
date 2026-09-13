#!/usr/bin/env python3
"""ad_batch3.py -- AUDIT_DATA 2026-09-13, device G (pod2, CPU, READ-ONLY). Is the DL-feature funding coverage a look-ahead?

F1/F2 (ad_batch2) showed: the splice panel the DL chain reads carries funding only for the symbols of the v1 canonical panel, and the DL
training features (dlw_v4raw dlw_fea82 fund_ema/fund_now) are 0.0 on 13.9-34.2 % of member pairs whose funding exists in the 829-name panel.
If that symbol set is a LATE list (the 2026-08 live pins), then "funding feature is non-zero" at a 2022 anchor encodes future survival.
G1  set identity: symbols with any finite f_fund_ema in wide_panel_4h_v1.npz  vs  /workspace/live_pins.json symbols_live.
G2  information content of the availability flag A = isfinite(v3splice f_fund_ema) at the anchor, restricted to DL member pairs whose
    funding IS finite in v2ext (so A isolates list membership, not true absence): per anchor with >= 20 names in each group,
    Spearman(A, y4s) and the demeaned forward-return gap mean(y4s | A=1) - mean(y4s | A=0) in bps; per-year mean, SE over anchors, t.
    (y4s = dlw_v4raw RAW Pi(1+r)-1 over rows [E+1, E+48] -- the accounting target.)
G3  who the A=0 names are: share never trading again within 90 days of the anchor; share inside the CRYPTO mask.
Usage: python3 ad_batch3.py <out_receipt.json>
"""
import os, sys, json, time, hashlib
import numpy as np
from scipy.stats import spearmanr

ENV_WHITELIST = set()
os.nice(19)
OUT = sys.argv[1]
W = "/workspace"
V1 = f"{W}/data/wide_panel_4h_v1.npz"; V2 = f"{W}/data/wide_panel_4h_v2ext.npz"; V3 = f"{W}/data/wide_panel_4h_v3splice.npz"
TG = f"{W}/dlw_v4raw/data/dlw_targets.npz"; PINS = f"{W}/live_pins.json"; UMASK = f"{W}/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"
CACHE = f"{W}/data/dlnative_5m_wide829_f16_holefix2.npz"
def utc(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
def yr(t): return time.gmtime(int(t)).tm_year
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()
assert not (ENV_WHITELIST - set(os.environ))
T0 = time.time()
rec = {"device": "ad_batch3.py", "self_sha256": sha(os.path.abspath(__file__)), "inputs": {p: sha(p) for p in (V1, V2, V3, TG, PINS, UMASK)}, "numpy": np.__version__}
P1 = np.load(V1, allow_pickle=True); syms = [str(s) for s in P1["symbols"]]
v1_fund = set(syms[j] for j in np.where(np.isfinite(P1["f_fund_ema"]).any(0))[0])
pins = json.load(open(PINS)); live = set(pins["symbols_live"])
rec["G1_v1_funding_symbols_vs_live_pins"] = {"v1_funding_symbols": len(v1_fund), "live_pins_symbols": len(live), "identical": v1_fund == live,
                                             "in_v1_not_live": sorted(v1_fund - live)[:30], "live_not_in_v1": sorted(live - v1_fund)[:30]}
print("G1", rec["G1_v1_funding_symbols_vs_live_pins"]["identical"], len(v1_fund), len(live), flush=True)
P2 = np.load(V2, allow_pickle=True); P3 = np.load(V3, allow_pickle=True)
t2 = P2["ts"].astype(np.int64); t3 = P3["ts"].astype(np.int64); pos2 = {int(t): i for i, t in enumerate(t2)}; pos3 = {int(t): i for i, t in enumerate(t3)}
FE2 = np.asarray(P2["f_fund_ema"]); FE3 = np.asarray(P3["f_fund_ema"])
T = np.load(TG, allow_pickle=True); E = T["E_ts"].astype(np.int64); MEM = T["members"]; Y = T["y4s"]
Z = np.load(CACHE, allow_pickle=True); cts = Z["ts"].astype(np.int64)
d = Z["data"]; f0 = np.isfinite(d[:, :, 0]); del d
last = len(cts) - 1 - np.argmax(f0[::-1], 0); has = f0.any(0); del f0
last_ts = np.where(has, cts[last], -1)
UZ = np.load(UMASK, allow_pickle=True); UTS = {int(t): k for k, t in enumerate(UZ["ts"].astype(np.int64))}; UM = np.asarray(UZ["mask"])
by = {}; g3 = {}
for i, t in enumerate(E):
    j2 = pos2.get(int(t)); j3 = pos3.get(int(t))
    if j2 is None or j3 is None: continue
    m = np.asarray(MEM[i], np.int64); y = Y[i, m].astype(np.float64)
    ok = np.isfinite(FE2[j2, m]) & np.isfinite(y)
    if ok.sum() < 60: continue
    A = np.isfinite(FE3[j3, m])[ok]; yy = y[ok]
    n1, n0 = int(A.sum()), int((~A).sum())
    yk = str(yr(t)); b = by.setdefault(yk, {"anchors": 0, "rho": [], "gap_bps": [], "pairs_A0": 0, "pairs_A1": 0})
    b["pairs_A0"] += n0; b["pairs_A1"] += n1
    mm = m[ok][~A]; gg = g3.setdefault(yk, {"A0_pairs": 0, "A0_never_trades_within_90d": 0, "A0_inside_crypto_mask": 0})
    gg["A0_pairs"] += n0; gg["A0_never_trades_within_90d"] += int((last_ts[mm] < t + 90 * 86400).sum())
    ur = UTS.get(int(t))
    if ur is not None: gg["A0_inside_crypto_mask"] += int(UM[ur, mm].sum())
    if n1 >= 20 and n0 >= 20:
        b["anchors"] += 1; b["rho"].append(float(spearmanr(A.astype(float), yy).correlation))
        dm = yy - yy.mean(); b["gap_bps"].append(float((dm[A].mean() - dm[~A].mean()) * 1e4))
out = {}
for yk, b in sorted(by.items()):
    r = np.array(b["rho"]); g = np.array(b["gap_bps"])
    out[yk] = {"anchors_both_groups_ge20": b["anchors"], "pairs_A1": b["pairs_A1"], "pairs_A0": b["pairs_A0"],
               "mean_spearman": (float(r.mean()) if len(r) else None), "t_spearman": (float(r.mean() / (r.std(ddof=1) / np.sqrt(len(r)))) if len(r) > 2 else None),
               "mean_gap_bps_A1_minus_A0": (float(g.mean()) if len(g) else None), "t_gap": (float(g.mean() / (g.std(ddof=1) / np.sqrt(len(g)))) if len(g) > 2 else None)}
rec["G2_availability_flag_information"] = out; rec["G2_note"] = "t statistics are naive over anchors: the flag is a persistent name attribute, so per-anchor readings are autocorrelated -- descriptive only"; rec["G3_who_are_A0"] = g3
rec["elapsed_s"] = round(time.time() - T0, 1)
json.dump(rec, open(OUT, "w"), indent=1)
print("AD_BATCH3_DONE", json.dumps(out), flush=True)
