#!/usr/bin/env python3
"""bt_tables_selftest.py — battery for the TABLE DEVICE bt_tables.py on synthetic fixtures + one real reproduction. Every check runs its
baseline first (must be green) and then each mutation (must be red); the verdict line is printed last and the exit code is 0 only if every
baseline is green and every mutation red.

  T1  hand-computed fixtures: CAGR, daily Sharpe (ddof 1, √365), 4h maxDD, 5-minute maxDD (a dip inside a window that 4h sampling misses),
      worst 30 days, CVaR 5 %, the g identity. Mutations: arithmetic annualisation, ddof 0, √252, maxDD without the starting point,
      5-minute maxDD read at window boundaries only.
  T2  REAL reproduction of stream R's published NAV arithmetic (233efec27, R_TABLES.json v2 via the judge-free nav_stats of r_tables.py) from
      its own ledgers SIM_S2_A0pred_s{42,2027}_CMB_rule.npz: W_ALPHA and every year, nav_return / annualised / daily Sharpe / maxDD within
      1e-12 relative. Mutations as T1 (each must move at least one published cell beyond the tolerance).
  T3  moving-block bootstrap: shape, blocks are runs of consecutive days, rng [20260919, 99] reproducible and different from another seed,
      block 1 = iid day resampling. Mutation: circular wrap / wrong block length detected.
  T4  paired estimator: identical series ⇒ Δ = 0, CI [0, 0], label (C); a series with +1 bp/day added ⇒ ΔCAGR > 0 with p_up < 0.05 ⇒ (A);
      the reverse ⇒ (B). Mutation: independent draws for the two arms ⇒ identical series get a non-zero CI (red).
  T5  §3.2 cells: 21 masks partition every labelled anchor of each variable exactly once; Bonferroni interval ⊇ CI95; a single-day cell is
      describe-only; AMENDMENT 1 item 3: cell index k = 0..20 in PROGRAM §4 order, the cell's CI equals the draws of rng [20260919, 1000 + k].
      Mutations: an off-by-one label row mapping; the old shared seed [20260919, 99] (both detected).
  T6  §3.1 periods: partial-recipe years labelled; 2024 split at the full-recipe start; every anchor in exactly one period.
  T7  §3.6 telescoping: Σ step deltas = total delta (interactions in the later step). Mutation: a step computed against the ORIGINAL
      baseline instead of the previous step breaks it.
  T8  mean path: per-window mean over path series equals np.mean of the stacked arrays; the 5-minute mean path compounds the mean returns.
usage: python3 bt_tables_selftest.py <replay_r receipts dir (R_TABLES.json + runs/SIM_*_CMB_rule.npz)>
"""
import json, math, os, sys, time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt_tables as BT

RD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "replay_r_2026-09-19", "receipts")
RES = []


def ok(name, cond, detail=None):
    RES.append((name, bool(cond), detail)); print(("  PASS " if cond else "  FAIL ") + name + ("" if detail is None else "  " + json.dumps(detail, default=str)[:200]), flush=True)


def mut(name, red, detail=None):
    """a mutation check: PASS means the mutation went RED (was detected)"""
    ok("[mutation red] " + name, red, detail)


