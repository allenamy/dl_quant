#!/usr/bin/env python3
"""b7v2_ctrl_diag.py — DIAGNOSTIC, NON-GATING. Why did the v1 B7 positive control (b7_compare.py 27fdcf8d…, run 2026-09-24T13Z, receipt
m3_shadow_b7_2026-09-24/receipts/run_2026-09-24T13Z) miss its frozen gate "max |Δβ| ≤ 1e-6 on ≥ 100 clean names" (observed 7.64e-4 on 449)?
Written and committed BEFORE any of its numbers were read. Changes nothing in the v1 verdict (UNDECIDED stays UNDECIDED).

HYPOTHESIS H (from reading the certified chain; NOT yet measured). The certified table price_full_raw_x0918r (23af32bd) is not log(close)
at the 4h boundaries. It is cumsum(log1p(ret5)) over the f16 cache x0918r (08bb2957) channel ret5 (rp_lib.base_logs; the cache builder's math
per rp_lib's docstring: ret5 = float16(clip(close_t / close_{t-5m} − 1, ±0.3))), with clipped bars restored from official klines and gap bars
filled (bt_prices_full_x0918r.py). Every f16 cell carries a rounding error of at most half an f16 ulp; over the 48 cells of a 4h bar these
errors do not telescope, whereas log(C_k / C_{k−1}) from 4h kline closes is exact. The v1 gate compared two different inputs at 1e-6.

INPUTS (pod2, read-only; each sha asserted): the certified table + meta; the f16 cache x0918r; rp_lib.py; the v1 control row
CTRL_certified_beta_1789761600.npz (1a35f9da, from BETA_M3_full 6dcf9782); the v1 klines KLINES_RAW.jsonl.gz (sha = the v1 FETCH_MANIFEST's);
the v1 per-name control CSV B7_CONTROL_per_name.csv (3c0fee8b); m2_lib.py (93f8e760, unchanged).

BASELINE ASSERTIONS (each refuses the run, exit 3 — they certify that this device reproduces both v1 sides before it measures anything):
  B1 the certified path on a slice of the table (m2_lib.bars_4h on rows [G0, ACTRL], meta first_fin / last_fin, UA cells in the slice) →
     m2_lib.betas_at(ACTRL) equals the certified row bitwise (uint64 view) on every symbol.
  B2 the v1 research path (b7_compare.py L84–116 construction, re-typed below as lp_from_boundaries) fed with the v1 klines reproduces the
     v1 CSV's beta_klines on every CSV row within 1e-13 (Mac numpy 1.26.4 vs pod2 numpy — max reported).
MEASUREMENTS:
  M1 input bound. For each v1 clean control name (CSV rows with ua_in_certified_window False) and each of the 180 4h bars (T_{k−1}, T_k]
     ending at ACTRL with a kline close at both ends: e = [table(T_k) − table(T_{k−1})] − [log C_k − log C_{k−1}]. The 48 cache cells with
     ts in (T_{k−1}, T_k] classify the bar: PURE = all 48 finite, none at the f16 clip bound, none gap-filled; OTHER otherwise (reported,
     not tested). PURE bound B = Σ_i h_i / (1 − |a_i| − h_i) + 1e-12, a_i = the f16 value, h_i = np.spacing(float16 |a_i|) / 2 (≥ the
     round-to-nearest error on either side of a_i). H predicts 0 PURE bars with |e| > B; each violation is named.
     RED CONTROL (the test must be able to fail): the same count against B/10 must be > 0, else the bound is too loose to discriminate and
     the reading is INCONCLUSIVE.
  M2 path identity. The v1 research path fed with the TABLE's boundary values (same availability as the klines; a table value that is not
     finite where a kline exists is treated as missing, counted) → β_tab. On the clean names: count bitwise equal to the certified β, max |Δ|,
     and, for names that differ, whether their 180-bar validity masks differ between the two paths (named).
  M3 attribution. Per clean name: gap = β_klines − β_cert, input part = β_klines − β_tab, path part = β_tab − β_cert (gap = input + path
     exactly). Reported: max |gap|, max |input|, max |path|, Σ|path| / Σ|gap|.
  M4 against the frozen B7 v2 rule (i) band (docs/DECISION_RULE_B7_v2_m3_shadow_2026-09-25.md, b80f52b39): number of clean names with
     |β_klines − β_cert| > max(0.01·|β_cert|, 0.002). REPORT ONLY — the rule was set on other data and is not recalibrated here.
READING (printed verbatim as the last line):
  H_SUPPORTED   iff M1 has 0 violations on ≥ 1000 PURE bars AND its red control is > 0 AND M2 is bitwise on every clean name whose
                validity masks agree;
  H_REFUTED     iff M1 has ≥ 1 violation;
  INCONCLUSIVE  otherwise (named reason).
usage (pod2): env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B b7v2_ctrl_diag.py <klines_gz> <control_csv> <ctrl_npz> <out_dir>
"""
import csv, gzip, hashlib, json, math, os, sys, time, zipfile, importlib.util

