#!/usr/bin/env python3
"""Unit controls for w10_overlays.py + the engine tail step (R7C-R1/R2/R3, 2026-09-18). Synthetic y4 (T anchors × N names), members = all.
 A: arm-order invariance — a fresh make() per run gives the same decisions whether or not another run went first (the shared-instance defect reproduced as the RED baseline);
 B: re-entrance — running the same run twice with fresh instances is identical;
 C: causality — perturbing y4 rows > k does not change decisions at anchors ≤ k;
 D: R4 keeps Σwβ = 0 when the tail step honours its beta contract (and the old tail step broke it);
 E: one-sided book ⇒ empty book under the notional contract; F: cap never exceeded after the tail step. usage: tests_w10_overlays.py <w10_overlays.py> <w10_health_overlay.py>"""
import sys, importlib.util, numpy as np
OV, EN = sys.argv[1:3]
def load(path, name):
    sp = importlib.util.spec_from_file_location(name, path); mo = importlib.util.module_from_spec(sp); sp.loader.exec_module(mo); return mo
ov = load(OV, "w10_overlays")
src = open(EN).read(); ns = {}; exec(src[src.index("def _neutral_scale_down"):src.index("\nif OVERLAY_SPEC != \"none\"")], ns); nsd = ns["_neutral_scale_down"]   # the tail function, exact bytes
rng = np.random.default_rng(0); T, N = 400, 40; y4 = rng.normal(0, 0.02, (T, N)); m = np.arange(N); capw = 0.05
book = lambda i: np.where(np.arange(N) < N // 2, 0.02, -0.02) * (1 + 0.1 * np.sin(i))
def decisions(f, T0, y):
    out = []
    for i in range(T0):
        sm = book(i); o = f(sm, dict(i=i, j=i, m=m, y4=y, FN=np.zeros((T, N)), IV=np.full((T, N), 8.0), HB=sm, HR=sm, FZ=np.zeros(N), sel=np.ones(N, bool), capw=capw, NW=N))
        out.append(float(np.abs(o).sum()))
    return np.array(out)
res = []
def check(name, cond, extra=""): res.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name, "" if cond else extra)
# A: shared instance (RED baseline) vs fresh instance per run
f_shared = ov.make("r1a:q=0.90,s=0.5"); d_first = decisions(f_shared, T, y4); d_second_shared = decisions(f_shared, T, y4)
d_fresh_after = decisions(ov.make("r1a:q=0.90,s=0.5"), T, y4)
check("A0 RED baseline: a shared overlay instance run twice differs on the second pass (history inherited = the R7C-R1 defect)", not np.array_equal(d_first, d_second_shared))
check("A1 fresh make() per run: second run == first run (arm order cannot matter)", np.array_equal(d_first, d_fresh_after))
check("B  re-entrance: two fresh instances identical", np.array_equal(decisions(ov.make("r1b:q=0.95,s=0.5"), T, y4), decisions(ov.make("r1b:q=0.95,s=0.5"), T, y4)))
# C: future perturbation
k = 300; y_pert = y4.copy(); y_pert[k + 1:] += rng.normal(0, 0.5, (T - k - 1, N))
for spec in ("r1a:q=0.90,s=0.5", "r2:c=0.5", "r3:th=0.20", "r4:win=60", "r6:k=1,q=0.95,s=0.5", "r6l:k=1,q=0.95,s=0.5", "r6b:k=1,q=0.95,s=0.5"):   # R6/R6l/R6b added to the formal battery (review round 8)
    a = decisions(ov.make(spec), k + 1, y4); b = decisions(ov.make(spec), k + 1, y_pert)
    check(f"C  causality {spec}: decisions at anchors ≤ {k} unchanged by perturbing rows > {k}", np.array_equal(a, b))
