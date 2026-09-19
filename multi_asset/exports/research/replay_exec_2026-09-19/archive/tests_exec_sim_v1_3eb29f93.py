#!/usr/bin/env python3
"""replay_exec 2026-09-19 · battery for exec_sim.py / v1_gate.py. Every claim: the GREEN baseline is asserted FIRST (and must be
non-vacuous: a measured population > 0), then each mutation must turn the SAME check RED. A mutation that stays green is a
failure of the battery (the check could not discriminate).

Claims
  [1] min-notional   no plan whose |rounded qty × mid| is below the symbol's venue floor is ever executed          mut: --no-min-notional
  [2] per-name stop  a held name at depth ≤ −30% on two consecutive N+40 reads (independently recomputed here from the sim's
                     own positions / entries, not from per_name_stop.evaluate) is in the stop set at the next traded decision and
                     its executor target is exactly 0                                                                mut: --no-stop
  [3] fees           every trade leg's fee = |notional| × the FROZEN calibration's rate for its maker flag and fee era (switch
                     instant read from the calibration JSON, recomputed here, not via Sim.fee_rate)                mut: --zero-fees, --fee-asset-wrong
  [4] funding        every charge = −q × P × rate (a long pays a positive rate), once per (symbol, fundingTime), with the venue's
                     own rate wherever the executor has a funding row; the sign convention is anchored on the REAL ledger
                     (funding_paid vs −position_notional × rate)                                               mut: --funding-sign-flip, --funding-double
  [5] accounting     per window: equity1 − equity0 = price_and_trading + funding − fee + transfer (1e-6 USDT)   mut: fee charged in the
                     window totals but not booked to equity (in-process subclass)
  [6] calibration    two runs on the same inputs give identical windows; the output depends on the frozen calibration     mut: p_zero + 0.05
  [7] read-only      the guard refuses an open() under ~/dl_quant_live (fresh interpreter)                        mut: same interpreter without the guard
  [8] V1 judge       judge(live, live) passes all four items                                                    mut: fee ×1.3, funding ×0.7, turnover ×1.3,
                                                                                                                     price shifted by 1.5 × tol
usage: tests_exec_sim.py [mirror]   → prints one line per check and a final verdict line; exit code 0 iff every check passed.
"""
import collections, copy, json, math, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import simlib as L

RESULTS = []


def check(name, ok, detail):
    RESULTS.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}", flush=True)


# ── [7] read-only guard: needs subprocesses, so it runs BEFORE this process installs its own guard ──
def t7_guard():
    probe = os.path.expanduser("~/dl_quant_live/config/book.json")
    code = ("import sys; sys.path.insert(0, %r); import simlib as L; %s\n"
            "try:\n    open(%r, 'rb').read(1); print('OPENED')\nexcept PermissionError as e:\n    print('REFUSED')") % (HERE, "{}", probe)
    g = subprocess.run([sys.executable, "-c", code.format("L.install_readonly_guard()")], capture_output=True, text=True).stdout.strip()
    check("7 read-only guard baseline (guard installed ⇒ open of a live path refused)", g == "REFUSED", f"child says {g!r}")
    m = subprocess.run([sys.executable, "-c", code.format("pass")], capture_output=True, text=True).stdout.strip()
    check("7 read-only guard mutation (no guard ⇒ the same open succeeds, i.e. the refusal came from the guard)", m == "OPENED", f"child says {m!r}")


def run(M, cal, X, P, F, mode="live", **knobs):
    import exec_sim as ES
    kn = {k: False for k in ("no_stop", "no_min_notional", "zero_fees", "fee_asset_wrong", "funding_sign_flip", "funding_double")}
    kn.update(knobs)
    S = ES.Sim(M, cal, mode, kn, X=X, panel=P, fund=F)
    W = S.run()
    return S, W


# ── claim checks (pure functions of a finished Sim) ──
def c1_min_notional(S):
    bad = [(A, s, d, fl) for (A, s, d, fl, tgt, prev, st) in S.plan_log if fl is not None and d != 0.0 and abs(d) < fl - 1e-9]
    n = sum(1 for x in S.plan_log if x[3] is not None and x[2] != 0.0)
    return n, bad