_extra = sorted(set(os.environ) - {"PATH", "HOME", "LC_CTYPE"})
assert not _extra, f"env outside whitelist PATH,HOME,LC_CTYPE: {_extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import m2_lib as M

ACTRL = 1789761600; H4 = 14400; ROW = 300; NB = 180; G0 = ACTRL - NB * H4; BTC = "BTCUSDT"
PIN = {
    "table": ("/workspace/baseline_tables_2026-09-19/work/price_full_raw_x0918r.npy", "23af32bd97c267d126c2109641815b92082b8688e35bcfbaaa1e88c2dc5bb5d8"),
    "meta": ("/workspace/baseline_tables_2026-09-19/work/price_full_raw_x0918r_meta.npz", "d1e49cc9f0a7ddc4104feb52a42da3024ba1e66ad5891a26c96f00cff7ce5d90"),
    "cache": ("/workspace/axis_0919/x0918r/data/dlnative_5m_wide829_f16_holefix2_x0918r.npz", "08bb295745e6df84cb42574ef073dc54817a19ad7754bf6319cfcb30bd9baa75"),
    "rp_lib": ("/workspace/raw_price_fix_2026-09-19/devices/rp_lib.py", "f802036f1a2e9e9f13f7347c49ecda68b54a38b9b2c6f3167f6ba40295c61488"),
    "m2_lib": (os.path.join(HERE, "m2_lib.py"), "93f8e76088ca523158df4d3ddb12f4f3239d0b75e3e0f7362ecc9ced914c8c9d"),
}
ARG_PIN = {"klines_gz": "78a7656c420107f8443b3dd02b7c072de1c88bcaaadaceb736550dcff616d24a",
           "control_csv": "3c0fee8bd84fae17d9c10b41ee814cdb991ee02d5afff8df45b887e53f3046f8",
           "ctrl_npz": "1a35f9da3bb87c67ca40dbf082fcbcbca9ae00c2aed4fecb2606132a65c763ba"}
T0 = time.time()


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)


def qs(x):
    x = np.asarray(x, float)
    if x.size == 0: raise ValueError("empty sequence")
    return {"n": int(x.size), "p50": float(np.quantile(x, .5)), "p90": float(np.quantile(x, .9)), "p99": float(np.quantile(x, .99)), "max": float(x.max())}


def refuse(rec, out, why):
    rec["refused"] = why; json.dump(rec, open(os.path.join(out, "B7V2_CTRL_DIAG.json"), "w"), indent=1, default=str)
    print("B7V2_CTRL_DIAG REFUSED", why, flush=True); sys.exit(3)