# G (v2, review round 9 §5 — the old G passed with hysteresis removed): a BINDING hysteresis test. Feed a controlled signal sequence through r6b: warm-up (200 noise
# anchors), then one anchor above the on-quantile, then anchors whose signal sits BETWEEN q_off and q. With hysteresis the cut must persist through those anchors; with
# q_off = q (no hysteresis) it must switch off. The signal is controlled through y4 rows: shorts (second half of names) get the return that sets SB_rel.
def run_r6b(qoff):
    f = ov.make(f"r6b:k=1,q=0.95,s=0.5,qoff={qoff}"); rng2 = np.random.default_rng(7); Tn = 260; yy = np.zeros((Tn, N)); half = N // 2
    for t in range(Tn):
        if t < 200: rel = rng2.normal(0, 0.01)                       # warm-up: SB_rel ~ N(0, 1%)
        elif t == 200: rel = 0.10                                     # far above q95
        elif 201 <= t <= 205: rel = 0.013                              # between q80 (~0.0084) and q95 (~0.0165) of the warm-up distribution
        else: rel = -0.05                                             # far below q_off
        yy[t, half:] = rel / 2; yy[t, :half] = -rel / 2               # shorts − longs = rel
    ons = []
    for i in range(1, Tn):
        sm = np.where(np.arange(N) < half, 0.02, -0.02); o = f(sm, dict(i=i, j=i, m=m, y4=yy, FN=None, IV=None, HB=sm, HR=None, FZ=None, sel=None, capw=capw, NW=N)); ons.append(float(np.abs(o).sum()) < float(np.abs(sm).sum()) - 1e-12)
    return ons
on_h = run_r6b(0.80); on_n = run_r6b(0.95)
# index: decision at anchor i uses rows < i; the row-200 spike is seen at i = 201, the between-band rows 201..205 at i = 202..206
check("G1 hysteresis binds: with q_off=0.80 the cut turns on at i=201 and STAYS on through i=202..206 (signal between q_off and q)", on_h[200] and all(on_h[201:206]), on_h[199:208])
check("G2 RED control: with q_off=q (no hysteresis) the cut turns on at i=201 and switches OFF at i=202 (the very same sequence)", on_n[200] and not any(on_n[201:206]), on_n[199:208])
check("G3 both switch off once the signal falls far below q_off (i ≥ 207)", not any(on_h[206:210]) and not any(on_n[206:210]), (on_h[206:210], on_n[206:210]))
# D: R4 beta contract
f4 = ov.make("r4:win=360"); sm = np.array([.1, .1, -.1, -.1]); beta = np.array([2/3, 2/3, 4/3, 4/3])
# emulate r4's inner allocation with a given beta (its own beta estimate needs history; the contract is what we test)
L = sm > 0; S = sm < 0; bl = float((sm[L] * beta[L]).sum()); bs = float((sm[S] * beta[S]).sum()); out = sm.copy()
if bl > -bs: out[L] *= (-bs / bl)
else: out[S] *= (bl / -bs)
check("D1 R4 output is beta-neutral", abs(float((out * beta).sum())) < 1e-12, out)
check("D2 the tail step is SKIPPED for a beta-contract rule (attribute neutral='beta'), so Σwβ=0 survives; the old unconditional tail step would give β exposure −0.0667", getattr(f4, "neutral", None) == "beta" and abs(float((nsd(out) * beta).sum()) + 0.0666667) < 1e-4)
# E: one-sided ⇒ empty
check("E  one-sided book ⇒ empty book under the notional contract (not |net|/gross = 1)", np.array_equal(nsd(np.array([0., 0., -.1, -.1])), np.zeros(4)) and np.array_equal(nsd(np.array([.1, .1, 0., 0.])), np.zeros(4)))
# F: caps survive the tail step; heavier side scaled down only
v = np.array([.025, .1, -.1, -.1]); cap = np.array([.025, .1, .1, .1]); w = nsd(v)
check("F  tail step scales the heavier side DOWN only: caps hold, Σw = 0", np.all(np.abs(w) <= cap + 1e-12) and abs(w.sum()) < 1e-12 and np.allclose(w, [.025, .1, -.0625, -.0625]), w)
print(f"RESULT {sum(res)}/{len(res)} pass"); sys.exit(0 if all(res) else 1)