def c2_stop(S, depth_limit=-0.30):
    """independent re-derivation: two consecutive N+40 reads at depth ≤ limit (name not already stopped / cooling) ⇒ the next
    TRADE decision must carry the name in the stop set with target exactly 0 (or the name is no longer held)"""
    status = {r["anchor"]: r["status"] for r in S.log_anchor}
    plans = collections.defaultdict(dict)
    for (A, s, d, fl, tgt, prev, st) in S.plan_log:
        plans[A][s] = (tgt, st, prev)
    trig, viol = [], []
    D = S.depth_log
    for k in range(1, len(D)):
        A0, _, d0, ex0 = D[k - 1]; A1, _, d1, ex1 = D[k]
        if A1 - A0 != 14400:
            continue
        for s, v in d1.items():
            if v <= depth_limit and d0.get(s, 0.0) <= depth_limit and s not in ex0 and s not in ex1:
                An = A1 + 14400
                if status.get(An) not in ("TRADE",):
                    continue
                trig.append((A1, s))
                got = plans.get(An, {}).get(s)
                if got is None:
                    viol.append((An, s, "no plan row for a held name"))
                elif not (got[1] and got[0] == 0.0):
                    viol.append((An, s, f"target {got[0]:+.2f} stop_flag {got[1]}"))
    return trig, viol


def c3_fees(S, cal):
    fr = cal["params"]["fee_rate"]; sw = float(fr["switch_ts"])
    err = 0.0; n = 0; tot = 0.0
    for (t, s, cash, maker, fee, kind) in S.trade_log:
        era = "BNB_era" if t < sw else "USDT_era"
        exp = abs(cash) * float(fr[era]["maker" if maker else "taker"])
        err = max(err, abs(fee - exp)); n += 1; tot += fee
    return n, tot, err


def c4_funding(S):
    worst = 0.0; seen = collections.Counter(); rate_mis = 0; n_live_keys = 0
    for (t, s, q, P, r, f) in S.fund_log:
        exp = -q * P * r
        worst = max(worst, abs(f - exp) / max(1e-9, abs(exp)) if exp != 0 else abs(f))
        seen[(s, int(t))] += 1
        lr = S.F.live.get((s, int(t)))
        if lr is not None:
            n_live_keys += 1; rate_mis += int(abs(lr - r) > 1e-15)
    dup = sum(1 for v in seen.values() if v > 1)
    return len(S.fund_log), worst, dup, rate_mis, n_live_keys


def c5_accounting(W):
    return max(abs((w["equity1"] - w["nav0"]) - (w["price_trade"] + w["funding"] - w["fee"] + w["transfer"])) for w in W)


