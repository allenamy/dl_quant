"""§27 终书残差第四腿 @pod: e = y4 − β_t·z_book 逐锚OLS → 慢LGBM双跑 → 四腿书 vs 三腿基线.
判据冻结: Δ全史(b)≥+0.10 且 2025+ 不降 且 双跑全过; 否则第四腿轴关闭.
"""
import json, time
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from scipy.stats import rankdata, spearmanr
MT = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]
names = [str(n) for n in MT["names"]]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
nA = len(E_ts); NW = 829
FEA = np.load("/workspace/data/wide_fea_v2ext.npy")
PW = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True)
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]; R24 = PW["f_rev_24h"]; FE = PW["f_fund_ema_v1"]
SLOW = np.load("/workspace/shadow_bundle/slow_pred_pinned.npy")
keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    n = ok.sum()
    if n >= 10: out[ok] = rankdata(v[ok]) / max(n - 1, 1) - 0.5
    return out
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
# ── 三腿 z_book(msharpe 权重, 与 extweek 同构) ──
LR = {leg: [] for leg in ("king", "rev24", "fund")}
idx = []
for i in range(nA):
    j = pw_row.get(int(E_ts[i]))
    if j is None: continue
    m = members[i]
    sc = {"king": SLOW[i, m], "rev24": -R24[j, m], "fund": FE[j, m]}
    ok = np.isfinite(y4[i, m])
    for leg in LR:
        z = np.nan_to_num(xz(sc[leg]))
        z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0
        g = np.abs(z).sum()
        LR[leg].append(float((z / g * np.nan_to_num(y4[i, m], nan=0.0)).sum() * 1e4) if g > 1e-9 else 0.0)
    idx.append(i)
LRa = {k: np.array(v) for k, v in LR.items()}
pos = {int(i): p for p, i in enumerate(idx)}
def w3_at(i):
    p = pos.get(int(i), 0); look = 900
    if p < look: return np.array([1/3, 1/3, 1/3])
    sl = slice(p - look, p)
    r = np.stack([LRa["king"][sl], LRa["rev24"][sl], LRa["fund"][sl]])
    shp = r.mean(1) / (r.std(1) + 1e-9); shp = np.maximum(shp, 0.0)
    return shp / shp.sum() if shp.sum() > 0 else np.array([1/3, 1/3, 1/3])
ZB = {}
for i in range(nA):
    j = pw_row.get(int(E_ts[i]))
    if j is None: continue
    m = members[i]
    sc = {"king": SLOW[i, m], "rev24": -R24[j, m], "fund": FE[j, m]}
    w3 = w3_at(i)
    ZB[i] = (w3[0] * np.nan_to_num(xz(sc["king"])) + w3[1] * np.nan_to_num(xz(sc["rev24"]))
             + w3[2] * np.nan_to_num(xz(sc["fund"])))
# ── 残差目标: e = y4 − β_t z_book(逐锚OLS), 秩化 ──
rows_X, rows_y, rows_a = [], [], []
for i in range(nA):
    if i not in ZB: continue
    m = members[i]
    yv = y4[i, m]; ok = np.isfinite(yv)
    if ok.sum() < 50: continue
    zb = ZB[i][ok]
    yy = yv[ok].astype(np.float64)
    vz = float(np.var(zb))
    beta = float(np.cov(zb, yy)[0, 1] / vz) if vz > 1e-12 else 0.0
    e = yy - beta * zb
    rr = rankdata(e) / max(len(e) - 1, 1) - 0.5
    rows_X.append(FEA[i, m[ok]][:, keep].astype(np.float32))
    rows_y.append(rr.astype(np.float32)); rows_a.append(np.full(ok.sum(), i, np.int32))
X = np.concatenate(rows_X); Y = np.concatenate(rows_y); A = np.concatenate(rows_a)
YRA = yrs[A]
import lightgbm as lgb
COST = {"b": [(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)],
        "c": [(1.0, 6.0, 0.75), (4.0, 8.0, 0.55), (8.0, 10.0, 0.35)]}
def tier_of(q):
    t = np.full(len(q), 2, np.int8); t[q >= 1e6] = 1; t[q >= 5e6] = 0
    return t
