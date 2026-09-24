#!/usr/bin/env python3
"""m3c_tests.py — red/green tests for the M3c change (AMENDMENT_3 §2-1 / AMENDMENT_2 §3-2): the combined-leverage budget 2.5 × NAV on top of
the M3b hook, and the /dev/shm temp redirect. pod2 only. OLD hook = M3b's m3_hook.py (sha 873769b9, imported by path under another module
name); NEW hook = this directory's m3_hook.py (M3c).

  C0  budget units (pure core):
        - leg larger than the room (book gross 2.0 NAV, BTC popped, formula leg 0.5 Gs): M3b places the full leg ⇒ combined 3.0 NAV (the red:
          above the budget); M3c scales it to 0.25 Gs ⇒ combined gross exactly 2.5 NAV (|err| ≤ 1e-9 NAV), cause unchanged, budget_scale 0.5;
        - book already above the budget (2.6 NAV): the leg may not increase the gross (combined ≤ 2.6 NAV; flat BTC ⇒ 'budget_zero'); a leg that
          crosses a BTC short passes up to the book's own gross;
        - book exactly at the limit with BTC on the leg's side ⇒ scale 0 ⇒ cause 'budget_zero', target untouched;
        - dust-only BTC + budget: the combined value uses the scaled leg (M3b logic kept);
        - within budget ⇒ budget_scale 1 and every M3b field bitwise equal to the M3b core's record;
        - max_combined_leverage None / 0 / −1 / nan / "2.5" / True ⇒ check_max_lev raises; run()'s config path refuses a missing key.
  C1  property: 3,000 random books (random BTC in / out / dust-only / force-flat / untradable, random β): with max_lev=None the M3c core's
      record equals the M3b core's on every M3b field, bitwise; with max_lev=2.5 the combined gross never exceeds max(2.5 NAV, book gross)
      by more than 1e-9 NAV and budget_scale == 1 whenever the M3b combined gross is within the budget.
  C2  temp redirect: after install_tmp_redirect, a HistMirror asked for /dev/shm/<x> creates <root>/<x> and /dev/shm/<x> does not exist.
  C3  in the certified simulator on the NC s42 book (one anchor from a flat book, decision only):
        (a) the MAIN anchor with the largest |β_exec| in the M3c flat-book diagnostic: if |formula leg| exceeds the room, M3b semantics
            (max_lev None) give combined target gross > 2.5 NAV (red) and M3c exactly 2.5 NAV (green); if the budget binds on NO flat-book
            anchor the test is recorded UNEXERCISED (never green) and the in-path truncation counts are the evidence;
        (b) the MAIN anchor with the smallest |β_exec| among 'applied': budget does not bind ⇒ M3c record == M3b-semantics record on every
            M3b field and the decision targets are equal;
        (c) the first MAIN 'applied_via_combined' anchor: the M3b dust logic still runs under the budget (cause 7, BTC released / planned).
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B m3c_tests.py PATH,HOME,LC_CTYPE <out.json> <overlay_config>
         <control_config> <m3c_flat_book_npz> <m3b_hook_py>
"""
import os, sys, json, time, shutil, importlib.util
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import m3_hook as HC                                           # M3c
DEV = "/workspace/baseline_tables_2026-09-19/devices_v3"
sys.path.insert(0, DEV)
import bt_driver_lib as DL

