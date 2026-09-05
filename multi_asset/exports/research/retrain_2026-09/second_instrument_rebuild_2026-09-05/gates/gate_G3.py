"""gate_G3.py — PREREG §2 G3 (caliber identity).
 (a) static: census of expm1( / log1p( / np.log( / log( in pod_stop_arms_v3.py, pod_slow_hist_folds.py, pod_fea_wide_hist.py,
     pod_panel_ext.py (verbatim src copies): every hit listed with line; hits on a return quantity must be 0 (volume-channel hits exempt).
 (b) numeric: panel Y4 == Σ_{rows E..E+47} ret5 recomputed from the rebuilt cache (float64 cumsum of float32 ret5, cast float32,
     NaN if <46 finite) on the FULL grid, bitwise incl. NaN positions;
     dlw_targets_hist.y4s vs raw zip closes c_{N+4h}/c_N - 1 on >=1000 sampled anchors (>=300 in 2020-21), one random member per anchor
     whose 48 bars are all present in the cache (missing bars are defined as zero-return by the target script, so cells with missing
     bars are not a definition test; their count is reported): max|Δ| <= 2e-5 => PASS. Also reported: Σ-simple (y4old) vs Π(1+r)-1 (y4s)
     cell-level per-year mean / mean-abs difference in bps (information).
Writes results/G3.json; exit 0 always."""
import os, re, sys, json, time, hashlib, zipfile
import numpy as np
ROOT = os.environ.get("JR_ROOT", "/workspace/review_scratch/jpline_rebuild")   # JR_ROOT only for the dry-test harness
sys.path.insert(0, f"{ROOT}/src"); from zload import zload
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
out = {"self_sha256": sha(os.path.abspath(__file__))}
# ---- (a) static census
VOL_HINT = re.compile(r"qv|cnt|log_qv|qvk|avgsz|log_cnt")
census = {}; n_return_hits = 0
for f in ("pod_stop_arms_v3.py", "pod_slow_hist_folds.py", "pod_fea_wide_hist.py", "pod_panel_ext.py"):
    hits = []
    for ln, line in enumerate(open(f"{ROOT}/src/{f}").read().splitlines(), 1):
        if re.search(r"\b(expm1|log1p|log)\s*\(", line):
            vol = bool(VOL_HINT.search(line)); hits.append({"line": ln, "text": line.strip()[:160], "volume_channel": vol})
            if not vol: n_return_hits += 1
    census[f] = {"sha256": sha(f"{ROOT}/src/{f}"), "hits": hits}
    for h in hits: print(f"  (a) {f}:{h['line']} {'[volume, exempt]' if h['volume_channel'] else '[RETURN PATH]'} {h['text']}", flush=True)
out["a_static"] = {"census": census, "n_return_path_hits": n_return_hits, "pass": n_return_hits == 0}
print(f"  (a) return-path log/expm1 hits: {n_return_hits} -> {'PASS' if n_return_hits == 0 else 'FAIL'}", flush=True)
# ---- (b1) Y4 == Σ ret5 full grid
Z = zload(f"{ROOT}/data/dlnative_5m_wide829_f16_hist.npz", allow_pickle=True); CTS = Z["ts"].astype(np.int64); CD = Z["data"]; NW = CD.shape[1]; TT = CD.shape[0]
PW = np.load(f"{ROOT}/data/wide_panel_4h_hist_v2_rebuilt.npz", allow_pickle=True); pts = PW["ts"].astype(np.int64); Y4 = PW["Y4"]
r5 = CD[:, :, 0].astype(np.float32); fin = np.isfinite(r5)
CS_r = np.concatenate([np.zeros((1, NW)), np.cumsum(np.where(fin, r5, 0).astype(np.float64), 0)]); CS_f = np.concatenate([np.zeros((1, NW), np.int32), np.cumsum(fin, 0, dtype=np.int32)])
grid = np.where(CTS % 14400 == 0)[0]; grid = grid[(grid >= 8640) & (grid + 288 <= TT)]
assert np.array_equal(CTS[grid], pts), "panel anchor grid != recomputed grid"
E = grid; y4n = CS_f[E + 48] - CS_f[E]; Y4re = (CS_r[E + 48] - CS_r[E]).astype(np.float32); Y4re[y4n < 46] = np.nan
fa = np.isfinite(Y4re); fb = np.isfinite(Y4); both = fa & fb; neq = both & (Y4re != Y4)
# independent recipe: direct float64 window sum (not cumsum-difference)
rng = np.random.default_rng(20260905); samp = rng.choice(len(E), size=300, replace=False); direct_neq = 0; direct_n = 0
for i in samp:
    w = np.where(fin[E[i]:E[i] + 48], r5[E[i]:E[i] + 48], 0).astype(np.float64).sum(0).astype(np.float32)
    okc = np.isfinite(Y4[i]); direct_n += int(okc.sum()); direct_neq += int((w[okc] != Y4[i][okc]).sum())
