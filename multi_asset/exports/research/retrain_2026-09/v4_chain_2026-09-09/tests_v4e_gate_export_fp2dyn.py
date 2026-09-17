#!/usr/bin/env python3
"""PROPOSED5 rev2: the fp2dyn export-gate variant versus the frozen v2, on the SAME synthetic books, E8 and E9 only (the two checks the variant
touches). The policy under test (independent review round 4): for a seat outside CHECK_SEATS only the gross ceiling (K6) and the E9 band are
informational; accounting identities (K1–K4, K7) and the baseline identity (approved sha, frozen-window coverage) still fold into the verdict.
Both modules are imported (their main guards keep import side-effect free) and their E8/E9 functions run on a fake context."""
import hashlib, importlib.util, json, os, sys, tempfile
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); FAILS, N = [], [0]
def check(name, ok, detail=None):
    N[0] += 1
    if not ok: FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:240]) if detail is not None else ""), flush=True)
def load(name):
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), f"{HERE}/{name}"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
V2, VD = load("v4e_gate_export_v2.py"), load("v4e_gate_export_fp2dyn.py")
COLS = V2.COLS; F0, F1 = 1_740_787_200, 1_786_000_000       # frozen window [2025-03-01, 2026-08-10 20Z) as in the contract thresholds
T0 = F0 - 1000 * 14400; TS = T0 + 14400 * np.arange(1000 + 3300, dtype=np.int64); NS = 5
RATE_MAX = max(fr * mk + (1 - fr) * tk for mk, tk, fr in [[1.8, 4.5, 0.85]])          # the fixture's single cost tier (K7 bound)
def book(gross=1.0, break_k4=False, gross_over=False, syms=None):
    n = len(TS); rec = np.zeros((n, len(COLS))); rec[:, 0] = TS
    osc = 1e-3 * np.sin(np.arange(n) * 0.7)                                                                # weights MOVE every row (K7 needs turnover > 0 on frozen rows)
    W = np.zeros((n, NS)); W[:, 0] = 0.3 + osc; W[:, 1] = -0.3 + osc; W[:, 2] = 0.2 - osc; W[:, 3] = -0.2 - osc     # Σ|W| = 1.0 exactly
    if gross_over: W[1200:1240, 4] = 0.03                                                                  # a few FROZEN rows at 1.03 (the tradable-regime fix-seat signature)
    g = np.abs(W).sum(1); rec[:, V2.C["gross_total"]] = g
    dW = np.abs(np.diff(W, axis=0)).sum(1); to = np.concatenate([[g[0]], dW]); rec[:, V2.C["turnover"]] = to          # K2: row 0 = the initial build
    cost = 0.5 * to * RATE_MAX; pnl = np.full(n, 1e-4); carry = np.full(n, 2e-5)                                        # K7: 0 < cost ≤ turnover × rate_max
    rec[:, V2.C["pnl"]] = pnl; rec[:, V2.C["carry"]] = carry; rec[:, V2.C["cost"]] = cost; rec[:, V2.C["net"]] = pnl - carry - cost + (1e-3 if break_k4 else 0)
    rec[:, V2.C["pnl_ex"]] = pnl; rec[:, V2.C["carry_ex"]] = carry; rec[:, V2.C["cost_ex"]] = cost; rec[:, V2.C["net_ex"]] = pnl - carry - cost + (1e-3 if break_k4 else 0)
    rec[:, V2.C["netlong"]] = W.sum(1) / np.maximum(g, 1e-12)
    return {"rec": rec, "W": W, "cols": COLS, "symbols": syms or [f"S{i}" for i in range(NS)], "cfg": {}}
class Cx:
    def __init__(self, B, BASE, base_shas, th_over=None):
        self.B, self.BASE = B, BASE; self.frozen = (F0, F1); self.res = {}
        self.th = {"gross_max": 1.000001, "gross_ratio_band": [0.6, 1.6], "gross_ratio_median_band": [0.8, 1.25], "n_frozen": int(((TS >= F0) & (TS < F1)).sum()), "w_gross_tol": 1e-6, "turnover_tol": 1e-6, "netlong_tol": 1e-6, "identity_tol": 1e-9}; self.th.update(th_over or {})
        self.ab = {"costb_tiers": [[1.8, 4.5, 0.85]], "baseline_books_sha256": base_shas, "baseline_arm": "A0"}
        self.books = {k: k for k in B}; self.bases = {k: k for k in BASE}
    def chk(self, name, ok, detail): self.res[name] = (bool(ok), detail); return ok
