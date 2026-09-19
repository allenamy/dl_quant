#!/usr/bin/env python3
"""Regression test for review finding R5-02 (docs REVIEW_round5_stage1_codex_2026-09-19.md R5-02; reviewer probe probes.py).

The reviewer's two counterexamples, run through (1) the FROZEN old repair loop (r_prices.py L143-150, extracted by AST exactly as the
reviewer did, sha 3614558d... asserted) to show the defect is real, and (2) the NEW code path (rp_lib.classify -> apply_patch, the functions
r_prices_raw.py and rp_restore.py call) to show:
  * with official bars: the true path is reproduced at every 5m boundary (A+25m fill price 40 / 60 / 180, endpoint 24 / 45);
  * without official bars: the device refuses a point path (UnavailablePath) and returns the admissible band instead
    (CE1: A+25m price in [34.2857, 70], containing both true paths; CE2: [130, +inf), the upper side unbounded => no "hi" scenario);
    the old device's CE2 value 67.08 lies OUTSIDE the band (it contradicts the known +clip);
  * the patch contract: entries off a bound bar, bound bars without an entry, and sign-inconsistent entries are refused.
Plus, when tests/fixture_real_cells.json exists (written from the pod patch by rp_fixture.py): on real multi-bound cells the new path equals
the official closes' path within float16 cache precision, and the old rule does not.
run: python3 tests/test_rp_counterexamples.py   (numpy only; exit 0 = all pass)
"""
import ast, hashlib, json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); DEV = os.path.join(HERE, "..", "devices"); sys.path.insert(0, DEV)
import rp_lib as RL

OLD = os.path.join(HERE, "..", "..", "replay_r_2026-09-19", "devices", "r_prices.py")
OLD_SHA = "3614558d6eb58200f1d15f51c3fb72ca7aa18da3a73b04fc4544c8edbfc899dc"
NB = 48; P1, P2 = 0, 9                         # the two clipped bars: E+5m and E+50m (reviewer rows 1 and 10 of a 49-row array)
K25 = 5                                        # boundary index of A+25m (after 5 bars)
RESULTS = []


def ok(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail)); print(("PASS " if cond else "FAIL ") + name + (("  " + str(detail)) if detail != "" else ""))


def truth(actual):
    """official closes (49) of a cell whose only moving bars are P1 and P2, starting at 100"""
    r = np.zeros(NB); r[P1], r[P2] = actual
    return 100.0 * np.concatenate([[1.0], np.cumprod(1.0 + r)]), r


def cache16(r):
    return np.array([np.float16(np.clip(x, -0.3, 0.3)) for x in r], np.float16)


def old_rule(actual):
    """the frozen r_prices.py loop, executed from its own AST on a one-cell block (as the reviewer's probes.py)"""
    src = open(OLD).read(); assert hashlib.sha256(src.encode()).hexdigest() == OLD_SHA, "frozen r_prices.py changed"
    node = next(n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.For) and ast.unparse(n.target) == "(a, jj)")
    r = np.zeros((NB + 1, 1)); r[1:, 0] = cache16(truth(actual)[1]).astype(np.float64)
    Lr = np.log1p(r); y = np.array([[np.prod(1.0 + np.array(actual)) - 1.0]])
    g = {"np": np, "need": np.array([[True]]), "Eidx": np.array([0]), "js": [0], "bnd": np.abs(r) >= .2999, "nanm": np.zeros_like(r, bool), "Lr": Lr, "y": y,
         "comp": np.array([[np.prod(1 + r) - 1]]), "UNEXPL": [], "PATCH": [], "E": np.array([0]), "Ecell": np.array([0]), "SY": ["S"]}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "frozen_price_patch", "exec"), g)
    return 100.0 * np.exp(np.concatenate([[0.0], np.cumsum(Lr[1:, 0])]))


def new_path(actual, closes):
    """the new code path: classify each bound bar against the official closes, apply_patch, cumulate"""
    _, r = truth(actual); r16 = cache16(r)
    bnd = np.nonzero(RL.is_bound(r16))[0]
    st, raw = zip(*[RL.classify(r16[p], closes[p + 1], closes[p]) for p in bnd])
    L = RL.base_logs(r16); RL.apply_patch(L, r16, bnd, np.zeros(len(bnd), np.int64), np.array(st), np.array(raw))
    return 100.0 * np.exp(np.concatenate([[0.0], np.cumsum(L)])), st


