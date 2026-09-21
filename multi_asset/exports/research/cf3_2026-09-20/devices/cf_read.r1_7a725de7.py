#!/usr/bin/env python3
"""cf_read.py — CF3 step 4: read the judge's output for every arm and produce the pre-registered tables.

Statistics come from the CERTIFIED reading device bt_tables.py (imported, not re-implemented):
series_from_path / series_mean / cell_metrics / path_distribution / paired / mean_ci.

GATE J (runs first; no number is emitted unless it passes)
  J1  the CF_BASE run reproduces the certified OBJB_A0|scaled run BITWISE (every AGG array and every
      one of the 32 PATH files, by sha256). The BASE arm's target book is bitwise the archived one, so
      anything else would mean this task's judge is not the baseline tables' judge.
  J2  g = price - funding - fee - unknown per anchor, every arm, |err| <= 1e-9 bps.
  J3  every arm shares the anchor axis and has exactly 32 path files.

POPULATIONS (PREREG 7.3, E-0920-C)
  Every table declares a CLOSED population with n. The three buckets COMBO / KING_FILE / HOLD are cut by
  the BASE arm's kind and are mutually exclusive and exhaustive (asserted). "No measurement" is never
  encoded as a benign number: every anchor in the window has a realised window return (an anchor where
  the book was flat or halted is a MEASURED zero, not a missing value), and the has-measurement variant
  HAS_POSITION (gross0 > 0 at the window start) is reported next to the whole-population figure with
  both n's and the named complement NO_POSITION.

usage: env -i ... /workspace/venv/bin/python -B cf_read.py <ENV_WHITELIST_CSV> <OUT_DIR>
"""
import itertools
import json
import math
import os
import sys
import time

import numpy as np

T0 = time.time()
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, "/workspace/cf3_2026-09-20/devices_bt")
sys.path.insert(0, "/workspace/cf3_2026-09-20/devices_bt/exec_copy")
import cf_lib as L                                     # noqa: E402
import bt_tables as BT                                 # noqa: E402

ENV_OK = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
OUT = sys.argv[2] if len(sys.argv) > 2 else f"{L.ROOT}/receipts"
chk = L.Checks(T0)
rec = L.rec_head("cf_read.py", sys.argv)
extra = sorted(set(rec["env"]) - ENV_OK)
chk("env.whitelist", not extra, {"extra": extra})

CFG_P = f"{L.ROOT}/RUN_CONFIG_CF3_2026-09-20.json"
CFG = json.load(open(CFG_P))
RUNS_ROOT = f"{L.ROOT}/runs"
CERT = "/workspace/baseline_tables_2026-09-19/runs/OBJB_A0_scaled_rule_raw_UAFE"
rec["inputs"] = {"config": {"path": CFG_P, "sha256": L.sha(CFG_P)},
                 "bt_tables": {"path": "/workspace/cf3_2026-09-20/devices_bt/bt_tables.py",
                               "sha256": L.sha("/workspace/cf3_2026-09-20/devices_bt/bt_tables.py")},
                 "cf_lib": {"path": f"{HERE}/cf_lib.py", "sha256": L.sha(f"{HERE}/cf_lib.py")},
                 "CF_ARMS_receipt": {"path": f"{OUT}/CF_ARMS.json", "sha256": L.sha(f"{OUT}/CF_ARMS.json")}}


def log(*a):
    print("[%7.1fs]" % (time.time() - T0), *a, flush=True)


def fail(msg):
    L.write_receipt(rec, chk, f"{OUT}/CF_READ.json", "REFUSED")
    print("CF_READ VERDICT=REFUSED failed=%s note=%s" % (chk.fails, msg), flush=True)
    sys.exit(3)


TAGS = [r["tag"] for r in CFG["runs"]]
ARM_OF = {r["tag"]: r["arm"].replace("CF_", "") for r in CFG["runs"]}
DIR_OF = {t: os.path.join(RUNS_ROOT, t.replace("|", "_")) for t in TAGS}

