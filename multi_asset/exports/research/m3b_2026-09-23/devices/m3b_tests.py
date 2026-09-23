#!/usr/bin/env python3
"""m3b_tests.py — red/green tests for the M3b hook change (docs/AMENDMENT_1_m3_beta_overlay_2026-09-23.md, 912788743): the dust judgement on the
COMBINED BTC target. pod2 only. The OLD hook is M3's m3_hook.py (sha db05d136, imported by path under another module name); the NEW hook is
this directory's m3_hook.py (M3b). Every test states the value under both hooks where that is the point of the test.

  B0  units of the M3b core (apply_overlay): dust-only BTC + combined NOT dust ⇒ 'applied_via_combined', BTC = before + add; combined still
      dust ⇒ 'btc_combined_dust', untouched; control never touches; btc_dust_only without is_dust raises; tradable BTC with a small combined
      value ⇒ M3's behaviour (applied) and only counted; a force_flat BTC is never released even if dust-only is claimed.
  B1  THE REQUIRED RED → GREEN, inside the certified simulator (one anchor from a flat book, decision only): A* = the MAIN anchor whose
      cause was 'btc_dust' in M3's flat-book diagnostic with the largest |intended hedge| (rule fixed here). Construction asserted: base BTC
      pre-reshape |notional| < 2 × min_notional AND |intended hedge| > 10 × that threshold. Assertion "the hedge is delivered to the book plan()
      orders" (|planned-book β| < 0.01 gross units AND BTC planned notional within 1 % of the intended hedge): under the M3 hook it must be
      FALSE (red, the defect), under the M3b hook TRUE (green). Also: in the M3b overlay decision record every non-BTC target equals the
      control's bitwise.
  B2  held-BTC case (2-anchor sim, seed 0): the first pair of consecutive MAIN anchors that were both 'btc_dust' in M3's flat-book
      diagnostic and at whose second anchor BTC is HELD in the M3b overlay run (scan in time order; rule fixed here). At the second anchor:
      cause 'applied_via_combined', BTC was in a clamp list and was released (btc_released = 1), planned post-trade book β |.| < 0.01.
      Under the M3 hook the same 2-anchor run never holds BTC at the second anchor (no hedge at the first) — printed, not asserted.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B m3b_tests.py PATH,HOME,LC_CTYPE <out.json> <overlay_config>
         <control_config> <m3_flat_book_npz> <m3_hook_py>
"""
import os, sys, json, time, shutil, importlib.util
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import m3_hook as HB                                           # M3b
import m3_rules as RU
DEV = "/workspace/baseline_tables_2026-09-19/devices_v3"
sys.path.insert(0, DEV)
import bt_driver_lib as DL

T0 = time.time()
outp, cfg_o, cfg_c, ep_m3, m3_hook_p = sys.argv[2:7]
M3_HOOK_SHA = "db05d13624eaad28"
assert HB.sha(m3_hook_p).startswith(M3_HOOK_SHA), "the OLD hook must be M3's m3_hook.py (db05d136)"
spec = importlib.util.spec_from_file_location("m3_hook_M3", m3_hook_p); HA = importlib.util.module_from_spec(spec); spec.loader.exec_module(HA)
assert getattr(HB, "VARIANT", None) == "M3b" and not hasattr(HA, "VARIANT")
OUT = {"device": "m3b_tests.py", "self_sha256": HB.sha(os.path.abspath(__file__)), "hook_m3b_sha256": HB.sha(os.path.join(HERE, "m3_hook.py")),
       "hook_m3_sha256": HB.sha(m3_hook_p), "configs": [cfg_o, HB.sha(cfg_o), cfg_c, HB.sha(cfg_c)], "m3_flat_book_npz": [ep_m3, HB.sha(ep_m3)],
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "pgid": os.getpgid(0), "tests": []}
FAILS = []


def rec(name, ok, **kw):
    OUT["tests"].append(dict(test=name, ok=bool(ok), **kw))
    print(("GREEN " if ok else "RED   ") + name + " " + json.dumps(kw, default=str)[:600], flush=True)
    if not ok: FAILS.append(name)


def raises(f):
    try:
        f(); return False
    except HB.M3Error:
        return True


