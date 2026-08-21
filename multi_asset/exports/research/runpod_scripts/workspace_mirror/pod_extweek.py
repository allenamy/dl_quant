"""extweek 判官: 终形书(slow_s1 × msharpe × K400 × α0.1/b2.5e-4)在 ext 数据上的五臂对决.
判据预冻结(P3 §20, 先于看数): ① 基线复现守卫: 旧窗(≤旧面板末锚)全史(2024+)夏普 ∈ 3.41±0.10,
违者 STOP_PIPELINE_DRIFT 退出不判臂; ② fundfix v1(normfix单位): Δ全史夏普 ≥ −0.05 ⇒ 采纳(平手正确性胜),
< −0.3 ⇒ 红旗"因子吃单位伪影"; ③ carry_fix(rate×4/iv): 记账更正, 无论方向替换头条, 报差值;
④ 真OOS周(旧末锚之后): 只判符号与量级, n~30 锚无统计力, 影子闸照旧.
臂: base(v0,half) / v1half / v2half / v0iv / v1iv; 窗口: full(2024+) + 2025+; 情景 b/c.
"""
import json, time
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from scipy.stats import rankdata, spearmanr
MT = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
nA = len(E_ts); NW = 829
PW = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True)
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]; R24 = PW["f_rev_24h"]
FE_V = {"v0": PW["f_fund_ema"], "v1": PW["f_fund_ema_v1"], "v2": PW["f_fund_ema_v2"]}
SLOW = np.load("/workspace/exports_train/slow_lgbm_pred_ext.npy")
MT0 = np.load("/workspace/data/wide_fea_v1_meta.npz", allow_pickle=True)
OLD_MAX_TS = int(MT0["E_ts"].astype(np.int64).max())
print(f"锚 {nA} 旧末锚 {time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime(OLD_MAX_TS))}", flush=True)

def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    n = ok.sum()
    if n >= 10: out[ok] = rankdata(v[ok]) / max(n - 1, 1) - 0.5
    return out
COST = {"b": [(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)],
        "c": [(1.0, 6.0, 0.75), (4.0, 8.0, 0.55), (8.0, 10.0, 0.35)]}
def tier_of(q):
    t = np.full(len(q), 2, np.int8); t[q >= 1e6] = 1; t[q >= 5e6] = 0
    return t

def leg_scores(i, FE):
    j = pw_row.get(int(E_ts[i]))
    if j is None: return None
    m = members[i]
    return {"king": SLOW[i, m], "rev24": -R24[j, m], "fund": FE[j, m]}, m

def build_leg_rets(FE):
    LR = {leg: [] for leg in ("king", "rev24", "fund")}
    idx = []
    for i in range(nA):
        ls = leg_scores(i, FE)
        if ls is None: continue
        sc, m = ls
        ok = np.isfinite(y4[i, m])
        for leg in LR:
            z = np.nan_to_num(xz(sc[leg]))
            z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0
            g = np.abs(z).sum()
            LR[leg].append(float((z / g * np.nan_to_num(y4[i, m], nan=0.0)).sum() * 1e4) if g > 1e-9 else 0.0)
        idx.append(i)
    return {k: np.array(v) for k, v in LR.items()}, {int(i): p for p, i in enumerate(idx)}

def msharpe_w(LR, i_pos):
    look = 900
    if i_pos < look: return (1/3, 1/3, 1/3)
    sl = slice(i_pos - look, i_pos)
    r = np.stack([LR["king"][sl], LR["rev24"][sl], LR["fund"][sl]])
    shp = r.mean(1) / (r.std(1) + 1e-9); shp = np.maximum(shp, 0.0)
    w = shp / shp.sum() if shp.sum() > 0 else np.array([1/3]*3)
    return tuple(w)

def build_targets(FE, weight_fn):
    Wt = np.zeros((nA, NW), np.float32); okA = np.zeros(nA, bool)
    for i in range(nA):
        ls = leg_scores(i, FE)
        if ls is None: continue
        sc, m = ls
        wk, wr, wf = weight_fn(i)
        zk = xz(sc["king"]); zr = xz(sc["rev24"]); zf = xz(sc["fund"])
        z = wk * np.nan_to_num(zk) + wr * np.nan_to_num(zr) + wf * np.nan_to_num(zf)
        ok = np.isfinite(y4[i, m])
        qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
        sel = ok & (qv4h >= 2.5e5)
        if sel.sum() < 80: continue
        w = np.where(sel, z, 0.0); w -= w[sel].mean()
        g = np.abs(w).sum()
        if g < 1e-9: continue
        w /= g
        capw = 2.5 / max(sel.sum(), 1)
        w = np.clip(w, -capw, capw)
        g2 = np.abs(w).sum()
        if g2 > 1e-9: w /= g2
        Wt[i, m] = w; okA[i] = True
    return Wt, okA