# ── GATE J1: the BASE run is the certified run, bitwise ─────────────────────
bd = DIR_OF["CF_BASE|scaled|rule|raw|UAFE"]
j1 = {"n_path_files": 0, "differing": []}
for i in range(32):
    a = f"{bd}/PATH_CF_BASE_scaled_rule_raw_UAFE_seed_{i:02d}.npz"
    b = f"{CERT}/PATH_OBJB_A0_scaled_rule_raw_UAFE_seed_{i:02d}.npz"
    sa, sb = L.sha(a), L.sha(b)
    j1["n_path_files"] += 1
    if sa != sb:
        j1["differing"].append({"seed": i, "mine": sa[:16], "certified": sb[:16]})
ZA = np.load(f"{bd}/AGG_CF_BASE_scaled_rule_raw_UAFE.npz")
ZB = np.load(f"{CERT}/AGG_OBJB_A0_scaled_rule_raw_UAFE.npz")
agg_bad = [k for k in ZB.files if k not in ZA.files or not (
    np.array_equal(np.asarray(ZA[k]), np.asarray(ZB[k])) if np.asarray(ZB[k]).dtype.kind in "iub"
    else L.bitwise_equal(np.asarray(ZA[k]).ravel(), np.asarray(ZB[k]).ravel())[0])]
j1["agg_keys_differing"] = agg_bad
chk("J1.base_run_is_the_certified_run_bitwise", not j1["differing"] and not agg_bad, j1)
if chk.fails:
    fail("Gate J1 — this task's judge is not the certified judge")

# ── load every arm ──────────────────────────────────────────────────────────
S = {}
for t in TAGS:
    paths, files = BT.load_run_dir(DIR_OF[t], R=int(CFG["paths_R"]))
    S[ARM_OF[t]] = {"paths": paths, "mean": BT.series_mean(paths), "files": files,
                    "agg": DIR_OF[t] + "/AGG_" + t.replace("|", "_") + ".npz"}
    log("loaded %-14s 32 paths" % ARM_OF[t])
S["NONE_GF"] = S["NONE"]                      # asserted byte-identical in cf_mkconfig
ARMS_FAITH = ["BASE", "noFUND", "noKING", "noF10", "onlyFUND", "onlyKING", "onlyF10", "NONE"]
ARMS_FROZ = ["BASE", "noFUND_GF", "noKING_GF", "noF10_GF", "onlyFUND_GF", "onlyKING_GF", "onlyF10_GF", "NONE_GF"]

A = S["BASE"]["mean"]["A"]
chk("J3.axis_shared_and_32_paths",
    all(np.array_equal(S[a]["mean"]["A"], A) and len(S[a]["paths"]) == 32 for a in S), {"n_anchors": int(len(A))})
gerr = {a: BT.g_identity_err(S[a]["mean"]) for a in S}
chk("J2.g_identity_per_arm", max(gerr.values()) <= 1e-9, {"max_abs_err_bps": max(gerr.values()), "per_arm": gerr})
if chk.fails:
    fail("Gate J2 / J3")

# ── populations ─────────────────────────────────────────────────────────────
F = np.load(f"{L.ROOT}/work/CF_ARM_FLAGS.npz")
fa = F["anchor"].astype(np.int64)
sel_rows = np.searchsorted(fa, A)
chk("population.flags_axis_covers_the_sim_window", bool(np.array_equal(fa[sel_rows], A)), None)
BASE_KIND = F["BASE_kind"][sel_rows]
GROSS0 = np.asarray(ZA["gross0_over_gmnav0_mean"])

BUCKETS = {"COMBO": BASE_KIND == 2, "KING_FILE": BASE_KIND == 1, "HOLD": BASE_KIND == 0}
chk("population.buckets_are_a_partition",
    bool(np.array_equal(sum(BUCKETS.values()), np.ones(len(A), int))),
    {k: int(v.sum()) for k, v in BUCKETS.items()})
if chk.fails:
    fail("population")

PERIODS = {p: L.period_mask(A, p) for p in ("HIST", "2026", "FULL_RECIPE", "PRE", "ALL_2022_06")}

