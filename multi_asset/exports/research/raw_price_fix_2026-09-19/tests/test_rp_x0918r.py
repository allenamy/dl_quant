#!/usr/bin/env python3
"""Regression test for the R5-02 extension to the x0918r data axis (ext_x0918r/, on top of commit 0c0fd45a0).

1. The base regression test (tests/test_rp_counterexamples.py, unchanged) runs first as a subprocess of the same interpreter; its exit code must be
   0 and its verdict line must read exactly "RESULT ALL PASS: 63 checks, 0 failed".
2. The 5 new-span clipped cells (tests/fixture_real_cells_x0918r.json, written by ext_x0918r/devices/rpx_restore.py from the checksum-verified
   archives) through the same code path the extended table uses (rp_lib.classify -> apply_patch):
   - the fixed path equals the official closes' path within the float16 budget of each cell at every 5m boundary;
   - statuses equal the extension patch file's;
   - AINUSDT 2026-09-16 00Z holds three clipped bars of mixed sign (-55.0%, -33.0%, +34.4%): the base-device rule (equal log shares) gives all three
     the same sign, deviates from the official path by far more than the fixed path, and the fixed path keeps every clip side;
   - single-clip cells: the equal-share rule and the fixed path agree to float32 precision (the rule only fails on multi-clip cells);
   - class check "data extended, patch not extended": the AIN cell with only 2 of its 3 entries is refused (PatchError), not left clipped;
   - no official bars: the AIN cell refuses a point path (UnavailablePath) and the admissible band (endpoint = meta y4) contains the official path
     at every 5m boundary.
run: python3 tests/test_rp_x0918r.py   (numpy only; exit 0 = all pass)
"""
import json, math, os, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "devices"))
import rp_lib as RL

RESULTS = []
def ok(name, cond, detail=""):
    RESULTS.append((name, bool(cond))); print(("PASS " if cond else "FAIL ") + name + (("  " + str(detail)) if detail != "" else ""))
def raises(fn, exc):
    try: fn(); return False
    except exc: return True

# ---------------- 1. base test, unchanged ----------------
p = subprocess.run([sys.executable, os.path.join(HERE, "test_rp_counterexamples.py")], capture_output=True, text=True)
last = [ln for ln in p.stdout.splitlines() if ln.startswith("RESULT ")]
ok("base_test.exit_code_0", p.returncode == 0, p.returncode)
ok("base_test.verdict_line", last == ["RESULT ALL PASS: 63 checks, 0 failed"], last)

# ---------------- 2. new-span real cells ----------------
fx = json.load(open(os.path.join(HERE, "fixture_real_cells_x0918r.json")))
ok("fixture.five_cells", len(fx["cells"]) == 5, len(fx["cells"]))
for c in fx["cells"]:
    tag = f"{c['sym']}@{c['E']}"
    r16 = np.array([np.nan if v is None else v for v in c["cache16"]], np.float64).astype(np.float16)
    cl = np.array(c["official_closes"], np.float64); bnd = np.nonzero(RL.is_bound(r16))[0]
    st, raw = zip(*[RL.classify(r16[k], cl[k + 1], cl[k]) for k in bnd])
    L = RL.base_logs(r16); RL.apply_patch(L, r16, bnd, np.zeros(len(bnd), np.int64), np.array(st), np.array(raw))
    newp = np.concatenate([[0.0], np.cumsum(L)]); offp = np.log(cl / cl[0]); oldp = np.array(c["old_logpath"], np.float64)
    e_new = float(np.max(np.abs(np.expm1(newp - offp)))); e_old = float(np.max(np.abs(np.expm1(oldp - offp))))
    ok(f"real.{tag}.fixed_path_equals_official(float16 budget)", e_new <= c["float16_bound"], (e_new, c["float16_bound"]))
    ok(f"real.{tag}.statuses_match_patch_file", [RL.STATUS_NAME[s] for s in st] == c["patch_status"], st)
    ok(f"real.{tag}.fixed_keeps_every_clip_side", all(np.sign(L[k]) == np.sign(float(r16[k])) for k in bnd))
    if len(bnd) >= 2:
        ok(f"real.{tag}.equal_share_rule_deviates", e_old > 100 * max(e_new, 1e-6), (e_old, e_new))
        ok(f"real.{tag}.equal_share_rule_flips_a_clip_side", any(np.sign(oldp[k + 1] - oldp[k]) != np.sign(float(r16[k])) for k in bnd))
    else:
        ok(f"real.{tag}.single_clip_rule_agrees_float32", float(np.max(np.abs(oldp - newp))) <= 1e-6, float(np.max(np.abs(oldp - newp))))

ain = [c for c in fx["cells"] if c["sym"] == "AINUSDT"]
ok("ain.present_with_three_mixed_clips", len(ain) == 1 and ain[0]["n_bound"] == 3)
if ain:
    c = ain[0]; r16 = np.array([np.nan if v is None else v for v in c["cache16"]], np.float64).astype(np.float16)
    cl = np.array(c["official_closes"], np.float64); bnd = np.nonzero(RL.is_bound(r16))[0]
    ok("ain.mixed_signs", sorted(np.sign(r16[bnd].astype(np.float64)).tolist()) == [-1.0, -1.0, 1.0], r16[bnd].tolist())
    st, raw = zip(*[RL.classify(r16[k], cl[k + 1], cl[k]) for k in bnd])
    ok("ain.patch_not_extended_is_refused", raises(lambda: RL.apply_patch(RL.base_logs(r16), r16, bnd[:2], [0, 0], np.array(st[:2]), np.array(raw[:2])), RL.PatchError))
    ok("ain.no_official_bars_refuses_point_path",
       raises(lambda: RL.apply_patch(RL.base_logs(r16), r16, bnd, np.zeros(3, np.int64), np.full(3, RL.UNAVAILABLE), np.full(3, np.nan)), RL.UnavailablePath))
    known = RL.base_logs(r16).copy(); sign = np.zeros(len(r16)); known[bnd] = np.nan; sign[bnd] = np.sign(r16[bnd].astype(np.float64))
    lo, hi = RL.feasible_band(known, sign, math.log1p(c["meta_y4"])); offp = np.log(cl / cl[0])
    # the band's endpoint is meta y4 (float32 and f16 inputs): allow the cell's float16 budget as slack at every boundary
    slack = math.log1p(c["float16_bound"]) + 1e-9
    ok("ain.band_contains_official_path", bool(np.all(lo - slack <= offp) and np.all(offp <= hi + slack)),
       (float(np.max(lo - offp)), float(np.max(offp - hi))))

n_fail = sum(1 for _, cnd in RESULTS if not cnd)
print("RESULT %s: %d checks, %d failed" % ("ALL PASS" if n_fail == 0 else "FAILURES", len(RESULTS), n_fail))
sys.exit(0 if n_fail == 0 else 1)
