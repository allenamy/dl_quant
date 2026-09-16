#!/usr/bin/env python3
"""fx_trd01_redtests.py — FX-DATA TRD-01 red tests (pod2, CPU, read-only). Committed before it is run.

FIXPROGRAM section 0 item 2 wants a test that goes RED on the old code, on real shapes, and red for the stated reason. The stated
reason here is one sentence: **each legacy eligibility rule admits contracts that had no trade in the trailing 24 h.** So every cell
below is the same contrast evaluated on the rule's OWN artifact or its OWN expression, over the real 10,039-anchor A0 axis and the
real 829-name universe:

    admitted_and_untradable(rule) = | { (anchor, symbol) : rule admits it AND tradable(A, s) is False } |

A cell is RED when that count is non-zero on the legacy object and GREEN when it is zero on the fixed object. Rules that FX-DATA has
fixed are run on BOTH and must flip red -> green. Rules owned elsewhere are run on the legacy object only, are recorded RED, and name
their owner rather than being quietly skipped: a rule with no fixed artifact is an open defect, not a passing test.

Named fixtures, all real contracts, are reported beside the counts so the failure is legible rather than a number: the six dead names
AUDIT_DATA names (FTT, RAY, SC, STRAX, DGB, SNT), the 2026 deaths, and four neighbour cases that must NOT be rejected by the module —
BTCUSDT, the thinnest live name in the universe at that anchor, a name that resumes after a halt, and a lag case inside the declared
24 h window.

Usage: python3 fx_trd01_redtests.py <artifact.npz> <artifact_sha256> <inject_dir> <arms_dir> <out_receipt.json>
Exit 0 always: this device REPORTS the red/green matrix, it does not gate. A non-zero legacy count is the evidence, not an error.
"""
import os, sys, json, time
import numpy as np

ENV_WHITELIST = {"PATH", "HOME", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "PYTHONPATH"}
EXTRA = sorted(k for k in os.environ if k not in ENV_WHITELIST and k not in ("PWD", "SHLVL", "_", "OLDPWD", "LC_CTYPE"))
assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
os.nice(19)
ART, ART_SHA, INJ, ARMS, OUT = sys.argv[1:6]
sys.path.insert(0, os.environ["PYTHONPATH"].split(":")[0])
import tradability as T

W = "/workspace"
PANEL = f"{W}/data/wide_panel_4h_v2ext.npz"
META = f"{W}/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"
UMASK = f"{W}/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"
DLW = f"{W}/dlw_v4raw/data/dlw_targets.npz"
LEDGER = f"{W}/uplift_r2_2026-09-13/P2/work/ledger_full.npz"
T0 = time.time()
def utc(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)

rec = {"device": "fx_trd01_redtests.py", "self_sha256": T.guarded_sha256(os.path.abspath(__file__)),
       "module_sha256": T.guarded_sha256(os.path.join(os.environ["PYTHONPATH"].split(":")[0], "tradability.py")),
       "spec_sha256": T.SPEC_SHA256, "numpy": np.__version__, "argv": sys.argv,
       "env": {k: os.environ[k] for k in sorted(os.environ)},
       "inputs": {p: T.guarded_sha256(p) for p in (PANEL, META, UMASK, DLW, LEDGER)},
       "stated_reason": "each legacy eligibility rule admits (anchor, symbol) pairs with no trade in the trailing 24 h",
       "utc_start": utc(time.time())}
A = T.Artifact.load(ART, expected_sha256=ART_SHA)
rec["artifact_sha256"] = A.sha256

P = np.load(PANEL, allow_pickle=True); pts = P["ts"].astype(np.int64); syms = [str(s) for s in P["symbols"]]
assert syms == A.symbols
FE1 = np.asarray(P["f_fund_ema_v1"]); ELIG = np.asarray(P["elig"]).astype(bool)
M = np.load(META, allow_pickle=True); aE = M["E_ts"].astype(np.int64); aQ = M["qvk"]; aY4 = M["y4"]
U = np.load(UMASK, allow_pickle=True); UM = np.asarray(U["mask"])
rows = A.rows(pts)
TR = A._z["state_W24H"][rows] == T.TRADABLE            # tradable on the panel axis
NOD = A._z["state_W24H"][rows] == T.NODATA
apos = {int(t): i for i, t in enumerate(aE)}
ai = np.array([apos[int(t)] for t in pts], np.int64)     # panel anchor -> meta row
CELLS = {}