SEATS = [("dyn", "42"), ("dyn", "2027"), ("fix", "42"), ("fix", "2027")]
def scenario(fix_over=False, fix_k4=False, dyn_over=False, fix_base_sha_wrong=False, fix_band=False):
    d = tempfile.mkdtemp(); B = {}; BASE = {}; base_shas = {}
    for seat, s in SEATS:
        bk = f"book_{seat}_s{s}"; bs = f"base_{seat}_s{s}"; fx = seat == "fix"
        B[bk] = book(gross_over=(fix_over and fx) or (dyn_over and not fx), break_k4=fix_k4 and fx)
        if fix_band and fx: B[bk]["rec"][:, V2.C["gross_total"]] *= 2.0                                     # ratio 2.0 > band 1.6
        BASE[bs] = book(); p = f"{d}/{bs}.npz"; np.savez(p, x=np.zeros(1)); base_shas[f"{seat}_s{s}"] = ("0" * 64) if (fix_base_sha_wrong and fx) else hashlib.sha256(open(p, "rb").read()).hexdigest()
        BASE[bs]["_path"] = p
    cx = Cx(B, BASE, base_shas); cx.bases = {k: v["_path"] for k, v in BASE.items()}; cx.books = {k: k for k in B}
    return cx
def run(mod, cx):
    import copy; c2 = copy.copy(cx); c2.res = {}
    mod.E8_books_content(c2); mod.E9_gross_band_vs_baseline(c2); return c2.res["E8_books_content"][0], c2.res["E9_gross_band_vs_baseline"][0], c2.res
r2 = run(V2, scenario()); rd = run(VD, scenario())
check("★ S0 clean books: v2 E8/E9 PASS and variant E8/E9 PASS (baseline green)", r2[0] and r2[1] and rd[0] and rd[1], (r2[:2], rd[:2]))
r2 = run(V2, scenario(fix_over=True)); rd = run(VD, scenario(fix_over=True))
check("★★★ S1 fix-seat gross 1.03 (the tradable-regime signature): v2 E8 FAIL, variant E8 PASS with informational_seat True on the fix books", (not r2[0]) and rd[0] and rd[2]["E8_books_content"][1]["book_fix_s42"]["informational_seat"] is True and rd[2]["E8_books_content"][1]["book_fix_s42"]["K6_ok"] is False, (r2[0], rd[0]))
r2 = run(V2, scenario(dyn_over=True)); rd = run(VD, scenario(dyn_over=True))
check("★★★ S2 dyn-seat gross 1.03: v2 FAIL and variant FAIL (the checked seat is never exempt)", (not r2[0]) and (not rd[0]), (r2[0], rd[0]))
r2 = run(V2, scenario(fix_k4=True)); rd = run(VD, scenario(fix_k4=True))
check("★★★ S3 reviewer: fix-seat K4 net identity broken: v2 FAIL and variant FAIL (rev2: accounting identities of a diagnostic book still fold)", (not r2[0]) and (not rd[0]) and rd[2]["E8_books_content"][1]["book_fix_s42"]["identities_ok"] is False, (r2[0], rd[0]))
r2 = run(V2, scenario(fix_base_sha_wrong=True)); rd = run(VD, scenario(fix_base_sha_wrong=True))
check("★★★ S4 reviewer: fix-seat baseline book sha not the approved one: v2 E9 FAIL and variant E9 FAIL (rev2: baseline identity folds for every seat)", (not r2[1]) and (not rd[1]), (r2[1], rd[1]))
r2 = run(V2, scenario(fix_band=True)); rd = run(VD, scenario(fix_band=True))
check("★★ S5 fix-seat gross ratio 2.0 (outside the band, identity intact): v2 E9 FAIL, variant E9 PASS with informational_seat True (only the band is informational)", (not r2[1]) and rd[1] and rd[2]["E9_gross_band_vs_baseline"][1]["book_fix_s42"]["informational_seat"] is True, (r2[1], rd[1]))
print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
if FAILS: print("FAILED:", *FAILS, sep="\n  "); sys.exit(1)
print("ALL PASS")
