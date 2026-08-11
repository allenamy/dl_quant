"""#48 门 B 第一步 —— 独立性前筛(PREREG_bookstate_pregate §2 原文: "独立性前筛"先跑)。
判据: 幸存特征 vs 任一在役腿 |rho| >= 0.6 ⇒ 先杀, 不进增量测。
口径: 逐时间戳 xsec rank-corr, 限于特征覆盖的 14 名 & 有限值, 再对时间取均值。"""
import sys, json
import numpy as np
from scipy.stats import rankdata
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
f = np.load(f"{MA}/exports/eda/bookstate14_features.npz", allow_pickle=True)
z = np.load(f"{MA}/exports/wide_dl_full_corrfund_causal_0731.npz", allow_pickle=True)
Fz, fts = f["F_z"], f["ts"]
fsyms = [str(x) for x in f["symbols"]]
names = [str(x) for x in f["feat_names"]]
SURV = ["cumdep_far_asym", "spread_bps"]
psyms = [str(x) for x in z["symbols"]]
cix = np.array([psyms.index(s) for s in fsyms])
ch = [str(x) for x in z["ch_names"]]
CL4 = z["CL4"][:, cix].astype(bool)
MEM = z["MEMBER110"][:, cix].astype(bool)

legs = {}
for nm, path, key in (("king", "/tmp/king_pred_newgen.npz", "king_pred"),
                      ("s2", "/tmp/s2_pred_newgen.npz", "s2_pred")):
    d = np.load(path, allow_pickle=True)
    kk = key if key in d.files else [x for x in d.files if x != "ts"][0]
    P = np.full((len(fts), len(fsyms)), np.nan, np.float32)
    pos = {int(t): i for i, t in enumerate(d["ts"])}
    rows = np.array([pos.get(int(t), -1) for t in fts])
    ok = rows >= 0
    P[ok] = d[kk][rows[ok]][:, cix]
    legs[nm] = P
    print(f"  leg {nm}: 覆盖 {ok.mean():.3f} 的特征时间戳", flush=True)
for nm, cn in (("funding", "funding_ema"), ("size", "size_dvol"),
               ("lturnover", "lturnover_24h"), ("rvol24", "rvol_24h")):
    legs[nm] = z["CH"][:, cix, ch.index(cn)].astype(np.float32)

out = {}
for s in SURV:
    k = names.index(s)
    row = {}
    for lname, L in legs.items():
        cs = []
        for i in range(len(fts)):
            m = MEM[i] & CL4[i] & np.isfinite(Fz[i, :, k]) & np.isfinite(L[i])
            if m.sum() >= 8:
                a, b = Fz[i, m, k], L[i, m]
                if a.std() > 1e-12 and b.std() > 1e-12:
                    c = np.corrcoef(rankdata(a), rankdata(b))[0, 1]
                    if np.isfinite(c):
                        cs.append(c)
        row[lname] = {"mean_rho": round(float(np.mean(cs)), 4) if cs else None,
                      "mean_abs_rho": round(float(np.mean(np.abs(cs))), 4) if cs else None,
                      "n_ts": len(cs)}
    worst = max((v["mean_abs_rho"] or 0) for v in row.values())
    row["_verdict"] = "KILL (|rho|>=0.6 vs 某在役腿)" if worst >= 0.6 else "PASS -> 进增量测"
    row["_max_abs_rho"] = round(worst, 4)
    out[s] = row
print(json.dumps(out, indent=1, ensure_ascii=False))
json.dump({"prereg": "PREREG_bookstate_pregate_2026-08-05.md", "step": "gate B 独立性前筛",
           "results": out},
          open(f"{MA}/exports/eda/RESULT_bookstate14_indep.json", "w"), indent=1, ensure_ascii=False)