# ───────────────────────── B0: units ─────────────────────────
def b0():
    syms = ["ADAUSDT", "BTCUSDT", "ETHUSDT"]; col = {s: j for j, s in enumerate(syms)}; brow = np.array([1.5, 1.0, 1.2]); gs = 200000.0
    base = {"ADAUSDT": -80000.0, "ETHUSDT": 60000.0}                     # BTC popped (dust) ⇒ β_exec = (−120000 + 72000)/200000 = −0.24
    dust = lambda v: abs(v) < 100.0
    t = dict(base); r = HB.apply_overlay(t, ["BTCUSDT"], (), gs, brow, col, "overlay", lambda: "btc_dust", True, dust)
    rec("B0.dust_only_combined_not_dust_applied", r["cause"] == HB.CAUSE["applied_via_combined"] and t["BTCUSDT"] == r["add_intended"] and abs(r["beta_after"]) < 1e-15,
        cause=r["cause"], add=r["add_intended"], beta_after=r["beta_after"])
    t = dict(base); r = HA.apply_overlay(t, ["BTCUSDT"], (), gs, brow, col, "overlay", lambda: "btc_dust")
    rec("B0.m3_hook_same_input_skips (the defect, expected)", r["cause"] == HA.CAUSE["btc_dust"] and "BTCUSDT" not in t, cause=r["cause"])
    small = {"ADAUSDT": -40.0, "ETHUSDT": 45.0}                          # β_exec·Gs = −60 + 54 = −6 ⇒ combined 6 < 100
    t = dict(small); r = HB.apply_overlay(t, ["BTCUSDT"], (), gs, brow, col, "overlay", lambda: "btc_dust", True, dust)
    rec("B0.dust_only_combined_still_dust_untouched", r["cause"] == HB.CAUSE["btc_combined_dust"] and t == small, cause=r["cause"], add=r["add_intended"])
    t = dict(base); r = HB.apply_overlay(t, ["BTCUSDT"], (), gs, brow, col, "control", lambda: "btc_dust", True, dust)
    rec("B0.control_never_touches", t == base and r["cause"] == HB.CAUSE["applied_via_combined"] and r["add_applied"] == 0.0, cause=r["cause"])
    rec("B0.dust_only_without_is_dust_raises", raises(lambda: HB.apply_overlay(dict(base), ["BTCUSDT"], (), gs, brow, col, "overlay", None, True, None)))
    tb = {"ADAUSDT": -40.0, "BTCUSDT": 30.0, "ETHUSDT": 45.0}; t = dict(tb)
    r = HB.apply_overlay(t, [], (), gs, brow, col, "overlay", None, False, dust)
    rec("B0.tradable_small_combined_applied_as_m3_and_counted", r["cause"] == HB.CAUSE["applied"] and r["combined_small"] == 1.0 and t["BTCUSDT"] == 30.0 + r["add_intended"],
        cause=r["cause"], combined=t["BTCUSDT"])
    t = dict(base); r = HB.apply_overlay(t, ["BTCUSDT"], ["BTCUSDT"], gs, brow, col, "overlay", lambda: "btc_dust", True, dust)
    rec("B0.force_flat_never_released", r["cause"] == HB.CAUSE["btc_force_flat"] and t == base, cause=r["cause"])


# ───────────────────────── context ─────────────────────────
CO, CC = json.load(open(cfg_o)), json.load(open(cfg_c)); ro, rc_ = CO["runs"][0], CC["runs"][0]
assert CO["m3_hook"]["device_sha256"] == OUT["hook_m3b_sha256"], "overlay config must pin this M3b hook"
ES, SL, BH, L2 = DL.import_modules(CO, DEV)
_orig_make = BH.make_sim_class
BETA = HB.BetaTable(CO["m3_hook"]["beta"]["npz"], CO["m3_hook"]["beta"]["sha256"])
_ck = []
C = DL.load_context(CO, ES, BH, L2, slice(0, int(CO["window"]["n_anchors"])), [ro, rc_], lambda n, ok, d=None: _ck.append((n, bool(ok))), lambda *a: None)
assert all(ok for _, ok in _ck), [n for n, ok in _ck if not ok]
ARMS = {ro["tag"].split("|")[0]: "overlay", rc_["tag"].split("|")[0]: "control"}


def sim(anchors, run, hook, keep=()):
    """from a flat book over `anchors` (consecutive), stopped at the last anchor's decision; returns (hook records, decision records)"""
    cls = hook.hooked_class_factory(_orig_make, BETA, ARMS, None)(ES)
    i0 = int(np.nonzero(C.anchors == anchors[0])[0][0]); i1 = i0 + len(anchors)
    assert np.array_equal(C.anchors[i0:i1], np.array(anchors, np.int64))
    W, fr = C.BOOKS[(run["arm"], run["book"])]
    tdir = "/dev/shm/m3b_tests_%d" % os.getpid()
    S = cls(C.BH.HistMirror(C.MIR, tdir), C.CAL, run["events"], {}, C.X, C.PANELS[run["price"]], C.fund, list(anchors), C.cfgmap, W[i0:i1], fr[i0:i1],
            C.PIT_by_tag[run["tag"]][i0:i1], C.SY, run["tag"], C.NAV0, 0, run["policy"], C.UA_SETS[run["ua_set"]], decisions_mode="none",
            keep_decisions=tuple(keep), stop_at=float(C.cfgmap[int(anchors[-1])]["t_dec"]))
    S.run(); shutil.rmtree(tdir, ignore_errors=True)
    return {int(r["A"]): r for r in S.m3_rec}, S.decisions.full


