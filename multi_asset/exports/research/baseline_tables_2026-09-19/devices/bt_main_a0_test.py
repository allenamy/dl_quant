#!/usr/bin/env python3
"""bt_main_a0_test.py — synthetic-fixture test of bt_tables.py main_a0 (the A0 part of the main tables) before it touches any real number.
Fixtures (written to a temp dir): 5 A0 runs × 32 path files (base, lit, three cost cells = base − a known constant per window), G0-style labels,
P2-CMB 'step-② after' paths on a shorter reconciliation window, and a steps-①② receipt consistent with them. Checks (baseline green, mutations red):
  A1 periods: the year periods partition the window; years before the full-recipe start are PARTIAL_RECIPE; 2024 is split at the start;
     FULL_RECIPE and PARTIAL_RECIPE windows partition the window and are never merged into one row
  A2 regime: 21 cells per label variant, computed on FULL_RECIPE anchors only; cell index / rng as AMENDMENT 1 item 3
  A3 cost cells: a cell that removes exactly 1e-5 of return per window has Δg = −0.05 bps in every period and ΔCAGR < 0
  A4 step ③: object B restricted to the reconciliation window shares its axis with P2; the restricted 5-minute path compounds to the restricted
     window returns; telescoping ① + ② + ③ = total; step-② 'after' == step-③ 'before'
  A5 per-period path distributions over 32 paths
  mutations: full-recipe start moved by one anchor changes the FULL_RECIPE count; a restriction off the 5-minute grid is refused; a wrong P2 dir
     for step ③ breaks 'step-② after == step-③ before'; shuffled label variables are refused
usage: python3 bt_main_a0_test.py <tmp_dir>
"""
import calendar, json, os, sys, tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt_tables as BT

TMP = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp()
RES = []


def ok(name, cond, detail=None):
    RES.append((name, bool(cond))); print(("  PASS " if cond else "  FAIL ") + name + ("" if detail is None else "  " + json.dumps(detail, default=str)[:220]), flush=True)


def mut(name, red, detail=None): ok("[mutation red] " + name, red, detail)


def ts(y, m, d, h=0): return calendar.timegm((y, m, d, h, 0, 0))


A = np.arange(ts(2023, 12, 1), ts(2024, 2, 10, 20) + 1, 14400, dtype=np.int64); n = len(A)
FRS = ts(2024, 1, 10); WA0, WA1 = ts(2023, 12, 1), ts(2024, 2, 5, 20)
rng = np.random.default_rng(3)


def write_path(d, s, r, axis, fee_shift=0.0):
    """one synthetic path file: window returns r − fee_shift, the fee field carries the shift so the g identity holds; 5-minute path = 48 equal
    sub-steps per window"""
    r = r - fee_shift
    nav = 1e5 * np.concatenate([[1.0], np.cumprod(1 + r)])
    nav5 = 1e5 * np.concatenate([[1.0], np.cumprod(np.repeat((1 + r) ** (1 / 48), 48))])
    fee = 1.0 + nav[:-1] * fee_shift * 2.0; funding = -np.ones(len(r))
    z = dict(A=axis, nav0=nav[:-1], nav1=nav[1:], navm0=nav[:-1], navm1=nav[1:], price_trade=(nav[1:] - nav[:-1]) - funding + fee, funding=funding, fee=fee,
             unk_price=np.zeros(len(r)), unk_funding=np.zeros(len(r)), unk_excluded=np.zeros(len(r)), turnover=np.full(len(r), 1e4), n_flatten_events=np.zeros(len(r)),
             n_stop_events=np.zeros(len(r)), status=np.zeros(len(r), np.int8), end_dust_usdt=np.zeros(len(r)), unk_notional=np.zeros(len(r)), gross0=2 * nav[:-1],
             nav5_t0=np.array(axis[0]), nav5_main=nav5, nav5_sim=nav5)
    os.makedirs(d, exist_ok=True); np.savez(f"{d}/PATH_x_seed_{s:02d}.npz", **z)


RUNS = [("OBJB_A0|scaled|rule|raw|UAFE", "scaled", None, 0.0), ("OBJB_A0|lit|rule|raw|UAFE", "lit", None, 0.0),
        ("OBJB_A0|scaled|rule|raw|UAFE|fee_x1.25", "scaled", "fee_x1.25", 1e-5), ("OBJB_A0|scaled|rule|raw|UAFE|slip_x1.5", "scaled", "slip_x1.5", 2e-5),
        ("OBJB_A0|scaled|rule|raw|UAFE|fill_x0.9", "scaled", "fill_x0.9", 3e-5)]