T0 = time.time()
outp, cfg_o, cfg_c, ep_c, m3b_hook_p = sys.argv[2:7]
assert HC.sha(m3b_hook_p).startswith("873769b995b91326"), "the OLD hook must be M3b's m3_hook.py (873769b9)"
spec = importlib.util.spec_from_file_location("m3_hook_M3b", m3b_hook_p); HB = importlib.util.module_from_spec(spec); spec.loader.exec_module(HB)
assert getattr(HC, "VARIANT", None) == "M3c" and getattr(HB, "VARIANT", None) == "M3b"
CO, CC = json.load(open(cfg_o)), json.load(open(cfg_c)); ro, rc_ = CO["runs"][0], CC["runs"][0]
TMPDIR = os.path.join(CO["paths"]["pod_root"], "tmp"); os.makedirs(TMPDIR, exist_ok=True)
OUT = {"device": "m3c_tests.py", "self_sha256": HC.sha(os.path.abspath(__file__)), "hook_m3c_sha256": HC.sha(os.path.join(HERE, "m3_hook.py")),
       "hook_m3b_sha256": HC.sha(m3b_hook_p), "configs": [cfg_o, HC.sha(cfg_o), cfg_c, HC.sha(cfg_c)], "m3c_flat_book_npz": [ep_c, HC.sha(ep_c)],
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "pgid": os.getpgid(0), "tests": [], "unexercised": []}
FAILS = []
M3B_FIELDS = ("gs", "n_target", "btc_before", "add_applied", "btc_dust_only", "combined_small", "beta_exec", "net_exec", "gross_exec", "add_intended",
              "cause", "btc_after", "beta_after")


def rec(name, ok, **kw):
    OUT["tests"].append(dict(test=name, ok=bool(ok), **kw))
    print(("GREEN " if ok else "RED   ") + name + " " + json.dumps(kw, default=str)[:600], flush=True)
    if not ok: FAILS.append(name)


def unexercised(name, **kw):
    OUT["unexercised"].append(dict(test=name, **kw)); print("UNEXERCISED " + name + " " + json.dumps(kw, default=str)[:400], flush=True)


def bits(r, keys=M3B_FIELDS):
    return {k: (np.float64(r[k]).view(np.uint64).item() if isinstance(r[k], float) else r[k]) for k in keys if k in r}


def raises(f):
    try:
        f(); return False
    except HC.M3Error:
        return True


def gross(t): return float(sum(abs(v) for v in t.values()))


