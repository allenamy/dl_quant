"""gate_G1.py — PREREG_second_instrument_rebuild_2026-09-05 §2 G1 / G1b.
G1 : rebuilt panel (stage 3) vs /workspace/data/wide_panel_4h_v1.npz (= 08-21 wide_panel_4h_hist_v2.npz, sha f14bc33d…):
     every array must have identical NaN positions and bitwise-equal finite values => PASS. Otherwise: per column x year counts of
     unequal cells + max|Δ|, NaN-position mismatches, top symbols, and a classification (data-source coverage / data content /
     float non-determinism) — never a manual fix. For Y4 mismatches (if any) a few cells are recomputed by hand from the raw zips.
G1b: rebuilt cache (2022+ segment) vs /workspace/data/dlnative_5m_wide829_f16_ext.npz on common (ts, symbol): unequal share per channel
     (informational, no threshold).
Writes results/G1.json. Prints G1 PASS/FAIL. Exit code 0 always (chain continues per prereg)."""
import os, sys, json, time, hashlib, zipfile, io
import numpy as np
ROOT = os.environ.get("JR_ROOT", "/workspace/review_scratch/jpline_rebuild")   # JR_ROOT only for the dry-test harness
sys.path.insert(0, f"{ROOT}/src"); from zload import zload
PA = os.environ.get("G1_A", f"{ROOT}/data/wide_panel_4h_hist_v2_rebuilt.npz"); PB = os.environ.get("G1_B", "/workspace/data/wide_panel_4h_v1.npz")   # env overrides only for the dry test of this script
CA = f"{ROOT}/data/dlnative_5m_wide829_f16_hist.npz"; CB = "/workspace/data/dlnative_5m_wide829_f16_ext.npz"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
def yr(t): return time.gmtime(int(t)).tm_year
T0 = time.time()
out = {"self_sha256": sha(os.path.abspath(__file__)), "inputs": {"rebuilt_panel": {"path": PA, "sha256": sha(PA)}, "v1_panel": {"path": PB, "sha256": sha(PB)}}}
print(f"G1 inputs: rebuilt {out['inputs']['rebuilt_panel']['sha256'][:16]}  v1 {out['inputs']['v1_panel']['sha256'][:16]}", flush=True)
A = np.load(PA, allow_pickle=True); B = np.load(PB, allow_pickle=True)
ka, kb = list(A.files), list(B.files)
out["keys"] = {"rebuilt": ka, "v1": kb, "same_set": sorted(ka) == sorted(kb), "same_order": ka == kb}
print(f"keys same_set {out['keys']['same_set']} same_order {out['keys']['same_order']}; rebuilt-only {sorted(set(ka)-set(kb))} v1-only {sorted(set(kb)-set(ka))}", flush=True)
tsa = A["ts"].astype(np.int64); tsb = B["ts"].astype(np.int64)
sa = [str(s) for s in A["symbols"]]; sb = [str(s) for s in B["symbols"]]
out["ts"] = {"n_rebuilt": int(len(tsa)), "n_v1": int(len(tsb)), "equal": bool(np.array_equal(tsa, tsb)),
             "first_rebuilt": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(tsa[0]))), "last_rebuilt": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(tsa[-1]))),
             "first_v1": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(tsb[0]))), "last_v1": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(tsb[-1])))}
