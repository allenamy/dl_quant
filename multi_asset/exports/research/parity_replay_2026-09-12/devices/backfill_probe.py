#!/usr/bin/env python3
"""Measure late back-fill of the producer's 5m cache: cells that were NaN in the earlier snapshot but finite in the later one,
restricted to rows <= the earlier snapshot's anchor (PREREG Phase 1 RESULT §3 hypothesis). Read-only. Usage: backfill_probe.py <snap_early_dir> <snap_late_dir>"""
import sys, json, time, numpy as np
a, b = sys.argv[1], sys.argv[2]
A = np.load(f"{a}/rolling.npz", allow_pickle=True); B = np.load(f"{b}/rolling.npz", allow_pickle=True)
ta, da = A["ts"].astype(np.int64), A["data"]; tb, db = B["ts"].astype(np.int64), B["data"]
A_anchor = int(json.load(open(f"{a}/aux.json"))["last_anchor"]); B_anchor = int(json.load(open(f"{b}/aux.json"))["last_anchor"])
common = np.intersect1d(ta, tb); common = common[common <= A_anchor]
ia = np.searchsorted(ta, common); ib = np.searchsorted(tb, common)
xa = da[ia].astype(np.float32); xb = db[ib].astype(np.float32)
fa = np.isfinite(xa[:, :, 3]); fb = np.isfinite(xb[:, :, 3])           # log_qv presence = the producer's own fill test (channel 3)
filled_later = (~fa) & fb; lost = fa & (~fb)
changed = fa & fb & (np.abs(xa[:, :, 0] - xb[:, :, 0]) > 0)
syms = json.load(open("multi_asset/exports/research/parity_replay_2026-09-12/phase2/producer_symbols.json"))["symbols_panel"]
by_sym = filled_later.sum(0); top = np.argsort(-by_sym)[:10]
rows_with_fill = np.where(filled_later.any(1))[0]
out = {"early": a, "late": b, "early_anchor": A_anchor, "late_anchor": B_anchor, "rows_compared": int(len(common)),
       "cells_filled_later": int(filled_later.sum()), "cells_lost": int(lost.sum()), "cells_changed_finite": int(changed.sum()),
       "symbols_with_fill": int((by_sym > 0).sum()), "top_symbols": [(syms[j], int(by_sym[j])) for j in top if by_sym[j] > 0],
       "rows_with_fill": int(len(rows_with_fill)), "earliest_filled_row_utc": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(common[rows_with_fill[0]]))) if len(rows_with_fill) else None,
       "latest_filled_row_utc": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(common[rows_with_fill[-1]]))) if len(rows_with_fill) else None}
print(json.dumps(out, ensure_ascii=False, indent=1))
