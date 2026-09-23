#!/usr/bin/env python3
"""m3_tests.py — red/green tests for M3 (m3_hook.py). pod2 only (the executor code and the certified simulator are imported from the pinned
paths). Every test has a BASELINE that must be green and, where it could be vacuous, a RED-CAPABILITY control (a deliberately wrong input or
a mutant of the hook that the same assertion must reject); a control that does not go red fails the test. Values are printed.

  U   units of the hook core: BTC untradable / force_flat ⇒ target untouched, cause coded; zero hedge ⇒ untouched; empty target ⇒ NaN β, named
      cause, untouched; an anchor off the β table, a symbol off its axis, Gs <= 0, a non-finite table value ⇒ raise (unknown is not zero)
  T1R future-perturbation invariance of the β MATRIX the hook reads (BETA_M3_full.npz), on the certified price table: 7 anchors incl. three in
      2026 and the last one (2026-09-18T20Z); BTC + every name with a UA cell near A + random names to 80; β at A BITWISE unchanged when every
      price row after A is perturbed and UA cells are added after A; the subset build equals the full-table matrix row bitwise; control: the bar
      ENDING at A perturbed ⇒ β changes
  T1H future invariance at the HOOK's read point, inside the certified simulator (one anchor from a flat book, decision only): a β table whose
      every row other than A is garbage (NaN / ±1e6) gives a hook record bitwise equal to the real table's; control: garbage in row A ⇒ differs
  T2  the value point is AFTER reshape + clamp (synthetic anchor, the executor's own anchor_loop.apply_withhold_and_reshape, tree 409ea16):
      a published book with net +10 % of Gs whose POP removes a +40k name and whose CLAMP pins a held untradable short. Assert β_exec equals the
      dense dot product of the FINAL executed target (≤ 1e-15), and that it differs from (i) the published / pre-reshape β, (ii) the β of the
      reshaped-but-unclamped target — both by > 0.005 (the construction really moves the net). Mutants: a hook reading the pre-reshape target
      (the M2 object) and a hook reading the target before the clamp must each FAIL the same assertion. Overlay: β after the hedge |.| ≤ 1e-12,
      only BTC changed (every other entry bitwise), BTC += −β_exec·Gs exactly.
  T2R the same on a REAL anchor inside the certified simulator: the executed target is exec_sim's own decision record (keep_decisions=(A,),
      control arm ⇒ target after POP→RESHAPE→CLAMP, untouched); hook β_exec == dense dot of that record (≤ 1e-15); the overlay arm's recorded
      target equals the control's except BTC, which equals control + add_intended bitwise; A = the MAIN anchor with the largest |β_exec − β_pre|
      in the flat-book diagnostic among anchors whose cause is 'applied' (rule fixed here) ⇒ also asserts |β_exec − β_pre| > 0.005 there.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B m3_tests.py PATH,HOME,LC_CTYPE <out.json> <overlay_config>
         <control_config> <exec_path_npz>
"""
import os, sys, json, time, calendar, copy, shutil
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import m2_lib as M
import m3_hook as H
import m3_rules as RU
DEV = "/workspace/baseline_tables_2026-09-19/devices_v3"
sys.path.insert(0, DEV)
import bt_driver_lib as DL

T0 = time.time()
outp, cfg_o, cfg_c, ep_npz = sys.argv[2:6]
OUT = {"device": "m3_tests.py", "self_sha256": H.sha(os.path.abspath(__file__)), "hook_sha256": H.sha(os.path.join(HERE, "m3_hook.py")),
       "m2_lib_sha256": H.sha(os.path.join(HERE, "m2_lib.py")), "configs": [cfg_o, H.sha(cfg_o), cfg_c, H.sha(cfg_c)], "exec_path_npz": [ep_npz, H.sha(ep_npz)],
       "numpy": np.__version__, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "pgid": os.getpgid(0), "tests": []}
FAILS = []


