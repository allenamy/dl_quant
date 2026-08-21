"""终验包: ① 慢书 8h cadence 臂(D清单①) ② 书级 Q4 最坏五分位(判据补完) ③ 在役形三腿复刻(D清单④, 近似标签).
全 CPU, 同引擎同成本(b=深度修正), 2025-26 主判.
"""
import json, time
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from scipy.stats import rankdata
MT = np.load("/workspace/data/wide_fea_v1_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
nA = len(E_ts); NW = 829
PW = np.load("/workspace/data/wide_panel_4h_v1.npz", allow_pickle=True)
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
FN = PW["f_fund_now"]; FE = PW["f_fund_ema"]; R24 = PW["f_rev_24h"]
psyms = list(PW["symbols"]); BTC_P = psyms.index("BTCUSDT"); BVOL = PW["f_vol_7d"][:, BTC_P]
SLOW = np.load("/workspace/exports_train/slow_lgbm_pred.npy")
KM = np.load("/workspace/exports_train/kcurve_meta_K400_s42.npz", allow_pickle=True)
k_ts = KM["E_ts"].astype(np.int64); k_yrs = KM["yrs"]; krow = {int(t): j for j, t in enumerate(k_ts)}
KING = None
for YV in (2023, 2024, 2025, 2026):
    p = np.load(f"/workspace/exports_train/kcurve_pred_K400_s42_{YV}.npy")
    if KING is None: KING = np.full_like(p, np.nan)
    KING[np.where(k_yrs == YV)[0]] = p[np.where(k_yrs == YV)[0]]
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    n = ok.sum()
    if n >= 10: out[ok] = rankdata(v[ok]) / max(n - 1, 1) - 0.5
    return out
COST_B = [(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)]
def tier_of(q):
    t = np.full(len(q), 2, np.int8); t[q >= 1e6] = 1; t[q >= 5e6] = 0
    return t
def build_w(score_fn, K=None):
    Wt = np.zeros((nA, NW), np.float32); okA = np.zeros(nA, bool)
    for i in range(nA):
        j = pw_row.get(int(E_ts[i]))
        if j is None: continue
        m = members[i]
        s = score_fn(i, j, m)
        if s is None: continue
        ok = np.isfinite(s) & np.isfinite(y4[i, m])
        qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
        sel = ok & (qv4h >= 2.5e5)
        if sel.sum() < 80: continue
        if K and sel.sum() > K:
            ord_ = np.argsort(-qv4h)
            kk = np.zeros(len(m), bool); cnt = 0
            for idx in ord_:
                if sel[idx]: kk[idx] = True; cnt += 1
                if cnt >= K: break
            sel = kk
        z = xz(np.where(sel, s, np.nan))
        w = np.nan_to_num(z); w -= w[sel].mean()
        g = np.abs(w).sum()
        if g < 1e-9: continue
        w /= g
        capw = 2.5 / max(sel.sum(), 1)
        w = np.clip(w, -capw, capw)
        g2 = np.abs(w).sum()
        if g2 > 1e-9: w /= g2
        Wt[i, m] = w; okA[i] = True
    return Wt, okA
def run_book(Wt, okA, al, bd, cadence=1):
    H = np.zeros(NW, np.float64)
    out_rows = []
    step = 0
    for i in range(nA):
        if not okA[i]: continue
        step += 1
        if cadence > 1 and (step % cadence) != 1:
            sm = H
        else:
            tgt = Wt[i].astype(np.float64)
            sm = H + al * (tgt - H)
            trade0 = sm - H
            sm = np.where(np.abs(trade0) < bd, H, sm)
        trade = sm - H
        j = pw_row[int(E_ts[i])]
        m = members[i]
        qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
        tr = tier_of(qv4h); tabs = np.abs(trade[m])
        cb = 0.0
        for tt in range(3):
            s_ = tr == tt
            mk, tk, fr = COST_B[tt]
            cb += tabs[s_].sum() * (fr * mk + (1 - fr) * tk)
        yv = np.nan_to_num(y4[i, m], nan=0.0)
        gross = float((sm[m] * yv).sum() * 1e4)
        fnow = np.nan_to_num(FN[j, m], nan=0.0)
        carry = float(-(sm[m] * fnow).sum() / 2 * 1e4)
        out_rows.append((i, gross, carry, cb, float(tabs.sum()), float(BVOL[j])))
        H = sm
    return out_rows
def summarize(rows, tag):
    arr = np.array([(g + c - cb) for _, g, c, cb, _, _ in rows])
    idx = np.array([i for i, *_ in rows])
    sub = yrs[idx] >= 2025
    n25 = arr[sub]
    sh = float(n25.mean() / (n25.std() + 1e-12) * np.sqrt(6 * 365))
    bv = np.array([b for *_, b in rows])[sub]
    q80 = np.nanquantile(bv, 0.8)
    q4 = n25[bv >= q80]
    shq4 = float(q4.mean() / (q4.std() + 1e-12) * np.sqrt(6 * 365))
    by = {}
    for y in (2025, 2026):
        yr_ = arr[(yrs[idx] == y)]
        by[y] = round(float(yr_.mean()), 3)
    print(f"[{tag}] 净{n25.mean():.3f} 夏普{sh:.2f} | Q4净{q4.mean():.3f} 夏普{shq4:.2f} | 逐年{by}", flush=True)
    return {"net": round(float(n25.mean()), 3), "sharpe": round(sh, 2), "q4_sharpe": round(shq4, 2), "by_year": by}
res = {}
Ws, okS = build_w(lambda i, j, m: SLOW[i, m])
res["slow_4h"] = summarize(run_book(Ws, okS, 0.1, 2.5e-4, 1), "慢书4h(基线)")
res["slow_8h"] = summarize(run_book(Ws, okS, 0.18, 2.5e-4, 2), "慢书8h cadence(α0.18≈等效)")
def replica(i, j, m):
    jk = krow.get(int(E_ts[i]))
    kg = KING[jk, m] if jk is not None else None
    if kg is None: return None
    z = 0.45 * np.nan_to_num(xz(kg)) + 0.35 * np.nan_to_num(xz(-R24[j, m])) + 0.20 * np.nan_to_num(xz(FE[j, m]))
    return z
Wr, okR = build_w(replica, K=110)
res["inservice_form_K110"] = summarize(run_book(Wr, okR, 0.05, 2.5e-4, 1), "在役形三腿复刻K110(近似)")
Wr4, okR4 = build_w(replica, K=None)
res["inservice_form_K400"] = summarize(run_book(Wr4, okR4, 0.1, 2.5e-4, 1), "在役形三腿宽版K400")
json.dump(res, open("/workspace/final_pack.json", "w"), indent=1)
print("FINAL_PACK_DONE", flush=True)