rec["populations"] = {}
for p, pm in PERIODS.items():
    d = {"n_anchors": int(pm.sum()),
         "first_anchor": L.iso(A[pm][0]) if pm.any() else None,
         "last_anchor": L.iso(A[pm][-1]) if pm.any() else None,
         "buckets_by_BASE_kind": {k: int((pm & v).sum()) for k, v in BUCKETS.items()},
         "HAS_POSITION_gross0_gt_0": int((pm & (GROSS0 > 0)).sum()),
         "NO_POSITION_gross0_eq_0": int((pm & (GROSS0 <= 0)).sum())}
    d["buckets_sum_equals_n"] = sum(d["buckets_by_BASE_kind"].values()) == d["n_anchors"]
    d["has_position_plus_no_position_equals_n"] = d["HAS_POSITION_gross0_gt_0"] + d["NO_POSITION_gross0_eq_0"] == d["n_anchors"]
    rec["populations"][p] = d
chk("population.closed_in_every_period",
    all(v["buckets_sum_equals_n"] and v["has_position_plus_no_position_equals_n"] for v in rec["populations"].values()), None)

# ── per-arm metrics, per period, per bucket ─────────────────────────────────
log("metrics ...")
TAB = {}
for arm in S:
    m = S[arm]["mean"]
    TAB[arm] = {}
    for p, pm in PERIODS.items():
        cell = BT.cell_metrics(m, pm)
        cell["path_distribution"] = BT.path_distribution(S[arm]["paths"], pm)
        # bucket g: closed population, both whole-population and has-measurement variants
        bk = {}
        for bname, bmask in BUCKETS.items():
            mm = pm & bmask
            n = int(mm.sum())
            hp = mm & (GROSS0 > 0)
            bk[bname] = {"n": n,
                         "g_whole_population": (float(m["g"][mm].mean()) if n else None),
                         "n_has_position": int(hp.sum()),
                         "g_has_position": (float(m["g"][hp].mean()) if hp.any() else None),
                         "n_no_position_named_subset": int(n - hp.sum())}
        cell["buckets_by_BASE_kind"] = bk
        cell["g_has_position"] = (float(m["g"][pm & (GROSS0 > 0)].mean()) if (pm & (GROSS0 > 0)).any() else None)
        cell["n_has_position"] = int((pm & (GROSS0 > 0)).sum())
        TAB[arm][p] = cell

# ── Delta vs BASE, paired MBB ───────────────────────────────────────────────
log("paired bootstrap ...")
DELTA = {}
DELTA_SEED = {}
for i, arm in enumerate([a for a in S if a != "BASE"]):
    DELTA[arm] = {}
    DELTA_SEED[arm] = [20260919, 777 + i]        # PREREG 8: rng [20260919, 777 + arm_index]
    for p in ("HIST", "2026", "FULL_RECIPE"):
        DELTA[arm][p] = BT.paired(S[arm]["mean"], S["BASE"]["mean"], mask=PERIODS[p],
                                  seed=(20260919, 777 + i))

# ── Shapley / LOO / LOI / interaction gap ───────────────────────────────────
PLAYERS = ("FUND", "KING", "F10")
COAL = {"BASE": frozenset(PLAYERS), "noFUND": frozenset(("KING", "F10")),
        "noKING": frozenset(("FUND", "F10")), "noF10": frozenset(("FUND", "KING")),
        "onlyFUND": frozenset(("FUND",)), "onlyKING": frozenset(("KING",)),
        "onlyF10": frozenset(("F10",)), "NONE": frozenset()}


def decomposition(arms, period, key):
    v = {}
    for arm in arms:
        base_arm = arm.replace("_GF", "")
        v[COAL[base_arm]] = TAB[arm][period][key]
    if any(x is None for x in v.values()):
        return {"UNAVAILABLE": "a coalition value is undefined (None) for this metric",
                "coalition_values": {"+".join(sorted(k)) if k else "(empty)": vv for k, vv in v.items()}}
    full, empty = frozenset(PLAYERS), frozenset()
    total = v[full] - v[empty]
    loo = {i: v[full] - v[full - {i}] for i in PLAYERS}
    loi = {i: v[frozenset((i,))] - v[empty] for i in PLAYERS}
    orders = {}
    marg = {i: [] for i in PLAYERS}
    for perm in itertools.permutations(PLAYERS):
        cur = frozenset()
        o = {}
        for i in perm:
            nxt = cur | {i}
            o[i] = v[nxt] - v[cur]
            marg[i].append(o[i])
            cur = nxt
        orders["->".join(perm)] = o
    shap = {i: float(np.mean(marg[i])) for i in PLAYERS}
    return {"coalition_values": {"+".join(sorted(k)) if k else "(empty)": vv for k, vv in v.items()},
            "total_v(N)-v(empty)": total,
            "LOO": loo, "LOI": loi,
            "GAP_LOO": total - sum(loo.values()), "GAP_LOI": total - sum(loi.values()),
            "shapley": shap,
            "shapley_sum_residual": total - sum(shap.values()),
            "per_ordering_marginals": orders,
            "per_signal_ordering_spread": {i: {"min": float(min(marg[i])), "max": float(max(marg[i])),
                                               "range": float(max(marg[i]) - min(marg[i]))} for i in PLAYERS},
            "decomposable_by_LOO": bool(abs(total - sum(loo.values())) <= 0.5 * abs(total)) if total else None}