# ───────────────────────── C0 units ─────────────────────────
def c0():
    syms = ["ADAUSDT", "BTCUSDT", "ETHUSDT"]; col = {s: j for j, s in enumerate(syms)}; gs = 200000.0; nav = 100000.0
    brow = np.array([2.0, 1.0, 1.0]); base = {"ADAUSDT": -100000.0, "ETHUSDT": 100000.0}          # β_exec = −0.5 ⇒ formula leg +100,000 = 0.5 Gs
    tb = dict(base); rb = HB.apply_overlay(tb, [], (), gs, brow, col, "overlay")
    tc = dict(base); r = HC.apply_overlay(tc, [], (), gs, brow, col, "overlay", max_lev=2.5, gm=2.0)
    rec("C0.M3b_full_leg_exceeds_budget (red)", gross(tb) / nav > 2.5, combined_over_nav=gross(tb) / nav)
    rec("C0.M3c_scaled_to_exactly_2.5_NAV (green)", abs(gross(tc) / nav - 2.5) <= 1e-9 and r["budget_scale"] == 0.5 and r["cause"] == HC.CAUSE["applied"]
        and r["add_intended"] == 100000.0 and r["add_leg"] == 50000.0 and tc["BTCUSDT"] == 50000.0, combined_over_nav=gross(tc) / nav, scale=r["budget_scale"])
    over = {"ADAUSDT": -130000.0, "ETHUSDT": 130000.0}; brow2 = np.array([1.5, 1.0, 1.0])            # 2.6 NAV; β_exec = −0.325 ⇒ leg +65,000
    t = dict(over); r = HC.apply_overlay(t, [], (), gs, brow2, col, "overlay", max_lev=2.5, gm=2.0)
    rec("C0.book_above_budget_leg_cannot_add_gross", gross(t) <= 260000.0 + 1e-6 and r["cause"] == HC.CAUSE["budget_zero"] and "BTCUSDT" not in t,
        combined_over_nav=gross(t) / nav, cause=r["cause"], scale=r["budget_scale"])
    over_b = {"ADAUSDT": -120000.0, "BTCUSDT": -20000.0, "ETHUSDT": 120000.0}; brow3 = np.array([1.5, 1.0, 1.0])   # β = (−180,000 − 20,000 + 120,000)/Gs = −0.4 ⇒ leg +80,000
    t = dict(over_b); r = HC.apply_overlay(t, [], (), gs, brow3, col, "overlay", max_lev=2.5, gm=2.0)
    rec("C0.book_above_budget_leg_reducing_BTC_short_passes_up_to_the_book_gross", abs(gross(t) - 260000.0) <= 1e-6 and r["budget_scale"] > 0,
        combined_over_nav=gross(t) / nav, btc_after=t["BTCUSDT"], scale=r["budget_scale"])
    at = {"ADAUSDT": -110000.0, "BTCUSDT": 30000.0, "ETHUSDT": 110000.0}; brow4 = np.array([2.0, 1.0, 1.0])      # 2.5 NAV exactly, BTC long, leg +
    t = dict(at); r = HC.apply_overlay(t, [], (), gs, brow4, col, "overlay", max_lev=2.5, gm=2.0)
    rec("C0.at_limit_same_side_budget_zero_untouched", r["cause"] == HC.CAUSE["budget_zero"] and t == at, cause=r["cause"], leg=r["add_intended"])
    dust = lambda v: abs(v) < 100.0
    t = dict(base); r = HC.apply_overlay(t, ["BTCUSDT"], (), gs, brow, col, "overlay", lambda: "btc_dust", True, dust, max_lev=2.5, gm=2.0)
    rec("C0.dust_only_uses_the_scaled_leg", r["cause"] == HC.CAUSE["applied_via_combined"] and t["BTCUSDT"] == 50000.0 and abs(gross(t) / nav - 2.5) <= 1e-9,
        cause=r["cause"], btc=t["BTCUSDT"])
    small = {"ADAUSDT": -60000.0, "ETHUSDT": 60000.0}; brow5 = np.array([1.1, 1.0, 1.0])              # β = −0.03 ⇒ leg +6,000 ≪ room
    t1 = dict(small); r1 = HB.apply_overlay(t1, [], (), gs, brow5, col, "overlay")
    t2 = dict(small); r2 = HC.apply_overlay(t2, [], (), gs, brow5, col, "overlay", max_lev=2.5, gm=2.0)
    rec("C0.within_budget_bitwise_M3b", bits(r1) == bits(r2) and t1 == t2 and r2["budget_scale"] == 1.0, scale=r2["budget_scale"])
    bad = [(v, raises(lambda v=v: HC.check_max_lev(v))) for v in (None, 0, -1.0, float("nan"), float("inf"), "2.5", True)]
    rec("C0.invalid_budget_raises", all(ok for _, ok in bad), cases=[[repr(v), ok] for v, ok in bad])
    rec("C0.check_max_lev_accepts_2.5", HC.check_max_lev(2.5) == 2.5)