out["symbols"] = {"equal": sa == sb, "n_rebuilt": len(sa), "n_v1": len(sb)}
print(f"ts equal {out['ts']['equal']} ({out['ts']['n_rebuilt']} vs {out['ts']['n_v1']}); symbols equal {out['symbols']['equal']}", flush=True)
# align on common ts (identity if equal)
common = np.intersect1d(tsa, tsb); ia = {int(t): i for i, t in enumerate(tsa)}; ib = {int(t): i for i, t in enumerate(tsb)}
ra = np.array([ia[int(t)] for t in common]); rb = np.array([ib[int(t)] for t in common])
yrs = np.array([yr(t) for t in common]); years = sorted(set(yrs.tolist()))
assert sa == sb, "symbol axes differ; column alignment would be ambiguous"
cols = {}; all_pass = out["ts"]["equal"] and out["symbols"]["equal"] and out["keys"]["same_set"]
mism_cells = {}
for k in ka:
    if k in ("ts", "symbols") or k not in kb: continue
    a = A[k][ra]; b = B[k][rb]
    rec = {"shape": list(a.shape), "dtype": str(a.dtype)}
    if a.dtype == bool or b.dtype == bool:
        neq = a != b; rec.update({"kind": "bool", "n_neq": int(neq.sum()), "by_year": {str(y): int(neq[yrs == y].sum()) for y in years}, "pass": bool(neq.sum() == 0)})
    else:
        a64 = a.astype(np.float64); b64 = b.astype(np.float64)
        fa = np.isfinite(a64); fb = np.isfinite(b64); nanmis = fa ^ fb; both = fa & fb
        neq = both & (a64 != b64); d = np.where(neq, np.abs(a64 - b64), 0.0)
        rel = np.where(neq, d / np.maximum(np.abs(b64), 1e-12), 0.0)
        rec.update({"kind": "float", "n_finite_both": int(both.sum()), "n_neq": int(neq.sum()), "n_nan_mismatch": int(nanmis.sum()),
                    "n_nan_only_rebuilt": int((fb & ~fa).sum()), "n_nan_only_v1": int((fa & ~fb).sum()),
                    "max_abs_diff": float(d.max()) if neq.any() else 0.0, "max_rel_diff": float(rel.max()) if neq.any() else 0.0,
                    "by_year": {str(y): {"n_neq": int(neq[yrs == y].sum()), "n_nan_mismatch": int(nanmis[yrs == y].sum()), "max_abs_diff": float(d[yrs == y].max()) if (yrs == y).any() else 0.0} for y in years},
                    "pass": bool(neq.sum() == 0 and nanmis.sum() == 0)})
        if not rec["pass"]:
            bad = neq | nanmis; per_sym = bad.sum(0); top = np.argsort(-per_sym)[:12]
            rec["top_symbols"] = [(sa[j], int(per_sym[j])) for j in top if per_sym[j] > 0]
            rec["n_symbols_affected"] = int((per_sym > 0).sum())
            first_bad = np.argwhere(bad)[:5]; rec["first_bad_cells"] = [(time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(common[i]))), sa[j], float(a64[i, j]), float(b64[i, j])) for i, j in first_bad]
            # classification heuristic (evidence, not a fix)
            if neq.sum() > 0 and nanmis.sum() == 0 and rec["max_rel_diff"] <= 1e-5: rec["class"] = "float non-determinism (all unequal cells within 1e-5 relative)"
            elif neq.sum() == 0 and nanmis.sum() > 0: rec["class"] = "coverage (NaN-position only: one side has data the other lacks)"
            elif k.startswith("f_fund"): rec["class"] = "funding-source difference (pod2 funding zips 2019-09..2026-08 for 829 symbols + 09-01 API tail vs the 08-21 pod's funding set) — see per-year table"
            else: rec["class"] = "data content differs (raw zip rows or code path) — see hand check"
            mism_cells[k] = (bad, a64, b64)
    cols[k] = rec; all_pass &= rec["pass"]
    tag = "PASS" if rec["pass"] else "FAIL"
    extra = "" if rec["pass"] else (f" n_neq {rec.get('n_neq')} nan_mismatch {rec.get('n_nan_mismatch')} max|Δ| {rec.get('max_abs_diff', 0):.3e} rel {rec.get('max_rel_diff', 0):.2e} symbols {rec.get('n_symbols_affected')} :: {rec.get('class')}")
    print(f"  {k:16s} {tag}{extra}", flush=True)
    if not rec["pass"] and rec.get("kind") == "float":
        print("      by year: " + " | ".join(f"{y}: neq {v['n_neq']} nan {v['n_nan_mismatch']} max {v['max_abs_diff']:.2e}" for y, v in rec["by_year"].items()), flush=True)
        print(f"      top symbols: {rec['top_symbols'][:8]}", flush=True)