def unknown_band(actual):
    """no official bars: refuse a point path, return the band and the extreme paths"""
    _, r = truth(actual); r16 = cache16(r); bnd = np.nonzero(RL.is_bound(r16))[0]
    L = RL.base_logs(r16)
    try:
        RL.apply_patch(L, r16, bnd, np.zeros(len(bnd), np.int64), np.full(len(bnd), RL.UNAVAILABLE), np.full(len(bnd), np.nan)); refused = False
    except RL.UnavailablePath:
        refused = True
    known = RL.base_logs(r16).copy(); sign = np.zeros(NB)
    known[bnd] = np.nan; sign[bnd] = np.sign(r16[bnd].astype(np.float64))
    total = math.log1p(np.prod(1.0 + np.array(actual)) - 1.0)
    lo, hi = RL.feasible_band(known, sign, total); plo, phi = RL.extreme_paths(known, sign, total)
    return refused, 100.0 * np.exp(lo), 100.0 * np.exp(hi), plo, phi


# ---------------- counterexample 1: -60% / -40% vs -40% / -60% (same cache, same endpoint) ----------------
for tag, act, px25 in (("CE1a", (-0.6, -0.4), 40.0), ("CE1b", (-0.4, -0.6), 60.0)):
    tr, _ = truth(act); op = old_rule(act)
    ok(f"{tag}.old_device_endpoint_matches", abs(op[-1] - 24.0) < 1e-9, op[-1])
    ok(f"{tag}.old_device_A+25m_wrong(defect_reproduced)", abs(op[K25] - px25) > 1.0 and abs(op[K25] - 48.98979485566356) < 1e-9, op[K25])
    np_, st = new_path(act, tr)
    ok(f"{tag}.new_status_RESTORED", all(s == RL.RESTORED for s in st), st)
    ok(f"{tag}.new_reproduces_true_path_every_boundary", np.max(np.abs(np_ / tr - 1.0)) < 1e-12, float(np.max(np.abs(np_ / tr - 1.0))))
    ok(f"{tag}.new_A+25m_price", abs(np_[K25] - px25) < 1e-9, np_[K25])
    refused, lo, hi, plo, phi = unknown_band(act)
    ok(f"{tag}.no_official_bars_refuses_point_path", refused)
    ok(f"{tag}.band_A+25m", abs(lo[K25] - 100 * 0.24 / 0.7) < 0.01 and abs(hi[K25] - 70.0) < 0.01, (round(lo[K25], 4), round(hi[K25], 4)))
    ok(f"{tag}.band_contains_both_true_paths", lo[K25] <= 40.0 <= hi[K25] and lo[K25] <= 60.0 <= hi[K25])
    ok(f"{tag}.band_endpoint_pinned", abs(lo[-1] - 24.0) < 1e-9 and abs(hi[-1] - 24.0) < 1e-9)
    ok(f"{tag}.both_scenarios_bounded", plo is not None and phi is not None)

# ---------------- counterexample 2: +80% then -75% (cache +clip, -clip; endpoint 45) ----------------
act = (0.8, -0.75); tr, _ = truth(act); op = old_rule(act)
ok("CE2.old_device_first_bar_negative(defect_reproduced)", op[1] < 100.0 and abs(op[1] / 100.0 - 1.0 + 0.32917960675006314) < 1e-9, op[1])
np_, st = new_path(act, tr)
ok("CE2.new_reproduces_true_path_every_boundary", np.max(np.abs(np_ / tr - 1.0)) < 1e-12)
ok("CE2.new_A+25m_price_180", abs(np_[K25] - 180.0) < 1e-9, np_[K25])
ok("CE2.new_endpoint_45", abs(np_[-1] - 45.0) < 1e-9, np_[-1])
refused, lo, hi, plo, phi = unknown_band(act)
ok("CE2.no_official_bars_refuses_point_path", refused)
ok("CE2.band_A+25m_is_[130,inf)", abs(lo[K25] - 100 * (1 + RL.EDGE)) < 1e-9 and math.isinf(hi[K25]), (lo[K25], hi[K25]))
ok("CE2.band_contains_true_180", lo[K25] <= 180.0 <= hi[K25])
ok("CE2.old_value_outside_band(sign_violation)", op[K25] < lo[K25], (op[K25], lo[K25]))
ok("CE2.hi_scenario_unbounded_is_refused(None)", phi is None and plo is not None)
ok("CE2.lo_scenario_is_valid_path_to_endpoint", abs(100 * math.exp(plo[-1]) - 45.0) < 1e-9 and abs(100 * math.exp(plo[K25]) - 100 * (1 + RL.EDGE)) < 1e-9)