def four_leg_book(RPRED):
    LR4 = {leg: [] for leg in ("king", "rev24", "fund", "resid")}
    idx4 = []
    for i in range(nA):
        j = pw_row.get(int(E_ts[i]))
        if j is None: continue
        m = members[i]
        sc = {"king": SLOW[i, m], "rev24": -R24[j, m], "fund": FE[j, m], "resid": RPRED[i, m]}
        ok = np.isfinite(y4[i, m])
        for leg in LR4:
            z = np.nan_to_num(xz(sc[leg]))
            z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0
            g = np.abs(z).sum()
            LR4[leg].append(float((z / g * np.nan_to_num(y4[i, m], nan=0.0)).sum() * 1e4) if g > 1e-9 else 0.0)
        idx4.append(i)
    LR4a = {k: np.array(v) for k, v in LR4.items()}
    pos4 = {int(i): p for p, i in enumerate(idx4)}
    def w4_at(i):
        p = pos4.get(int(i), 0); look = 900
        if p < look: return np.array([0.25] * 4)
        sl = slice(p - look, p)
        r = np.stack([LR4a[l][sl] for l in ("king", "rev24", "fund", "resid")])
        shp = r.mean(1) / (r.std(1) + 1e-9); shp = np.maximum(shp, 0.0)
        return shp / shp.sum() if shp.sum() > 0 else np.array([0.25] * 4)
    H = np.zeros(NW, np.float64)
    rec = []
    for i in range(nA):
        j = pw_row.get(int(E_ts[i]))
        if j is None: continue
        m = members[i]
        sc = {"king": SLOW[i, m], "rev24": -R24[j, m], "fund": FE[j, m], "resid": RPRED[i, m]}
        w4 = w4_at(i)
        z = sum(w4[k] * np.nan_to_num(xz(sc[l])) for k, l in enumerate(("king", "rev24", "fund", "resid")))
        ok = np.isfinite(y4[i, m])
        qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
        sel = ok & (qv4h >= 2.5e5)
        if sel.sum() < 80: continue
        w = np.where(sel, z, 0.0); w -= w[sel].mean()
        g = np.abs(w).sum()
        if g < 1e-9: continue
        w /= g
        capw = 2.5 / max(int(sel.sum()), 1)
        w = np.clip(w, -capw, capw)
        g2 = np.abs(w).sum()
        if g2 > 1e-9: w /= g2
        tgt = np.zeros(NW); tgt[m] = w
        sm = H + 0.1 * (tgt - H)
        trade = sm - H
        sm = np.where(np.abs(trade) < 2.5e-4, H, sm)
        trade = sm - H
        tr = tier_of(qv4h); tabs = np.abs(trade[m])
        cb = sum(tabs[tr == tt].sum() * (fr * mk + (1 - fr) * tk) for tt, (mk, tk, fr) in enumerate(COST["b"]))
        yv = np.nan_to_num(y4[i, m], nan=0.0)
        fnow = np.nan_to_num(FN[j, m], nan=0.0)
        ivv = IV[j, m]; ivv = np.where(np.isfinite(ivv) & (ivv > 0), ivv, 8.0)
        car = (sm[m] * fnow * (4.0 / ivv)).sum() * 1e4
        rec.append((int(E_ts[i]), float((sm[m] * yv).sum() * 1e4 - car - cb)))
        H = sm
    out = {}
    for yr_min, tag in ((2024, "full"), (2025, "2025p")):
        arr = np.array([n for t, n in rec if time.gmtime(t).tm_year >= yr_min])
        out[tag] = {"mean": round(float(arr.mean()), 3),
                    "sharpe": round(float(arr.mean() / (arr.std() + 1e-12) * np.sqrt(6 * 365)), 2)}
    return out
res = {"runs": []}
for run in (1, 2):
    RPRED = np.full((nA, NW), np.nan, np.float32)
    for YV in (2024, 2025, 2026):
        tr = YRA < YV; te = YRA == YV
        if te.sum() == 0: continue
        g = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63,
                              subsample=0.8, colsample_bytree=0.8, n_jobs=100, verbose=-1).fit(X[tr], Y[tr])
        pv = g.predict(X[te]); a_te = A[te]
        for a in np.unique(a_te):
            s_ = a_te == a; m = members[a]; okm = np.isfinite(y4[a, m])
            RPRED[a, m[okm]] = pv[s_]
    # 逐折 IC 对 y4(可比口径)与对残差目标
    icd = {}
    for YV in (2024, 2025, 2026):
        s_ = yrs == YV
        ics_y, ics_e = [], []
        for i in np.where(s_)[0]:
            if i not in ZB: continue
            m = members[i]
            ok = np.isfinite(y4[i, m]) & np.isfinite(RPRED[i, m])
            if ok.sum() < 40: continue
            ics_y.append(sp(RPRED[i, m], y4[i, m]))
        icd[str(YV)] = round(float(np.nanmean(ics_y)), 4) if ics_y else None
    book = four_leg_book(RPRED)
    # 相关谱
    cors = {}
    smpl = [i for i in range(0, nA, 17) if i in ZB]
    for leg, arrf in (("king", lambda i, m: SLOW[i, m]), ("rev24", lambda i, m: -R24[pw_row[int(E_ts[i])], m]),
                      ("fund", lambda i, m: FE[pw_row[int(E_ts[i])], m])):
        cc = []
        for i in smpl:
            m = members[i]
            cc.append(sp(RPRED[i, m], arrf(i, m)))
        cors[leg] = round(float(np.nanmean(cc)), 3)
    res["runs"].append({"ic_y4": icd, "book4": book, "leg_corr": cors})
    print(f"[run{run}] 残差腿IC(y4口径) {icd} 四腿书 {book} 相关 {cors}", flush=True)
json.dump(res, open("/workspace/resid4.json", "w"), indent=1)
print("RESID4_DONE", flush=True)
