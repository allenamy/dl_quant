"""f10v2_legs for the v4 chain: SAME formulas as pod_legs_ext.py (Z24/ZFD rank-z scatter on members; WL = trailing-900 msharpe of
king/rev24/fund leg returns), but ALL rows recomputed from v4 inputs (v4 members, v4 king PRED, v4 y4s) — no 'old rows verbatim'
(that policy served live continuity; a full-retrain quantification must be internally consistent).
Self-check: on anchors outside every hole neighbourhood the recomputed Z24/ZFD must equal the OLD legs bitwise-ish (formula identity)."""
import json, os, time, calendar, numpy as np
from scipy.stats import rankdata
TGP = os.environ["LEGS_TG"]; MTP = os.environ["LEGS_META"]; PRP = os.environ["LEGS_PRED"]; OUTP = os.environ["LEGS_OUT"]
OLD = np.load("/workspace/f8_ext/data/f10v2_legs.npz", allow_pickle=True)
TG = np.load(TGP, allow_pickle=True); PW = np.load("/workspace/data/wide_panel_4h_v3splice.npz", allow_pickle=True); MT = np.load(MTP, allow_pickle=True); PRED = np.load(PRP)
E_ts = TG["E_ts"].astype(np.int64); members = TG["members"]; y4s = TG["y4s"]; nA = len(E_ts); NW = y4s.shape[1]
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}; fe_row = {int(t): i for i, t in enumerate(MT["E_ts"].astype(np.int64))}; old_row = {int(t): i for i, t in enumerate(OLD["E_ts"].astype(np.int64))}
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
Z24o = np.full((nA, NW), np.nan, np.float32); ZFDo = np.full((nA, NW), np.nan, np.float32); WLo = np.full((nA, 3), 1/3, np.float32)
for i in range(nA):
    z24, zfd = build_row(i); Z24o[i] = z24; ZFDo[i] = zfd; WLo[i] = msharpe_w(i).astype(np.float32)
# self-check: formula identity vs OLD legs outside hole neighbourhoods
H = [(calendar.timegm((2022,2,26,0,0,0)), calendar.timegm((2022,4,20,0,0,0))), (calendar.timegm((2026,8,12,0,0,0)), 2**40)]
def far(t): return not any(lo - 4*3600 <= t <= hi for lo, hi in H)
chk = [i for i in range(nA) if int(E_ts[i]) in old_row and far(int(E_ts[i]))][-300:]
OZ24 = OLD["Z24"]; OZFD = OLD["ZFD"]; OWL = OLD["WL"]   # materialise once (NpzFile[key] in a loop re-reads the array every access)
ex24 = []; exfd = []; wl = []
for i in chk:
    oi = old_row[int(E_ts[i])]
    for new, old, acc in ((Z24o[i], OZ24[oi], ex24), (ZFDo[i], OZFD[oi], exfd)):
        ok = np.isfinite(new) & np.isfinite(old); acc.append(float(np.mean(np.abs(new[ok] - old[ok]) < 1e-6)) if ok.sum() else np.nan)
    wl.append(float(np.abs(WLo[i] - OWL[oi]).max()))
e24, efd, wmax = float(np.nanmean(ex24)), float(np.nanmean(exfd)), float(np.max(wl))
print(f"selfcheck (300 anchors outside hole neighbourhoods) Z24 exact {e24:.4f} ZFD exact {efd:.4f} | WL max|Δ| vs old {wmax:.4f} (king PRED generation differs; reported)", flush=True)
assert e24 >= 0.999 and efd >= 0.999, "legs formula identity FAIL"
meta = {"note": "v4: all rows recomputed (v4 members / v4 king PRED / v4 y4s); formulas verbatim pod_legs_ext.py", "inputs": {"targets": TGP, "meta": MTP, "pred": PRP}, "selfcheck": {"z24_exact": e24, "zfd_exact": efd, "wl_maxdiff_vs_old": wmax}, "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
os.makedirs(os.path.dirname(OUTP), exist_ok=True); np.savez(OUTP, Z24=Z24o, ZFD=ZFDo, WL=WLo, E_ts=E_ts, meta_json=json.dumps(meta)); print("LEGS_V4_DONE", OUTP, flush=True)