base_r = [rng.normal(2e-4, 4e-3, n) for _ in range(32)]; lit_r = [rng.normal(1e-4, 4e-3, n) for _ in range(32)]
root = f"{TMP}/runs"
for tag, book, cc, shift in RUNS:
    for s in range(32): write_path(f"{root}/{tag.replace('|', '_')}", s, lit_r[s] if book == "lit" else base_r[s], A, shift)
WA = A[(A >= WA0) & (A <= WA1)]; p2d = f"{TMP}/p2raw"
p2_r = [rng.normal(1.5e-4, 4e-3, len(WA)) for _ in range(32)]
for s in range(32): write_path(p2d, s, p2_r[s], WA)
LAB = rng.integers(-1, 3, size=(n, 7)).astype(np.int8)
np.savez(f"{TMP}/labels.npz", ts=A, vars=np.array(BT.PROGRAM_VARS), LAB_EXCL=LAB, LAB_INCL=LAB)
cfg = {"status": "FROZEN (fixture)", "object": "fixture", "paths_R": 32, "window": {"first_anchor": "2023-12-01T00:00:00Z", "last_anchor": "2024-02-10T20:00:00Z",
       "full_recipe_start": "2024-01-10T00:00:00Z", "coverage": "fixture"}, "runs": [{"tag": t, "book": b, **({"cost_cell": c} if c else {})} for t, b, c, _ in RUNS]}
json.dump(cfg, open(f"{TMP}/cfg.json", "w"))
p2_paths, _ = BT.load_run_dir(p2d); p2_mean = BT.series_mean(p2_paths); m2 = BT.cell_metrics(p2_mean, np.ones(len(WA), bool))
v2 = {k: m2[k] - 0.01 for k in ("cagr", "sharpe_daily", "maxdd_4h", "g")}; v2.update(first_anchor=int(WA[0]), last_anchor=int(WA[-1]), maxdd_5m=None, nav_return=0.0)
a1 = {k: m2[k] - 0.004 for k in ("cagr", "sharpe_daily", "maxdd_4h", "g")}
rec12 = {"steps": {"s42": {"v2_full": v2, "step1": {"before": v2, "after": a1, "delta_point": {k: a1[k] - v2[k] for k in a1}},
                            "step2": {"after": {k: m2[k] for k in ("cagr", "sharpe_daily", "maxdd_4h", "g")}, "delta_point": {k: m2[k] - a1[k] for k in a1}}}}}
json.dump(rec12, open(f"{TMP}/rec12.json", "w"))
BT.main_a0([f"{TMP}/cfg.json", root, f"{TMP}/labels.npz", p2d, f"{TMP}/rec12.json", f"{TMP}/out.json"])
O = json.load(open(f"{TMP}/out.json")); T = O["tables"]

print("A1 periods")
P = BT.periods_a0(A, FRS, "2024-02-10")
years = [k for k in P if not k.endswith("window") and "window" not in k]
cov = sum(P[k]["mask"].astype(int) for k in years)
ok("A1.year_periods_partition_the_window", int(cov.min()) == 1 and int(cov.max()) == 1, years)
ok("A1.pre_start_years_PARTIAL_and_2024_split", "2023 (PARTIAL_RECIPE)" in P and "2024 (PARTIAL_RECIPE, before full-recipe start)" in P and "2024 (full recipe)" in P)
fw = P["FULL_RECIPE window"]["mask"]; pw = P["PARTIAL_RECIPE window (not the production strategy)"]["mask"]
ok("A1.full_and_partial_windows_partition_never_merged", bool(np.all(fw ^ pw)) and int(fw.sum()) == int((A >= FRS).sum()) and not any("WHOLE" in k for k in T["per_period scaled (main)"]))
print("A2 regime")
RX = T["regime_21_cells EXCL (FULL_RECIPE window, main reading)"]
ok("A2.21_cells", sum(len(v) for v in RX.values()) == 21)
nfull = int((A >= FRS).sum()); labf = LAB[A >= FRS]
ok("A2.cells_on_FULL_RECIPE_anchors_only", all(sum(RX[v][l]["n_anchors"] for l in BT.LEVELS) == int((labf[:, j] >= 0).sum()) for j, v in enumerate(BT.PROGRAM_VARS)), {"full_anchors": nfull})
ok("A2.cell_index_and_rng_amendment1", RX["RG-ALT"]["high"]["cell_index"] == 20 and RX["RG-ALT"]["high"]["rng"] == [20260919, 1020] and RX["RG-TREND"]["low"]["rng"] == [20260919, 1000])
print("A3 cost cells")
CC = T["cost_sensitivity (main reading, Δ = cell − base, same fill seeds)"]
dg = [v["d_g"] for v in CC["fee_x1.25"].values()]
ok("A3.fee_cell_dg_is_minus_0.05_in_every_period", all(abs(x + 0.05) < 1e-9 for x in dg) and all(v["d_cagr"] < 0 for v in CC["fee_x1.25"].values()), dg[:3])
ok("A3.larger_shift_larger_cost", all(CC["fill_x0.9"][k]["d_g"] < CC["slip_x1.5"][k]["d_g"] < CC["fee_x1.25"][k]["d_g"] for k in CC["fee_x1.25"]))
print("A4 step ③")
RC = next(v for k, v in T.items() if k.startswith("reconciliation"))
st = RC["steps_3"]["③ P2-CMB → certified object B A0 (B-scaled, main)"]
ok("A4.telescoping_1_2_3", max(RC["chain_1_2_3"]["telescoping_abs_err"].values()) < 1e-12, RC["chain_1_2_3"]["telescoping_abs_err"])
ok("A4.step2_after_equals_step3_before", max(RC["chain_1_2_3"]["step2_after_equals_step3_before"].values()) < 1e-12)
base_paths, _ = BT.load_run_dir(f"{root}/OBJB_A0_scaled_rule_raw_UAFE"); rs = BT.restrict(BT.series_mean(base_paths), WA0, WA1)
r1 = BT.restrict(base_paths[0], WA0, WA1)          # per path (on the MEAN path, mean-of-5m compounding and mean-of-window compounding differ by design)
ok("A4.restricted_axis_and_5m_path_consistent_per_path", np.array_equal(r1["A"], WA) and np.array_equal(rs["A"], WA) and abs(r1["nav5"][-1] / np.prod(1 + r1["r"]) - 1) < 1e-9,
   float(r1["nav5"][-1] / np.prod(1 + r1["r"]) - 1))
