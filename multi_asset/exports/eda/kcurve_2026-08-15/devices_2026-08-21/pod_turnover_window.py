"""保真度质询: 回放换手 0.046/锚(全史) vs 影子日志 0.0075 —— 是书不同还是时段/字段不同?
在权威构造(pod_legweight_arms 同构, base)上输出逐锚 |Δw| 合计的时间序列, 看 2026-08 窗口 vs 全史。"""
import json, time, numpy as np, sys
sys.path.insert(0, "/workspace")
exec(open("/workspace/pod_legweight_arms.py").read().split("def run(look, cap):")[0])
def w3_at(p, look=900):
    if p < look: return np.array([1/3]*3)
    sl = slice(p - look, p); r = np.stack([LRa["king"][sl], LRa["rev24"][sl], LRa["fund"][sl]])
    shp = np.maximum(r.mean(1)/(r.std(1)+1e-9), 0.0); return shp/shp.sum() if shp.sum() > 0 else np.array([1/3]*3)
H = np.zeros(NW); rows = []
for i in range(nA):
    j = pw_row.get(int(E_ts[i]))
    if j is None: continue
    m = members[i]; sc = {"king": SLOW[i, m], "rev24": -R24[j, m], "fund": FE[j, m]}
    w3 = w3_at(pos.get(int(i), 0))
    z = w3[0]*np.nan_to_num(xz(sc["king"])) + w3[1]*np.nan_to_num(xz(sc["rev24"])) + w3[2]*np.nan_to_num(xz(sc["fund"]))
    ok = np.isfinite(y4[i, m]); qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48; sel = ok & (qv4h >= 2.5e5)
    if sel.sum() < 80: continue
    w = np.where(sel, z, 0.0); w -= w[sel].mean(); g = np.abs(w).sum()
    if g < 1e-9: continue
    w /= g; capw = 2.5/max(int(sel.sum()),1); w = np.clip(w, -capw, capw); g2 = np.abs(w).sum()
    if g2 > 1e-9: w /= g2
    tgt = np.zeros(NW); tgt[m] = w
    sm = H + 0.1*(tgt - H); trade = sm - H; sm = np.where(np.abs(trade) < 2.5e-4, H, sm); trade = sm - H
    rows.append((int(E_ts[i]), float(np.abs(trade).sum()), float(np.abs(sm).sum()), int(sel.sum()), int((np.abs(trade) >= 2.5e-4).sum())))
    H = sm
T = np.array(rows); ts = T[:,0]
def seg(lo, hi, tag):
    m = (ts >= lo) & (ts < hi)
    print(tag, "n", int(m.sum()), "turnover均", round(float(T[m,1].mean()),5), "gross均", round(float(T[m,2].mean()),4), "sel均", round(float(T[m,3].mean()),0), "过带名数均", round(float(T[m,4].mean()),1), flush=True)
seg(0, 9e18, "全史")
seg(time.mktime(time.strptime("2026-08-01","%Y-%m-%d")) - time.timezone, 9e18, "2026-08 窗")
seg(time.mktime(time.strptime("2026-06-01","%Y-%m-%d")) - time.timezone, 9e18, "2026-06 起")
seg(time.mktime(time.strptime("2024-01-01","%Y-%m-%d")) - time.timezone, time.mktime(time.strptime("2025-01-01","%Y-%m-%d")) - time.timezone, "2024 全年")
# 逐月换手中位
import collections
by = collections.defaultdict(list)
for t, tr, g, s, k in rows: by[time.strftime("%Y-%m", time.gmtime(t))].append(tr)
print("逐月换手均值(近8月):", {k: round(float(np.mean(v)),4) for k, v in list(sorted(by.items()))[-8:]}, flush=True)