DEC = {}
for gate, arms in (("G-FAITHFUL", ARMS_FAITH), ("G-FROZEN", ARMS_FROZ)):
    DEC[gate] = {}
    for p in ("HIST", "2026", "FULL_RECIPE"):
        DEC[gate][p] = {k: decomposition(arms, p, k) for k in ("g", "cagr", "sharpe_daily", "maxdd_4h", "nav_return")}
        DEC[gate][p]["additive_key"] = "g (bps/anchor/target-gross) — the only additive one; cagr/sharpe/maxdd/nav_return are NON-additive and their LOO/Shapley are DESCRIPTIVE ONLY"

resid = max(abs(DEC[gt][p]["g"]["shapley_sum_residual"]) for gt in DEC for p in ("HIST", "2026", "FULL_RECIPE")
            if "shapley_sum_residual" in DEC[gt][p]["g"])
chk("shapley.sums_to_total_on_g", resid <= 1e-9, {"max_abs_residual_bps": resid})

rec["gate_J"] = {"J1": j1, "J2_max_g_identity_err": max(gerr.values())}
rec["tables"] = TAB
rec["delta_vs_BASE"] = DELTA
rec["delta_bootstrap_seed_by_arm"] = DELTA_SEED
rec["decomposition"] = DEC
NS = json.load(open(f"{OUT}/CF_ARMS.json"))["named_subsets_by_period"]
rec["named_subsets"] = NS
rec["C3_trigger_cdegen_share"] = {
    p: {a: {"n_affected": NS[p][a]["DEGEN_BOTH"] + NS[p][a]["DEGEN_ONE"],
            "share": (NS[p][a]["DEGEN_BOTH"] + NS[p][a]["DEGEN_ONE"]) / NS[p]["n_anchors"],
            "over_20pct": (NS[p][a]["DEGEN_BOTH"] + NS[p][a]["DEGEN_ONE"]) / NS[p]["n_anchors"] > 0.20}
        for a in ("noFUND", "noKING", "noF10", "onlyFUND", "onlyKING", "onlyF10", "NONE")}
    for p in ("HIST", "2026", "FULL_RECIPE")}
rec["C3_verdict"] = ("PREREG C3 fires wherever over_20pct is true: the decomposition there is "
                     "CONVENTION-DOMINATED, so Shapley and LOI are reported in an appendix under a "
                     "withdrawal banner and LOO + the gap are the primary reading. The LOI arms and the "
                     "empty coalition are 100% affected BY CONSTRUCTION in every period (turning off two "
                     "of three signals necessarily empties a component), so Shapley is withdrawn in every "
                     "period; the LOO family is convention-free in 2026 (0%).")
rec["blind_protocol"] = ("CFG-04 / CFG-06: historical replay only; pooled chase weights 0.5/0.5 as in the certified "
                         "config; no per-experiment-arm execution outcome is computed, printed or stored")

rsha = L.write_receipt(rec, chk, f"{OUT}/CF_READ.json", "PASS" if not chk.fails else "REFUSED")
print("CF_READ VERDICT=%s checks=%d failed=%s receipt_sha256=%s"
      % ("PASS" if not chk.fails else "REFUSED", len(chk.items), chk.fails, rsha), flush=True)
sys.exit(0 if not chk.fails else 3)
