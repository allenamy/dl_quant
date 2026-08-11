"""#48 门 A(存在性) — PREREG_bookstate_pregate_2026-08-05.md §2 逐字执行。
判据: 7 特征各自 14 币内 xsec rank-IC vs Y4(CL4 掩码), #21 同族年折;
任一特征 |IC| 的 5 折 t>=2 ⇒ 进门 B; 全部 t<2 ⇒ 整轨杀。本脚本只执行, 不解释判据。"""
import sys, os, json
import numpy as np
from scipy.stats import rankdata
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
FEAT = os.path.join(MA, "exports/eda/bookstate14_features.npz")
PANEL = os.path.join(MA, "exports/wide_dl_full_corrfund_causal_0731.npz")

f = np.load(FEAT, allow_pickle=True)
z = np.load(PANEL, allow_pickle=True)
Fz = f["F_z"]; fts = f["ts"]; fsyms = [str(x) for x in f["symbols"]]
names = [str(x) for x in f["feat_names"]]
pts = z["ts"].astype(np.int64)
assert np.array_equal(fts, pts), "ts 不对齐 — 装置作废(预注册作废条件)"
psyms = [str(x) for x in z["symbols"]]
cix = [psyms.index(s) for s in fsyms]
Y4 = z["Y4"][:, cix]; CL4 = z["CL4"][:, cix].astype(bool)
pts_s = pts // 1000 if int(pts[0]) > 10**11 else pts
import datetime as dt
years = np.array([dt.datetime.utcfromtimestamp(int(t)).year for t in pts_s])
res = {}
for k, nm in enumerate(names):
    per_year = {}
    for yr in (2022, 2023, 2024, 2025, 2026):
        rows = np.where(years == yr)[0]
        ics = []
        for i in rows:
            m = CL4[i] & np.isfinite(Y4[i]) & np.isfinite(Fz[i, :, k])
            if m.sum() >= 8:
                c = np.corrcoef(rankdata(Fz[i, m, k]), rankdata(Y4[i, m]))[0, 1]
                if np.isfinite(c):
                    ics.append(c)
        if ics:
            per_year[yr] = float(np.mean(ics))
    v = np.array(list(per_year.values()))
    t = float(np.mean(v) / np.std(v, ddof=1) * np.sqrt(len(v))) if len(v) > 1 and np.std(v) > 1e-12 else float("nan")
    res[nm] = {"per_year_ic": {str(y): round(x, 4) for y, x in per_year.items()},
               "mean_ic": round(float(np.mean(v)), 4) if len(v) else None,
               "t_abs": round(abs(t), 2) if np.isfinite(t) else None,
               "sign_consistent": bool(len(v) and (np.all(v > 0) or np.all(v < 0)))}
survivors = [n for n, r in res.items() if r["t_abs"] is not None and r["t_abs"] >= 2.0]
out = {"prereg": "PREREG_bookstate_pregate_2026-08-05.md", "gate": "A", "results": res,
       "survivors": survivors,
       "verdict": ("PASS -> 门 B" if survivors else "整轨杀(空结果条款): 全部 |t|<2")}
print(json.dumps(out, indent=1, ensure_ascii=False))
json.dump(out, open(os.path.join(MA, "exports/eda/RESULT_bookstate14_gateA.json"), "w"),
          indent=1, ensure_ascii=False)