def rec(name, ok, **kw):
    OUT["tests"].append(dict(test=name, ok=bool(ok), **kw))
    print(("GREEN " if ok else "RED   ") + name + " " + json.dumps(kw, default=str)[:500], flush=True)
    if not ok: FAILS.append(name)


def raises(f, exc=H.M3Error):
    try:
        f(); return False
    except exc:
        return True


def fake_table(anchor, B, symbols):
    bt = H.BetaTable.__new__(H.BetaTable)
    bt.anchor = np.asarray(anchor, np.int64); bt.B = np.asarray(B, np.float64); bt.symbols = list(symbols)
    bt.row = {int(a): i for i, a in enumerate(bt.anchor.tolist())}; bt.col = {s: j for j, s in enumerate(bt.symbols)}
    return bt


# ───────────────────────── U: hook core units ─────────────────────────
def t_units():
    syms = ["ADAUSDT", "BTCUSDT", "ETHUSDT"]; col = {s: j for j, s in enumerate(syms)}; brow = np.array([1.5, 1.0, 1.2]); gs = 1000.0
    base = {"ADAUSDT": -400.0, "BTCUSDT": 100.0, "ETHUSDT": 300.0}      # β_exec = (−600 + 100 + 360)/1000 = −0.14
    t = dict(base); r = H.apply_overlay(t, ["BTCUSDT"], (), gs, brow, col, "overlay", lambda: "btc_dust")
    rec("U.btc_untradable_untouched_cause_coded", t == base and r["cause"] == H.CAUSE["btc_dust"] and r["add_applied"] == 0.0, rec_=r)
    t = dict(base); r = H.apply_overlay(t, ["XUSDT"], ["BTCUSDT"], gs, brow, col, "overlay")
    rec("U.btc_force_flat_untouched", t == base and r["cause"] == H.CAUSE["btc_force_flat"], cause=r["cause"])
    t = dict(base); r = H.apply_overlay(t, [], (), gs, brow, col, "overlay")
    rec("U.overlay_applies_minus_beta_times_gs", abs(r["beta_exec"] + 0.14) < 1e-15 and t["BTCUSDT"] == 100.0 + r["add_intended"] and abs(r["beta_after"]) < 1e-15
        and all(t[s] == base[s] for s in syms if s != "BTCUSDT"), beta_exec=r["beta_exec"], add=r["add_intended"], beta_after=r["beta_after"])
    t = dict(base); r = H.apply_overlay(t, [], (), gs, brow, col, "control")
    rec("U.control_never_touches", t == base and r["add_applied"] == 0.0 and r["cause"] == H.CAUSE["applied"], cause=r["cause"])
    z = {"ADAUSDT": -256.0, "ETHUSDT": 512.0}; brow0 = np.array([1.5, 1.0, 0.75]); t = dict(z)
    r = H.apply_overlay(t, [], (), 1024.0, brow0, col, "overlay")                                          # −0.375 + 0.375 = 0 exactly
    rec("U.zero_hedge_creates_no_btc_entry", t == z and "BTCUSDT" not in t and r["cause"] == H.CAUSE["zero_hedge"], beta_exec=r["beta_exec"])
    t = {}; r = H.apply_overlay(t, [], (), gs, brow, col, "overlay")
    rec("U.empty_target_named_nan_untouched", t == {} and np.isnan(r["beta_exec"]) and r["cause"] == H.CAUSE["empty_target"], cause=r["cause"])
    bt = fake_table([0, 14400], np.ones((2, 3)), syms)
    cases = [("anchor_off_table", lambda: bt.row_of(28800)), ("symbol_off_axis", lambda: H.book_beta({"FOOUSDT": 1.0}, gs, brow, col)),
             ("gs_zero", lambda: H.book_beta(base, 0.0, brow, col)), ("gs_nan", lambda: H.apply_overlay(dict(base), [], (), float("nan"), brow, col, "overlay")),
             ("bad_mode", lambda: H.apply_overlay(dict(base), [], (), gs, brow, col, "hedge"))]
    res = [(n, raises(f)) for n, f in cases]
    tmp = "/dev/shm/m3_tests_%d_nan.npz" % os.getpid()
    np.savez(tmp, anchor=np.array([0], np.int64), beta=np.array([[np.nan, 1.0, 1.0]]), symbols=np.array(syms)); res.append(("nonfinite_table", raises(lambda: H.BetaTable(tmp))))
    np.savez(tmp, anchor=np.array([0], np.int64), beta=np.array([[1.0, 0.9, 1.0]]), symbols=np.array(syms)); res.append(("btc_column_not_1", raises(lambda: H.BetaTable(tmp))))
    os.remove(tmp)
    rec("U.unknown_raises", all(ok for _, ok in res), cases=res)