# ---------------- patch contract ----------------
_, r = truth((-0.6, -0.4)); r16 = cache16(r); L = RL.base_logs(r16)
def raises(fn, exc):
    try: fn(); return False
    except exc: return True
ok("contract.entry_off_bound_bar_refused", raises(lambda: RL.apply_patch(L.copy(), r16, [P1, P2, 3], [0, 0, 0], [1, 1, 1], [-0.6, -0.4, 0.01]), RL.PatchError))
ok("contract.bound_bar_without_entry_refused", raises(lambda: RL.apply_patch(L.copy(), r16, [P1], [0], [1], [-0.6]), RL.PatchError))
ok("contract.wrong_sign_restored_refused", raises(lambda: RL.apply_patch(L.copy(), r16, [P1, P2], [0, 0], [1, 1], [0.6, -0.4]), RL.PatchError))
ok("contract.restored_within_clip_refused", raises(lambda: RL.apply_patch(L.copy(), r16, [P1, P2], [0, 0], [1, 1], [-0.25, -0.4]), RL.PatchError))
ok("contract.conflict_status_refused", raises(lambda: RL.apply_patch(L.copy(), r16, [P1, P2], [0, 0], [RL.CONFLICT, 1], [0.2, -0.4]), RL.UnavailablePath))
ok("classify.conflict_when_official_contradicts_cache", RL.classify(np.float16(-0.3), 120.0, 100.0)[0] == RL.CONFLICT)
ok("classify.not_clipped_when_rounding_only", RL.classify(np.float16(0.3), 129.995, 100.0)[0] == RL.NOT_CLIPPED)
ok("classify.unavailable_when_close_missing", RL.classify(np.float16(0.3), None, 100.0)[0] == RL.UNAVAILABLE)
ok("band.infeasible_endpoint_refused", raises(lambda: RL.feasible_band(np.array([np.nan, 0.0]), np.array([1.0, 0.0]), math.log(1.1)), RL.InfeasibleCell))

# ---------------- real cells from the pod patch (fixture written by rp_fixture.py), if present ----------------
FX = os.path.join(HERE, "fixture_real_cells.json")
if os.path.exists(FX):
    fx = json.load(open(FX))
    for c in fx["cells"]:
        r16 = np.array([np.nan if v is None else v for v in c["cache16"]], np.float64).astype(np.float16)
        cl = np.array(c["official_closes"], np.float64); bnd = np.nonzero(RL.is_bound(r16))[0]
        st, raw = zip(*[RL.classify(r16[p], cl[p + 1], cl[p]) for p in bnd])
        L = RL.base_logs(r16); RL.apply_patch(L, r16, bnd, np.zeros(len(bnd), np.int64), np.array(st), np.array(raw))
        newp = np.concatenate([[0.0], np.cumsum(L)]); offp = np.log(cl / cl[0])
        oldp = np.array(c["old_logpath"], np.float64)
        e_new = float(np.max(np.abs(np.expm1(newp - offp)))); e_old = float(np.max(np.abs(np.expm1(oldp - offp))))
        ok(f"real.{c['sym']}@{c['E']}.new_path_equals_official(float16 precision)", e_new <= c["float16_bound"], (e_new, c["float16_bound"]))
        ok(f"real.{c['sym']}@{c['E']}.old_path_deviates", e_old > 10 * max(e_new, 1e-6), e_old)
        ok(f"real.{c['sym']}@{c['E']}.new_statuses_match_patch_file", [RL.STATUS_NAME[s] for s in st] == c["patch_status"], st)
else:
    print("SKIP real-cell fixture (tests/fixture_real_cells.json absent)")

n_fail = sum(1 for _, c, _ in RESULTS if not c)
print("RESULT %s: %d checks, %d failed" % ("ALL PASS" if n_fail == 0 else "FAILURES", len(RESULTS), n_fail))
sys.exit(0 if n_fail == 0 else 1)
