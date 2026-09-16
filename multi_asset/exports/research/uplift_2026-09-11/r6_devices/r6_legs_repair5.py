"""R6 §6.2 WHITELIST variant: repair the 5 dead legs rows (2026-08-31 04Z..20Z).

FINDING (this round, wider than PREREG §1.3 registered): on the incumbent v4 legs
/workspace/f8_v4/data/f10v2_legs.npz the last 5 anchors have Z24 finite 0/400, ZFD finite 0/400 and
WL = [1/3,1/3,1/3] — not merely funding-blind, but EVERY leg score absent and the msharpe seat collapsed to the
un-learned equal-weight prior, because pod_legs_v4b.py's build_row() returns all-NaN when the panel has no row at
that anchor, and the v2ext/v3splice panels end 2026-08-31 00Z while the king/DL axes end 2026-08-31 20Z.
The judge's "08-31 (6)" window and its "EXTENDED ...->2026-08-31 20Z" window both contain those 5 anchors.

The extension gives those anchors a real panel row, so they can be repaired. PREREG §6.2 whitelists exactly this
propagation (5 anchors only). This script produces the REPAIRED variant BESIDE the verbatim-prefix one and reports
the per-anchor delta, so the change is a decision with evidence rather than a silent rewrite of 5 pre-existing rows.
Every other pre-existing row is asserted bitwise unchanged.
"""
import json, os, time, numpy as np, hashlib
from scipy.stats import rankdata
SRC = os.environ["REP_SRC"]; PANEL = os.environ["REP_PANEL"]; TGP = os.environ["REP_TG"]
OUTP = os.environ["REP_OUT"]
import calendar
WL_TS = [calendar.timegm((2026, 8, 31, h, 0, 0)) for h in (4, 8, 12, 16, 20)]   # FIXED: the literal 1787803200 was 2026-08-27 04:00Z, not 2026-08-31 04:00Z
def U(t): return time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda: f.read(1<<24), b""): h.update(c)
    return h.hexdigest()
S = np.load(SRC, allow_pickle=True); PW = np.load(PANEL, allow_pickle=True); TG = np.load(TGP, allow_pickle=True)
E_ts = S["E_ts"].astype(np.int64); Z24 = S["Z24"].copy(); ZFD = S["ZFD"].copy(); WL = S["WL"].copy()
members = TG["members"]; y4s = TG["y4s"]; NW = y4s.shape[1]
assert np.array_equal(TG["E_ts"].astype(np.int64), E_ts), "legs/targets axis mismatch"
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
R24 = PW["f_rev_24h"]; FE = PW["f_fund_ema_v1"]
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan); n = ok.sum()
    if n >= 10: out[ok] = rankdata(v[ok]) / max(n - 1, 1) - 0.5
    return out
# leg returns over the whole axis (same formula as pod_legs_v4b.leg_ret), for the msharpe seat
PRED = np.load(os.environ["REP_PRED"]); MT = np.load(os.environ["REP_META"], allow_pickle=True)
fe_row = {int(t): i for i, t in enumerate(MT["E_ts"].astype(np.int64))}
LRs = []; lr_idx = []
for i in range(len(E_ts)):
    j = pw_row.get(int(E_ts[i]))
    if j is None: continue
    m = members[i]; fi = fe_row.get(int(E_ts[i]))
    kp = PRED[fi, m] if fi is not None else np.full(len(m), np.nan)
    sc = {"king": kp, "rev24": -R24[j, m], "fund": FE[j, m]}; ok = np.isfinite(y4s[i, m]); o = []
    for leg in ("king","rev24","fund"):
        z = np.nan_to_num(xz(sc[leg])); z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0; g = np.abs(z).sum()
        o.append(float((z/g*np.nan_to_num(y4s[i, m], nan=0.0)).sum()*1e4) if g > 1e-9 else 0.0)
    LRs.append(o); lr_idx.append(i)
LRs = np.array(LRs); pos = {int(i): p for p, i in enumerate(lr_idx)}
def msharpe_w(i):
    p = pos.get(int(i), 0)
    if p < 900: return np.array([1/3,1/3,1/3])
    r = LRs[p-900:p].T; shp = r.mean(1)/(r.std(1)+1e-9); shp = np.maximum(shp, 0.0)
    return shp/shp.sum() if shp.sum() > 0 else np.array([1/3]*3)
delta = []
for t in WL_TS:
    i = int(np.searchsorted(E_ts, t)); assert int(E_ts[i]) == t, (t, E_ts[i])
    j = pw_row.get(t); m = members[i]
    before = {"Z24_finite": int(np.isfinite(Z24[i]).sum()), "ZFD_finite": int(np.isfinite(ZFD[i]).sum()), "WL": np.round(WL[i],4).tolist()}
    z24 = np.full(NW, np.nan, np.float32); zfd = np.full(NW, np.nan, np.float32)
    if j is not None:
        z24[m] = xz(-R24[j, m]).astype(np.float32); zfd[m] = xz(FE[j, m]).astype(np.float32)
    Z24[i] = z24; ZFD[i] = zfd; WL[i] = msharpe_w(i).astype(np.float32)
    delta.append({"anchor": U(t), "panel_row_now_exists": j is not None, "before": before,
                  "after": {"Z24_finite": int(np.isfinite(Z24[i]).sum()), "ZFD_finite": int(np.isfinite(ZFD[i]).sum()), "WL": np.round(WL[i],4).tolist()}})
    print(json.dumps(delta[-1]), flush=True)
others = np.array([i for i in range(len(E_ts)) if int(E_ts[i]) not in set(WL_TS)])
assert np.array_equal(S["Z24"][others], Z24[others], equal_nan=True), "a non-whitelisted Z24 row changed"
assert np.array_equal(S["ZFD"][others], ZFD[others], equal_nan=True), "a non-whitelisted ZFD row changed"
assert np.array_equal(S["WL"][others], WL[others], equal_nan=True), "a non-whitelisted WL row changed"
np.savez(OUTP, Z24=Z24, ZFD=ZFD, WL=WL, E_ts=E_ts, meta_json=json.dumps(
    {"note": "PREREG §6.2 whitelist repair of the 5 dead legs rows 2026-08-31 04Z..20Z; every other row bitwise identical to " + SRC,
     "src": SRC, "src_sha256": sha(SRC), "panel": PANEL, "delta": delta,
     "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}))
json.dump({"src": SRC, "out": OUTP, "out_sha256": sha(OUTP), "delta": delta,
           "non_whitelisted_rows_bitwise_unchanged": True, "n_rows": int(len(E_ts))},
          open("/workspace/uplift_2026-09-11/r6/RECEIPT_legs_repair5.json","w"), indent=1)
print("R6_LEGS_REPAIR5_DONE", OUTP, flush=True)