def replay(Wt, okA, scen, carry):
    H = np.zeros(NW, np.float64)
    rec = []  # (ts, net)
    for i in range(nA):
        if not okA[i]: continue
        tgt = Wt[i].astype(np.float64)
        sm = H + 0.1 * (tgt - H)
        trade = sm - H
        sm = np.where(np.abs(trade) < 2.5e-4, H, sm)
        trade = sm - H
        j = pw_row[int(E_ts[i])]
        m = members[i]
        qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
        tr = tier_of(qv4h); tabs = np.abs(trade[m])
        cb = 0.0
        for tt in range(3):
            s_ = tr == tt
            mk, tk, fr = COST[scen][tt]
            cb += tabs[s_].sum() * (fr * mk + (1 - fr) * tk)
        yv = np.nan_to_num(y4[i, m], nan=0.0)
        fnow = np.nan_to_num(FN[j, m], nan=0.0)
        if carry == "half":
            car = (sm[m] * fnow).sum() / 2 * 1e4
        else:
            ivv = IV[j, m]; ivv = np.where(np.isfinite(ivv) & (ivv > 0), ivv, 8.0)
            car = (sm[m] * fnow * (4.0 / ivv)).sum() * 1e4
        net = float((sm[m] * yv).sum() * 1e4 - car - cb)
        rec.append((int(E_ts[i]), net))
        H = sm
    return rec

def stats(rec, ts_max=None, yr_min=2024):
    arr = np.array([(t, n) for t, n in rec if (ts_max is None or t <= ts_max)])
    if arr.size == 0: return None
    y_ = np.array([time.gmtime(int(t)).tm_year for t in arr[:, 0]])
    n = arr[y_ >= yr_min, 1]
    if len(n) < 100: return None
    return {"n": len(n), "mean_bps": round(float(n.mean()), 3),
            "sharpe": round(float(n.mean() / (n.std() + 1e-12) * np.sqrt(6 * 365)), 2)}

RES = {}
ARMS = [("base", "v0", "half"), ("v1half", "v1", "half"), ("v2half", "v2", "half"),
        ("v0iv", "v0", "iv"), ("v1iv", "v1", "iv")]
REC_KEEP = {}
for nm, fv, carry in ARMS:
    FE = FE_V[fv]
    LR, pos = build_leg_rets(FE)
    Wt, okA = build_targets(FE, lambda i: msharpe_w(LR, pos.get(int(i), 0)))
    for scen in ("b", "c"):
        rec = replay(Wt, okA, scen, carry)
        old_full = stats(rec, ts_max=OLD_MAX_TS, yr_min=2024)
        old_25 = stats(rec, ts_max=OLD_MAX_TS, yr_min=2025)
        ext_full = stats(rec, ts_max=None, yr_min=2024)
        RES[f"{nm}_{scen}"] = {"old_full": old_full, "old_2025p": old_25, "ext_full": ext_full}
        print(f"[{nm} {scen}] 旧窗全史 {old_full} | 旧窗2025+ {old_25} | 含延长周 {ext_full}", flush=True)
        if nm in ("base", "v1iv") and scen == "b":
            REC_KEEP[nm] = rec
    # 基线守卫
    if nm == "base":
        g = RES["base_b"]["old_full"]
        if g is None or not (3.31 <= g["sharpe"] <= 3.51):
            print(f"STOP_PIPELINE_DRIFT base_b old_full={g} 不在 3.41±0.10", flush=True)
            json.dump(RES, open("/workspace/extweek.json", "w"), indent=1)
            sys.exit(3)
        print("基线复现守卫 PASS", flush=True)

# 真OOS周: 逐锚 + 逐日
week = {}
for nm, rec in REC_KEEP.items():
    tail = [(t, n) for t, n in rec if t > OLD_MAX_TS]
    days = {}
    for t, n in tail:
        d = time.strftime("%m-%d", time.gmtime(t))
        days[d] = round(days.get(d, 0.0) + n, 2)
    week[nm] = {"n_anchors": len(tail), "sum_bps": round(sum(n for _, n in tail), 2), "by_day": days,
                "anchors": [(time.strftime("%m-%dT%H", time.gmtime(t)), round(n, 2)) for t, n in tail]}
    print(f"[真OOS周 {nm}] n={len(tail)} 合计{week[nm]['sum_bps']}bps 逐日{days}", flush=True)
RES["week"] = week

# 诊断: 单位混合直接证据 + fund 腿独立 IC
diag = {}
for fv in ("v0", "v1"):
    FE = FE_V[fv]
    c4, c8 = [], []
    for j in range(0, len(PW["ts"]), 97):
        iv_ = IV[j]; fe_ = FE[j]
        ok = np.isfinite(iv_) & np.isfinite(fe_)
        c4 += list(np.abs(fe_[ok & (iv_ == 4)])); c8 += list(np.abs(fe_[ok & (iv_ == 8)]))
    diag[fv] = {"mean_abs_iv4": round(float(np.mean(c4)), 7), "mean_abs_iv8": round(float(np.mean(c8)), 7),
                "ratio_8over4": round(float(np.mean(c8) / max(np.mean(c4), 1e-12)), 3)}
    print(f"[单位诊断 {fv}] |ema| iv4={diag[fv]['mean_abs_iv4']} iv8={diag[fv]['mean_abs_iv8']} 比 {diag[fv]['ratio_8over4']}", flush=True)
def sp_(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
for fv in ("v0", "v1", "v2"):
    FE = FE_V[fv]
    ics = []
    for i in range(0, nA, 7):
        ls = leg_scores(i, FE)
        if ls is None: continue
        sc, m = ls
        ics.append(sp_(sc["fund"], y4[i, m]))
    diag[f"ic_{fv}"] = round(float(np.nanmean(ics)), 5)
    print(f"[fund腿IC {fv}] {diag[f'ic_{fv}']}", flush=True)
RES["diag"] = diag
json.dump(RES, open("/workspace/extweek.json", "w"), indent=1)
daily = {nm: week[nm]["by_day"] for nm in week}
json.dump(daily, open("/workspace/extweek_daily.json", "w"), indent=1)
print("EXTWEEK_DONE", flush=True)
