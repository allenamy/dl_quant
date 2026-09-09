"""f10v2_legs for the v4 chain, POLICY = pod_legs_ext.py (in-service): OLD rows verbatim from the in-service training legs (f8_ext/data/f10v2_legs.npz:
Z24/ZFD/WL), NEW anchors (v4 axis minus old axis = the 6 anchors of 2026-08-31) built with the same formulas from v4 inputs (v4 members / king v4 PRED / y4s).
Why (AMENDMENT 5): pod_legs_v4.py recomputed WL for ALL rows from a king PRED that has no predictions before 2024 => king seat (= the DL's weight in the
training book) ~0.007 in 2023 vs 0.587 in the in-service legs; the DL then learned from ~half the rows (D2/D3 single-fold receipts, diag_202507.json).
Self-checks: common rows bitwise equal to the in-service legs; new rows finite; WL(new rows) msharpe over the trailing 900 anchors of v4 leg returns."""
import json, os, time, numpy as np
from scipy.stats import rankdata
TGP = os.environ["LEGS_TG"]; MTP = os.environ["LEGS_META"]; PRP = os.environ["LEGS_PRED"]; OUTP = os.environ["LEGS_OUT"]
OLD = np.load("/workspace/f8_ext/data/f10v2_legs.npz", allow_pickle=True); OE = OLD["E_ts"].astype(np.int64); OZ24 = OLD["Z24"]; OZFD = OLD["ZFD"]; OWL = OLD["WL"]   # materialised once
TG = np.load(TGP, allow_pickle=True); PW = np.load("/workspace/data/wide_panel_4h_v3splice.npz", allow_pickle=True); MT = np.load(MTP, allow_pickle=True); PRED = np.load(PRP)
E_ts = TG["E_ts"].astype(np.int64); members = TG["members"]; y4s = TG["y4s"]; nA = len(E_ts); NW = y4s.shape[1]
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}; fe_row = {int(t): i for i, t in enumerate(MT["E_ts"].astype(np.int64))}; old_row = {int(t): i for i, t in enumerate(OE)}
R24 = PW["f_rev_24h"]; FE = PW["f_fund_ema_v1"]
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan); n = ok.sum()
    if n >= 10: out[ok] = rankdata(v[ok]) / max(n - 1, 1) - 0.5
    return out
def build_row(i):
    j = pw_row.get(int(E_ts[i])); m = members[i]; z24 = np.full(NW, np.nan, np.float32); zfd = np.full(NW, np.nan, np.float32)
    if j is not None: z24[m] = xz(-R24[j, m]).astype(np.float32); zfd[m] = xz(FE[j, m]).astype(np.float32)
    return z24, zfd
def leg_ret(i):
    j = pw_row.get(int(E_ts[i])); fi = fe_row.get(int(E_ts[i])); m = members[i]
    if j is None: return None
    kp = PRED[fi, m] if fi is not None else np.full(len(m), np.nan); sc = {"king": kp, "rev24": -R24[j, m], "fund": FE[j, m]}; ok = np.isfinite(y4s[i, m]); out = []
    for leg in ("king", "rev24", "fund"):
        z = np.nan_to_num(xz(sc[leg])); z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0; g = np.abs(z).sum()
        out.append(float((z / g * np.nan_to_num(y4s[i, m], nan=0.0)).sum() * 1e4) if g > 1e-9 else 0.0)
    return out
LRs = []; lr_idx = []
for i in range(nA):
    r = leg_ret(i)
    if r is not None: LRs.append(r); lr_idx.append(i)
LRs = np.array(LRs); pos = {int(i): p for p, i in enumerate(lr_idx)}
def msharpe_w(i):
    p = pos.get(int(i), 0)
    if p < 900: return np.array([1/3, 1/3, 1/3])
    r = LRs[p-900:p].T; shp = r.mean(1) / (r.std(1) + 1e-9); shp = np.maximum(shp, 0.0)
    return shp / shp.sum() if shp.sum() > 0 else np.array([1/3]*3)
Z24o = np.full((nA, NW), np.nan, np.float32); ZFDo = np.full((nA, NW), np.nan, np.float32); WLo = np.full((nA, 3), 1/3, np.float32); n_copy = 0; new_rows = []
for i in range(nA):
    oi = old_row.get(int(E_ts[i]))
    if oi is not None: Z24o[i] = OZ24[oi]; ZFDo[i] = OZFD[oi]; WLo[i] = OWL[oi]; n_copy += 1
    else: z24, zfd = build_row(i); Z24o[i] = z24; ZFDo[i] = zfd; WLo[i] = msharpe_w(i).astype(np.float32); new_rows.append(i)
# self-checks
ci = [i for i in range(nA) if int(E_ts[i]) in old_row]; oi = [old_row[int(E_ts[i])] for i in ci]
assert np.array_equal(Z24o[ci], OZ24[oi], equal_nan=True) and np.array_equal(ZFDo[ci], OZFD[oi], equal_nan=True) and np.array_equal(WLo[ci], OWL[oi]), "old rows not verbatim"
assert all(np.isfinite(WLo[i]).all() for i in new_rows), "new rows WL not finite"
no_panel = [i for i in new_rows if pw_row.get(int(E_ts[i])) is None]   # the v3splice panel ends 2026-08-31 00Z: anchors after it have no rev24/fund row => Z24/ZFD NaN (trainer maps NaN->0; these rows are only ever in the 202608 test fold / refit validation slice)
print(f"new rows without a panel row (Z24/ZFD NaN by construction): {[time.strftime('%F %HZ', time.gmtime(int(E_ts[i]))) for i in no_panel]}", flush=True)
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); wl_by_year = {int(y): WLo[yrs == y].mean(0).round(4).tolist() for y in sorted(set(yrs))}
print(f"legs v4b: old rows verbatim {n_copy}/{nA}; new rows {len(new_rows)} = {[time.strftime('%F %HZ', time.gmtime(int(E_ts[i]))) for i in new_rows]}; WL(new) = {WLo[new_rows].round(3).tolist()}", flush=True)
print("WL mean by year (king, rev24, fund):", wl_by_year, flush=True)
meta = {"note": "v4b: POLICY pod_legs_ext.py — in-service training legs rows verbatim (f8_ext/data/f10v2_legs.npz) + new anchors same formulas with v4 inputs (AMENDMENT 5; replaces pod_legs_v4.py whose all-rows WL had king seat ~0 before 2024)",
        "inputs": {"old_legs": "/workspace/f8_ext/data/f10v2_legs.npz", "targets": TGP, "meta": MTP, "pred": PRP}, "n_copy": n_copy, "new_rows": [int(E_ts[i]) for i in new_rows], "new_rows_without_panel_row": [int(E_ts[i]) for i in no_panel], "wl_by_year": wl_by_year, "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
os.makedirs(os.path.dirname(OUTP), exist_ok=True); np.savez(OUTP, Z24=Z24o, ZFD=ZFDo, WL=WLo, E_ts=E_ts, meta_json=json.dumps(meta)); print("LEGS_V4B_DONE", OUTP, flush=True)
