"""rider_spotsup.py — rider arm inputs (PREREG_allweather §5 amendment): (1) spot-support score matrix for the device copy (SPOTSUP_NPZ: ts = panel ts,
symbols = panel symbols, mat = raw spot/perp 24h quote-volume log-ratio qvr_24h from the A1 shift-0 feature file, NaN elsewhere; the device
rank-transforms it within the anchor's members); (2) interaction table: fund z decile (xz of panel f_fund_ema_v1 within META members, the fund leg
score of the health-check main arm, UMASK_SCOPE=trade) × spot-support tercile (xz of qvr_24h within members; 'none' = no spot score) ->
next-4h accounting return (prod-caliber meta y4 = Π(1+r5)-1 over [E+1,E+48], bps), raw mean and within-anchor demeaned mean, per year, with counts;
plus the top-minus-bottom fund-decile spread per spot tercile per year.
env: A1_NPZ META_IN (v2ext meta, members) META_PROD (meta_newprod, y4 accounting) PANEL_IN OUT_NPZ OUT_JSON
"""
import os, json, time, hashlib
import numpy as np
from scipy.stats import rankdata
SELF = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
A1 = np.load(os.environ["A1_NPZ"], allow_pickle=True); names = [str(n) for n in A1["names"]]; k = names.index("qvr_24h")
MT = np.load(os.environ.get("META_IN", "/workspace/data/wide_fea_v2ext_meta.npz"), allow_pickle=True)
MP = np.load(os.environ.get("META_PROD", "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz"), allow_pickle=True)
PW = np.load(os.environ.get("PANEL_IN", "/workspace/data/wide_panel_4h_v2ext.npz"), allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; assert np.array_equal(A1["E_ts"].astype(np.int64), E_ts)
assert np.array_equal(MP["E_ts"].astype(np.int64), E_ts), "meta_newprod E_ts != v2ext meta E_ts"
y4p = MP["y4"]; FE = PW["f_fund_ema_v1"]; pts = PW["ts"].astype(np.int64); syms = [str(s) for s in PW["symbols"]]
pw_row = {int(t): j for j, t in enumerate(pts)}
Q = np.asarray(A1["F"][:, :, k], np.float32)
mat = np.full((len(pts), len(syms)), np.nan, np.float32)
nskip = 0
for i, t in enumerate(E_ts):
    j = pw_row.get(int(t))
    if j is None: nskip += 1; continue   # META anchors before the panel's first row (138, 2022-01) are skipped by the device too
    mat[j] = Q[i]
print(f"anchors_without_panel_row {nskip}/{len(E_ts)}", flush=True)
np.savez_compressed(os.environ["OUT_NPZ"], ts=pts, symbols=np.array(syms), mat=mat, source=os.environ["A1_NPZ"], column="qvr_24h", self_sha256=SELF)
print(f"SPOTSUP matrix {mat.shape} finite {np.isfinite(mat).mean():.4f} -> {os.environ['OUT_NPZ']}", flush=True)
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 10: out[ok] = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
    return out
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
S = {}; SD = {}; N = {}
for i in range(len(E_ts)):
    j = pw_row.get(int(E_ts[i]))
    if j is None: continue
    m = members[i]; y = y4p[i, m]; ok = np.isfinite(y)
    fz = xz(FE[j, m]); sz = xz(Q[i, m])
    if ok.sum() < 50 or np.isfinite(fz).sum() < 50: continue
    dec = np.floor((fz + 0.5) * 10 - 1e-9).astype(int); dec = np.clip(dec, 0, 9)
    ter = np.where(np.isfinite(sz), np.clip(np.floor((sz + 0.5) * 3 - 1e-9), 0, 2), 3).astype(int)
    yd = y - np.nanmean(y[ok]); yr = str(yrs[i])
    for key, tbl in ((yr, None),):
        S.setdefault(key, np.zeros((10, 4))); SD.setdefault(key, np.zeros((10, 4))); N.setdefault(key, np.zeros((10, 4), int))
        sel = ok & np.isfinite(fz)
        np.add.at(S[key], (dec[sel], ter[sel]), y[sel]); np.add.at(SD[key], (dec[sel], ter[sel]), yd[sel]); np.add.at(N[key], (dec[sel], ter[sel]), 1)
res = {"self_sha256": SELF, "definition": {"fund_z": "xz(f_fund_ema_v1 within META members) decile 0=most negative .. 9=most positive (long side of the live fund leg = +rank)",
       "spot_tercile": "xz(qvr_24h within members) tercile 0=least spot-supported, 2=most; 3=no spot score", "y4": "prod-caliber meta y4 (Π(1+r5)-1), bps; demeaned = minus anchor member mean"},
       "by_year": {}}
for yr in sorted(S):
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = S[yr] / N[yr] * 1e4; dmean = SD[yr] / N[yr] * 1e4
    spread = {["low", "mid", "high", "none"][t]: round(float(dmean[9, t] - dmean[0, t]), 2) if N[yr][9, t] > 100 and N[yr][0, t] > 100 else None for t in range(4)}
    res["by_year"][yr] = {"n": N[yr].tolist(), "mean_bps": np.round(mean, 2).tolist(), "demeaned_bps": np.round(dmean, 2).tolist(), "top_minus_bottom_decile_demeaned_bps": spread}
    print(f"[{yr}] top-bottom fund-decile spread (demeaned bps) by spot tercile: {spread}; n by tercile {N[yr].sum(0).tolist()}", flush=True)
json.dump(res, open(os.environ["OUT_JSON"], "w"), indent=1)
print("RIDER_SPOTSUP_DONE", flush=True)