# ---------------- T1 fixtures ----------------
print("T1 fixtures")
A = np.arange(0, 3 * 86400, 14400, dtype=np.int64) + 1_700_006_400 - (1_700_006_400 % 86400)   # 3 UTC days × 6 windows
r = np.zeros(len(A)); r[0] = 0.10; r[6] = -0.05; r[12] = 0.02                                   # day returns 0.10, −0.05, 0.02
ud, rd = BT.daily(A, r)
ok("T1.daily_returns", np.allclose(rd, [0.10, -0.05, 0.02], atol=1e-15), rd.tolist())
nav = 1.10 * 0.95 * 1.02
ok("T1.cagr", abs(BT.cagr(rd) - (nav ** (365 / 3) - 1)) < 1e-12, BT.cagr(rd))
sd = np.std([0.10, -0.05, 0.02], ddof=1)
ok("T1.sharpe_ddof1_sqrt365", abs(BT.sharpe(rd) - np.mean([0.10, -0.05, 0.02]) / sd * math.sqrt(365)) < 1e-12)
ok("T1.maxdd_4h", abs(BT.maxdd_4h(r) - (-0.05)) < 1e-15, BT.maxdd_4h(r))
mut("T1.arithmetic_annualisation", abs(np.mean(rd) * 365 - BT.cagr(rd)) > 1e-6)
mut("T1.sharpe_ddof0", abs(np.mean(rd) / np.std(rd) * math.sqrt(365) - BT.sharpe(rd)) > 1e-6)
mut("T1.sharpe_sqrt252", abs(np.mean(rd) / sd * math.sqrt(252) - BT.sharpe(rd)) > 1e-6)
r2 = np.array([-0.10, 0.05]); mut("T1.maxdd_without_start_point", abs(BT.maxdd_nav(np.cumprod(1 + r2)) - BT.maxdd_4h(r2)) > 1e-6, [BT.maxdd_nav(np.cumprod(1 + r2)), BT.maxdd_4h(r2)])
# 5-minute path with a dip inside window 0 that the 4h sampling misses
t5 = A[0] + 300 * np.arange(len(A) * 48 + 1, dtype=np.int64)
nav5 = np.ones(len(t5)); lvl = np.concatenate([[1.0], np.cumprod(1 + r)])
for w in range(len(A)):
    nav5[w * 48:(w + 1) * 48 + 1] = np.linspace(lvl[w], lvl[w + 1], 49)
nav5[10] = 0.80                                                                            # −20 % dip at 00:50 of day 1, recovered by 04:00
s = dict(A=A, r=r, g=1e4 * r / 2, pnl=1e4 * r / 2, car=np.zeros(len(A)), cst=np.zeros(len(A)), unk=np.zeros(len(A)), tau=np.zeros(len(A)),
         dstop=np.zeros(len(A)), nstop=np.zeros(len(A)), halt=np.zeros(len(A)), hold=np.zeros(len(A)), dust=np.zeros(len(A)), unk_notional=np.zeros(len(A)), t5=t5, nav5=nav5)
m_all = np.ones(len(A), bool)
c = BT.cell_metrics(s, m_all)
exp5 = 0.80 / (1.0 + 0.10 * 9 / 48) - 1.0                                                # peak = the 00:45 point of the linear ramp
ok("T1.maxdd_5m_sees_intra_window_dip", abs(c["maxdd_5m"] - exp5) < 1e-12 and abs(c["maxdd_4h"] - (-0.05)) < 1e-15, [c["maxdd_5m"], exp5, c["maxdd_4h"]])
mut("T1.maxdd_5m_read_at_window_boundaries_only", abs(BT.maxdd_nav(nav5[::48]) - c["maxdd_5m"]) > 1e-6)
ok("T1.g_identity", BT.g_identity_err(s) == 0.0)
s_bad = dict(s, cst=np.full(len(A), 0.1)); mut("T1.g_identity_detects_a_missing_component", BT.g_identity_err(s_bad) > 1e-9)
rd40 = np.concatenate([np.full(10, 0.01), np.full(30, -0.01), [0.02]])
ok("T1.worst_30d", abs(BT.worst_30d(rd40) - (0.99 ** 30 - 1)) < 1e-12, BT.worst_30d(rd40))
ok("T1.cvar5", abs(BT.cvar5(np.arange(1, 101) / 100.0) - np.mean([0.01, 0.02, 0.03, 0.04, 0.05])) < 1e-15)
mut("T1.cvar5_quantile_not_mean", abs(np.quantile(np.arange(1, 101) / 100.0, 0.05) - BT.cvar5(np.arange(1, 101) / 100.0)) > 1e-6)