out["b1_Y4_sum"] = {"n_cells_both_finite": int(both.sum()), "n_neq": int(neq.sum()), "n_nan_mismatch": int((fa ^ fb).sum()), "pass": bool(neq.sum() == 0 and (fa ^ fb).sum() == 0),
                    "direct_float64_window_sum_sample": {"n_anchors": 300, "n_cells": direct_n, "n_neq": direct_neq}}
print(f"  (b1) Y4 == Σ_[E,E+47] ret5 (cumsum recipe): both-finite {both.sum()} neq {neq.sum()} nan-mismatch {(fa ^ fb).sum()} -> {'PASS' if out['b1_Y4_sum']['pass'] else 'FAIL'}; direct float64 window sum on 300 anchors: neq {direct_neq}/{direct_n}", flush=True)
del CS_r, CS_f
# ---- (b2) y4s vs raw zip closes
DT = np.load(f"{ROOT}/data/dlw_hist/data/dlw_targets.npz", allow_pickle=True)
dts = DT["E_ts"].astype(np.int64); drow = DT["E_row"].astype(np.int64); MS = DT["members"]; y4s = DT["y4s"]; y4old = DT["y4old"]; syms = [str(s) for s in DT["symbols"]]
assert syms == [str(s) for s in Z["symbols"]]
yrs = np.array([time.gmtime(int(t)).tm_year for t in dts])
idx_early = np.where(yrs <= 2021)[0]; idx_late = np.where(yrs >= 2022)[0]
n_early = min(350, len(idx_early)); n_late = 1100 - n_early
pick = np.concatenate([rng.choice(idx_early, size=n_early, replace=False), rng.choice(idx_late, size=n_late, replace=False)])
zcache = {}
def closes_for(s, months):
    key = (s, tuple(sorted(months)))
    if key in zcache: return zcache[key]
    cl = {}
    for mo in sorted(months):
        cands = [f"{ROOT}/klines5m/{s}/{s}-5m-{mo}.zip"] + [f"{ROOT}/klines5m/{s}/{s}-5m-{mo}-{d:02d}.zip" for d in range(1, 32)]
        for zp in cands:
            if not os.path.exists(zp): continue
            with zipfile.ZipFile(zp) as z: raw = z.read(z.namelist()[0]).decode().splitlines()
            for ln in raw:
                p = ln.split(",")
                if p and p[0].isdigit(): cl[int(p[0]) // 1000 + 300] = float(p[4])   # bar close time = open_time + 5 min
    zcache[key] = cl; return cl
res = []; skipped_missing = 0; skipped_clip = 0
for i in pick:
    E = int(drow[i]); m = MS[i]; N = int(dts[i])
    cand = [j for j in m if np.isfinite(y4s[i, j]) and fin[E + 1:E + 49, j].all()]
    if not cand: skipped_missing += 1; continue
    j = int(rng.choice(cand))
    if np.abs(r5[E + 1:E + 49, j]).max() >= 0.3: skipped_clip += 1
    months = set()
    for t in (N, N + 4 * 3600): g = time.gmtime(t); months.add(f"{g.tm_year}-{g.tm_mon:02d}")
    cl = closes_for(syms[j], months)
    c0 = cl.get(N); c1 = cl.get(N + 4 * 3600)
    if c0 is None or c1 is None: skipped_missing += 1; continue
    y_raw = c1 / c0 - 1.0
    # information: float16 quantisation bound of the cache path (each 5m return rounded to float16, rel. step 2^-11): |Δ| <= (1+|y|)·Σ|r_i|·2^-11 to first order
    rr = np.abs(r5[E + 1:E + 49, j].astype(np.float64)); f16_bound = float((1.0 + abs(y_raw)) * rr.sum() * 2.0 ** -11)
    res.append({"anchor": iso(N), "symbol": syms[j], "y4s": float(y4s[i, j]), "raw": float(y_raw), "y4old": float(y4old[i, j]), "year": int(yrs[i]), "clipped": bool(rr.max() >= 0.3), "f16_bound": f16_bound, "abs_diff": float(abs(y4s[i, j] - y_raw))})
d = np.array([abs(r["y4s"] - r["raw"]) for r in res]); d_nc = np.array([abs(r["y4s"] - r["raw"]) for r in res if not r["clipped"]])
n_early_done = sum(1 for r in res if r["year"] <= 2021)
b2 = {"n_sampled": len(res), "n_2020_21": n_early_done, "n_skipped_missing_bars_or_rows": skipped_missing, "n_clipped_cells_in_sample": skipped_clip,
      "max_abs_diff_all": float(d.max()), "p99_abs_diff": float(np.percentile(d, 99)), "median_abs_diff": float(np.median(d)),
      "max_abs_diff_excluding_clipped": float(d_nc.max()) if len(d_nc) else float("nan"),
      "n_cells_over_2e-5": int((d > 2e-5).sum()), "n_cells_over_2e-5_within_f16_bound": int(sum(1 for r in res if r["abs_diff"] > 2e-5 and r["abs_diff"] <= 1.5 * r["f16_bound"])),
      "max_ratio_absdiff_over_f16_bound": float(max(r["abs_diff"] / max(r["f16_bound"], 1e-12) for r in res)),
      "pass": bool(len(res) >= 1000 and n_early_done >= 300 and d.max() <= 2e-5), "worst": sorted(res, key=lambda r: -abs(r["y4s"] - r["raw"]))[:5]}
out["b2_y4s_vs_raw"] = b2
print(f"  (b2) y4s vs raw closes: n {len(res)} (2020-21: {n_early_done}); max|Δ| {b2['max_abs_diff_all']:.3e} (p99 {b2['p99_abs_diff']:.2e}, median {b2['median_abs_diff']:.2e}); excl. clipped cells {b2['max_abs_diff_excluding_clipped']:.3e}; skipped {skipped_missing} -> {'PASS' if b2['pass'] else 'FAIL'}", flush=True)
print(f"  (b2) info: cells over 2e-5: {b2['n_cells_over_2e-5']}, of which within 1.5x the float16 quantisation bound: {b2['n_cells_over_2e-5_within_f16_bound']}; max |Δ|/f16_bound over all cells {b2['max_ratio_absdiff_over_f16_bound']:.2f}", flush=True)
for r in b2["worst"][:3]: print(f"       worst: {r}", flush=True)
# ---- (b3) Σ-simple vs Π(1+r)-1 information (cell level, per year, bps)
info = {}
for y in sorted(set(yrs.tolist())):
    mrow = yrs == y; a = y4old[mrow]; b = y4s[mrow]; ok = np.isfinite(a) & np.isfinite(b)
    info[str(y)] = {"n_cells": int(ok.sum()), "mean_y4old_minus_y4s_bps": float(np.mean(a[ok] - b[ok]) * 1e4), "mean_abs_bps": float(np.mean(np.abs(a[ok] - b[ok])) * 1e4), "nan_mismatch": int((np.isfinite(a) ^ np.isfinite(b)).sum())}
out["b3_sum_vs_prod_info"] = info
print("  (b3) Σ-simple[E,E+47] − Π(1+r)−1[E+1,E+48] per year (bps): " + " | ".join(f"{y}: {v['mean_y4old_minus_y4s_bps']:+.3f} (|·| {v['mean_abs_bps']:.2f}, n {v['n_cells']})" for y, v in info.items()), flush=True)
out["G3_PASS"] = bool(out["a_static"]["pass"] and out["b1_Y4_sum"]["pass"] and b2["pass"])
print(f"G3 (a) {'PASS' if out['a_static']['pass'] else 'FAIL'} (b1) {'PASS' if out['b1_Y4_sum']['pass'] else 'FAIL'} (b2) {'PASS' if b2['pass'] else 'FAIL'} => {'PASS' if out['G3_PASS'] else 'FAIL'}", flush=True)
json.dump(out, open(f"{ROOT}/results/G3.json", "w"), indent=1); print("wrote results/G3.json")
