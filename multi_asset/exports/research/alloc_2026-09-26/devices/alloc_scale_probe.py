#!/usr/bin/env python3
"""alloc_scale_probe.py — design-phase measurements for the combination-layer design (docs/DESIGN_combination_layer_2026-09-26.md).
READ-ONLY. NO candidate arm is built or read here. Two parts:

PART 1 (seats, in-service rule only, from legs.npz 9ee5886f):
  G1  recompute the in-service msharpe(900) seat from legs.npz LR exactly as nc_legs.py L42-L59 does (history at anchor i = the finite
      LR rows appended up to i, i.e. LR[:i] finite rows), cast to float32 like WL, and require BITWISE equality with legs.npz WL on every
      row where WL is finite. If this fails the device does not know the in-service operator and must STOP.
  S   descriptive of the in-service masked seat w2m = WL2/(WL0+WL2) per segment, and of the trailing-900 leg return sigma / correlation
      (king, fund) -- behavioural footprint only, no book reading.

PART 2 (noise scale, from EXISTING retained engine series already reported elsewhere; no new book is built):
  For pairs of existing cells, per segment: n full days, daily sigma of each book, daily correlation, sigma of the path-mean daily
  difference, iid SE, 30-day MBB SE (bt_tables.mbb_indices convention, B=10000, rng (20260923,1)), and dbar -- the dbar is printed ONLY
  as an instrument check against the already-committed SIGMA_F10_2026-09-25.json values (T0_s42 vs NC_s42X: pre2026 +0.51328...,
  2026 -1.25418...). If the check fails, PART 2 numbers are not reported.
usage: /workspace/venv/bin/python -B alloc_scale_probe.py <out.json>
"""
import os, sys, json, math, hashlib, calendar, time
import numpy as np

LEGS = "/dev/shm/news2_2026-09-23/work/legs.npz"
LEGS_SHA16 = "9ee5886f37d1727c"
R = "/workspace/dlarch_2026-09-24/receipts"
CELLS = {
    "NC_s42X": f"{R}/RETAIN_REFNC_s42_SELFCTL_2026-09-26.json/SER_DLARCH_REF_NC_s42X_scaled_rule_raw_UAFE.npz",
    "NC_s2027X": f"{R}/RETAIN_REFNC_s2027_2026-09-26.json/SER_DLARCH_REF_NC_s2027X_scaled_rule_raw_UAFE.npz",
    "NC_s7X": f"{R}/RETAIN_REFNC_s7_2026-09-26.json/SER_DLARCH_REF_NC_s7X_scaled_rule_raw_UAFE.npz",
    "T0_s42": f"{R}/RETAIN_s42_2026-09-25.json/SER_DLARCH_T0_s42_scaled_rule_raw_UAFE.npz",
    "F10FULL_s42": f"{R}/RETAIN_F10FULL_s42_2026-09-26.json/SER_DLARCH_G1_T0_nomask_frac1_s42_scaled_rule_raw_UAFE.npz",
}
PAIRS = [("T0_s42", "NC_s42X"), ("F10FULL_s42", "NC_s42X"), ("NC_s2027X", "NC_s42X"), ("NC_s7X", "NC_s42X")]
CHECK = {"pre2026": 0.5132805490339347, "2026": -1.2541852256446868}      # SIGMA_F10_2026-09-25.json t0_cells["42"].dbar
SEG = {"2023H2": ("2023-06-30T04:00:00Z", "2023-12-31T20:00:00Z"), "2024": ("2024-01-01T00:00:00Z", "2024-12-31T20:00:00Z"),
       "2025": ("2025-01-01T00:00:00Z", "2025-12-31T20:00:00Z"), "pre2026": ("2023-06-30T04:00:00Z", "2025-12-31T20:00:00Z"),
       "2026": ("2026-01-01T00:00:00Z", "2026-09-18T20:00:00Z")}      # 2026 = lead revision 3 extension to the X axis end
DAY = 86400; B = 10000; RNG = (20260923, 1); BLOCK = 30; LOOK = 900


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))


def msharpe_history(LR):
    """nc_legs.py L42-L59 verbatim in effect: LR list grows by one entry at anchor i (LRm[i-1] set at step i) BEFORE w3 is computed."""
    n = LR.shape[0]; hist = {"king": [], "rev24": [], "fund": []}; W = np.full((n, 3), np.nan)
    for i in range(n):
        if i >= 1 and np.isfinite(LR[i - 1]).all():
            for j, leg in enumerate(("king", "rev24", "fund")): hist[leg].append(float(LR[i - 1, j]))
        if len(hist["king"]) >= LOOK:
            r = np.stack([np.array(hist[leg][-LOOK:]) for leg in ("king", "rev24", "fund")])
            shp = r.mean(1) / (r.std(1) + 1e-9); shp = np.maximum(shp, 0.0)
            W[i] = shp / shp.sum() if shp.sum() > 0 else np.array([1 / 3] * 3)
        else:
            W[i] = np.array([1 / 3] * 3)
    return W