def iso(A): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(A)))


Z = np.load(ep_m3); ZA = Z["anchor"].astype(np.int64); main = (Z["window"] == 0) & Z["reached"].astype(bool); dust4 = main & (Z["cause_c"] == 4)


def b1():
    k = int(np.argmax(np.where(dust4, np.abs(Z["intended_gross_units"]), -1.0))); A = int(ZA[k])
    ra, _ = sim([A], ro, HA); rb, db = sim([A], ro, HB, keep=(A,)); rc, dc = sim([A], rc_, HB, keep=(A,))
    ra, rb, rc = ra[A], rb[A], rc[A]
    thr = 2.0 * 50.0
    btc_pre = abs(float(Z["btc_before_c"][k]))                            # M3 flat-book control: executed base BTC (popped ⇒ 0)
    rec("B1.construction.base_btc_dust_and_large_hedge", rb["btc_dust_only"] == 1.0 and abs(rc["add_intended"]) > 10 * thr and btc_pre < thr,
        anchor=iso(A), btc_exec_base=btc_pre, intended_hedge_usdt=rc["add_intended"], threshold_usdt=thr)

    def delivered(r):
        post = (r["pos_beta"] + r["plan_beta"]); bn = r["btc_plan_notional"]
        return bool(abs(post) < 0.01 and np.isfinite(bn) and abs(bn - r["add_intended"]) <= 0.01 * abs(r["add_intended"])), post, bn
    da, pa, bna = delivered(ra); dbb, pb, bnb = delivered(rb)
    rec("B1.M3_hook_does_NOT_deliver (red before the change)", not da, cause=ra["cause"], planned_book_beta=pa, btc_planned=bna, intended=ra["add_intended"])
    rec("B1.M3b_hook_delivers (green after the change)", dbb and rb["cause"] == HB.CAUSE["applied_via_combined"], cause=rb["cause"], planned_book_beta=pb,
        btc_planned=bnb, intended=rb["add_intended"])
    to, tc = db[A]["target"], dc[A]["target"]
    others = all(to.get(s) == tc.get(s) for s in set(to) | set(tc) if s != HB.BTC)
    rec("B1.M3b_other_names_bitwise_control", others and to.get(HB.BTC) == tc.get(HB.BTC, 0.0) + rb["add_intended"], btc_control=tc.get(HB.BTC), btc_overlay=to.get(HB.BTC))


def b2():
    idx = np.nonzero(dust4)[0]; tried = 0
    for k in idx.tolist():
        if k + 1 >= len(ZA) or not dust4[k + 1] or int(ZA[k + 1]) - int(ZA[k]) != 14400: continue
        A1, A2 = int(ZA[k]), int(ZA[k + 1]); tried += 1
        rb, _ = sim([A1, A2], ro, HB)
        if A2 not in rb or abs(rb[A2]["btc_held_notional"]) <= 1e-9: continue
        r = rb[A2]; post = r["pos_beta"] + r["plan_beta"]
        ra, _ = sim([A1, A2], ro, HA)
        rec("B2.held_btc_released_and_hedged", r["cause"] == HB.CAUSE["applied_via_combined"] and r["btc_released"] == 1.0 and abs(post) < 0.01,
            pair=[iso(A1), iso(A2)], pairs_scanned=tried, btc_held=r["btc_held_notional"], btc_target=r["btc_after"], planned_book_beta=post,
            m3_hook_same_pair={"cause_at_A2": ra.get(A2, {}).get("cause"), "btc_held_at_A2": ra.get(A2, {}).get("btc_held_notional")})
        return
    rec("B2.held_btc_released_and_hedged", False, why="no consecutive dust pair with BTC held at the second anchor", pairs_scanned=tried)


b0(); b1(); b2()
OUT["n_tests"] = len(OUT["tests"]); OUT["n_red"] = len(FAILS); OUT["red"] = FAILS; OUT["runtime_s"] = round(time.time() - T0, 1)
OUT["VERDICT"] = "ALL GREEN" if not FAILS else "RED"
json.dump(OUT, open(outp + ".tmp", "w"), indent=1, default=str); os.replace(outp + ".tmp", outp)
print(f"M3B_TESTS VERDICT={OUT['VERDICT']} tests={OUT['n_tests']} red={len(FAILS)} out_sha256={HB.sha(outp)}", flush=True)
sys.exit(0 if not FAILS else 1)