def main():
    t7_guard()
    M = L.Mirror(sys.argv[1] if len(sys.argv) > 1 else L.MIRROR_DEFAULT)
    L.install_readonly_guard()
    bad = M.verify_manifest()
    check("0 mirror bytes equal INPUT_MANIFEST", not bad, f"{len(bad)} mismatching files")
    import exec_sim as ES
    cal = json.load(open(os.path.join(HERE, "CALIBRATION_FROZEN_2026-09-19.json")))
    X = ES.ExecutorCode(M); P = L.Panel(M); L.build_references(M, P); F = L.FundingBook(M)
    t0 = time.time()
    S0, W0 = run(M, cal, X, P, F)
    print(f"      baseline run {time.time() - t0:.1f} s: {len(W0)} windows, {len(S0.trade_log)} trade legs, {len(S0.fund_log)} funding charges", flush=True)

    # [1]
    n, badm = c1_min_notional(S0)
    check("1 min-notional baseline", n > 0 and not badm, f"{n} executed plans, {len(badm)} below the venue floor")
    Sm, _ = run(M, cal, X, P, F, no_min_notional=True)
    n2, bad2 = c1_min_notional(Sm)
    check("1 min-notional mutation --no-min-notional turns it RED", len(bad2) > 0, f"{len(bad2)} executed plans below the floor (of {n2})")
    # [2]
    trig, viol = c2_stop(S0)
    check("2 per-name stop baseline", len(trig) > 0 and not viol, f"{len(trig)} independent −30%×2 triggers, {len(viol)} violations")
    Ss, _ = run(M, cal, X, P, F, no_stop=True)
    trig2, viol2 = c2_stop(Ss)
    check("2 per-name stop mutation --no-stop turns it RED", len(viol2) > 0, f"{len(trig2)} triggers, {len(viol2)} violations e.g. {viol2[:2]}")
    # [3]
    n, tot, err = c3_fees(S0, cal)
    check("3 fees baseline", n > 0 and tot > 0 and err <= 1e-9, f"{n} legs, fee {tot:,.2f} USDT, max |fee − recomputed| {err:.2e}")
    for kn in ("zero_fees", "fee_asset_wrong"):
        Sf, _ = run(M, cal, X, P, F, **{kn: True})
        n2, tot2, err2 = c3_fees(Sf, cal)
        check(f"3 fees mutation --{kn.replace('_', '-')} turns it RED", err2 > 1e-6, f"fee {tot2:,.2f} USDT, max |fee − recomputed| {err2:.4f}")
    # [4]
    rows = M.range_rows("funding", "20260826", "20260919")
    sg = [(float(r["funding_paid"]), -float(r["position_notional_at_settlement"]) * float(r["funding_rate"])) for r in rows
          if abs(float(r["funding_paid"])) > 1e-6]
    agree = sum(1 for a, b in sg if a * b > 0) / len(sg)
    check("4 funding sign convention on the REAL ledger (paid = −notional × rate)", agree >= 0.99, f"{agree:.4%} of {len(sg)} live rows agree in sign")
    n, worst, dup, mis, nk = c4_funding(S0)
    check("4 funding baseline", n > 0 and worst <= 1e-9 and dup == 0 and mis == 0 and nk > 0,
          f"{n} charges, max rel err {worst:.1e}, {dup} duplicate (symbol, time), {mis}/{nk} rate mismatches vs the executor's rows")
    for kn in ("funding_sign_flip", "funding_double"):
        Sf, _ = run(M, cal, X, P, F, **{kn: True})
        n2, worst2, dup2, mis2, nk2 = c4_funding(Sf)
        check(f"4 funding mutation --{kn.replace('_', '-')} turns it RED", worst2 > 1e-6, f"max rel err {worst2:.3f}")
    # [5]
    e = c5_accounting(W0)
    check("5 accounting identity baseline", e <= 1e-6, f"max |Δequity − (price + funding − fee + transfer)| = {e:.2e} USDT")

    class LeakSim(ES.Sim):
        def trade(self, t, s, notional_mid, b, slip, maker, kind):
            k0 = self.K; fee0 = self.acc["fee"]
            out = super().trade(t, s, notional_mid, b, slip, maker, kind)
            self.K += self.acc["fee"] - fee0          # mutation: the fee is reported but never leaves equity
            return out
    kn = {k: False for k in ("no_stop", "no_min_notional", "zero_fees", "fee_asset_wrong", "funding_sign_flip", "funding_double")}
    SL = LeakSim(M, cal, "live", kn, X=X, panel=P, fund=F); WL = SL.run()
    e2 = c5_accounting(WL)
    check("5 accounting mutation (fee not booked to equity) turns it RED", e2 > 1e-3, f"max identity error {e2:,.4f} USDT")
    # [6]
    S1, W1 = run(M, cal, X, P, F)
    same = all(json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True) for a, b in zip(W0, W1)) and len(W0) == len(W1)
    check("6 determinism baseline (two runs, identical windows)", same, f"{len(W0)} windows compared")
    cal2 = copy.deepcopy(cal); cal2["params"]["maker_first"]["p_zero"] += 0.05
    S2, W2 = run(M, cal2, X, P, F)
    diff = sum(abs(a["turnover"] - b["turnover"]) for a, b in zip(W0, W2))
    check("6 calibration binding mutation (p_zero + 0.05) changes the output", diff > 1.0, f"Σ|Δ turnover| {diff:,.2f} USDT")
    # [8]
    import v1_gate as V
    Wl, _ = L.live_windows()
    live_w = [w for w in Wl if L.A_V1_FIRST <= L.nominal(w["t0"]) <= L.A_V1_LAST]
    lt, _ = V.live_turnover(M, live_w)
    same_w = [dict(w, turnover=t) for w, t in zip(live_w, lt)]
    it = V.judge(same_w, live_w, lt)
    check("8 V1 judge baseline judge(live, live)", all(it[k]["pass"] for k in it), {k: it[k]["pass"] for k in it})
    muts = {"fee": ("fee", 1.3), "funding": ("funding", 0.7), "turnover_over_gross": ("turnover", 1.3)}
    for item, (fld, f) in muts.items():
        mw = [dict(w, **{fld: w[fld] * f}) for w in same_w]
        it2 = V.judge(mw, live_w, lt)
        check(f"8 V1 judge mutation {fld} ×{f} ⇒ item {item} FAIL", not it2[item]["pass"], f"ratio {it2[item]['ratio']:.3f}")
    tol = it["price_and_trading"]["tolerance"]
    mw = [dict(w, price_trade=w["price_trade"] + 1.5 * tol / len(same_w)) for w in same_w]
    it3 = V.judge(mw, live_w, lt)
    check("8 V1 judge mutation price + 1.5·tol ⇒ price FAIL", not it3["price_and_trading"]["pass"],
          f"total diff {it3['price_and_trading']['total_diff']:+,.1f} vs tol {tol:,.1f}; CI {it3['price_and_trading']['daily_diff_ci95']}")

    n_ok = sum(1 for _, ok, _ in RESULTS if ok)
    if n_ok == len(RESULTS):
        print(f"BATTERY VERDICT: ALL PASS {n_ok}/{len(RESULTS)} checks (baselines green first, every mutation red)")
        sys.exit(0)
    print(f"BATTERY VERDICT: FAILURES {len(RESULTS) - n_ok}/{len(RESULTS)} checks failed: " + "; ".join(n for n, ok, _ in RESULTS if not ok))
    sys.exit(1)


if __name__ == "__main__":
    main()