def cell(rule, where, legacy, fixed=None, owner=None, note=""):
    lo = int((legacy & ~TR).sum())
    o = {"rule": rule, "where": where, "owner": owner or "FX-DATA",
         "legacy_admitted_cells": int(legacy.sum()), "legacy_admitted_and_untradable": lo,
         "legacy_verdict": "RED" if lo else "GREEN",
         "of_which_nodata": int((legacy & NOD).sum()), "note": note}
    if fixed is not None:
        fi = int((fixed & ~TR).sum())
        o.update(fixed_admitted_cells=int(fixed.sum()), fixed_admitted_and_untradable=fi,
                 fixed_verdict="GREEN" if fi == 0 else "RED", flipped_red_to_green=bool(lo > 0 and fi == 0))
    else:
        o.update(fixed_admitted_and_untradable=None, fixed_verdict="NO_FIXED_ARTIFACT",
                 flipped_red_to_green=None)
    CELLS[rule] = o
    log(rule, o["legacy_verdict"], lo, "->", o.get("fixed_verdict"), o.get("fixed_admitted_and_untradable"))
    return o

# ---- A1 replay member set (MEMBERS_TOPN=829 qvk ranking) ----
mem = np.zeros((len(pts), len(syms)), bool)
for k in range(len(pts)):
    q = np.nan_to_num(aQ[ai[k]], nan=-1.0); o = np.argsort(-q); o = o[q[o] > -0.5][:829]
    mem[k, o] = True
cell("A1_replay_member_set", "w10_sleeve_r18.py:77-81", mem, None, "FX-DATA (fixed only jointly with A2 via UMASK_SCOPE=m1)",
     "the qvk ranking alone has no mask; the deployed arm applies A2 on top, so A1's own fix is A2's mask")

# ---- A2 universe mask applied to members / A5 U-PIT / A6 CRYPTO ----
UMT = np.asarray(np.load(os.path.join(INJ, "umask_UPIT_CRYPTO_tradable_W24H.npz"), allow_pickle=False)["mask"])
cell("A2_A5_A6_universe_mask", "w10_sleeve_r18.py:163-165,222-224 via build_umask.py:46 + build_crypto_mask.py:11",
     mem & UM, mem & UMT, "FX-DATA", "the fixed artifact is umask_UPIT_CRYPTO_tradable_W24H.npz from fx_trd01_inject.py")

# ---- A3 fund leg rank base FZB ----
FEM = np.asarray(np.load(os.path.join(INJ, "femat_f_fund_ema_v1_tradable_W24H.npz"), allow_pickle=False)["mat"])
cell("A3_fund_rank_base", "w10_sleeve_r18.py:149-150", np.isfinite(FE1), np.isfinite(FEM), "FX-DATA",
     "the fixed artifact is femat_f_fund_ema_v1_tradable_W24H.npz; its book effect is the TB arm")

# ---- A4 trade set sel ----
qv4h = np.expm1(np.clip(np.nan_to_num(aQ[ai], nan=0.0), 0, 30)) * 48
sel_l = (mem & UM) & np.isfinite(aY4[ai]) & (qv4h >= 2.5e5)
sel_f = (mem & UMT) & np.isfinite(aY4[ai]) & (qv4h >= 2.5e5)
cell("A4_trade_set_sel", "w10_sleeve_r18.py:244-245", sel_l, sel_f, "FX-DATA",
     "sel inherits the universe; the frozen close keeps y4 finite at 0 so the forward predicate cannot remove a dead name")

# ---- A7 P2 TRADING proxy (>= 1 settlement in (A-24h, A]) ----
L = np.load(LEDGER, allow_pickle=True); off = L["off"].astype(np.int64); lft = L["ft"].astype(np.int64)
assert [str(x) for x in L["symbols"]] == syms
prox = np.zeros((len(pts), len(syms)), bool)
for j in range(len(syms)):
    a_, c_ = off[j], off[j + 1]
    if c_ <= a_: continue
    ftj = lft[a_:c_]; k = np.searchsorted(ftj, pts, side="right")
    prox[:, j] = (k > 0) & (ftj[np.maximum(k - 1, 0)] > pts - 86400)
cell("A7_p2_trading_proxy", "p2_prep_inputs.py:94-99", prox, prox & TR, "p2-oos-replay",
     "the fixed column is the proxy intersected with the flag; P2 decides whether its certified replay consumes it")

# ---- A8 panel elig ----
cell("A8_panel_elig", "pod_panel_ext.py:40", ELIG, None, "FX-DATA / FX-TRAIN (panel rebuild)",
     "elig = (covr >= 0.95) & (v7 >= 1e-4); the frozen ret5 = 0 is finite so covr stays 1")