# ---------------- T2 real reproduction of stream R's published NAV arithmetic ----------------
print("T2 stream-R reproduction")
RT = json.load(open(os.path.join(RD, "R_TABLES.json")))
worst = 0.0; n_cells = 0; mut_hits = {"annual_arith": 0, "ddof0": 0, "sqrt252": 0, "maxdd_daily": 0}
for seed in ("s42", "s2027"):
    Z = np.load(os.path.join(RD, "runs", f"SIM_S2_A0pred_{seed}_CMB_rule.npz"))
    sv = BT.series_from_v2(Z); pub = RT["tables"][f"S2_A0pred_{seed}|CMB|rule"]
    yrs = np.array([time.gmtime(int(t)).tm_year for t in sv["A"]])
    cells = [("W_ALPHA", np.ones(len(sv["A"]), bool), pub["W_ALPHA"]["nav"])] + [(str(y), yrs == y, pub["year"][str(y)]["nav"]) for y in range(2022, 2027)]
    for nm, m, p in cells:
        cm = BT.cell_metrics(sv, m)
        for mine, theirs in ((cm["nav_return"], p["nav_return"]), (cm["cagr"], p["nav_return_annualised"]), (cm["sharpe_daily"], p["nav_sharpe_daily"]), (cm["maxdd_4h"], p["nav_maxdd"])):
            if theirs is None: continue
            worst = max(worst, abs(mine - theirs) / max(1.0, abs(theirs))); n_cells += 1
        ud_, rd_ = BT.daily(sv["A"][m], sv["r"][m])
        if p["nav_return_annualised"] is not None and abs(np.mean(rd_) * 365 - p["nav_return_annualised"]) > 1e-12: mut_hits["annual_arith"] += 1
        if p["nav_sharpe_daily"] is not None and abs(rd_.mean() / rd_.std() * math.sqrt(365) - p["nav_sharpe_daily"]) > 1e-12: mut_hits["ddof0"] += 1
        if p["nav_sharpe_daily"] is not None and abs(rd_.mean() / rd_.std(ddof=1) * math.sqrt(252) - p["nav_sharpe_daily"]) > 1e-12: mut_hits["sqrt252"] += 1
        if abs(BT.maxdd_nav(np.concatenate([[1.0], np.cumprod(1 + rd_)])) - p["nav_maxdd"]) > 1e-12: mut_hits["maxdd_daily"] += 1
ok("T2.published_nav_return_cagr_sharpe_maxdd_reproduced", worst <= 1e-12 and n_cells == 48, {"cells": n_cells, "max_rel_err": worst})
for k, v in mut_hits.items(): mut(f"T2.{k}_moves_published_cells", v > 0, {"cells_moved": v})

# ---------------- T3 bootstrap ----------------
print("T3 moving-block bootstrap")
I = BT.mbb_indices(23, 5, B=200)
ok("T3.shape", I.shape == (200, 23))
runs_ok = all(np.all(np.diff(row[i:i + 5]) == 1) for row in I for i in range(0, 20, 5))
ok("T3.blocks_are_consecutive_days", runs_ok)
ok("T3.within_range_noncircular", int(I.min()) >= 0 and int(I.max()) <= 22)
ok("T3.reproducible", np.array_equal(I, BT.mbb_indices(23, 5, B=200)))
mut("T3.other_seed_differs", not np.array_equal(I, BT.mbb_indices(23, 5, B=200, seed=(20260919, 98))))
Ic = (np.random.default_rng([20260919, 99]).integers(0, 23, size=(200, 5))[:, :, None] + np.arange(5)).reshape(200, 25)[:, :23] % 23
mut("T3.circular_wrap_would_differ", not np.array_equal(Ic, I))
I1 = BT.mbb_indices(23, 1, B=200); ok("T3.block1_is_day_iid_shape", I1.shape == (200, 23) and int(I1.max()) <= 22)

# ---------------- T4 paired estimator ----------------
print("T4 paired estimator")
rng = np.random.default_rng(7); nd = 400
A4 = (1_700_006_400 - 1_700_006_400 % 86400) + 14400 * np.arange(nd * 6, dtype=np.int64)
r4 = rng.normal(0.0002, 0.004, len(A4))
def mk(r_):
    return dict(A=A4, r=r_, g=1e4 * r_ / 2)
P0 = BT.paired(mk(r4), mk(r4.copy()), B=2000)
ok("T4.identical_series_zero", all(abs(P0[k]["estimate"]) == 0 and P0[k]["ci95"] == [0.0, 0.0] for k in ("d_sharpe", "d_cagr", "d_g")) and P0["d_cagr"]["label"].startswith("(C)"),
   {k: P0[k]["ci95"] for k in ("d_sharpe", "d_cagr", "d_g")})
up = r4 + 1e-4 / 6
P1 = BT.paired(mk(up), mk(r4), B=2000)
ok("T4.better_series_label_A", P1["d_cagr"]["estimate"] > 0 and P1["d_cagr"]["p_up"] < 0.05 and P1["d_cagr"]["label"].startswith("(A)") and P1["d_g"]["label"].startswith("(A)"),
   {"d_cagr": P1["d_cagr"]["estimate"], "p_up": P1["d_cagr"]["p_up"]})
