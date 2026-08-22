"""WA 附件: 容量/最小名义额地板 与 宇宙覆盖 读数(从 run 阶段存档的 Wb_d30 权重与 close1h 网格计算; 只读).
NAV 情景: 15.4k(当前)/50k/250k × gross 2; 地板 $5 / $20; EMA 尘埃 |w|<5e-4; 逐名日成交额占比(名义/7日均4h成交额).
"""
import json, time, numpy as np, datetime as dt
WA = "/mnt/storage/private/work_hsy/probe_artifacts/wa"
fmt = lambda t: time.strftime("%Y-%m-%d", time.gmtime(int(t)))
Z = np.load(f"{WA}/wa_weights_Wb_d30.npz", allow_pickle=True); ts = Z["ts"].astype(np.int64); W = Z["W"].astype(np.float64); syms = [str(s) for s in Z["symbols"]]
C = np.load(f"{WA}/close1h_829.npz", allow_pickle=True); hts = C["ts"].astype(np.int64); QV = C["qv"].astype(np.float64); hpos = {int(t): i for i, t in enumerate(hts)}
i0 = np.array([hpos[int(t)] for t in ts])
cq = np.concatenate([np.zeros((1, QV.shape[1])), np.cumsum(np.nan_to_num(QV), 0)]); cf = np.concatenate([np.zeros((1, QV.shape[1])), np.cumsum(np.isfinite(QV), 0)])
a0 = np.maximum(i0 - 168, 0)
with np.errstate(all="ignore"):
    qv4h = (cq[i0 + 1] - cq[a0]) / np.maximum(cf[i0 + 1] - cf[a0], 1) * 4
yr = np.array([time.gmtime(int(t)).tm_year for t in ts])
gross = np.abs(W).sum(1); aw = np.abs(W)
out = {"n_anchors": int(len(ts)), "span": [fmt(ts[0]), fmt(ts[-1])], "gross_mean": float(gross.mean()), "nheld_gt1e-9": float((aw > 1e-9).sum(1).mean()), "nheld_gt5e-4": float((aw > 5e-4).sum(1).mean()),
       "dust_share_lt5e-4": float((aw * (aw < 5e-4)).sum(1).mean() / gross.mean()), "scenarios": {}}
for nav in (15400.0, 50000.0, 250000.0):
    G = nav * 2.0; notion = aw / gross[:, None] * G          # 恒定 gross 2 口径下逐名名义
    with np.errstate(all="ignore"):
        part = notion / qv4h
    sc = {"floor5_gross_share": float((aw * (notion < 5.0) * (aw > 1e-9)).sum(1).mean() / gross.mean()), "floor20_gross_share": float((aw * (notion < 20.0) * (aw > 1e-9)).sum(1).mean() / gross.mean()),
          "names_ge20": float(((notion >= 20.0)).sum(1).mean()), "names_ge100": float(((notion >= 100.0)).sum(1).mean()),
          "gross_share_notional_gt1pct_of_4hqv": float((aw * np.nan_to_num(part > 0.01)).sum(1).mean() / gross.mean()), "gross_share_notional_gt5pct_of_4hqv": float((aw * np.nan_to_num(part > 0.05)).sum(1).mean() / gross.mean()),
          "by_year_floor20_share": {int(y): float((aw[yr == y] * (notion[yr == y] < 20.0) * (aw[yr == y] > 1e-9)).sum(1).mean() / gross[yr == y].mean()) for y in sorted(set(yr.tolist()))}}
    out["scenarios"][f"nav{int(nav)}_gross2"] = sc
# 宇宙覆盖: 退市名权重份额(以 1h 数据在 2026-07-31 后仍有数为"现存")
last_fin = np.array([hts[np.where(np.isfinite(C["close"][:, j]))[0][-1]] if np.isfinite(C["close"][:, j]).any() else 0 for j in range(len(syms))])
delisted = last_fin < int(dt.datetime(2026, 7, 31, tzinfo=dt.timezone.utc).timestamp())
out["delisted_names_in_panel"] = int(delisted.sum())
out["gross_share_on_delisted_by_year"] = {int(y): float((aw[yr == y][:, delisted]).sum(1).mean() / gross[yr == y].mean()) for y in sorted(set(yr.tolist()))}
# 名义额相对 4h 成交额分布(2026)
m26 = yr == 2026
out["participation_2026_nav250k"] = {"median_pct": float(np.nanmedian((aw[m26] / gross[m26][:, None] * 500000.0 / qv4h[m26])[aw[m26] > 5e-4]) * 100), "p90_pct": float(np.nanpercentile((aw[m26] / gross[m26][:, None] * 500000.0 / qv4h[m26])[aw[m26] > 5e-4], 90) * 100)}
json.dump(out, open(f"{WA}/wa_followup_capacity.json", "w"), indent=1)
print(json.dumps(out, indent=1))