def mbb_indices(n, block, B, seed):     # bt_tables.py L220 verbatim
    block = int(min(block, n)); k = int(math.ceil(n / block))
    rng = np.random.default_rng(list(seed))
    st = rng.integers(0, n - block + 1, size=(B, k))
    return (st[:, :, None] + np.arange(block)[None, None, :]).reshape(B, k * block)[:, :n]


def daily(A, r):                          # bt_tables.py L105 verbatim
    d = (np.asarray(A, np.int64) // DAY) * DAY
    ud, inv = np.unique(d, return_inverse=True); out = np.ones(len(ud)); np.multiply.at(out, inv, 1.0 + np.asarray(r, float))
    return ud, out - 1.0


def main():
    out = {"device": "alloc_scale_probe.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "no_candidate_arm_read": True}
    # ───────── PART 1 ─────────
    ls = sha(LEGS); assert ls.startswith(LEGS_SHA16), f"legs.npz sha {ls[:16]} != {LEGS_SHA16}"
    L = np.load(LEGS); a = L["E_ts"].astype(np.int64); WL = L["WL"]; LR = L["LR"]; ready = L["ready"]
    Wre = msharpe_history(LR).astype(np.float32)
    fin = np.isfinite(WL).all(1)
    eq = np.array_equal(Wre[fin].view(np.uint32), WL[fin].view(np.uint32))
    ndiff = int((Wre[fin].view(np.uint32) != WL[fin].view(np.uint32)).any(1).sum())
    out["G1_seat_identity"] = {"legs_sha256": ls, "rows_compared": int(fin.sum()), "rows_ready": int(ready.sum()), "BITWISE_IDENTICAL": bool(eq),
                               "rows_differing": ndiff, "axis": [time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(a[0]))),
                                                                  time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(a[-1])))]}
    print("G1 seat identity", out["G1_seat_identity"], flush=True)
    assert eq, "G1 FAILED: the recomputed in-service seat is not bitwise WL -- STOP"
    # red control for G1: +1 bps on ONE fund LR entry must break it, on (at most) the <=900 anchors whose window holds that entry.
    # (Run 1 used a one-ulp float64 change and it did NOT fire: WL is float32, so the identity is at float32 resolution -- which is the
    # resolution evolve() consumes. The instrument was right, the expectation was wrong; kept here so the resolution is on record.)
    LR2 = LR.copy(); k = int(np.flatnonzero(np.isfinite(LR2).all(1))[5000]); LR2[k, 2] = LR2[k, 2] + 1.0
    Wred = msharpe_history(LR2).astype(np.float32)
    out["G1_red_control"] = {"perturbed_row": k, "delta": "+1.0 bps on one fund LR entry", "run1_one_ulp_float64_rows_differing": 0,
                             "rows_differing": int((Wred[fin].view(np.uint32) != WL[fin].view(np.uint32)).any(1).sum()), "max_possible": LOOK}
    assert out["G1_red_control"]["rows_differing"] > 0, "G1 red control did not fire"
    print("G1 red control", out["G1_red_control"], flush=True)
    W = WL.astype(np.float64); den = W[:, 0] + W[:, 2]; w2m = np.where(den > 1e-12, W[:, 2] / np.where(den > 1e-12, den, 1), 0.5)
    # trailing-900 leg sigma and correlation (king, fund), same history convention
    sig = np.full((len(a), 2), np.nan); cor = np.full(len(a), np.nan); hk, hf = [], []
    for i in range(len(a)):
        if i >= 1 and np.isfinite(LR[i - 1]).all(): hk.append(LR[i - 1, 0]); hf.append(LR[i - 1, 2])
        if len(hk) >= LOOK:
            x = np.array(hk[-LOOK:]); y = np.array(hf[-LOOK:]); sig[i] = [x.std(), y.std()]
            cor[i] = np.corrcoef(x, y)[0, 1] if x.std() > 0 and y.std() > 0 else np.nan
    seats = {}
    for s, (lo, hi) in SEG.items():
        m = (a >= ts(lo)) & (a <= ts(hi)) & ready & fin
        v = w2m[m]; sk = sig[m, 0]; sf = sig[m, 1]; ok = np.isfinite(sk) & np.isfinite(sf) & (sk > 0)
        seats[s] = {"n": int(m.sum()), "fund_seat_mean": float(v.mean()), "p10": float(np.percentile(v, 10)), "p50": float(np.median(v)),
                    "p90": float(np.percentile(v, 90)), "frac_fund_seat_gt": {str(t): float((v > t).mean()) for t in (0.5, 0.6, 0.7, 0.8)},
                    "frac_fund_seat_eq_1": float((v >= 1 - 1e-6).mean()), "frac_fund_seat_eq_0": float((v <= 1e-6).mean()),
                    "trailing900_sigma_fund_over_king_median": float(np.median(sf[ok] / sk[ok])) if ok.any() else None,
                    "trailing900_corr_king_fund_median": float(np.nanmedian(cor[m])) if np.isfinite(cor[m]).any() else None,
                    "seat_abs_change_per_anchor_median": float(np.median(np.abs(np.diff(v)))) if len(v) > 1 else None}
    out["S_seat_descriptive"] = seats
    print(json.dumps(seats, indent=1), flush=True)
    # ───────── PART 2 ─────────
    S = {}
    for k, p in CELLS.items():
        z = np.load(p); S[k] = {"A": z["anchors"].astype(np.int64), "r": z["r_per_path"], "sha256": sha(p)}
    A = S["NC_s42X"]["A"]
    for k in S: assert np.array_equal(S[k]["A"], A)
    out["cells"] = {k: {"path": CELLS[k], "sha256": S[k]["sha256"]} for k in S}
    res = {}; check = {}
    for x, y in PAIRS:
        res[f"{x}-{y}"] = {}
        for s, (lo, hi) in SEG.items():
            m = (A >= ts(lo)) & (A <= ts(hi))
            d_ = (A[m] // DAY) * DAY; ud, c = np.unique(d_, return_counts=True); days = ud[c == 6]
            def dser(r):
                u, rd = daily(A[m], r[m]); pos = np.searchsorted(u, days); assert np.all(u[pos] == days); return rd[pos]
            Dx = np.stack([dser(r) for r in S[x]["r"]]); Dy = np.stack([dser(r) for r in S[y]["r"]])
            D = (Dx - Dy).mean(0); bx = Dx.mean(0); by = Dy.mean(0)
            idx = mbb_indices(len(D), BLOCK, B, RNG); mb = D[idx].mean(1)
            ac = [float(np.corrcoef(D[:-l], D[l:])[0, 1]) for l in (1, 2, 3, 5, 10)]
            res[f"{x}-{y}"][s] = {"n_days": int(len(D)), "dbar_bps_per_day": float(1e4 * D.mean()),
                                  "sd_daily_diff_bps": float(1e4 * D.std(ddof=1)), "iid_se_bps": float(1e4 * D.std(ddof=1) / math.sqrt(len(D))),
                                  "mbb30_se_bps": float(1e4 * mb.std(ddof=1)), "mbb30_ci95_halfwidth_bps": float(1e4 * (np.percentile(mb, 97.5) - np.percentile(mb, 2.5)) / 2),
                                  "sd_daily_book_x_bps": float(1e4 * bx.std(ddof=1)), "sd_daily_book_y_bps": float(1e4 * by.std(ddof=1)),
                                  "corr_daily_books": float(np.corrcoef(bx, by)[0, 1]), "acf_daily_diff_lags_1_2_3_5_10": ac}
            if x == "T0_s42" and y == "NC_s42X" and s in CHECK:
                check[s] = {"probe": float(1e4 * D.mean()), "receipt": CHECK[s], "abs_diff": abs(float(1e4 * D.mean()) - CHECK[s])}
    out["instrument_check_vs_SIGMA_F10"] = check
    ok = all(v["abs_diff"] < 1e-9 for v in check.values())
    out["instrument_check_PASS"] = bool(ok)
    print("instrument check", check, "PASS" if ok else "FAIL", flush=True)
    if ok:
        out["PART2_noise_scale"] = res
        print(json.dumps(res, indent=1), flush=True)
    else:
        out["PART2_noise_scale"] = "WITHHELD: instrument check failed"
    json.dump(out, open(sys.argv[1] + ".tmp", "w"), indent=1); os.replace(sys.argv[1] + ".tmp", sys.argv[1])
    rb = json.load(open(sys.argv[1])); assert rb["self_sha256"] == out["self_sha256"]
    print("written", sys.argv[1], sha(sys.argv[1])[:16], flush=True)


if __name__ == "__main__":
    main()
