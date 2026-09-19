#!/usr/bin/env python3
"""c0_repro.py — stream C0 step 1: reproduce the realcost replay device's per-anchor pnl_ex / carry_ex / cost_ex (and the seat-weighted
leg_fund, and the saved seat-input legs_fund) of BOTH in-role arms (A0 s42, A0 s2027) from the saved book weights W × meta y4 RAW /
panel funding, with the formulas of c0_lib.py (= w10_health.py 8684d9a9 verbatim). Every recorded anchor is checked (not a sample).
pod2, CPU, read-only on every input; writes only OUT_DIR. Exit 0 only if every gate passes — the attribution device refuses otherwise.

GATES (frozen here before the first run):
  R0  every rec row's ts maps to a meta row and a panel row
  R1  pnl_ex : every anchor ts <= UB: |Δ| <= 1e-6 · max(|ref|, S_abs), S_abs = Σ_{k∈m} |smr_k·y_k|·1e4
  R2  carry_ex: same with S_abs = Σ_{k∈m} |smr_k·f_k·4/iv_k|·1e4
      Why max(|ref|, S_abs) and not |ref| alone: W is stored as float32 (relative precision 2^-24 ≈ 6e-8 per weight), so the attainable
      absolute precision of Σ w·y is ~6e-8·S_abs; a plain relative error is undefined when the sum cancels to ≈ 0. The plain relative error
      |Δ|/|ref| is REPORTED for every anchor (share ≤ 1e-6, max on |ref| ≥ 0.1 bps) but is not the gate.
  R3  cost_ex: |Δ| <= 1e-6 · max(|ref|, S_abs), S_abs = Σ_{k∈m} (|smr_k| + |HR_k|)·blend_k (fee needs the previous recorded row's smr)
  R4  gross_total: |Σ|W| − gross_total| <= 1e-6 · gross_total ;  nmember == |m| exactly
  R5  leg_fund (seat-weighted, rec column) recomputed from f_fund_ema_v1: |Δ| <= 1e-9 · max(1, |ref|)   (float64 inputs; no float32 W involved)
  R6  legs_fund (seat input saved in the npz) recomputed: |Δ| <= 1e-9 · max(1, |ref|) on every rec row
  R7  window level: mean over W_ALPHA (ts <= UB minus first 900 anchors) and over every UTC month 2025-01..2026-08 of pnl/gt, carry/gt,
      cost/gt: |Δ| <= 1e-6 · max(1, |ref|)
usage: python c0_repro.py <OUT_DIR>
"""
import json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c0_lib as L

T0 = time.time(); OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
chk = L.Checks(T0)
rec = {"device": "c0_repro.py", "self_sha256": L.sha(os.path.abspath(__file__)), "lib_sha256": L.sha(L.__file__), "numpy": np.__version__, "argv": sys.argv,
       "env": {k: os.environ[k] for k in sorted(os.environ)}, "utc_start": L.utc(time.time())}
rec["inputs"] = L.verify_inputs(chk, L.INPUTS)
if chk.fails:
    json.dump(rec | {"checks": chk.rows, "failed": chk.fails, "VERDICT": "REFUSED"}, open(f"{OUT}/RECEIPT_c0_repro.json", "w"), indent=1); sys.exit(3)
