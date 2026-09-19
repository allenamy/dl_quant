#!/usr/bin/env python3
"""bt_battery.py — battery for the v3.1 HISTORY DRIVER (bt_hist_sim31.py + bt_driver_lib.py + bt_launch.py). Each check runs its baseline
first (must be green); every mutation must go red. Real inputs (pinned by the frozen run config), short windows, pod2 CPU. It calls the
production functions (bt_driver_lib.load_context / make_sim / run_one / aggregate_arrays), never a re-implementation.

  D0  pins + price receipt + executor tree (verify_pins).
  D1  audits on a real window (old/LEGACY and raw/UA-FREEZE-EXCLUDE, 2 seeds): fee = |cash|·rate exactly, funding = −q·P·rate, no duplicate
      charge, window identity, main-return identity, 5-minute NAV = window snapshot at every boundary, effective fee rates = the USDT era.
      Mutations: exec_sim knob --funding-double (funding audit red); --fee-asset-wrong (fee-rate check red).
  D2  determinism: the same (run, seed) twice ⇒ every array bitwise equal; another seed ⇒ different. (No mutation: a property check.)
  D3  v2-EQUIVALENT DECISION where it exists: the first W_ALPHA anchor (flat book, NAV 100,000) with the mutation knob that restores v2's
      decision bar (--legacy-decision-lookahead ⇒ the N+25 bar) must reproduce stream R's v2 record (sizing gross, symbols, withheld, plans
      sent, min-notional skips, planned turnover). Beyond that anchor a v2-equivalent run does not exist: v3.1 replaced v2's expected-value
      fills by per-request draws, removed the guaranteed exit completion, and uses the pooled calibration — so paths diverge by design.
      Mutation: v3.1's own decision bar (N+20) ⇒ the planned turnover differs (red).
  D4  FUTURE-PRICE INVARIANCE on history: every price after the decision bar of anchor A_k is perturbed ⇒ the decision digests of every
      anchor ≤ A_k are identical; positive control: A_{k+1}'s digest does change. Mutation: --legacy-decision-lookahead ⇒ A_k changes (red).
  D5  UNAVAILABLE GAPS ARE NEVER PRICED (UA-FREEZE-EXCLUDE) on the real AERGOUSDT gap 2025-04-16 00:05–11:05 with an injected holding
      (target weight + tradable override, so the gap is exercised): no AERGO fill is booked inside a UA bar; no AERGO plan at frozen anchors;
      UNKNOWN cells held and excluded; the result is bitwise invariant to garbage written into the table at the UA bars. (B') on a synthetic
      UA stretch N+25..N+60 of a held name: fills there are cancelled. Mutations: LEGACY-ZERO-RETURN reads the garbage (red); an empty UA
      index books fills inside the gap (red); LEGACY books the (B') fills (red).
  D6  A PRICE-SOURCE SWITCH CHANGES ONLY PRICES: switching to a byte-copy of the same table ⇒ bitwise identical results; the frozen config's
      runs differ only in {tag, price, policy, ua_set, role}. Mutations: the switch also swaps cref (red); the switch also drops funding (red).
  D7  THE 32-PATH MEAN EQUALS THE AVERAGE OF THE PER-PATH FILES (on a given run directory): AGG json shas = the files; aggregate_arrays over
      the files read back in seed order = AGG npz bitwise. Mutations: one path file tampered (red); one seed missing (red).
  D8  RULE MODE: an injected −12 % shock to every name ⇒ §4-2 flatten and HALT until the next UTC day. Mutation: mode 'live' (no rule) (red).
  D9  5-MINUTE NAV = the simulator's own equity at that bar (stop the same run at random bars). Mutation: the next bar's equity (red).
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_battery.py PATH,HOME,LC_CTYPE <config.json> <agg_run_dir> <out.json>
"""
import os, sys, json, time, copy, collections, math, shutil
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
import numpy as np

T0 = time.time()
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt_driver_lib as DL
CFG = json.load(open(sys.argv[2])); AGG_DIR = sys.argv[3]; OUTP = sys.argv[4]
RES = []


def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)


def ok(name, cond, detail=None):
    RES.append(dict(check=name, ok=bool(cond), detail=detail)); log(("PASS " if cond else "FAIL ") + name, json.dumps(detail, default=str)[:260] if detail is not None else "")


