import json, time, numpy as np
from collections import defaultdict
R = json.load(open("/workspace/uplift_2026-09-11/infra1_cost/fill_cost_rows.json"))
rows = R["rows"]; print("rows", len(rows), "dedup fills", R["n_dedup"])
P = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True)
M = np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz", allow_pickle=True)
psym = [str(s) for s in P["symbols"]]; sidx = {s: i for i, s in enumerate(psym)}
E = M["E_ts"].astype(np.int64); qvk = M["qvk"]
erow = {int(t): i for i, t in enumerate(E)}
pts = P["ts"].astype(np.int64); prow = {int(t): i for i, t in enumerate(pts)}
VOL = np.asarray(P["f_vol_7d"], float); AM = np.asarray(P["f_amihud_24h"], float)
g4 = lambda ts: int(np.floor(ts / 14400.0) * 14400)
hit = miss = 0
for r in rows:
    k = g4(r["anchor_ts"]); r["g4"] = k
    j = erow.get(k); c = sidx.get(r["symbol"])
    if j is None or c is None:
        r["qv4h"] = None; miss += 1; continue
    q = qvk[j, c]
    r["qv4h"] = float(np.expm1(np.clip(q, 0, 30)) * 48) if np.isfinite(q) else None
    pj = prow.get(k)
    r["vol7d"] = float(VOL[pj, c]) if pj is not None and np.isfinite(VOL[pj, c]) else None
    r["amihud"] = float(AM[pj, c]) if pj is not None and np.isfinite(AM[pj, c]) else None
    hit += 1
print("panel join: hit", hit, "miss", miss)
anchors = sorted(set(r["g4"] for r in rows))
print("live anchors", len(anchors), time.strftime("%Y-%m-%d %HZ", time.gmtime(anchors[0])), "->", time.strftime("%Y-%m-%d %HZ", time.gmtime(anchors[-1])))
ja = sorted(set(r["g4"] for r in rows if r.get("qv4h") is not None))
print("joined anchors", len(ja), time.strftime("%Y-%m-%d %HZ", time.gmtime(ja[0])), "->", time.strftime("%Y-%m-%d %HZ", time.gmtime(ja[-1])))
# notional coverage
tot = sum(r["mk_nz"] + r["tk_nz"] for r in rows)
jn = sum(r["mk_nz"] + r["tk_nz"] for r in rows if r.get("qv4h") is not None)
print("filled notional total %.0f  joined %.0f (%.1f%%)" % (tot, jn, 100 * jn / tot))
json.dump(rows, open("/workspace/uplift_2026-09-11/infra1_cost/rows_joined.json", "w"))
