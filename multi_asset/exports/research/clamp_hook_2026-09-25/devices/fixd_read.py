#!/usr/bin/env python3
"""FIX-D engine arm vs the filed baseline (NC s42X): per path the book-return series of the D arm (fa_ladsave recipe over PATH_*_seed_NN)
against SER_EXT_NEWS2_s42X row by row. Reports: n paths; per-anchor mean over paths of (r_D − r_base) — sum and mean in bps, by year
(2023H2 / 2024 / 2025 / 2026 to 09-18T20Z, the frozen-SEG caveat not applicable here: one axis), the share of anchors where any path
differs; and the post-clamp net / NAV in the D arm from the hook rows (all seeds pooled; the baseline distribution is c4hook2's seed 0).
This is the engine before/after reading requested by the lead — NOT the family judgement (DECISION RULE rev 7 891aec11c runs later).
usage: /workspace/venv/bin/python -B fixd_read.py <cell dir> <hook dir> <filed SER npz> <out json>"""
import glob, json, os, sys, time, collections
import numpy as np
sys.path.insert(0, "/dev/shm/news_2026-09-23/engine")
import bt_tables as BT                                    # noqa: E402
CELL, HOOK, SER, OUT = sys.argv[1:5]; tag = os.path.basename(CELL.rstrip("/"))
S = np.load(SER); A = S["anchors"].astype(np.int64)
P = []
for k in range(32):
    f = f"{CELL}/PATH_{tag}_seed_{k:02d}.npz"
    if os.path.exists(f): P.append((k, BT.series_from_path(np.load(f))))
rec = {"n_paths": len(P)}
if P:
    D = np.stack([np.asarray(p["r"], np.float64) - S["r_per_path"][k] for k, p in P]); ax_ok = all(np.array_equal(np.asarray(p["A"], np.int64), A) for _, p in P)
    m = D.mean(0); yr = np.array([time.strftime("%Y", time.gmtime(int(t))) for t in A])
    rec.update({"axes_equal": bool(ax_ok), "share_anchors_any_path_differs": float((np.abs(D) > 0).any(0).mean()),
                "mean_diff_bps_per_anchor": float(m.mean() * 1e4), "sum_diff_bps": float(m.sum() * 1e4),
                "by_year": {y: {"n": int((yr == y).sum()), "mean_bps": float(m[yr == y].mean() * 1e4), "sum_bps": float(m[yr == y].sum() * 1e4)} for y in sorted(set(yr))}})
rows = [json.loads(l) for f in glob.glob(f"{HOOK}/HOOK_*.jsonl") for l in open(f) if l.strip()]
v = [r["book_net_usdt"] / (r["sizing_gross"] / 2.0) for r in rows if r.get("book_net_usdt") is not None and r.get("sizing_gross")]
dp = sum(1 for r in rows if (r.get("targets") or {}) and False)
rec["hook_rows"] = len(rows)
if v:
    v = np.array(v); rec["post_clamp_net_over_nav_pct"] = {"n": len(v), "mean": float(v.mean() * 100), "pct": {str(q): float(np.percentile(v, q) * 100) for q in (5, 25, 50, 75, 95)},
                                                          "median_abs": float(np.median(np.abs(v)) * 100), "p95_abs": float(np.percentile(np.abs(v), 95) * 100)}
json.dump(rec, open(OUT, "w"), indent=1)
print("FIXD_READ", json.dumps(rec)[:1500])