def mut(name, red, detail=None): ok("[mutation red] " + name, red, detail)


def quiet(*a, **k): pass


pin_fail = []
DL.verify_pins(CFG, lambda n, c, d=None: pin_fail.append(n) if not c else None)
ok("D0.pins_price_receipt_executor_tree", not pin_fail, pin_fail)
ES, SL, BH, L2 = DL.import_modules(CFG, HERE)
SL.install_readonly_guard()
RUNS = {r["tag"]: r for r in CFG["runs"]}
R_OLD = RUNS["S2_A0pred_s42|CMB|rule|old|LEGACY"]; R_RAW = RUNS["S2_A0pred_s42|CMB|rule|raw|UAFE"]
AX0 = np.arange(DL.ts(CFG["window"]["first_anchor"]), DL.ts(CFG["window"]["last_anchor"]) + 1, 14400, dtype=np.int64)
PM = np.load(CFG["pins"]["price_full_meta"]["path"], allow_pickle=True); G0 = int(PM["grid"][0])
LPM = {k: np.load(CFG["pins"][f"price_full_{k}"]["path"], mmap_mode="r") for k in ("old", "raw")}


def sel_of(start_iso, n):
    k0 = int(np.searchsorted(AX0, DL.ts(start_iso))); return slice(k0, k0 + n)