# ───────────────────────── C1 property ─────────────────────────
def c1():
    rng = np.random.default_rng(20260924); col = {f"S{j:02d}USDT": j for j in range(12)}; col["BTCUSDT"] = 12
    syms = sorted(col); brow_all = rng.uniform(-1, 4, (3000, 13)); brow_all[:, 12] = 1.0
    n_eq = n_budget_ok = n_scale1_ok = n_bind = 0; worst = 0.0; bad = []
    for i in range(3000):
        gs = float(rng.uniform(1e4, 1e6)); nav = gs / 2.0
        names = [s for s in syms if s != "BTCUSDT" and rng.random() < 0.8]
        t = {s: float(rng.normal(0, gs / 8)) for s in names}
        mode_btc = rng.integers(0, 5)
        if mode_btc == 1: t["BTCUSDT"] = float(rng.normal(0, gs / 10))
        if mode_btc == 2: t["BTCUSDT"] = float(rng.uniform(-50, 50))
        if not t: t = {"S00USDT": gs / 2}
        g = gross(t); scale_to = rng.uniform(0.8, 1.35) * gs / g
        t = {k: v * scale_to for k, v in t.items()}
        ut = ["BTCUSDT"] if mode_btc in (2, 3, 4) else []; ff = ["BTCUSDT"] if mode_btc == 4 else []
        dust_only = mode_btc == 2
        dust = (lambda v: abs(v) < 100.0)
        brow = brow_all[i]
        ta = dict(t); ra = HB.apply_overlay(ta, ut, ff, gs, brow, col, "overlay", (lambda: "btc_untradable_other"), dust_only, dust)
        tb = dict(t); rb = HC.apply_overlay(tb, ut, ff, gs, brow, col, "overlay", (lambda: "btc_untradable_other"), dust_only, dust)
        if bits(ra) == bits(rb) and ta == tb: n_eq += 1
        else: bad.append(i)
        tc = dict(t); rc = HC.apply_overlay(tc, ut, ff, gs, brow, col, "overlay", (lambda: "btc_untradable_other"), dust_only, dust, max_lev=2.5, gm=2.0)
        lim = max(2.5 * nav, gross(t)); over = gross(tc) - lim; worst = max(worst, over / nav)
        if over <= 1e-9 * nav: n_budget_ok += 1
        within = gross(ta) <= lim
        if ra["cause"] not in (0, 7) or rc["add_intended"] == 0.0 or within == (rc["budget_scale"] == 1.0): n_scale1_ok += 1   # only where M3b placed a leg
        if rc["budget_scale"] < 1.0: n_bind += 1
    rec("C1.budget_none_equals_M3b_bitwise_3000_books", n_eq == 3000, n_equal=n_eq, first_bad=bad[:5])
    rec("C1.budget_never_exceeded", n_budget_ok == 3000, n_ok=n_budget_ok, worst_excess_over_nav=worst)
    rec("C1.scale1_iff_M3b_within_budget", n_scale1_ok == 3000, n_ok=n_scale1_ok, n_binding=n_bind)
    rec("C1.property_exercised_both_branches", 0 < n_bind < 3000, n_binding=n_bind)


# ───────────────────────── context + C2 / C3 ─────────────────────────
ES, SL, BH, L2 = DL.import_modules(CO, DEV)
root = HC.install_tmp_redirect(BH, TMPDIR)


def c2():
    probe = "/dev/shm/m3c_redirect_probe_%d" % os.getpid()
    M = BH.HistMirror("/nonexistent_mirror_root", probe)
    rec("C2.tmp_redirect_off_dev_shm", os.path.isdir(os.path.join(root, os.path.basename(probe))) and not os.path.exists(probe) and not M.tdir.startswith("/dev/shm"),
        tdir=M.tdir)
    shutil.rmtree(M.tdir, ignore_errors=True)


c0(); c1(); c2()
_orig_make = BH.make_sim_class
BETA = HC.BetaTable(CO["m3_hook"]["beta"]["npz"], CO["m3_hook"]["beta"]["sha256"])
_ck = []
C = DL.load_context(CO, ES, BH, L2, slice(0, int(CO["window"]["n_anchors"])), [ro, rc_], lambda n, ok, d=None: _ck.append((n, bool(ok))), lambda *a: None)
assert all(ok for _, ok in _ck), [n for n, ok in _ck if not ok]
ARMS = {ro["tag"].split("|")[0]: "overlay", rc_["tag"].split("|")[0]: "control"}
MAXLEV = HC.check_max_lev(CO["m3_hook"]["max_combined_leverage"])


