"""§26 2024 弱年归因(定性, 无判据): 逐年六拆解."""
import json, time
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from scipy.stats import rankdata
MT = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
nA = len(E_ts); NW = 829
PW = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True)
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]; R24 = PW["f_rev_24h"]; FE = PW["f_fund_ema_v1"]
SLOW = np.load("/workspace/shadow_bundle/slow_pred_pinned.npy")
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    n = ok.sum()
    if n >= 10: out[ok] = rankdata(v[ok]) / max(n - 1, 1) - 0.5
    return out
LEG = {leg: [] for leg in ("king", "rev24", "fund")}
CAR, DISP, TS = [], [], []
for i in range(nA):
    j = pw_row.get(int(E_ts[i]))
    if j is None: continue
    m = members[i]
    sc = {"king": SLOW[i, m], "rev24": -R24[j, m], "fund": FE[j, m]}
    ok = np.isfinite(y4[i, m])
    if ok.sum() < 50: continue
    for leg in LEG:
        z = np.nan_to_num(xz(sc[leg]))
        z = np.where(ok, z, 0.0); z -= z[ok].mean()
        g = np.abs(z).sum()
        LEG[leg].append(float((z / g * np.nan_to_num(y4[i, m], nan=0.0)).sum() * 1e4) if g > 1e-9 else 0.0)
    ivv = IV[j, m]; ivv = np.where(np.isfinite(ivv) & (ivv > 0), ivv, 8.0)
    CAR.append(float(np.nanmean(np.abs(np.nan_to_num(FN[j, m]) * (4 / ivv))) * 1e4))
    DISP.append(float(np.nanstd(y4[i, m][ok]) * 1e4))
    TS.append(int(E_ts[i]))
TS = np.array(TS); Y = np.array([time.gmtime(t).tm_year for t in TS])
out = {}
for yv in (2023, 2024, 2025, 2026):
    s_ = Y == yv
    if s_.sum() < 100: continue
    legs = {leg: np.array(LEG[leg])[s_] for leg in LEG}
    r = np.stack([legs[l] for l in ("king", "rev24", "fund")])
    C = np.corrcoef(r)
    out[str(yv)] = {
        "leg_sharpe": {l: round(float(legs[l].mean() / (legs[l].std() + 1e-12) * np.sqrt(6*365)), 2) for l in legs},
        "leg_mean_bps": {l: round(float(legs[l].mean()), 3) for l in legs},
        "corr_kr": round(float(C[0, 1]), 3), "corr_kf": round(float(C[0, 2]), 3), "corr_rf": round(float(C[1, 2]), 3),
        "abs_carry_bps": round(float(np.array(CAR)[s_].mean()), 3),
        "xsec_disp_bps": round(float(np.array(DISP)[s_].mean()), 1),
        "n": int(s_.sum())}
    print(f"[{yv}] {json.dumps(out[str(yv)], ensure_ascii=False)}", flush=True)
json.dump(out, open("/workspace/attrib_2024.json", "w"), indent=1)
print("ATTRIB_DONE", flush=True)