P2 = BT.paired(mk(r4), mk(up), B=2000)
ok("T4.worse_series_label_B", P2["d_cagr"]["label"].startswith("(B)"), P2["d_cagr"]["label"])
ok("T4.labels_marked_descriptive_main_reading_sharpe", P2["main_reading"] == "d_sharpe" and "no switch decision" in P2["labels"])
ud4, ra = BT.daily(A4, r4); Ia = BT.mbb_indices(len(ud4), 5, 2000); Ib = BT.mbb_indices(len(ud4), 5, 2000, seed=(1, 2))
d_ind = np.array([BT.cagr(ra[i]) for i in Ia[:300]]) - np.array([BT.cagr(ra[j]) for j in Ib[:300]])
mut("T4.independent_draws_give_nonzero_CI_on_identical_series", float(np.percentile(d_ind, 97.5) - np.percentile(d_ind, 2.5)) > 1e-3)

# ---------------- T5 regime cells ----------------
print("T5 regime cells")
lab_ts = A4.copy(); LAB = rng.integers(-1, 3, size=(len(A4), 7)).astype(np.int8)
VN = list(BT.PROGRAM_VARS)
cells = BT.regime_cells(A4, lab_ts, LAB, VN)
part = all(int(sum(m.sum() for m in cells[VN[j]].values())) == int((LAB[:, j] >= 0).sum()) and
           int(sum(m.astype(int) for m in cells[VN[j]].values()).max()) <= 1 for j in range(7))
ok("T5.21_cells_partition_labelled_anchors", part and sum(len(v) for v in cells.values()) == 21)
s5 = dict(A=A4, r=r4, g=1e4 * r4 / 2, pnl=1e4 * r4 / 2, car=np.zeros(len(A4)), cst=np.zeros(len(A4)), unk=np.zeros(len(A4)), tau=np.zeros(len(A4)),
          dstop=np.zeros(len(A4)), nstop=np.zeros(len(A4)), halt=np.zeros(len(A4)), hold=np.zeros(len(A4)), dust=np.zeros(len(A4)), unk_notional=np.zeros(len(A4)), t5=None, nav5=None)
RT5 = BT.regime_table(s5, {"RG-TREND": cells["RG-TREND"], "RG-DISP": cells["RG-DISP"]}, B=1000)
c0 = RT5["RG-TREND"]["low"]["g_ci"]["block_5d"]
ok("T5.bonferroni_contains_ci95", c0["ci_bonf"][0] <= c0["ci95"][0] and c0["ci_bonf"][1] >= c0["ci95"][1], c0)
ok("T5.cell_index_and_rng_follow_AMENDMENT1_item3", [BT.regime_cell_index(v, l) for v in VN for l in BT.LEVELS] == list(range(21))
   and RT5["RG-DISP"]["high"]["cell_index"] == 8 and RT5["RG-DISP"]["high"]["rng"] == [20260919, 1008] and RT5["RG-TREND"]["low"]["rng"] == [20260919, 1000])