# ───────────────────────── T1R: β matrix future invariance on the certified table ─────────────────────────
def t1_real(beta):
    W = "/workspace/baseline_tables_2026-09-19/work/"
    PM = np.load(W + "price_full_raw_x0918r_meta.npz", allow_pickle=True); SY = [str(s) for s in PM["symbols"]]; bj = SY.index(M.BTC)
    LPf = np.load(W + "price_full_raw_x0918r.npy", mmap_mode="r"); grid = PM["grid"].astype(np.int64)
    rng = np.random.default_rng(20260923)
    for iso in ("2023-09-14T08:00:00Z", "2024-03-12T16:00:00Z", "2025-04-07T00:00:00Z", "2025-10-10T20:00:00Z", "2026-02-05T12:00:00Z",
                "2026-06-15T04:00:00Z", "2026-09-18T20:00:00Z"):
        A = calendar.timegm(time.strptime(iso, "%Y-%m-%dT%H:%M:%SZ"))
        rA = int((A - grid[0]) // M.ROW); r0 = rA - (M.N_WIN + 2) * 48; r1 = min(len(grid), rA + 30 * 48)
        ur_all = PM["unavail_grid_row"].astype(np.int64); uc_all = PM["unavail_col"].astype(np.int64)
        near = np.unique(uc_all[(ur_all >= r0) & (ur_all < r1)])
        pool = np.setdiff1d(np.arange(len(SY)), np.concatenate([[bj], near]))
        cols = np.concatenate([[bj], near, rng.choice(pool, max(0, 80 - 1 - len(near)), replace=False)]).astype(np.int64)
        LP = np.array(LPf[r0:r1][:, cols]); g = grid[r0:r1]
        sel = (ur_all >= r0) & (ur_all < r1) & np.isin(uc_all, cols); cmap = {int(c): i for i, c in enumerate(cols)}
        ur = ur_all[sel] - r0; uc = np.array([cmap[int(c)] for c in uc_all[sel]], np.int64)
        ff = PM["first_fin"].astype(np.int64)[cols]; lf = PM["last_fin"].astype(np.int64)[cols]
        T, R, V = M.bars_4h(LP, g, ff, lf, ur, uc); B0, N0, E0, _ = M.betas_at(T, R, V, np.array([A]), 0)
        LP2 = LP.copy(); k = rA - r0
        n_fut = len(LP2) - k - 1
        if n_fut > 0:
            LP2[k + 1:] += np.random.default_rng(5).normal(0, 0.3, LP2[k + 1:].shape)
        fut_ua = np.arange(k + 1, min(k + 200, len(LP2)))
        ur2 = np.concatenate([ur, fut_ua]); uc2 = np.concatenate([uc, np.full(len(fut_ua), 1 + (len(cols) - 1) // 2)])
        T2, R2, V2 = M.bars_4h(LP2, g, ff, lf, ur2, uc2); B2, N2, E2, _ = M.betas_at(T2, R2, V2, np.array([A]), 0)
        same = np.array_equal(B0.view(np.uint64), B2.view(np.uint64)) and np.array_equal(N0, N2)
        LP3 = LP.copy(); LP3[k, 1:] += 0.05
        T3, R3, V3 = M.bars_4h(LP3, g, ff, lf, ur, uc); B3, *_ = M.betas_at(T3, R3, V3, np.array([A]), 0)
        full = beta.row_of(A)[cols]
        rec(f"T1R.{iso}.future_invariance_real.baseline_bitwise_equal", same and n_fut > 0, n_cols=len(cols), n_future_rows_perturbed=int(n_fut),
            future_ua_added=int(len(fut_ua)), n_est=int(E0.sum()))
        rec(f"T1R.{iso}.control_bar_ending_at_A_changes_beta", not np.array_equal(B0.view(np.uint64), B3.view(np.uint64)), max_abs_diff=float(np.max(np.abs(B0 - B3))))
        rec(f"T1R.{iso}.subset_equals_full_matrix_row_bitwise", np.array_equal(B0[0].view(np.uint64), np.ascontiguousarray(full).view(np.uint64)),
            max_abs_diff=float(np.max(np.abs(B0[0] - full))))


# ───────────────────────── context for the in-simulator tests ─────────────────────────
CO, CC = json.load(open(cfg_o)), json.load(open(cfg_c)); ro, rc_ = CO["runs"][0], CC["runs"][0]
ES, SL, BH, L2 = DL.import_modules(CO, DEV)
_orig_make = BH.make_sim_class
BETA = H.BetaTable(CO["m3_hook"]["beta"]["npz"], CO["m3_hook"]["beta"]["sha256"])
_ck = []
C = DL.load_context(CO, ES, BH, L2, slice(0, int(CO["window"]["n_anchors"])), [ro, rc_], lambda n, ok, d=None: _ck.append((n, bool(ok))), lambda *a: None)
assert all(ok for _, ok in _ck), [n for n, ok in _ck if not ok]


def sim_one(A, run, beta, keep=False):
    """one anchor from a flat book with the M3 hook built on `beta`, decision only; returns (hook record, exec_sim decision record)"""
    cls = H.hooked_class_factory(_orig_make, beta, {ro["tag"].split("|")[0]: "overlay", rc_["tag"].split("|")[0]: "control"}, None)(ES)
    i = int(np.nonzero(C.anchors == A)[0][0]); W, fr = C.BOOKS[(run["arm"], run["book"])]
    tdir = "/dev/shm/m3_tests_%d" % os.getpid()
    S = cls(C.BH.HistMirror(C.MIR, tdir), C.CAL, run["events"], {}, C.X, C.PANELS[run["price"]], C.fund, [A], C.cfgmap, W[i:i + 1], fr[i:i + 1],
            C.PIT_by_tag[run["tag"]][i:i + 1], C.SY, run["tag"], C.NAV0, 0, run["policy"], C.UA_SETS[run["ua_set"]], decisions_mode="none",
            keep_decisions=(A,) if keep else (), stop_at=float(C.cfgmap[A]["t_dec"]))
    S.run(); shutil.rmtree(tdir, ignore_errors=True)
    if len(S.m3_rec) != 1: raise H.M3Error(f"{A}: {len(S.m3_rec)} hook records")
    return S.m3_rec[0], (S.decisions.full.get(int(A)) if keep else None)


def rec_bits(r):
    return {k: np.float64(r[k]).view(np.uint64).item() if isinstance(r[k], float) else r[k] for k in sorted(r)}


def t1_hook():
    for iso in ("2024-03-12T16:00:00Z", "2026-02-05T12:00:00Z", "2026-09-18T20:00:00Z"):
        A = calendar.timegm(time.strptime(iso, "%Y-%m-%dT%H:%M:%SZ"))
        i = BETA.row[A]
        Bg = BETA.B.copy(); rng = np.random.default_rng(11)
        Bg[:i] = np.nan; Bg[i + 1:] = rng.choice([-1e6, 1e6], size=Bg[i + 1:].shape)
        g_tab = fake_table(BETA.anchor, Bg, BETA.symbols)
        for run in (rc_, ro):
            r0, _ = sim_one(A, run, BETA); r1, _ = sim_one(A, run, g_tab)
            rec(f"T1H.{iso}.{run['arm']}.other_rows_garbage_record_bitwise_equal", rec_bits(r0) == rec_bits(r1), beta_exec=r0["beta_exec"], add=r0["add_intended"])
        Bc = BETA.B.copy(); Bc[i] = Bc[i] + 0.25
        r2, _ = sim_one(A, rc_, fake_table(BETA.anchor, Bc, BETA.symbols)); r0, _ = sim_one(A, rc_, BETA)
        rec(f"T1H.{iso}.control_row_A_changed_record_differs", r2["beta_exec"] != r0["beta_exec"], beta_exec_real=r0["beta_exec"], beta_exec_mutated=r2["beta_exec"])


# ───────────────────────── T2: the value point is after reshape + clamp (synthetic, executor's own function) ─────────────────────────
def t2_synth():
    X = C.X; AL = X.AL
    check_switch = AL.RESHAPE_REDEMEAN is True and AL.RESHAPE_RESCALE is True
    syms = ["ADAUSDT", "BNBUSDT", "BTCUSDT", "DOGEUSDT", "ETHUSDT", "LINKUSDT", "SOLUSDT", "XRPUSDT"]
    bvals = {"ADAUSDT": 1.1, "BNBUSDT": 0.7, "BTCUSDT": 1.0, "DOGEUSDT": 1.4, "ETHUSDT": 1.2, "LINKUSDT": 1.3, "SOLUSDT": 1.6, "XRPUSDT": 0.9}
    col = {s: j for j, s in enumerate(syms)}; brow = np.array([bvals[s] for s in syms]); gs = 200000.0
    pub = {"ETHUSDT": 30000.0, "SOLUSDT": 30000.0, "XRPUSDT": 20000.0, "DOGEUSDT": -40000.0, "ADAUSDT": -40000.0, "LINKUSDT": -30000.0,
           "BTCUSDT": 10000.0, "BNBUSDT": 40000.0}                       # net +20k = +10 % of Gs; BNB unheld untradable ⇒ POP; LINK held short
    held = {"LINKUSDT": -10000.0}; untr = ["BNBUSDT", "LINKUSDT"]
    tgt = dict(pub); AL.apply_withhold_and_reshape(tgt, held, untr, gs, floors_usdt=None, force_flat=())
    noclamp = dict(pub); AL.apply_withhold_and_reshape(noclamp, {}, ["BNBUSDT"], gs, floors_usdt=None, force_flat=())
    final = dict(tgt)
    r = H.apply_overlay(tgt, untr, (), gs, brow, col, "control")
    dense = float(sum(final[s] * bvals[s] for s in final)) / gs
    b_pre = float(sum(pub[s] * bvals[s] for s in pub)) / gs
    b_noclamp = float(sum(noclamp[s] * bvals[s] for s in noclamp)) / gs
    net_pre, net_noclamp, net_final = sum(pub.values()) / gs, sum(noclamp.values()) / gs, sum(final.values()) / gs
    rec("T2.construction.reshape_switches_on_and_clamp_pins_link", check_switch and final["LINKUSDT"] == -10000.0 and noclamp["LINKUSDT"] != -10000.0
        and "BNBUSDT" not in final, link_final=final["LINKUSDT"], link_noclamp=noclamp.get("LINKUSDT"), net_pre=net_pre, net_noclamp=net_noclamp, net_final=net_final)
    rec("T2.baseline.beta_exec_equals_dense_dot_of_final_target", abs(r["beta_exec"] - dense) <= 1e-15, beta_exec=r["beta_exec"], dense=dense)
    rec("T2.construction.reshape_and_clamp_each_move_net_and_beta", abs(dense - b_pre) > 0.005 and abs(dense - b_noclamp) > 0.005
        and abs(net_noclamp - net_pre) > 0.05 and abs(net_final - net_noclamp) > 0.05,
        beta_published=b_pre, beta_reshaped_unclamped=b_noclamp, beta_final=dense, net_pre=net_pre, net_noclamp=net_noclamp, net_final=net_final)

    def mutant_pre(target, untradable, force_flat, g, brow_, col_, mode):      # the M2 object: β of the published / pre-reshape target
        return {"beta_exec": H.book_beta(pub, g, brow_, col_)[0]}

    def mutant_noclamp(target, untradable, force_flat, g, brow_, col_, mode):  # reshaped but read before the clamp
        return {"beta_exec": H.book_beta(noclamp, g, brow_, col_)[0]}
    for nm, mut in (("pre_reshape", mutant_pre), ("before_clamp", mutant_noclamp)):
        rm = mut(dict(final), untr, (), gs, brow, col, "control")
        rec(f"T2.mutant_{nm}.fails_the_same_assertion", not (abs(rm["beta_exec"] - dense) <= 1e-15), mutant_beta=rm["beta_exec"], dense=dense)
    t_o = dict(final); ro_ = H.apply_overlay(t_o, untr, (), gs, brow, col, "overlay")
    others = all(np.float64(t_o[s]).view(np.uint64) == np.float64(final[s]).view(np.uint64) for s in final if s != "BTCUSDT")
    rec("T2.overlay.neutral_only_btc_changed_exact_add", abs(ro_["beta_after"]) <= 1e-12 and others and t_o["BTCUSDT"] == final["BTCUSDT"] + (-r["beta_exec"] * gs),
        beta_after=ro_["beta_after"], add=ro_["add_applied"])


def t2_real():
    Z = np.load(ep_npz); A_ = Z["anchor"]; w = Z["window"]; r = Z["reached"].astype(bool)
    d = np.where(r & (w == 0) & (Z["cause_c"] == H.CAUSE["applied"]), np.abs(Z["beta_exec_c"] - Z["beta_pre_c"]), -1.0)   # MAIN, hedge applied
    A = int(A_[int(np.argmax(d))])
    rc, dc = sim_one(A, rc_, BETA, keep=True); rov, do = sim_one(A, ro, BETA, keep=True)
    tgt_c = dc["target"]; tgt_o = do["target"]; brow = BETA.row_of(A); gs = rc["gs"]
    dense = float(sum(v * brow[BETA.col[s]] for s, v in tgt_c.items())) / gs
    rec("T2R.real_anchor.beta_exec_equals_dense_dot_of_exec_sim_decision_target", abs(rc["beta_exec"] - dense) <= 1e-15 and abs(rc["beta_exec"] - rc["beta_pre"]) > 0.005,
        anchor=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(A)), beta_exec=rc["beta_exec"], dense=dense, beta_pre=rc["beta_pre"], net_exec=rc["net_exec"])
    oth = set(tgt_c) | set(tgt_o)
    same_others = all(tgt_c.get(s) == tgt_o.get(s) for s in oth if s != H.BTC)
    rec("T2R.real_anchor.overlay_target_equals_control_plus_add_on_btc_only", same_others and tgt_o[H.BTC] == tgt_c.get(H.BTC, 0.0) + rc["add_intended"]
        and rov["cause"] == H.CAUSE["applied"], btc_control=tgt_c.get(H.BTC), btc_overlay=tgt_o.get(H.BTC), add=rc["add_intended"])
    rec("T2R.real_anchor.control_mutant_pre_reshape_would_fail", abs(rc["beta_pre"] - dense) > 1e-15, beta_pre=rc["beta_pre"], dense=dense)


t_units(); t1_real(BETA); t1_hook(); t2_synth(); t2_real()
OUT["n_tests"] = len(OUT["tests"]); OUT["n_red"] = len(FAILS); OUT["red"] = FAILS; OUT["runtime_s"] = round(time.time() - T0, 1)
OUT["VERDICT"] = "ALL GREEN" if not FAILS else "RED"
json.dump(OUT, open(outp + ".tmp", "w"), indent=1, default=str); os.replace(outp + ".tmp", outp)
print(f"M3_TESTS VERDICT={OUT['VERDICT']} tests={OUT['n_tests']} red={len(FAILS)} out_sha256={H.sha(outp)}", flush=True)
sys.exit(0 if not FAILS else 1)