ok("A4.step3_after_is_object_B_on_the_reconciliation_window", abs(st["after"]["cagr"] - BT.cell_metrics(rs, np.ones(len(WA), bool))["cagr"]) < 1e-15)
print("A5 distributions")
pp = T["per_period scaled (main)"]["FULL_RECIPE window"]["path_distribution"]
ok("A5.path_distribution_32_paths_both_samplings", pp["maxdd_5m"]["n_paths"] == 32 and pp["maxdd_4h"]["median"] is not None and pp["maxdd_5m"]["median"] <= pp["maxdd_4h"]["median"] + 1e-12)
print("mutations")
P2_ = BT.periods_a0(A, FRS + 14400, "2024-02-10")
mut("M1.start_moved_one_anchor_changes_FULL_RECIPE", int(P2_["FULL_RECIPE window"]["mask"].sum()) == nfull - 1)
try:
    BT.restrict(BT.series_mean(base_paths), WA0 + 150, WA1); red = False
except AssertionError:
    red = True
mut("M2.restriction_off_the_5m_grid_refused", red)
for s_ in range(32): write_path(f"{TMP}/p2wrong", s_, p2_r[s_] + 1e-4, WA)
BT.main_a0([f"{TMP}/cfg.json", root, f"{TMP}/labels.npz", f"{TMP}/p2wrong", f"{TMP}/rec12.json", f"{TMP}/out_m3.json"])
O3 = json.load(open(f"{TMP}/out_m3.json")); RC3 = next(v for k, v in O3["tables"].items() if k.startswith("reconciliation"))
mut("M3.wrong_P2_dir_breaks_step2_after_equals_step3_before", max(RC3["chain_1_2_3"]["step2_after_equals_step3_before"].values()) > 1e-6)
np.savez(f"{TMP}/labels_bad.npz", ts=A, vars=np.array(list(BT.PROGRAM_VARS)[::-1]), LAB_EXCL=LAB, LAB_INCL=LAB)
try:
    BT.main_a0([f"{TMP}/cfg.json", root, f"{TMP}/labels_bad.npz", p2d, f"{TMP}/rec12.json", f"{TMP}/out_m4.json"]); red = False
except AssertionError:
    red = True
mut("M4.shuffled_label_variables_refused", red)
n_pass = sum(1 for _, c in RES if c); line = ("BT_MAIN_A0_TEST VERDICT: ALL PASS %d/%d checks (baselines green, every mutation red)" % (n_pass, len(RES))) if n_pass == len(RES) else \
    ("BT_MAIN_A0_TEST VERDICT: FAIL %d/%d checks; failed: %s" % (n_pass, len(RES), [k for k, c in RES if not c]))
print(line); sys.exit(0 if n_pass == len(RES) else 1)