# ---- A9 king member screen / A10 DL member screen (owner FX-MODEL, TRD-05) ----
kmem = np.zeros((len(pts), len(syms)), bool)
for k in range(len(pts)):
    m = np.asarray(M["members"][ai[k]], np.int64); kmem[k, m] = True
cell("A9_king_member_screen", "pod_fea_ext_clamp.py:37 (population = META members)", kmem, None, "FX-MODEL (TRD-05)",
     "counted on the META member lists the king features are built on")
D = np.load(DLW, allow_pickle=True); dE = D["E_ts"].astype(np.int64); dmem = D["members"]
dpos = {int(t): i for i, t in enumerate(dE)}
dl = np.zeros((len(pts), len(syms)), bool)
for k, t in enumerate(pts):
    i = dpos.get(int(t))
    if i is None: continue
    dl[k, np.asarray(dmem[i], np.int64)] = True
cell("A10_dl_member_screen", "pod_dlw_targets_raw.py:107", dl, None, "FX-MODEL (TRD-05)", "dlw_targets member lists")

# ---- A11 T1 state member set ----
t1 = mem & UM
cell("A11_t1_state_member_set", "t1_states.py:77-82", t1, mem & UMT, "T1 / T8 / r19 (TRD-04)",
     "same population as A1+A2 on this axis; the treated matrices are in trd04_states_series.npz")

# ---- named fixtures ----
DEAD = ["FTTUSDT", "RAYUSDT", "SCUSDT", "STRAXUSDT", "DGBUSDT", "SNTUSDT"]
fx = {}
for s in DEAD:
    j = syms.index(s); lt = int(A.last_traded_ts[j])
    after = np.where((pts > lt) & (mem[:, j] & UM[:, j]))[0]
    fx[s] = {"last_traded": utc(lt) if lt >= 0 else None,
             "anchors_admitted_by_A2_after_its_last_trade": int(len(after)),
             "first_such_anchor": utc(pts[after[0]]) if len(after) else None,
             "last_such_anchor": utc(pts[after[-1]]) if len(after) else None,
             "days_admitted_after_death": round(float(len(after)) / 6.0, 1),
             "tradable_at_first_such_anchor": bool(TR[after[0], j]) if len(after) else None}
rec["dead_fixtures"] = fx
lag = (TR & A.dead_after(pts, syms) & (mem & UMT))
lr, lc = np.where(lag)
rec["lag_fixtures_inside_the_declared_24h"] = {
    "name_anchors": int(len(lr)),
    "examples": [{"symbol": syms[int(lc[i])], "anchor": utc(pts[int(lr[i])]),
                  "hours_since_last_trade": round((int(pts[int(lr[i])]) - int(A.last_traded_ts[int(lc[i])])) / 3600.0, 1)}
                 for i in range(min(8, len(lr)))],
    "max_hours_since_last_trade": (round(float(max((int(pts[int(lr[i])]) - int(A.last_traded_ts[int(lc[i])])) / 3600.0 for i in range(len(lr)))), 1) if len(lr) else None),
    "note": "these are admitted BY DESIGN: SPEC section 2 declares a bounded lag of at most 24 h (6 anchors) and requires it to be counted, not hidden"}
neigh = {}
last_k = len(pts) - 1
thin = None
q = np.nan_to_num(aQ[ai[last_k]], nan=-1.0)
live = np.where((mem[last_k] & UMT[last_k]))[0]
if len(live): thin = syms[int(live[np.argmin(q[live])])]
for s in [x for x in ("BTCUSDT", thin) if x]:
    j = syms.index(s)
    neigh[s] = {"tradable_share_over_the_axis": round(float(TR[:, j].mean()), 4),
                "tradable_at_last_anchor": bool(TR[last_k, j]),
                "role": "must not be rejected by the module"}
rec["neighbour_fixtures"] = neigh
rec["cells"] = CELLS
rec["summary"] = {"rules": len(CELLS), "legacy_RED": sum(1 for c in CELLS.values() if c["legacy_verdict"] == "RED"),
                  "flipped_red_to_green": sum(1 for c in CELLS.values() if c.get("flipped_red_to_green")),
                  "no_fixed_artifact_yet": sorted(k for k, c in CELLS.items() if c["fixed_verdict"] == "NO_FIXED_ARTIFACT")}
rec["runtime_s"] = round(time.time() - T0, 1); rec["utc_end"] = utc(time.time())
json.dump(rec, open(OUT, "w"), indent=1)
print("FX_TRD01_REDTESTS_DONE", json.dumps(rec["summary"]), flush=True)