def slice_prices(sel, which=("old", "raw"), pad=2):
    a0 = int(AX0[sel][0]); a1 = int(AX0[sel][-1]) + 14400
    r0 = max(0, (a0 - pad * 14400 - G0) // 300); r1 = min(LPM["old"].shape[0], (a1 + pad * 14400 - G0) // 300 + 1)
    return {k: (np.array(LPM[k][r0:r1]), G0 + 300 * r0, PM[f"cref_{k}"]) for k in which}, r0


def ctx(sel, runs, prices):
    fails = []
    c = DL.load_context(CFG, ES, BH, L2, sel, runs, lambda n, cnd, d=None: fails.append(n) if not cnd else None, quiet, prices=prices)
    assert not fails, fails
    return c


def arrays_equal(a, b, keys=None):
    keys = keys or sorted(set(a) & set(b))
    diff = [k for k in keys if not np.array_equal(np.asarray(a[k]), np.asarray(b[k]), equal_nan=True)]
    return not diff, diff


# ---------------- D1 audits + D2 determinism ----------------
SEL1 = sel_of("2025-03-01T00:00:00Z", 60)
P1, _ = slice_prices(SEL1)
C1 = ctx(SEL1, [R_OLD, R_RAW], P1)
base = {}
for r in (R_OLD, R_RAW):
    for sd in (0, 1):
        arr, out, S = DL.run_one(C1, r, sd); base[(r["tag"], sd)] = (arr, out)
        ok(f"D1.audits_clean.{r['price']}.seed{sd}", DL.audits_clean(out["audits"]), out["audits"])
        fee_exp = out["audits"]["notional_maker"] * C1.CAL["params"]["fee_rate"]["USDT_era"]["maker"] + out["audits"]["notional_taker"] * C1.CAL["params"]["fee_rate"]["USDT_era"]["taker"]
        ok(f"D1.effective_fee_rates_are_USDT_era.{r['price']}.seed{sd}", abs(arr["fee"].sum() - fee_exp) <= 1e-9 * max(1.0, fee_exp), [float(arr["fee"].sum()), fee_exp])
arr_fd, out_fd, _ = DL.run_one(C1, R_RAW, 0, knobs={"funding_double": True})
mut("D1.funding_double_breaks_the_funding_audit", out_fd["audits"]["funding_max_err"] > 1e-9, out_fd["audits"]["funding_max_err"])
arr_fw, out_fw, _ = DL.run_one(C1, R_RAW, 0, knobs={"fee_asset_wrong": True})
fe = out_fw["audits"]["notional_maker"] * C1.CAL["params"]["fee_rate"]["USDT_era"]["maker"] + out_fw["audits"]["notional_taker"] * C1.CAL["params"]["fee_rate"]["USDT_era"]["taker"]
mut("D1.fee_asset_wrong_breaks_the_fee_rate_check", abs(arr_fw["fee"].sum() - fe) > 1e-9 * max(1.0, fe), [float(arr_fw["fee"].sum()), fe])
arr_r, _, _ = DL.run_one(C1, R_RAW, 0)
eq, diff = arrays_equal(arr_r, base[(R_RAW["tag"], 0)][0])
ok("D2.same_seed_bitwise_identical", eq, diff[:5])
eq01, _ = arrays_equal(base[(R_RAW["tag"], 0)][0], base[(R_RAW["tag"], 1)][0], ["navm1", "turnover", "fee"])
ok("D2.other_seed_differs", not eq01)

# ---------------- D3 v2-equivalent decision at the first W_ALPHA anchor ----------------
SEL3 = slice(0, 1)
P3, _ = slice_prices(SEL3, ("old",))
C3 = ctx(SEL3, [R_OLD], P3)
V2 = np.load(CFG["baseline_v2"]["runs"]["S2_A0pred_s42"])
a3, o3, _ = DL.run_one(C3, R_OLD, 0, knobs={"legacy_decision_lookahead": True})
fields = ("equity_at_decision", "sizing_gross", "n_symbols", "n_untradable", "n_plans_sent", "n_skip_min_notional", "plan_turnover")
cmp3 = {f: (float(a3["rec_" + f][0]), float(V2["rec_" + f][0])) for f in fields}
good3 = all((abs(x - y) <= 1e-9 * max(1.0, abs(y))) for x, y in cmp3.values())
ok("D3.v2_decision_record_reproduced_first_anchor_with_v2_decision_bar", good3 and int(V2["A"][0]) == int(a3["A"][0]), cmp3)
a3n, _, _ = DL.run_one(C3, R_OLD, 0)
mut("D3.v31_own_decision_bar_changes_planned_turnover", abs(float(a3n["rec_plan_turnover"][0]) - float(V2["rec_plan_turnover"][0])) > 1e-6 * float(V2["rec_plan_turnover"][0]),
    [float(a3n["rec_plan_turnover"][0]), float(V2["rec_plan_turnover"][0])])

# ---------------- D4 future-price invariance ----------------
k4 = 30; A4 = C1.anchors; t_dec = float(A4[k4] + 1440); b_dec = int(t_dec // 300 * 300)
LPpert = P1["raw"][0].copy(); rp0 = (b_dec - P1["raw"][1]) // 300
rng = np.random.default_rng([20260919, 4]); LPpert[rp0 + 1:] += np.cumsum(rng.normal(0, 0.02, (LPpert.shape[0] - rp0 - 1, LPpert.shape[1])), axis=0)
C4 = ctx(SEL1, [R_RAW], {"raw": P1["raw"]}); C4p = ctx(SEL1, [R_RAW], {"raw": (LPpert, P1["raw"][1], P1["raw"][2])})
def digests(c, knobs, stop):
    S = DL.make_sim(c, R_RAW, 0, "/dev/shm/bt_bat_d4_%d" % os.getpid(), knobs=knobs, decisions_mode="digest", stop_at=stop); S.run(); shutil.rmtree("/dev/shm/bt_bat_d4_%d" % os.getpid(), ignore_errors=True)
    return dict(S.decisions)
d0 = digests(C4, {}, t_dec + 0.5); d1 = digests(C4p, {}, t_dec + 0.5)
upto = [a for a in A4[:k4 + 1] if int(a) in d0]
ok("D4.decisions_up_to_A_k_invariant_to_future_prices", len(upto) >= 25 and all(d0[a] == d1.get(a) for a in upto), {"anchors_compared": len(upto)})
t_next = float(A4[k4 + 1] + 1440)
e0 = digests(C4, {}, t_next + 0.5); e1 = digests(C4p, {}, t_next + 0.5)
ok("D4.positive_control_A_k+1_sees_the_perturbation", e0.get(int(A4[k4 + 1])) != e1.get(int(A4[k4 + 1])))
m0 = digests(C4, {"legacy_decision_lookahead": True}, t_dec + 0.5); m1 = digests(C4p, {"legacy_decision_lookahead": True}, t_dec + 0.5)
mut("D4.lookahead_decision_changes_A_k", m0.get(int(A4[k4])) != m1.get(int(A4[k4])))

# ---------------- D5 UNAVAILABLE never priced ----------------
SEL5 = sel_of("2025-04-14T00:00:00Z", 30)
P5, r05 = slice_prices(SEL5, ("raw",))
C5 = ctx(SEL5, [R_RAW], P5)
SY = C5.SY; jA = SY.index("AERGOUSDT")
W5, fr5 = C5.BOOKS[(R_RAW["arm"], R_RAW["book"])]; W5 = W5.copy(); fr5 = np.ones_like(fr5)
W5[:, jA] = 0.03 * np.abs(W5).sum(1)
TRS5 = C5.TRS.copy(); TRS5[:, jA] = 2
C5.cfgmap = BH.CfgMap31(TRS5, C5.tr_row, SY, C5.GM, CFG["current_production_config"]["chase_weights"], 1440)
PIT5 = C5.PIT.copy(); PIT5[:, jA] = True; C5.PIT = PIT5
UAx = C5.UA_SETS["UNAVAILABLE_3084"]; ua_rows = UAx.by_col[jA]
ua_ts = set((UAx.g0 + 300 * ua_rows).tolist())
def run_capture(c, policy, panel=None, ua=None, knobs=None, name="AERGOUSDT"):
    S = DL.make_sim(c, R_RAW, 0, "/dev/shm/bt_bat_d5_%d" % os.getpid(), book=(W5, fr5), panel=panel, policy=policy, knobs=knobs)
    if ua is not None: S.UA = ua
    trades = []; orig = S.trade_log.append
    def app(x, orig=orig):
        if x[1] == name: trades.append((float(x[0]), float(x[2])))
        orig(x)
    S.trade_log.append = app
    Wn = S.run(); shutil.rmtree("/dev/shm/bt_bat_d5_%d" % os.getpid(), ignore_errors=True)
    return DL.path_arrays(c, S, Wn), S, trades
in_ua = lambda t: int(math.ceil(t / 300) * 300) in ua_ts
a5, S5, tr5 = run_capture(C5, "UA-FREEZE-EXCLUDE")
held = float(a5["unk_held"].max()); frozen = int(np.nansum(a5["rec_n_frozen"] > 0))
ok("D5.positive_control_AERGO_held_into_the_gap", held >= 1 and any(abs(q) > 0 for _, q in tr5), {"max_unknown_held_names": held, "aergo_trades": len(tr5)})
ok("D5.no_AERGO_fill_booked_inside_a_UA_bar", not any(in_ua(t) for t, _ in tr5), {"inside": [t for t, _ in tr5 if in_ua(t)][:5]})
fz = [int(a) for a, n_ in zip(a5["A"], a5["rec_n_frozen"]) if n_ > 0]
trades_from_frozen = [t for t, _ in tr5 for a in fz if a + 1440 <= t <= a + 1440 + 1200]
ok("D5.frozen_anchors_present_and_no_AERGO_trade_from_a_frozen_decision", len(fz) >= 3 and not trades_from_frozen, {"frozen_anchors": len(fz), "trades_from_frozen": trades_from_frozen[:5], "ua": dict(S5.ua)})
dr = (a5["navm1"] / a5["navm0"] - 1.0) - (a5["nav1"] / a5["nav0"] - 1.0); unk = a5["unk_excluded"] * (a5["unk_price"] + a5["unk_funding"])
hit = unk != 0.0
ok("D5.unknown_cells_excluded_only_where_they_exist", DL.audits_clean(DL.path_summary(C5, S5, a5, R_RAW, 0, 0.0)["audits"]) and hit.sum() >= 1
   and bool(np.all(np.abs(dr[hit]) > 0)) and float(np.abs(dr[~hit]).max()) <= 1e-12,
   {"windows_with_unknown_pnl": int(hit.sum()), "max_abs_dr_elsewhere": float(np.abs(dr[~hit]).max()), "unk_sum": float(unk.sum())})
LPg = P5["raw"][0].copy()
for rr in ua_rows.tolist():
    pr = rr + (UAx.g0 - P5["raw"][1]) // 300
    if 0 <= pr < LPg.shape[0]: LPg[pr, jA] += 3.0 + 0.1 * (pr % 7)
LPg_legacy = LPg.copy()                                                                 # ua_hold below restores its OWN array in place
n_garbage = int((LPg != P5["raw"][0]).sum())
Pg = BH.FullPanel(LPg, P5["raw"][1], SY, PM["first_fin"], PM["cref_raw"], PM["ref_px"]); n_held = Pg.ua_hold(UAx)
a5g, _, _ = run_capture(C5, "UA-FREEZE-EXCLUDE", panel=Pg)
eq5, diff5 = arrays_equal(a5, a5g)
ok("D5.bitwise_invariant_to_garbage_at_UA_bars", eq5 and n_garbage > 0 and n_held == n_garbage, {"diff": diff5[:5], "garbage_cells": n_garbage, "held_cells": n_held})
PgL = BH.FullPanel(LPg_legacy, P5["raw"][1], SY, PM["first_fin"], PM["cref_raw"], PM["ref_px"])
ok("D5.legacy_panel_still_carries_the_garbage", int((PgL.LP != P5["raw"][0]).sum()) == n_garbage)
aL0, _, trL = run_capture(C5, "LEGACY-ZERO-RETURN"); aLg, _, _ = run_capture(C5, "LEGACY-ZERO-RETURN", panel=PgL)
mut("D5.LEGACY_reads_the_garbage", not arrays_equal(aL0, aLg)[0])
empty = BH.UAIndex(UAx.g0, UAx.n, np.array([], np.int64), np.array([], np.int64), len(SY))
aE, SE, trE = run_capture(C5, "UA-FREEZE-EXCLUDE", ua=empty)
mut("D5.empty_UA_index_trades_or_prices_through_the_gap", int(np.nansum(aE["rec_n_frozen"] > 0)) == 0 and (any(in_ua(t) for t, _ in trE) or not arrays_equal(aE, a5)[0]),
    {"frozen": int(np.nansum(aE["rec_n_frozen"] > 0)), "inside": len([t for t, _ in trE if in_ua(t)])})
# (B'): a synthetic UA stretch N+25 .. N+60 on a name the real book holds at anchor A_k (window SEL1)
S_probe = DL.make_sim(C1, R_RAW, 0, "/dev/shm/bt_bat_probe_%d" % os.getpid(), stop_at=t_dec - 1); S_probe.run(); shutil.rmtree("/dev/shm/bt_bat_probe_%d" % os.getpid(), ignore_errors=True)
held_names = sorted(S_probe.q, key=lambda s_: -abs(S_probe.q[s_] * (S_probe.px(s_, b_dec) or 0)))
Ak = int(A4[k4])
def fills_in(c, policy, uaidx, name):
    S = DL.make_sim(c, R_RAW, 0, "/dev/shm/bt_bat_bp_%d" % os.getpid(), policy=policy)
    S.UA = uaidx; got = []; orig = S.trade_log.append
    def app(x, orig=orig):
        if x[1] == name and Ak + 1500 < x[0] <= Ak + 3600: got.append(x)
        orig(x)
    S.trade_log.append = app
    S.run(); shutil.rmtree("/dev/shm/bt_bat_bp_%d" % os.getpid(), ignore_errors=True)
    return got, S
pick = None
for nm in held_names[:40]:
    g_leg, _ = fills_in(C1, "LEGACY-ZERO-RETURN", C1.UA_SETS["UNAVAILABLE_3084"], nm)
    if g_leg: pick = nm; break
if pick is None:
    ok("D5b.found_a_name_with_fills_in_N+25..N+60", False)
else:
    jP = SY.index(pick); rows_b = np.arange((Ak + 1500 + 300 - C1.GRID0) // 300, (Ak + 3600 - C1.GRID0) // 300 + 1)
    synth = BH.UAIndex(C1.GRID0, C1.NG, rows_b, np.full(len(rows_b), jP), len(SY))
    g_ua, S_ua = fills_in(C1, "UA-FREEZE-EXCLUDE", synth, pick)
    ok("D5b.fills_inside_a_UA_stretch_are_cancelled", len(g_ua) == 0 and S_ua.ua.get("fills_cancelled_ua_bar", 0) > 0, {"name": pick, "booked": len(g_ua), "cancelled": S_ua.ua.get("fills_cancelled_ua_bar", 0)})
    g_legacy, _ = fills_in(C1, "LEGACY-ZERO-RETURN", synth, pick)
    mut("D5b.LEGACY_books_them", len(g_legacy) > 0, {"booked": len(g_legacy)})

# ---------------- D6 price switch changes only prices ----------------
Pcopy = {"old": P1["old"], "raw": (P1["old"][0].copy(), P1["old"][1], PM["cref_old"])}
R_sw = dict(R_OLD, tag=R_OLD["tag"] + "|switch_to_copy", price="raw")
C6 = ctx(SEL1, [R_OLD, R_sw], Pcopy)
a6o, _, _ = DL.run_one(C6, R_OLD, 0); a6c, _, _ = DL.run_one(C6, R_sw, 0)
eq6, diff6 = arrays_equal(a6o, a6c)
ok("D6.switch_to_identical_content_is_bitwise_identical", eq6, diff6[:5])
keys_all = set().union(*[set(r) for r in CFG["runs"]])
cfg_ok = True
for arm in {r["arm"] for r in CFG["runs"]}:
    rs = [r for r in CFG["runs"] if r["arm"] == arm]
    for x in rs:
        for y in rs:
            dk = {k for k in keys_all if x.get(k) != y.get(k)}
            cfg_ok &= dk <= {"tag", "price", "policy", "ua_set", "role"}
ok("D6.config_runs_differ_only_in_price_policy_labels", cfg_ok)
Pbad = {"old": P1["old"], "raw": (P1["old"][0].copy(), P1["old"][1], PM["cref_raw"])}
C6b = ctx(SEL1, [R_OLD, R_sw], Pbad); a6b, _, _ = DL.run_one(C6b, R_sw, 0)
mut("D6.switch_that_also_swaps_cref", not arrays_equal(a6o, a6b)[0])
F_empty = BH.HistFunding(CFG["pins"]["ledger_full"]["path"], C6.SY, 0, 1)
a6f, _, _ = DL.run_one(C6, R_sw, 0, fund=F_empty)
mut("D6.switch_that_also_drops_funding", not arrays_equal(a6o, a6f)[0])

# ---------------- D7 the 32-path mean = the average of the per-path files ----------------
aggj = [f for f in os.listdir(AGG_DIR) if f.startswith("AGG_") and f.endswith(".json")]
if len(aggj) != 1:
    ok("D7.one_AGG_file_in_the_directory", False, aggj)
else:
    J = json.load(open(os.path.join(AGG_DIR, aggj[0]))); Z = np.load(os.path.join(AGG_DIR, aggj[0][:-5] + ".npz"))
    shas_ok = all(DL.sha(os.path.join(AGG_DIR, f["npz"])) == f["sha256"] for f in J["path_files"]) and DL.sha(os.path.join(AGG_DIR, aggj[0][:-5] + ".npz")) == J["agg_npz_sha256"]
    ok("D7.path_file_shas_match_the_AGG_listing", shas_ok, {"n_paths": len(J["path_files"])})
    P = [np.load(os.path.join(AGG_DIR, f["npz"])) for f in sorted(J["path_files"], key=lambda f: f["seed"])]
    re = DL.aggregate_arrays(P, C1.GM)
    ok("D7.mean_recomputed_from_files_equals_AGG_bitwise", all(np.array_equal(re[k], Z[k]) for k in re), {"keys": len(re), "n_paths": len(P)})
    Pt = [dict((k, p[k]) for k in p.files) for p in P]; Pt[0]["navm1"] = Pt[0]["navm1"] * 1.0001
    mut("D7.tampered_path_file_changes_the_mean", not np.array_equal(DL.aggregate_arrays(Pt, C1.GM)["r_main_mean"], Z["r_main_mean"]))
    mut("D7.missing_seed_changes_the_mean", len(P) < 2 or not np.array_equal(DL.aggregate_arrays(P[1:], C1.GM)["r_main_mean"], Z["r_main_mean"]))

# ---------------- D8 rule mode ----------------
SEL8 = sel_of("2025-03-03T00:00:00Z", 12)
P8, _ = slice_prices(SEL8, ("raw",))
LP8 = P8["raw"][0].copy(); shock_b = DL.ts("2025-03-03T10:05:00Z"); rs8 = (shock_b - P8["raw"][1]) // 300
C8 = ctx(SEL8, [R_RAW], {"raw": (LP8, P8["raw"][1], P8["raw"][2])})
w8 = C8.BOOKS[(R_RAW["arm"], R_RAW["book"])][0][1]                                      # the 04Z target: longs fall 12 %, shorts rise 12 % (adverse to the book)
LP8[rs8:, :] += np.where(w8 > 0, math.log(0.88), np.where(w8 < 0, math.log(1.12), 0.0))[None, :]
a8, o8, S8 = DL.run_one(C8, R_RAW, 0)
halts = int((a8["status"] == 1).sum()); fl = o8["events_fired_counts"].get("FLATTEN", 0)
# the shock bar closes 10:05, after the 08Z anchor's evaluation (08:45); the first evaluation that sees it is the 12Z anchor's (12:45) ⇒ flatten at
# max(12Z + 2760 s, 12:45 + 1 s) = 12:46; the 12Z decision (12:24) precedes it; HALT for 16Z and 20Z; 03-04 00Z trades again.
# (try2 of this battery asserted HALT from 12Z — a fixture-expectation error; its receipt is kept as BT_BATTERY_try2.json)
st = {int(a): int(x) for a, x in zip(a8["A"], a8["status"])}
exp_halt = [DL.ts("2025-03-03T16:00:00Z"), DL.ts("2025-03-03T20:00:00Z")]
ok("D8.rule_flatten_at_first_eval_after_shock_and_halt_until_next_day", fl == 1 and o8["flatten_log"][0][0] == "2025-03-03T12:46:00Z" and all(st[a] == 1 for a in exp_halt)
   and st[DL.ts("2025-03-03T12:00:00Z")] != 1 and st[DL.ts("2025-03-04T00:00:00Z")] != 1 and halts == 2,
   {"flattens": fl, "halt_anchors": halts, "flatten_log": o8["flatten_log"]})
S8l = DL.make_sim(C8, dict(R_RAW, events="live"), 0, "/dev/shm/bt_bat_d8_%d" % os.getpid()); S8l.run(); shutil.rmtree("/dev/shm/bt_bat_d8_%d" % os.getpid(), ignore_errors=True)
mut("D8.no_rule_no_flatten", sum(1 for e in S8l.events_fired if e["type"] == "FLATTEN") == 0)

# ---------------- D9 5-minute NAV = the simulator's own equity ----------------
full = base[(R_RAW["tag"], 0)][0]; nav5 = full["nav5_sim"]; t50 = int(full["nav5_t0"])
rng9 = np.random.default_rng([20260919, 9]); picks = sorted(set(int(x) for x in rng9.integers(1, len(nav5) - 2, 6)))
worst = 0.0; worst_shift = 0.0
for i in picks:
    b = t50 + 300 * i
    S9 = DL.make_sim(C1, R_RAW, 0, "/dev/shm/bt_bat_d9_%d" % os.getpid(), stop_at=b); S9.run(); shutil.rmtree("/dev/shm/bt_bat_d9_%d" % os.getpid(), ignore_errors=True)
    e = S9.equity(b); worst = max(worst, abs(e / nav5[i] - 1.0)); worst_shift = max(worst_shift, abs(e / nav5[i + 1] - 1.0))
ok("D9.nav5_equals_simulator_equity_at_random_bars", worst <= 1e-12, {"bars": picks, "max_rel_err": worst})
mut("D9.next_bar_comparison_detected", worst_shift > 1e-9, {"max_rel_err_shifted": worst_shift})

n_pass = sum(1 for r in RES if r["ok"]); n = len(RES)
line = ("BT_BATTERY VERDICT: ALL PASS %d/%d checks (baselines green first, every mutation red)" % (n_pass, n)) if n_pass == n else \
       ("BT_BATTERY VERDICT: FAIL %d/%d checks; failed: %s" % (n_pass, n, [r["check"] for r in RES if not r["ok"]]))
json.dump(dict(device="bt_battery.py", self_sha256=DL.sha(os.path.abspath(__file__)), python=sys.version.split()[0], numpy=np.__version__, argv=sys.argv,
               config_sha256=DL.sha(sys.argv[2]), agg_dir=AGG_DIR, results=RES, verdict=line, runtime_s=round(time.time() - T0, 1)), open(OUTP, "w"), indent=1, default=str)
print(line, flush=True)
sys.exit(0 if n_pass == n else 1)