C = L.load_common(chk)
rec["arms"] = {}
for seed in L.SEEDS:
    A = L.load_arm(seed, chk)
    R = A["R"]; cols = A["cols"]; ts = R[:, 0].astype(np.int64); col = lambda n: R[:, cols.index(n)]
    chk(f"s{seed}.R0_rows_map", all(int(t) in C["mrow"] and int(t) in C["prow"] for t in ts), {"rows": len(ts), "first": L.utc(ts[0]), "last": L.utc(ts[-1])})
    _, S = L.per_name(A, C, keep_rows=np.zeros(len(ts), bool))
    wub = ts <= L.UB
    res = {}
    for nm, ref, sab, g in (("pnl_ex", col("pnl_ex"), S["S_abs_price"], "R1"), ("carry_ex", col("carry_ex"), S["S_abs_carry"], "R2"), ("cost_ex", col("cost_ex"), S["S_abs_cost"], "R3")):
        d = np.abs(S[nm] - ref)[wub]; rr = ref[wub]; sa = sab[wub]
        tol = 1e-6 * np.maximum(np.abs(rr), sa)
        big = np.abs(rr) >= 0.1
        with np.errstate(all="ignore"): prel = np.where(np.abs(rr) > 0, d / np.abs(rr), np.where(d == 0, 0.0, np.inf))
        res[nm] = {"anchors": int(wub.sum()), "max_abs_diff_bps": float(d.max()), "max_diff_over_scale": float((d / np.maximum(np.maximum(np.abs(rr), sa), 1e-300)).max()),
                   "n_fail_gate": int((d > tol).sum()), "plain_rel_share_le_1e-6": float((prel <= 1e-6).mean()),
                   "plain_rel_max_on_absref_ge_0p1bps": float(prel[big].max()) if big.any() else None, "n_absref_ge_0p1bps": int(big.sum()),
                   "plain_rel_p99_on_absref_ge_0p1bps": float(np.quantile(prel[big], 0.99)) if big.any() else None}
        chk(f"s{seed}.{g}_{nm}", res[nm]["n_fail_gate"] == 0, res[nm])
    gt = col("gross_total")
    dg = np.abs(S["gross_W"] - gt)
    chk(f"s{seed}.R4_gross_and_nmember", bool((dg <= 1e-6 * gt).all()) and bool(np.array_equal(S["nmember"].astype(np.int64), col("nmember").astype(np.int64))),
        {"max_rel_gross": float((dg / gt).max()), "nmember_mismatch_rows": int((S["nmember"].astype(np.int64) != col("nmember").astype(np.int64)).sum())})
    dl = np.abs(S["leg_fund"] - col("leg_fund")); tl = 1e-9 * np.maximum(1, np.abs(col("leg_fund")))
    chk(f"s{seed}.R5_leg_fund_seat_weighted", bool((dl <= tl).all()), {"max_abs_diff": float(dl.max()), "rows": len(dl)})
    lmap = {int(t): k for k, t in enumerate(A["legs_ts"])}
    li = np.array([lmap[int(t)] for t in ts]); ls = A["legs_fund"][li]
    d6 = np.abs(S["legs_fund_seatinput"] - ls)
    chk(f"s{seed}.R6_legs_fund_seat_input", bool((d6 <= 1e-9 * np.maximum(1, np.abs(ls))).all()), {"max_abs_diff": float(d6.max()), "rows": len(d6)})
    # R7 window level (judge units: per unit gross)
    WA = wub.copy(); WA[:900] = False
    mon = np.array([time.strftime("%Y-%m", time.gmtime(int(t))) for t in ts])
    wins = {"W_ALPHA": WA, **{m_: WA & (mon == m_) for m_ in sorted(set(mon[WA].tolist())) if "2025-01" <= m_ <= "2026-08"}}
    r7 = {}; worst = 0.0
    for wn, mk in wins.items():
        r7[wn] = {}
        for nm in ("pnl_ex", "carry_ex", "cost_ex"):
            a = float((S[nm][mk] / gt[mk]).mean()); b = float((col(nm)[mk] / gt[mk]).mean())
            r7[wn][nm] = {"repro": a, "rec": b}; worst = max(worst, abs(a - b) / max(1.0, abs(b)))
    chk(f"s{seed}.R7_window_means", worst <= 1e-6, {"worst_rel": worst, "W_ALPHA": r7["W_ALPHA"], "2026-08": r7.get("2026-08")})
    res["window_means"] = r7
    res["gross_outside_members"] = {"share_of_gross_mean_2025_2026": float((S["gross_outside_m"] / gt)[WA & (ts >= 1735689600)].mean()),
                                    "by_month": {m_: float((S["gross_outside_m"][mk] / gt[mk]).mean()) for m_, mk in wins.items() if m_ != "W_ALPHA"}}
    rec["arms"][f"A0_s{seed}"] = res
rec.update({"checks": chk.rows, "n_checks": len(chk.rows), "failed": chk.fails, "VERDICT": "PASS" if not chk.fails else "FAIL", "runtime_s": round(time.time() - T0, 1),
            "utc_end": L.utc(time.time())})
json.dump(rec, open(f"{OUT}/RECEIPT_c0_repro.json", "w"), indent=1, default=str)
chk.log("VERDICT", rec["VERDICT"], "failed", chk.fails)
sys.exit(0 if not chk.fails else 3)