out["columns"] = cols; out["G1_PASS"] = bool(all_pass)
print(f"G1 {'PASS' if all_pass else 'FAIL'}: {sum(1 for c in cols.values() if c['pass'])}/{len(cols)} arrays bitwise (NaN positions + finite values), ts equal {out['ts']['equal']}", flush=True)
# ---- hand check from raw zips for Y4 mismatches (definition: Σ_{rows E..E+47} float16(clip(pct_change(close), ±0.3)), rows = bar close times)
if "Y4" in mism_cells:
    bad, a64, b64 = mism_cells["Y4"]; cells = np.argwhere(bad)
    rng = np.random.default_rng(20260905); pick = cells[rng.choice(len(cells), size=min(6, len(cells)), replace=False)]
    hand = []
    for i, j in pick:
        N = int(common[i]); s = sa[j]; months = set()
        for t in (N - 300, N + 47 * 300):
            g = time.gmtime(t); months.add(f"{g.tm_year}-{g.tm_mon:02d}")
        closes = {}
        for mo in sorted(months):
            for zp in (f"{ROOT}/klines5m/{s}/{s}-5m-{mo}.zip",) + tuple(f"{ROOT}/klines5m/{s}/{s}-5m-{mo}-{d:02d}.zip" for d in range(1, 32)):
                if not os.path.exists(zp): continue
                with zipfile.ZipFile(zp) as z:
                    raw = z.read(z.namelist()[0]).decode().splitlines()
                for ln in raw:
                    p = ln.split(",")
                    if not p[0].isdigit(): continue
                    closes[int(p[0]) // 1000 + 300] = float(p[4])   # ts = open_time + 5min (bar close)
        rows = [N + 300 * q for q in range(-1, 48)]   # need close at E-1 .. E+47 to form 48 pct_changes for rows E..E+47
        cv = [closes.get(t, np.nan) for t in rows]
        r = np.array([(cv[q] / cv[q - 1] - 1.0) if (np.isfinite(cv[q]) and np.isfinite(cv[q - 1])) else np.nan for q in range(1, 49)])
        # NOTE: pandas pct_change(fill_method=None) uses the previous *present* row; when a bar is missing the next present bar's return spans the gap.
        rq = np.clip(r, -0.3, 0.3).astype(np.float16).astype(np.float32)
        nfin = int(np.isfinite(rq).sum()); y_hand = float(np.nansum(rq.astype(np.float64))) if nfin >= 46 else float("nan")
        hand.append({"anchor": time.strftime("%Y-%m-%d %H:%M", time.gmtime(N)), "symbol": s, "rebuilt": float(a64[i, j]), "v1": float(b64[i, j]), "hand_from_raw_zips": y_hand, "n_finite_bars": nfin,
                     "n_close_rows_found": int(np.isfinite(cv).sum())})
        print(f"  HAND Y4 {hand[-1]}", flush=True)
    out["Y4_hand_check"] = hand
# ---- G1b: cache 2022+ vs _ext cache
try:
    if os.environ.get("G1_SKIP_B") == "1": raise RuntimeError("G1b skipped by env (dry test)")
    ZA = zload(CA, allow_pickle=True); ZB = zload(CB, allow_pickle=True)
    ta = ZA["ts"].astype(np.int64); tb = ZB["ts"].astype(np.int64); cha = [str(c) for c in ZA["ch"]]; chb = [str(c) for c in ZB["ch"]]
    assert [str(s) for s in ZA["symbols"]] == [str(s) for s in ZB["symbols"]] and cha == chb
    ct = np.intersect1d(ta, tb); ja = np.searchsorted(ta, ct); jb = np.searchsorted(tb, ct)
    assert np.array_equal(ta[ja], ct) and np.array_equal(tb[jb], ct)
    yb = np.array([yr(t) for t in ct]); g1b = {"n_common_ts": int(len(ct)), "first": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(ct[0]))), "last": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(ct[-1]))), "channels": {}}
    DA = ZA["data"]; DB = ZB["data"]
    for c, nm in enumerate(cha):
        xa = DA[ja, :, c]; xb = DB[jb, :, c]
        fa = np.isfinite(xa); fb = np.isfinite(xb); both = fa & fb; nanmis = fa ^ fb
        neq = both & (xa != xb)
        rec = {"n_both_finite": int(both.sum()), "n_neq": int(neq.sum()), "unequal_share": float(neq.sum() / max(both.sum(), 1)), "n_nan_mismatch": int(nanmis.sum()),
               "n_nan_only_rebuilt": int((fb & ~fa).sum()), "n_nan_only_ext": int((fa & ~fb).sum()),
               "by_year": {str(y): {"n_neq": int(neq[yb == y].sum()), "n_nan_mismatch": int(nanmis[yb == y].sum()), "n_both": int(both[yb == y].sum())} for y in sorted(set(yb.tolist()))}}
        if neq.any():
            d = np.abs(xa[neq].astype(np.float64) - xb[neq].astype(np.float64)); rec["max_abs_diff"] = float(d.max()); rec["median_abs_diff"] = float(np.median(d))
        g1b["channels"][nm] = rec
        print(f"  G1b {nm:10s} both_finite {rec['n_both_finite']} neq {rec['n_neq']} ({rec['unequal_share']:.2e}) nan_mismatch {rec['n_nan_mismatch']} (only-rebuilt-NaN {rec['n_nan_only_rebuilt']}, only-ext-NaN {rec['n_nan_only_ext']})", flush=True)
    # NaN-mismatch rows: where are they (first rows of ext = pct_change left edge is a known artefact)
    xa = DA[ja, :, 0]; xb = DB[jb, :, 0]; nanmis = np.isfinite(xa) ^ np.isfinite(xb); rows_bad = np.where(nanmis.any(1))[0]
    g1b["ret5_nan_mismatch_rows"] = {"n_rows": int(len(rows_bad)), "first_rows": [time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(ct[r]))) for r in rows_bad[:10]]}
    print(f"  G1b ret5 NaN-mismatch rows {len(rows_bad)}: first {g1b['ret5_nan_mismatch_rows']['first_rows'][:6]}", flush=True)
    out["G1b"] = g1b
except Exception as e:
    out["G1b"] = {"error": repr(e)}; print(f"G1b error {e!r}", flush=True)
out["elapsed_s"] = round(time.time() - T0, 1)
json.dump(out, open(f"{ROOT}/results/G1.json", "w"), indent=1)
print(f"wrote results/G1.json ({out['elapsed_s']} s)", flush=True)
