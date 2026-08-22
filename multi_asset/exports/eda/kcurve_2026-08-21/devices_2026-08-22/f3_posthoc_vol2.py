"""F3 · POST-HOC 诊断臂(非预注册, 只报不录取): VOL2(f_vol_7d + f_range_24h 等权秩复合)作第四腿 A15_VOL2 / NF15_VOL2 的书级 S2 读数.
动机: 预注册里 VOL2 只是 S1 族诊断臂; 首读 VOL2 是唯一过 S1 的族(ICW 也过且偏向 VOL 族, 但 ICW 的 S2 显著为负) ⇒ 用同装置补一读书级, 明标 POST-HOC.
复用 f3_zoo_nonfunding_leg.py(预注册臂逐位不变; 本脚本不改其任何函数), 基线 B0/NF0 序列取自 f3_series.npz(同一次运行).
用法 @jpline: python f3_posthoc_vol2.py
"""
import sys, json, time, numpy as np
sys.argv = ["x"]
import f3_zoo_nonfunding_leg as M
R = {"stage": "posthoc_vol2", "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "self_sha256": M.sha(__file__), "device_sha256": M.SELF_SHA, "note": "POST-HOC, non-prereg; report only"}
M.load_all(); M.build_composites()
M._add("A15_VOL2", ["king", "rev24", "fund", "VOL2"], ("fixed_last", 0.15)); M._add("NF15_VOL2", ["king", "rev24", "VOL2"], ("fixed_last", 0.15))
SER = np.load(f"{M.OUT}/f3_series.npz", allow_pickle=True)
def base_series(nm, key):
    return SER[f"{nm}__ts"].astype(np.int64), SER[f"{nm}__{key}"]
out = {}
for arm, base in (("A15_VOL2", "B0"), ("NF15_VOL2", "NF0")):
    o = M._job(arm); ts = o["ts"]; acc = o["acc"]
    m_main = ts <= M.T_END_MAIN
    summ = M.summarize(acc, ts, o["mkt"], arm, yr_mask=m_main, wh=o["wh"], leg_names=o["legs"])
    ent = {"summary_main": summ, "vs": base}
    for key, lab in (("net_g2_c4.137", "4.137"), ("net_g2_c6.23", "6.23"), ("net_g2", "3.52")):
        bts, bser = base_series(base, key); cm = np.intersect1d(ts, bts); cm = cm[cm <= M.T_END_MAIN]
        x = acc[key][np.searchsorted(ts, cm)]; y = bser[np.searchsorted(bts, cm)]
        yr = M.yr_of(cm)
        ent[f"dnet@{lab}"] = M.boot_delta_mean(x, y); ent[f"dSharpe@{lab}"] = M.boot_delta_sharpe(x, y)
        ent[f"dnet@{lab}_by_year"] = {int(y_): round(float((x - y)[yr == y_].mean()), 4) for y_ in sorted(set(yr.tolist()))}
        ent[f"sharpe_arm@{lab}"] = round(M.sharpe_a(x), 3); ent[f"sharpe_base@{lab}"] = round(M.sharpe_a(y), 3)
    out[arm] = ent
    M.log("POSTHOC", arm, "sharpe", ent["sharpe_arm@3.52"], "vs", ent["sharpe_base@3.52"], "dSharpe@3.52", ent["dSharpe@3.52"], "dnet@4.137", ent["dnet@4.137"], "by_year", ent["dnet@4.137_by_year"])
R["arms"] = out
json.dump(R, open(f"{M.OUT}/f3_posthoc_vol2_2026-08-22.json", "w"), indent=1, default=str)
M.log("POSTHOC DONE")
