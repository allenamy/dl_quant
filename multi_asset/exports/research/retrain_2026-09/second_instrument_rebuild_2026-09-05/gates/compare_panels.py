"""compare_panels.py — receipts for the funding-scope plan and the G1 residual classification (lead instruction 09-05):
(a) 450-scope panel (FUND_SCOPE input patch) vs the DIAG-A masked panel (output columns masked): per-array bitwise equality;
(b) August tail: for ZRXUSDT/AGIXUSDT/TONUSDT the last anchor with finite Y4 in v1 vs rebuilt; one raw daily-zip row by hand
    (ZRXUSDT 2026-08-12 first bar) vs the cache cell; (c) f_fund_iv / f_fund_ema_v1 unequal cells: symbols, anchor range, value pairs;
(d) residual funding NaN-mismatch of the 450-scope panel vs v1: per symbol counts, years, direction. Writes results/panel_probe.json."""
import os, json, time, zipfile
import numpy as np
ROOT = os.environ.get("JR_ROOT", "/workspace/review_scratch/jpline_rebuild")
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
P450 = np.load(f"{ROOT}/data/wide_panel_4h_hist_v2_rebuilt_fund450.npz", allow_pickle=True); PM = np.load(f"{ROOT}/data/wide_panel_4h_hist_v2_rebuilt_fund450_DIAG.npz", allow_pickle=True)
V1 = np.load("/workspace/data/wide_panel_4h_v1.npz", allow_pickle=True); R = np.load(f"{ROOT}/data/wide_panel_4h_hist_v2_rebuilt.npz", allow_pickle=True)
sym = [str(s) for s in V1["symbols"]]; ts = V1["ts"].astype(np.int64); yrs = np.array([time.gmtime(int(t)).tm_year for t in ts])
out = {}
eq = {}
for k in P450.files:
    a = P450[k]; b = PM[k]
    eq[k] = bool(np.array_equal(a, b)) if a.dtype.kind in "biuU" else bool(np.array_equal(a, b, equal_nan=True))
out["a_scope_panel_vs_masked_panel_bitwise"] = eq; print("(a) 450-scope panel == masked DIAG panel per array:", eq, flush=True)
# (b) tail
tail = {}
for s in ("ZRXUSDT", "AGIXUSDT", "TONUSDT", "BTCUSDT"):
    j = sym.index(s); fv = np.where(np.isfinite(V1["Y4"][:, j]))[0]; fr = np.where(np.isfinite(R["Y4"][:, j]))[0]
    tail[s] = {"v1_last_finite_Y4_anchor": iso(ts[fv[-1]]) if len(fv) else None, "rebuilt_last_finite_Y4_anchor": iso(ts[fr[-1]]) if len(fr) else None, "n_finite_v1": int(len(fv)), "n_finite_rebuilt": int(len(fr))}
print("(b) tail:", tail, flush=True)
zp = f"{ROOT}/klines5m/ZRXUSDT/ZRXUSDT-5m-2026-08-12.zip"; zq = f"{ROOT}/klines5m/ZRXUSDT/ZRXUSDT-5m-2026-08-11.zip"
hand = {}
if os.path.exists(zp) and os.path.exists(zq):
    def rows(p):
        with zipfile.ZipFile(p) as z: raw = z.read(z.namelist()[0]).decode().splitlines()
        return [ln.split(",") for ln in raw if ln and ln.split(",")[0].isdigit()]
    r12 = rows(zp); r11 = rows(zq)
    c_prev = float(r11[-1][4]); c_first = float(r12[0][4]); ot = int(r12[0][0]) // 1000
    import sys; sys.path.insert(0, f"{ROOT}/src"); from zload import zload
    Z = zload(f"{ROOT}/data/dlnative_5m_wide829_f16_hist.npz", allow_pickle=True); CTS = Z["ts"].astype(np.int64); row = int(np.searchsorted(CTS, ot + 300))
    cell = float(Z["data"][row, sym.index("ZRXUSDT"), 0])
    hand = {"zip": os.path.basename(zp), "first_row_open_time": iso(ot), "first_row_close": c_first, "prev_file_last_close": c_prev, "hand_ret5_f16": float(np.float16(np.clip(c_first / c_prev - 1, -0.3, 0.3))), "cache_cell_ret5": cell, "cache_row_ts": iso(CTS[row]), "equal": bool(np.float16(np.clip(c_first / c_prev - 1, -0.3, 0.3)) == np.float16(cell)),
            "n_rows_0812_file": len(r12), "n_rows_0811_file": len(r11)}
    print("(b) hand row:", hand, flush=True)
out["b_tail"] = {"last_finite": tail, "hand_row": hand}
# (c) iv / ema_v1 unequal cells (rebuilt 829 panel vs v1)
cc = {}
for k in ("f_fund_iv", "f_fund_ema_v1", "f_fund_ema_v2"):
    a = R[k].astype(np.float64); b = V1[k].astype(np.float64); neq = np.isfinite(a) & np.isfinite(b) & (a != b); ii, jj = np.where(neq)
    per = {}
    for i, j in zip(ii, jj): per.setdefault(sym[j], []).append((iso(ts[i]), float(a[i, j]), float(b[i, j])))
    cc[k] = {"n_cells": int(neq.sum()), "n_symbols": len(per), "anchor_range": [iso(ts[ii.min()]), iso(ts[ii.max()])] if len(ii) else None,
             "per_symbol": {s: {"n": len(v), "first": v[0][0], "last": v[-1][0], "value_pairs_rebuilt_v1": sorted(set((round(x[1], 6), round(x[2], 6)) for x in v))[:6]} for s, v in per.items()}}
    print(f"(c) {k}: {cc[k]['n_cells']} cells, symbols {list(per)[:20]}, range {cc[k]['anchor_range']}", flush=True)
    for s, v in list(per.items())[:6]: print(f"     {s}: n {len(v)} {v[0][0]}..{v[-1][0]} pairs {cc[k]['per_symbol'][s]['value_pairs_rebuilt_v1']}", flush=True)
out["c_iv_ema_unequal"] = cc
# (d) residual NaN-mismatch 450-scope vs v1
dd = {}
for k in ("f_fund_now", "f_fund_ema_v1"):
    a = P450[k]; b = V1[k]; fa = np.isfinite(a); fb = np.isfinite(b); mis = fa ^ fb; per = {}
    for j in np.where(mis.any(0))[0]:
        rws = np.where(mis[:, j])[0]; per[sym[j]] = {"n": int(len(rws)), "first": iso(ts[rws[0]]), "last": iso(ts[rws[-1]]), "years": sorted(set(int(y) for y in yrs[rws])), "nan_in_v1_only": int((fa[:, j] & ~fb[:, j]).sum()), "nan_in_rebuilt_only": int((~fa[:, j] & fb[:, j]).sum())}
    dd[k] = {"n_cells": int(mis.sum()), "per_symbol": per}
    print(f"(d) {k}: residual NaN-mismatch {mis.sum()} cells over {len(per)} symbols: " + "; ".join(f"{s} n{v['n']} {v['first'][:10]}..{v['last'][:10]} v1NaN {v['nan_in_v1_only']}/rebNaN {v['nan_in_rebuilt_only']}" for s, v in per.items()), flush=True)
out["d_residual_nan_mismatch_450_vs_v1"] = dd
json.dump(out, open(f"{ROOT}/results/panel_probe.json", "w"), indent=1); print("wrote results/panel_probe.json")