def sim(A, run, max_lev):
    cls = HC.hooked_class_factory(_orig_make, BETA, ARMS, None, max_lev=max_lev)(ES)
    i = int(np.nonzero(C.anchors == A)[0][0]); W, fr = C.BOOKS[(run["arm"], run["book"])]
    tdir = os.path.join(TMPDIR, "m3c_tests_%d" % os.getpid())
    S = cls(C.BH.HistMirror(C.MIR, tdir), C.CAL, run["events"], {}, C.X, C.PANELS[run["price"]], C.fund, [A], C.cfgmap, W[i:i + 1], fr[i:i + 1],
            C.PIT_by_tag[run["tag"]][i:i + 1], C.SY, run["tag"], C.NAV0, 0, run["policy"], C.UA_SETS[run["ua_set"]], decisions_mode="none",
            keep_decisions=(A,), stop_at=float(C.cfgmap[A]["t_dec"]))
    S.run(); shutil.rmtree(tdir, ignore_errors=True)
    if len(S.m3_rec) != 1: raise HC.M3Error(f"{A}: {len(S.m3_rec)} hook records")
    return S.m3_rec[0], S.decisions.full[int(A)]["target"]


def iso(A): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(A)))


def c3():
    Z = np.load(ep_c); ZA = Z["anchor"].astype(np.int64); main = (Z["window"] == 0) & Z["reached"].astype(bool)
    nav0 = float(C.NAV0)
    k = int(np.argmax(np.where(main, np.abs(Z["beta_exec_c"]), -1.0))); A = int(ZA[k])
    rb, tb = sim(A, ro, None); rc, tc = sim(A, ro, MAXLEV)
    gb, gc = gross(tb) / nav0, gross(tc) / nav0
    if rb["cause"] in (0, 7) and gb > MAXLEV:
        rec("C3a.max_beta_anchor.M3b_semantics_exceed_budget (red)", gb > MAXLEV, anchor=iso(A), beta_exec=rb["beta_exec"], combined_over_nav=gb)
        rec("C3a.max_beta_anchor.M3c_exactly_at_budget (green)", abs(gc - MAXLEV) <= 1e-9 and rc["budget_scale"] < 1.0, anchor=iso(A), combined_over_nav=gc,
            scale=rc["budget_scale"])
    else:
        unexercised("C3a.budget_binds_on_the_flat_book", anchor=iso(A), beta_exec=rb["beta_exec"], M3b_combined_over_nav=gb, cause=rb["cause"],
                    note="the largest |β_exec| MAIN anchor on the flat book does not exceed the room; in-path truncation counts are the evidence")
    ok = main & np.isin(Z["cause_c"], [0])
    k = int(np.argmin(np.where(ok, np.abs(Z["beta_exec_c"]), np.inf))); A = int(ZA[k])
    rb, tb = sim(A, ro, None); rc, tc = sim(A, ro, MAXLEV)
    rec("C3b.non_binding_anchor_equals_M3b_semantics", bits(rb) == bits(rc) and tb == tc and rc["budget_scale"] == 1.0, anchor=iso(A), beta_exec=rc["beta_exec"])
    k7 = np.nonzero(main & (Z["cause_c"] == 7))[0]
    if len(k7):
        A = int(ZA[k7[0]]); rc, tc = sim(A, ro, MAXLEV)
        rec("C3c.dust_only_logic_under_budget", rc["cause"] == 7 and np.isfinite(rc["btc_plan_notional"]) and rc["btc_plan_notional"] != 0.0, anchor=iso(A),
            btc_planned=rc["btc_plan_notional"], leg=rc["add_leg"])
    else:
        unexercised("C3c.dust_only_logic_under_budget", note="no 'applied_via_combined' anchor in MAIN on the flat book")


c3()
OUT["n_tests"] = len(OUT["tests"]); OUT["n_red"] = len(FAILS); OUT["red"] = FAILS; OUT["runtime_s"] = round(time.time() - T0, 1)
OUT["VERDICT"] = "ALL GREEN" if not FAILS else "RED"
json.dump(OUT, open(outp + ".tmp", "w"), indent=1, default=str); os.replace(outp + ".tmp", outp)
print(f"M3C_TESTS VERDICT={OUT['VERDICT']} tests={OUT['n_tests']} red={len(FAILS)} unexercised={len(OUT['unexercised'])} out_sha256={HC.sha(outp)}", flush=True)
sys.exit(0 if not FAILS else 1)
