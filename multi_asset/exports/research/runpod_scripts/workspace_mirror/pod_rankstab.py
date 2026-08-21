"""秩特征稳定性仪器: ① 成员流动率(逐锚进出) ② 秩变动分解: 全宇宙秩变 vs 共同成员内秩变(差=宇宙变动伪信号)
③ 滞回宇宙对照: 慢书在 滞回成员(进top380/出430/每42锚=7天才刷新) 下的换手与净额差.
"""
import json, time
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from scipy.stats import rankdata, spearmanr
MT = np.load("/workspace/data/wide_fea_v1_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
nA = len(E_ts); NW = 829
FEA = np.load("/workspace/data/wide_fea_v1.npy")
names = [str(n) for n in MT["names"]]
probe_feat = names.index("vol_2016_r") if "vol_2016_r" in names else None
# ① 成员流动
churn = []
for i in range(1, nA):
    if yrs[i] < 2024: continue
    a, b = set(members[i - 1].tolist()), set(members[i].tolist())
    churn.append(len(a ^ b) / max(len(a | b), 1))
print(f"① 逐锚成员流动率: 均值 {np.mean(churn)*100:.2f}% P95 {np.percentile(churn,95)*100:.2f}%", flush=True)
# ② 秩变动分解(用慢打分器的秩): 相邻锚, 共同成员上: 全宇宙秩 vs 共同集内重算秩
SLOW = np.load("/workspace/exports_train/slow_lgbm_pred.npy")
full_d, common_d = [], []
for i in range(1, nA, 3):
    if yrs[i] < 2024: continue
    m0, m1 = members[i - 1], members[i]
    common = np.intersect1d(m0, m1)
    if len(common) < 100: continue
    s0f, s1f = SLOW[i - 1, m0], SLOW[i, m1]
    ok0 = np.isfinite(s0f); ok1 = np.isfinite(s1f)
    r0 = np.full(NW, np.nan); r1 = np.full(NW, np.nan)
    if ok0.sum() < 50 or ok1.sum() < 50: continue
    r0[m0[ok0]] = rankdata(s0f[ok0]) / ok0.sum()
    r1[m1[ok1]] = rankdata(s1f[ok1]) / ok1.sum()
    cc = common[np.isfinite(r0[common]) & np.isfinite(r1[common])]
    if len(cc) < 100: continue
    full_d.append(float(np.abs(r1[cc] - r0[cc]).mean()))
    s0c, s1c = SLOW[i - 1, cc], SLOW[i, cc]
    rc0 = rankdata(s0c) / len(cc); rc1 = rankdata(s1c) / len(cc)
    common_d.append(float(np.abs(rc1 - rc0).mean()))
fd, cd = np.mean(full_d), np.mean(common_d)
print(f"② 秩变动分解(慢分, 共同成员): 全宇宙秩口径 |Δrank| {fd:.4f} vs 共同集内 {cd:.4f} ⇒ 宇宙变动贡献 {(fd-cd)/fd*100:.1f}%", flush=True)
# ③ 滞回宇宙: 每 42 锚才刷新成员(进 top380 / 出 >430 名), 对照逐锚刷新
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    n = ok.sum()
    if n >= 10: out[ok] = rankdata(v[ok]) / max(n - 1, 1) - 0.5
    return out
def run_book(hyst):
    cur = None
    H = np.zeros(NW, np.float64)
    rets, tos, subm = [], [], []
    for i in range(nA):
        m = members[i]
        s = SLOW[i, m]
        ok = np.isfinite(s) & np.isfinite(y4[i, m])
        qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
        base = ok & (qv4h >= 2.5e5)
        if base.sum() < 80: continue
        if not hyst or cur is None or i % 42 == 0:
            rk = np.argsort(np.argsort(-np.where(base, qv4h, -1)))
            if hyst and cur is not None:
                keep = np.zeros(len(m), bool)
                for k in range(len(m)):
                    if not base[k]: continue
                    inb = m[k] in cur
                    if (inb and rk[k] < 430) or (not inb and rk[k] < 380): keep[k] = True
                sel = keep
            else:
                sel = base
            cur = set(m[sel].tolist())
        sel = np.array([mm in cur for mm in m]) & ok
        if sel.sum() < 80: continue
        z = xz(np.where(sel, s, np.nan))
        w = np.nan_to_num(z); w -= w[sel].mean()
        g = np.abs(w).sum()
        if g < 1e-9: continue
        w /= g
        capw = 2.5 / max(sel.sum(), 1)
        w = np.clip(w, -capw, capw)
        g2 = np.abs(w).sum()
        if g2 > 1e-9: w /= g2
        tgt = np.zeros(NW); tgt[m] = w
        sm = H + 0.1 * (tgt - H)
        trade = sm - H
        sm = np.where(np.abs(trade) < 2.5e-4, H, sm)
        yv = np.zeros(NW); yv[m] = np.nan_to_num(y4[i, m], nan=0.0)
        rets.append(float((sm * yv).sum() * 1e4))
        tos.append(float(np.abs(sm - H).sum()))
        subm.append(bool(yrs[i] >= 2025))
        H = sm
    rets = np.array(rets); sub = np.array(subm)
    return float(rets[sub].mean()), float(np.array(tos)[sub].mean())
g_live, to_live = run_book(False)
g_hyst, to_hyst = run_book(True)
print(f"③ 滞回宇宙对照(慢书, 2025-26): 逐锚刷新 毛{g_live:.3f} 换手{to_live:.4f} | 滞回7天 毛{g_hyst:.3f} 换手{to_hyst:.4f} "
      f"⇒ 换手省 {(to_live-to_hyst)/max(to_live,1e-9)*100:.1f}% 毛差 {(g_hyst-g_live):.3f}", flush=True)
json.dump({"churn_mean": float(np.mean(churn)), "rankdelta_full": fd, "rankdelta_common": cd,
           "hyst": {"gross_live": g_live, "to_live": to_live, "gross_hyst": g_hyst, "to_hyst": to_hyst}},
          open("/workspace/rankstab.json", "w"), indent=1)
print("RANKSTAB_DONE", flush=True)