def lp_from_boundaries(syms, vals):
    """b7_compare.py L91–114 construction, re-typed (the only change: the boundary log price comes from `vals[s][t]` instead of
    log(float(close))). vals: {symbol: {boundary_ts: log price}} with only the boundaries that exist. Grid [G0, ACTRL]."""
    grid = np.arange(G0, ACTRL + 1, ROW, dtype=np.int64); nS = len(syms)
    LP = np.full((len(grid), nS), np.nan); ff = np.full(nS, -1, np.int64); lf = np.full(nS, -1, np.int64)
    bnd = np.arange(G0, ACTRL + 1, H4, dtype=np.int64); brow = ((bnd - G0) // ROW).astype(np.int64)
    ua_r, ua_c = [], []
    for j, s in enumerate(syms):
        px = vals.get(s, {})
        have = [t for t in bnd.tolist() if t in px]
        if not have: continue
        ff[j], lf[j] = min(have), max(have)
        last = np.nan
        for t, r0 in zip(bnd.tolist(), brow.tolist()):
            if t in px: last = px[t]; LP[r0, j] = last
            elif ff[j] <= t <= lf[j]: ua_r.append(r0); ua_c.append(j)
            nxt = r0 + H4 // ROW
            if nxt <= len(grid) - 1 and np.isfinite(last): LP[r0 + 1:nxt, j] = last
    return LP, grid, ff, lf, np.array(ua_r, np.int64), np.array(ua_c, np.int64)


def main():
    kl_p, csv_p, ctrl_p, out = [os.path.abspath(a) for a in sys.argv[1:5]]; os.makedirs(out, exist_ok=True)
    rec = {"device": "b7v2_ctrl_diag.py", "self_sha256": sha(os.path.abspath(__file__)), "status": "DIAGNOSTIC, NON-GATING",
           "python": sys.version.split()[0], "numpy": np.__version__, "argv": sys.argv, "utc_start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "inputs": {}, "anchor_ctrl": ACTRL, "window": [G0, ACTRL]}
    for k, (p, s) in PIN.items():
        g = sha(p); rec["inputs"][k] = {"path": p, "sha256": g}
        if g != s: refuse(rec, out, f"pin {k}: {g[:16]} != {s[:16]}")
    for k, p in (("klines_gz", kl_p), ("control_csv", csv_p), ("ctrl_npz", ctrl_p)):
        g = sha(p); rec["inputs"][k] = {"path": p, "sha256": g}
        if g != ARG_PIN[k]: refuse(rec, out, f"pin {k}: {g[:16]} != {ARG_PIN[k][:16]}")
    spec = importlib.util.spec_from_file_location("rp_lib", PIN["rp_lib"][0]); RL = importlib.util.module_from_spec(spec); spec.loader.exec_module(RL)

    PM = np.load(PIN["meta"][0], allow_pickle=True); SY = [str(s) for s in PM["symbols"]]; sj = {s: j for j, s in enumerate(SY)}
    grid_t = PM["grid"].astype(np.int64); g0t = int(grid_t[0])
    if not np.all(np.diff(grid_t) == ROW): refuse(rec, out, "table grid not 5-minute contiguous")
    r_lo, r_hi = (G0 - g0t) // ROW, (ACTRL - g0t) // ROW
    if int(grid_t[r_lo]) != G0 or int(grid_t[r_hi]) != ACTRL: refuse(rec, out, "window rows off the table grid")
    TAB = np.load(PIN["table"][0], mmap_mode="r"); TS_ = np.asarray(TAB[r_lo:r_hi + 1], np.float64)
    C = np.load(ctrl_p); csy = [str(s) for s in C["symbols"]]
    if csy != SY: refuse(rec, out, "control symbols != table symbols")

    # ---- B1: certified path on the slice reproduces the certified row bitwise ----
    ur = PM["unavail_grid_row"].astype(np.int64); uc = PM["unavail_col"].astype(np.int64)
    ins = (ur >= r_lo) & (ur <= r_hi)
    T1, R1, V1 = M.bars_4h(TS_, grid_t[r_lo:r_hi + 1], PM["first_fin"].astype(np.int64), PM["last_fin"].astype(np.int64), ur[ins] - r_lo, uc[ins])
    Bc, Nc, Ec, _ = M.betas_at(T1, R1, V1, np.array([ACTRL], np.int64), sj[BTC])
    b1 = np.array_equal(Bc[0].view(np.uint64), np.ascontiguousarray(C["beta"], np.float64).view(np.uint64)) and np.array_equal(Nc[0], C["nobs"].astype(np.int32)) \
        and np.array_equal(Ec[0], C["est"].astype(bool))
    rec["B1_certified_path_bitwise"] = bool(b1)
    if not b1: refuse(rec, out, "B1: the certified path on the slice does not reproduce the certified row bitwise")
    log("B1 OK")

    # ---- klines (b7_compare.py L86–101 rules) ----
    kl = {}
    with gzip.open(kl_p, "rt") as f:
        for ln in f:
            d = json.loads(ln); kl[d["symbol"]] = json.loads(d["body"])
    ksy = sorted(kl); logc = {}; bad = 0
    for s in ksy:
        px = {}
        for k in kl[s]:
            ot, ct, c = int(k[0]) // 1000, int(k[6]), float(k[4])
            if ct != (ot + H4) * 1000 - 1 or not (c > 0): bad += 1; continue
            if G0 <= ot + H4 <= ACTRL: px[ot + H4] = math.log(c)
        logc[s] = px
    rec["klines"] = {"n_symbols": len(ksy), "n_bad_klines_skipped": bad}

    # ---- B2: v1 research path reproduces the v1 CSV ----
    LPk, gk, ffk, lfk, uark, uack = lp_from_boundaries(ksy, logc)
    Tk, Rk, Vk = M.bars_4h(LPk, gk, ffk, lfk, uark, uack)
    Bk, Nk, Ek, _ = M.betas_at(Tk, Rk, Vk, np.array([ACTRL], np.int64), ksy.index(BTC))
    rows = list(csv.DictReader(open(csv_p)))
    kj = {s: j for j, s in enumerate(ksy)}
    d2 = [abs(float(Bk[0, kj[r["symbol"]]]) - float(r["beta_klines"])) for r in rows]
    rec["B2_v1_klines_path_max_abs_diff"] = float(max(d2)); rec["B2_n_rows"] = len(rows)
    if not (len(rows) >= 100 and max(d2) <= 1e-13): refuse(rec, out, f"B2: v1 klines β not reproduced (max {max(d2)})")
    log("B2 OK max", max(d2))
    clean = [r["symbol"] for r in rows if r["ua_in_certified_window"] == "False"]
    rec["n_clean_names"] = len(clean)

    # ---- M2: v1 path fed with the table's boundary values ----
    bnd = np.arange(G0, ACTRL + 1, H4, dtype=np.int64); brow_t = ((bnd - G0) // ROW).astype(np.int64)
    tvals = {}; n_tab_nonfinite_at_kline = 0
    for s in ksy:
        if s not in sj: continue
        j = sj[s]; px = {}
        for t in logc[s]:
            v = float(TS_[(t - G0) // ROW, j])
            if np.isfinite(v): px[t] = v
            else: n_tab_nonfinite_at_kline += 1
        tvals[s] = px
    tsy = sorted(tvals)
    LPt, gt, fft, lft, uart, uact = lp_from_boundaries(tsy, tvals)
    Tt, Rt, Vt = M.bars_4h(LPt, gt, fft, lft, uart, uact)
    Bt, Nt, Et, _ = M.betas_at(Tt, Rt, Vt, np.array([ACTRL], np.int64), tsy.index(BTC))
    tj = {s: j for j, s in enumerate(tsy)}
    per = []; m2_bitwise = 0; m2_mask_diff = []; m2_nonbit_same_mask = []
    for s in clean:
        j = sj[s]; bc = float(Bc[0, j]); bt = float(Bt[0, tj[s]]); bk = float(Bk[0, kj[s]])
        same_bits = np.float64(bt).view(np.uint64) == np.float64(bc).view(np.uint64)
        mask_same = bool(np.array_equal(Vt[1:, tj[s]] & Vt[1:, tsy.index(BTC)], V1[1:, j] & V1[1:, sj[BTC]]))
        if same_bits: m2_bitwise += 1
        elif mask_same: m2_nonbit_same_mask.append(s)
        else: m2_mask_diff.append(s)
        per.append([s, bc, bt, bk, bk - bc, bk - bt, bt - bc, int(Nc[0, j]), int(Nt[0, tj[s]]), mask_same])
    rec["M2"] = {"n_clean": len(clean), "n_bitwise_equal": m2_bitwise, "n_differ_same_mask": len(m2_nonbit_same_mask), "differ_same_mask": m2_nonbit_same_mask,
                 "n_differ_mask_differs": len(m2_mask_diff), "differ_mask_differs": m2_mask_diff, "n_table_nonfinite_where_kline": n_tab_nonfinite_at_kline,
                 "max_abs_path_part": float(max(abs(p[6]) for p in per))}
    gap = np.array([p[4] for p in per]); inp = np.array([p[5] for p in per]); pth = np.array([p[6] for p in per])
    rec["M3"] = {"max_abs_gap": float(np.abs(gap).max()), "max_abs_input_part": float(np.abs(inp).max()), "max_abs_path_part": float(np.abs(pth).max()),
                 "sum_abs_path_over_sum_abs_gap": float(np.abs(pth).sum() / np.abs(gap).sum()), "abs_gap": qs(np.abs(gap)), "abs_input_part": qs(np.abs(inp))}
    band = [p for p in per if abs(p[4]) > max(0.01 * abs(p[1]), 0.002)]
    rec["M4_rule_i_band_exceed"] = {"n": len(band), "names": [[p[0], p[1], p[3], p[4]] for p in band],
                                    "note": "REPORT ONLY; rule (i) of b80f52b39 is 必报不作门 and was set on other data"}
    log("M2/M3/M4 done")

    # ---- M1: f16 rounding bound per 4h bar (stream the cache ret5 channel for the window) ----
    Z = np.load(PIN["cache"][0], allow_pickle=True); CTS = Z["ts"].astype(np.int64); CSY = [str(s) for s in Z["symbols"]]; CH = [str(c) for c in Z["ch"]]
    if CSY != SY or CH[0] != "ret5" or not np.all(np.diff(CTS) == ROW): refuse(rec, out, "cache axes")
    c_lo = int(np.searchsorted(CTS, G0 + ROW)); c_hi = int(np.searchsorted(CTS, ACTRL))
    if int(CTS[c_lo]) != G0 + ROW or int(CTS[c_hi]) != ACTRL: refuse(rec, out, "cache window rows")
    zf = zipfile.ZipFile(PIN["cache"][0]); fh = zf.open("data.npy"); ver = np.lib.format.read_magic(fh)
    shp, fo, dt = (np.lib.format.read_array_header_1_0(fh) if ver == (1, 0) else np.lib.format.read_array_header_2_0(fh))
    if not (shp == (len(CTS), len(SY), len(CH)) and not fo and dt == np.float16): refuse(rec, out, f"cache data header {shp}")
    rowb = len(SY) * len(CH) * 2; W = np.empty((c_hi - c_lo + 1, len(SY)), np.float16); r0 = 0
    while r0 <= c_hi:
        k = min(8192, c_hi + 1 - r0); buf = fh.read(k * rowb)
        if len(buf) != k * rowb: refuse(rec, out, "short read")
        a, b = max(r0, c_lo), r0 + k
        if b > a: W[a - c_lo:b - c_lo] = np.frombuffer(buf, np.float16).reshape(k, len(SY), len(CH))[a - r0:b - r0, :, 0]
        r0 += k
    fh.close(); log("cache window streamed", W.shape)
    gfr = PM["gapfilled_grid_row"].astype(np.int64); gfc = PM["gapfilled_col"].astype(np.int64)
    gts = g0t + gfr * ROW; gin = (gts > G0) & (gts <= ACTRL)
    GF = np.zeros(W.shape, bool); GF[(gts[gin] - (G0 + ROW)) // ROW, gfc[gin]] = True
    A64 = W.astype(np.float64); fin = np.isfinite(A64); bound = RL.is_bound(W)
    Hh = np.where(fin, np.spacing(np.abs(W).astype(np.float16)).astype(np.float64) / 2.0, np.nan)
    termB = Hh / (1.0 - np.abs(A64) - Hh)
    n_pure = 0; n_red = 0; viol = []; ratios = []; e_pure = []; e_other = []; n_skip_nokl = 0
    for s in clean:
        j = sj[s]; px = logc[s]
        for k in range(1, NB + 1):
            ta, tb = int(bnd[k - 1]), int(bnd[k])
            if ta not in px or tb not in px: n_skip_nokl += 1; continue
            e = (float(TS_[brow_t[k], j]) - float(TS_[brow_t[k - 1], j])) - (px[tb] - px[ta])
            sl = slice((ta + ROW - (G0 + ROW)) // ROW, (tb - (G0 + ROW)) // ROW + 1)
            if sl.stop - sl.start != 48: refuse(rec, out, "bar slice length")
            f, bd, gf = fin[sl, j], bound[sl, j], GF[sl, j]
            if f.all() and not bd.any() and not gf.any():
                B = float(termB[sl, j].sum()) + 1e-12; n_pure += 1; e_pure.append(abs(e)); ratios.append(abs(e) / B)
                if abs(e) > B: viol.append([s, tb, e, B])
                if abs(e) > B / 10.0: n_red += 1
            else:
                e_other.append(abs(e))
    rec["M1"] = {"n_pure_bars": n_pure, "n_other_bars": len(e_other), "n_bars_without_kline_ends": n_skip_nokl, "n_violations": len(viol), "red_control_n_over_bound_div10": n_red,
                 "violations_first50": viol[:50], "abs_e_pure": qs(e_pure) if e_pure else None, "abs_e_over_bound_pure": qs(ratios) if ratios else None,
                 "abs_e_other": qs(e_other) if e_other else None}
    log("M1 done", n_pure, len(viol))

    if len(viol) >= 1: reading = "H_REFUTED"; why = f"{len(viol)} PURE bars exceed the f16 bound"
    elif n_pure >= 1000 and n_red > 0 and len(m2_nonbit_same_mask) == 0: reading = "H_SUPPORTED"; why = "0 violations; path bitwise where masks agree"
    else: reading = "INCONCLUSIVE"; why = f"n_pure={n_pure}, red={n_red}, differ_same_mask={len(m2_nonbit_same_mask)}"
    rec["reading"] = reading; rec["reading_reason"] = why; rec["utc_end"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(os.path.join(out, "B7V2_CTRL_DIAG_per_name.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["symbol", "beta_cert", "beta_tabpath", "beta_klines", "gap_kl_minus_cert", "input_part_kl_minus_tab",
                                       "path_part_tab_minus_cert", "nobs_cert", "nobs_tabpath", "pair_mask_same"]); w.writerows(per)
    op = os.path.join(out, "B7V2_CTRL_DIAG.json"); json.dump(rec, open(op, "w"), indent=1, default=str)
    print(f"B7V2_CTRL_DIAG READING={reading} n_pure={n_pure} n_viol={len(viol)} red_div10={n_red} M2_bitwise={m2_bitwise}/{len(clean)} "
          f"max_gap={rec['M3']['max_abs_gap']} max_path={rec['M3']['max_abs_path_part']} M4_band_exceed={len(band)} out_sha256={sha(op)}", flush=True)


if __name__ == "__main__":
    main()