days5 = np.unique((A4 // 86400) * 86400)
ref, _ = BT.mean_ci(A4, s5["g"], cells["RG-DISP"]["high"], days5, block=5, idx=BT.mbb_indices(len(days5), 5, 1000, (20260919, 1008)))
ok("T5.cell_CI_equals_its_own_seed_draws", ref["ci95"] == RT5["RG-DISP"]["high"]["g_ci"]["block_5d"]["ci95"], ref["ci95"])
shared, _ = BT.mean_ci(A4, s5["g"], cells["RG-DISP"]["high"], days5, block=5, idx=BT.mbb_indices(len(days5), 5, 1000, (20260919, 99)))
mut("T5.shared_seed_99_would_give_another_CI", shared["ci95"] != RT5["RG-DISP"]["high"]["g_ci"]["block_5d"]["ci95"])
one = np.zeros(len(A4), bool); one[:3] = True
RT6 = BT.regime_table(s5, {"RG-VOL": {"low": one}}, B=200)
ok("T5.single_day_cell_describe_only", RT6["RG-VOL"]["low"].get("ci") == "single-day cell: describe only")
cells_shift = BT.regime_cells(A4, lab_ts, np.roll(LAB, 1, axis=0), VN)
mut("T5.off_by_one_label_row_detected", not np.array_equal(cells_shift["RG-TREND"]["low"], cells["RG-TREND"]["low"]))

# ---------------- T6 periods ----------------
print("T6 periods")
import calendar
A6 = np.arange(calendar.timegm((2022, 6, 30, 0, 0, 0)), calendar.timegm((2026, 9, 18, 20, 0, 0)) + 1, 14400, dtype=np.int64)
frs = calendar.timegm((2024, 6, 29, 0, 0, 0))
YC = BT.year_cells(A6, frs)
cover = sum(v["mask"].astype(int) for v in YC.values())
ok("T6.every_anchor_in_exactly_one_period", int(cover.min()) == 1 and int(cover.max()) == 1, list(YC))
ok("T6.2024_split_and_partial_labelled", any(k.startswith("2024 (PARTIAL") for k in YC) and "2024 (full recipe)" in YC and all(v["partial_recipe"] for k, v in YC.items() if k.startswith(("2022H2", "2023"))))
ok("T6.2026_07_describe_only", YC["2026-07-01→end"]["describe_only"] is True)
YC0 = BT.year_cells(A6, None); mut("T6.no_full_recipe_start_means_no_split", "2024" in YC0 and not any("PARTIAL" in k for k in YC0))

# ---------------- T7 telescoping ----------------
print("T7 reconciliation telescoping")
def mkfull(r_):
    return dict(A=A4, r=r_, g=1e4 * r_ / 2, pnl=1e4 * r_ / 2, car=np.zeros(len(A4)), cst=np.zeros(len(A4)), unk=np.zeros(len(A4)), tau=np.zeros(len(A4)),
                dstop=np.zeros(len(A4)), nstop=np.zeros(len(A4)), halt=np.zeros(len(A4)), hold=np.zeros(len(A4)), dust=np.zeros(len(A4)), unk_notional=np.zeros(len(A4)), t5=None, nav5=None)
s0 = mkfull(r4); s1 = mkfull(r4 + 2e-5); s2 = mkfull(r4 * 1.1 + 1e-5)
st1 = BT.recon_step("1", s0, s1, B=300); st2 = BT.recon_step("2", s1, s2, B=300)
tel = BT.telescoping_ok([st1, st2], st1["before"], st2["after"])
ok("T7.sum_of_steps_equals_total", max(tel.values()) < 1e-12, tel)
st2_bad = BT.recon_step("2 vs original", s0, s2, B=300)
tel_bad = BT.telescoping_ok([st1, st2_bad], st1["before"], st2_bad["after"])
mut("T7.step_against_original_baseline_breaks_telescoping", max(tel_bad.values()) > 1e-9, tel_bad)

# ---------------- T8 mean path ----------------
print("T8 mean path")
paths = []
for k in range(4):
    rr = r4[:12] + 1e-4 * k
    t8 = A4[0] + 300 * np.arange(12 * 48 + 1, dtype=np.int64); n8 = np.concatenate([[1.0], np.cumprod(np.repeat(1 + rr, 48) ** (1 / 48))])
    paths.append(dict(A=A4[:12], r=rr, g=1e4 * rr / 2, pnl=1e4 * rr / 2, car=np.zeros(12), cst=np.zeros(12), unk=np.zeros(12), tau=np.zeros(12), dstop=np.zeros(12),
                      nstop=np.zeros(12), halt=np.zeros(12), hold=np.zeros(12), dust=np.zeros(12), unk_notional=np.zeros(12), t5=t8, nav5=n8))
ms = BT.series_mean(paths)
ok("T8.window_mean_equals_stacked_mean", np.array_equal(ms["r"], np.stack([p["r"] for p in paths]).mean(0)))
r5m = np.stack([p["nav5"][1:] / p["nav5"][:-1] - 1 for p in paths]).mean(0)
ok("T8.nav5_mean_path_compounds_mean_5m_returns", np.allclose(ms["nav5"], np.concatenate([[1.0], np.cumprod(1 + r5m)]), rtol=0, atol=1e-15))
mut("T8.mean_over_a_dropped_seed_differs", not np.array_equal(BT.series_mean(paths[:3])["r"], ms["r"]))

# ── T9 §3.5 pairing table plumbing (main_pair): common window, arm order, per-fill-path pairing, label source ──
def mkpath(rr, A):
    n = len(rr); t = A[0] + 300 * np.arange(n * 48 + 1, dtype=np.int64)
    return dict(A=A, r=rr, g=1e4 * rr / 2, pnl=1e4 * rr / 2, car=np.zeros(n), cst=np.zeros(n), unk=np.zeros(n), tau=np.zeros(n), dstop=np.zeros(n),
                nstop=np.zeros(n), halt=np.zeros(n), hold=np.zeros(n), dust=np.zeros(n), unk_notional=np.zeros(n),
                t5=t, nav5=np.concatenate([[1.0], np.cumprod(np.repeat(1 + rr, 48) ** (1 / 48))]))


nA = 400; A9 = A4[0] + 14400 * np.arange(nA, dtype=np.int64)
rng9 = np.random.default_rng(7)
base = rng9.normal(0.0, 2e-3, size=(8, nA))
PA = [mkpath(base[i] + 3e-4, A9) for i in range(8)]          # arm A (in-service): +3 bp per window on every fill path
PB = [mkpath(base[i], A9) for i in range(8)]                 # arm B (retrain): the same fill paths without it
mA = BT.series_mean(PA); mB = BT.series_mean(PB)
c1 = BT.pair_cell(mA, mB, PA, PB, np.ones(nA, bool))
ok("T9.pair_cell_delta_is_A_minus_B_and_positive", c1["delta_point"]["g"] > 0 and abs(c1["delta_point"]["g"] - (1e4 * 3e-4 / 2)) < 1e-9
   and c1["paired_bootstrap_5d"]["d_g"]["estimate"] > 0, {"d_g": c1["delta_point"]["g"], "boot": c1["paired_bootstrap_5d"]["d_g"]["estimate"]})
ok("T9.label_comes_from_the_estimator_itself", c1["label_on_the_main_reading"] == c1["paired_bootstrap_5d"]["d_sharpe"]["label"]
   and "no switch decision" in c1["labels_are"], c1["label_on_the_main_reading"])
c2 = BT.pair_cell(mB, mA, PB, PA, np.ones(nA, bool))
mut("T9.swapping_the_arms_flips_every_sign", abs(c2["delta_point"]["g"] + c1["delta_point"]["g"]) < 1e-12
    and c2["per_fill_path_delta"]["g"]["median"] < 0 < c1["per_fill_path_delta"]["g"]["median"], {"A-B": c1["delta_point"]["g"], "B-A": c2["delta_point"]["g"]})
ok("T9.per_fill_path_pairing_is_by_seed", abs(c1["per_fill_path_delta"]["g"]["p05"] - c1["per_fill_path_delta"]["g"]["p95"]) < 1e-9
   and c1["per_fill_path_delta"]["g"]["n"] == len(PA), c1["per_fill_path_delta"]["g"])
mut("T9.unpaired_arms_(shuffled_seed_order)_widen_the_per_path_spread",
    abs(BT.pair_cell(mA, mB, PA, PB[::-1], np.ones(nA, bool))["per_fill_path_delta"]["g"]["p95"]
        - BT.pair_cell(mA, mB, PA, PB[::-1], np.ones(nA, bool))["per_fill_path_delta"]["g"]["p05"]) > 1e-6)
sA, sB, common = BT.restrict_to_common(mA, BT.restrict(mB, int(A9[10]), int(A9[-1])))
ok("T9.restrict_to_common_reports_what_it_dropped", common["n_common"] == nA - 10 and common["dropped_a"] == 10 and common["dropped_b"] == 0
   and np.array_equal(sA["A"], sB["A"]), common)
mDIS = BT.series_mean([mkpath(base[i], A9 + 14400 * nA) for i in range(8)])      # a disjoint axis, no shared anchor at all
try:
    BT.restrict_to_common(mA, mDIS); no_err = True
except AssertionError:
    no_err = False
mut("T9.arms_that_share_no_anchor_are_refused", not no_err)

n_pass = sum(1 for _, c_, _ in RES if c_); n = len(RES)
line = ("BT_TABLES_SELFTEST VERDICT: ALL PASS %d/%d checks (baselines green, every mutation red)" % (n_pass, n)) if n_pass == n else \
       ("BT_TABLES_SELFTEST VERDICT: FAIL %d/%d checks; failed: %s" % (n_pass, n, [nm for nm, c_, _ in RES if not c_]))
print(line)
sys.exit(0 if n_pass == n else 1)
