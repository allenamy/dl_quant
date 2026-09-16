#!/usr/bin/env python3
"""fm_red_builders.py -- FX-MODEL queue item 2: red tests that go red ON THE LEGACY BUILDERS for the right reason.

Runs the UNMODIFIED legacy builders (via runpy, env-driven; their sources are never edited) against a small
REAL-SHAPE fixture and asserts the CORRECT (production-aligned / causal) behaviour. A case counts as a valid red only
when the builder ran to completion, produced its artifact, and an assertion on a VALUE failed. Crashes and missing
artifacts are reported as INVALID and are NOT evidence of the defect (lead's rule: "a crash or missing fixture is
INVALID").

Outcome vocabulary written into the receipt:
  RED_CORRECT        builder completed, artifact present, value assertion failed  -> valid red; defect demonstrated
  GREEN              builder completed and the correct-behaviour assertion held   -> defect NOT present here
  INVALID_CRASH      builder raised                                               -> NOT evidence
  INVALID_NOARTIFACT builder returned but wrote no readable artifact              -> NOT evidence

Safety / scope: this module does not import or call subprocess, os.system, bash-anything, or requests, and reaches no
network and no venue. It touches nothing under ~/wide_shadow or ~/dl_quant_live. It reads the legacy builder sources
and writes a fixture plus builder outputs into a caller-supplied scratch directory. It is therefore outside the
battery-window rule of FIXPROGRAM 14.1 -- grep this file for subprocess / bash / os.system / requests: zero hits.

The fixture is real-SHAPE, not real data: the builders' own channel order and npz member names, float16 cache, 5-minute
grid with anchors on ts %% 14400 == 0, a BTCUSDT column (the targets builder indexes it), a panel carrying F6_KEYS and a
Y4 consistent with the cache so the builder's own alignment self-check passes on its own terms.

Usage:
  FM_RED_OUT=<receipt.json> FM_RED_TMP=<scratchdir> python3 fm_red_builders.py
"""
import os, sys, json, time, hashlib, runpy, io, contextlib, traceback
import numpy as np

T0 = time.time()
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
RETRAIN = os.path.join(REPO, "multi_asset", "exports", "research", "retrain_2026-09")
CHAIN = os.path.join(RETRAIN, "v4_chain_2026-09-09")
KING_BUILDER = os.path.join(CHAIN, "pod_fea_ext_clamp.py")
DLW_FEA_BUILDER = os.path.join(RETRAIN, "pod_dlw_features_ext.py")
DLW_TGT_BUILDER = os.path.join(CHAIN, "pod_dlw_targets_raw.py")
OUT = os.environ["FM_RED_OUT"]
TMP = os.environ["FM_RED_TMP"]
os.makedirs(TMP, exist_ok=True)

CHN = ["ret5", "range", "cpos", "log_qv", "log_cnt", "log_avgsz", "tbf"]
F6_KEYS = ["f_rev_4h", "f_rev_24h", "f_vol_7d", "f_range_24h", "f_mom_7d", "f_fund_ema"]
BAR_S, ANCHOR_S = 300, 14400
T_ROWS = 10320            # -> ~203 grid anchors: the targets builder's alignment self-check needs nA > 120
NW = 80                   # >= MIN_MEM 50 and >= MIN_RES 60; < NTOP 400 so no top-N truncation confounds the tests
EPOCH0 = 1640995200       # 2022-01-01T00:00:00Z, a multiple of 14400
GENUINE_ZERO_NAME = 3     # this name's funding really IS 0.0 in the panel


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def grid_rows():
    return [r for r in range(0, T_ROWS, 48) if r >= 576 and r + 48 <= T_ROWS - 1]


def make_cache(path, seed=0, impulse=None, qv_bump=None, nan_from=None, freeze_from=None):
    """Well-behaved cache: every bar finite, every name liquid and volatile, distinct per-name volume.

    impulse     (row, j, v) set ret5 at exactly one cell
    qv_bump     (row, j, v) set log_qv at exactly one cell
    nan_from    (row, j)    ret5 NaN from that row on  -> a non-finite forward label
    freeze_from (row, j)    ret5 exactly 0 (finite) from that row on -> a delisted contract's frozen rows
    """
    rs = np.random.RandomState(seed)
    ts = (EPOCH0 + BAR_S * np.arange(T_ROWS)).astype(np.int64)
    data = np.zeros((T_ROWS, NW, len(CHN)), np.float16)
    r = (rs.randn(T_ROWS, NW) * 0.002).astype(np.float32)
    data[:, :, 0] = r.astype(np.float16)
    data[:, :, 1] = np.abs(r * 2).astype(np.float16)
    data[:, :, 2] = (rs.rand(T_ROWS, NW) * 0.5 + 0.25).astype(np.float16)
    data[:, :, 3] = (10.0 + np.arange(NW)[None, :] * 0.01).astype(np.float16)   # log_qv, distinct per name
    data[:, :, 4] = np.float16(5.0)
    data[:, :, 5] = np.float16(3.0)
    data[:, :, 6] = np.float16(0.5)
    if freeze_from is not None:
        data[freeze_from[0]:, freeze_from[1], 0] = np.float16(0.0)
    if nan_from is not None:
        data[nan_from[0]:, nan_from[1], 0] = np.float16(np.nan)
    if impulse is not None:
        data[impulse[0], impulse[1], 0] = np.float16(impulse[2])
    if qv_bump is not None:
        data[qv_bump[0], qv_bump[1], 3] = np.float16(qv_bump[2])
    syms = ["BTCUSDT"] + ["N%03dUSDT" % i for i in range(1, NW)]      # the targets builder indexes BTCUSDT
    np.savez(path, ts=ts, data=data, symbols=np.array(syms), ch=np.array(CHN))
    return ts, np.array(syms), data


def make_panel(path, ts, syms, data, fund_nan_names=(), drop_anchors=()):
    """Panel on the 4h grid. Y4 is computed FROM the cache so the targets builder's own alignment check passes."""
    rows = grid_rows()
    drop = set(int(x) for x in drop_anchors)
    keep_rows = [r for r in rows if int(ts[r]) not in drop]
    n = len(keep_rows)
    r5 = data[:, :, 0].astype(np.float64)
    Y4 = np.stack([np.nansum(r5[r + 1:r + 49], axis=0) for r in keep_rows]).astype(np.float32)
    rs = np.random.RandomState(99)
    cols = {k: (rs.randn(n, len(syms)) * 0.01).astype(np.float32) for k in F6_KEYS}
    ema = np.full((n, len(syms)), 0.0001, np.float32)
    now = np.full((n, len(syms)), 0.0002, np.float32)
    ema[:, GENUINE_ZERO_NAME] = 0.0
    now[:, GENUINE_ZERO_NAME] = 0.0
    for j in fund_nan_names:
        ema[:, j] = np.nan
        now[:, j] = np.nan
    cols["f_fund_ema"] = ema
    np.savez(path, ts=np.array([int(ts[r]) for r in keep_rows], np.int64), symbols=syms, Y4=Y4,
             f_fund_now=now, f_fund_ema_v1=ema.copy(), **cols)
    return [int(ts[r]) for r in keep_rows]


def run_builder(src, env):
    old = dict(os.environ)
    buf = io.StringIO()
    try:
        os.environ.update({k: str(v) for k, v in env.items()})
        sys.path.insert(0, RETRAIN)
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            runpy.run_path(src, run_name="__main__")
        return True, buf.getvalue(), None
    except BaseException:
        return False, buf.getvalue(), traceback.format_exc()
    finally:
        if sys.path and sys.path[0] == RETRAIN:
            sys.path.pop(0)
        os.environ.clear()
        os.environ.update(old)


def dl_targets(d, tag, cache, panel):
    o = os.path.join(d, "dl%s" % tag)
    os.makedirs(os.path.join(o, "data"), exist_ok=True)
    os.makedirs(os.path.join(o, "results"), exist_ok=True)
    ok, so, err = run_builder(DLW_TGT_BUILDER, {"DLWT_CACHE": cache, "DLWT_PANEL": panel, "DLWT_OUT": o})
    return o, os.path.join(o, "data", "dlw_targets.npz"), ok, so, err


CASES = []


def case(cid, item, statement):
    def deco(fn):
        CASES.append((cid, item, statement, fn))
        return fn
    return deco


def res(cid, status, expected=None, observed=None, why=None, tail=None, error=None):
    return {"case": cid, "outcome": status, "expected": expected, "observed": observed, "why_red": why,
            "builder_stdout_tail": (tail or "")[-700:], "error": error}


# ------------------------------------------------------------------ king builder (TIM-01)
def _king(d, tag, cache, panel):
    fea, meta = os.path.join(d, "f%s.npy" % tag), os.path.join(d, "m%s.npz" % tag)
    ok, so, err = run_builder(KING_BUILDER, {"CACHE_IN": cache, "PANEL_IN": panel, "FEA_OUT": fea, "META_OUT": meta})
    return fea, meta, ok, so, err


@case("R-TIM-1", "TIM-01", "king feature window must END AT row E, the bar closing at the anchor, as the producer serves")
def r_tim_1(d):
    E, j = 4032, 5
    c, p = os.path.join(d, "c1.npz"), os.path.join(d, "p1.npz")
    ts, syms, data = make_cache(c, seed=0, impulse=(E, j, 0.25))
    make_panel(p, ts, syms, data)
    fea, meta, ok, so, err = _king(d, "1", c, p)
    if not ok:
        return res("R-TIM-1", "INVALID_CRASH", tail=so, error=err)
    if not (os.path.exists(fea) and os.path.exists(meta)):
        return res("R-TIM-1", "INVALID_NOARTIFACT", tail=so)
    F, M = np.load(fea), np.load(meta, allow_pickle=True)
    ets = M["E_ts"].astype(np.int64)
    hit = np.where(ets == int(ts[E]))[0]
    if not len(hit):
        return res("R-TIM-1", "INVALID_NOARTIFACT", why="anchor absent from the meta", tail=so)
    col = [str(x) for x in M["names"]].index("ret5_sum_48_v")
    got = float(F[int(hit[0]), j, col])
    r5 = data[:, :, 0].astype(np.float64)
    want = float(r5[E - 48 + 1:E + 1, j].sum())     # served window [E-w+1, E]
    legacy = float(r5[E - 48:E, j].sum())           # legacy window [E-w, E-1]
    if abs(got - want) <= 3e-3:
        return res("R-TIM-1", "GREEN", want, got)
    return res("R-TIM-1", "RED_CORRECT", want, got,
               why=("a +0.25 impulse sits on the anchor bar E of one name. The legacy window sums rows [E-w, E-1] "
                    "= %.6f and misses it; the window the producer serves, [E-w+1, E], = %.6f." % (legacy, want)),
               tail=so)


@case("R-TIM-2", "TIM-01", "king label must be rows [E+1, E+48], the four hours AFTER the anchor, as the book is accounted")
def r_tim_2(d):
    E, j = 4032, 5
    c, p = os.path.join(d, "c2.npz"), os.path.join(d, "p2.npz")
    ts, syms, data = make_cache(c, seed=1, impulse=(E, j, 0.10))
    make_panel(p, ts, syms, data)
    fea, meta, ok, so, err = _king(d, "2", c, p)
    if not ok:
        return res("R-TIM-2", "INVALID_CRASH", tail=so, error=err)
    if not os.path.exists(meta):
        return res("R-TIM-2", "INVALID_NOARTIFACT", tail=so)
    M = np.load(meta, allow_pickle=True)
    hit = np.where(M["E_ts"].astype(np.int64) == int(ts[E]))[0]
    if not len(hit):
        return res("R-TIM-2", "INVALID_NOARTIFACT", why="anchor absent from the meta", tail=so)
    got = float(M["y4"][int(hit[0]), j])
    r5 = data[:, :, 0].astype(np.float64)
    want, legacy = float(r5[E + 1:E + 49, j].sum()), float(r5[E:E + 48, j].sum())
    if abs(got - want) <= 3e-3:
        return res("R-TIM-2", "GREEN", want, got)
    return res("R-TIM-2", "RED_CORRECT", want, got,
               why=("the independent review's anchor-bar impulse test, as a test: ONLY row E carries +0.10. The legacy "
                    "label sums rows [E, E+47] = %.6f, so it READS the anchor bar; the true four hours after E sum to "
                    "%.6f. A clock/label definition shift, NOT a peek at future prices." % (legacy, want)), tail=so)


@case("R-TIM-3", "TIM-01", "king builder must emit EVERY grid anchor; the unclamped E-2016 must not delete early anchors")
def r_tim_3(d):
    c, p = os.path.join(d, "c3.npz"), os.path.join(d, "p3.npz")
    ts, syms, data = make_cache(c, seed=2)
    make_panel(p, ts, syms, data)
    fea, meta, ok, so, err = _king(d, "3", c, p)
    if not ok:
        return res("R-TIM-3", "INVALID_CRASH", tail=so, error=err)
    if not os.path.exists(meta):
        return res("R-TIM-3", "INVALID_NOARTIFACT", tail=so)
    M = np.load(meta, allow_pickle=True)
    got = set(int(x) for x in M["E_ts"].astype(np.int64))
    want_rows = [r for r in range(0, T_ROWS, 48) if r >= 576 and r + 48 <= T_ROWS]
    want = set(int(ts[r]) for r in want_rows)
    miss_rows = sorted(int(np.where(ts == m)[0][0]) for m in (want - got))
    if not miss_rows:
        return res("R-TIM-3", "GREEN", len(want), len(got))
    return res("R-TIM-3", "RED_CORRECT", len(want), len(got),
               why=("every bar of this fixture is finite and every name volatile, so all %d grid anchors should clear "
                    "the member screen. %d are missing and ALL have E < 2016: rows %s. Mechanism: n7/qvm/m7/v7 index an "
                    "UNCLAMPED E-2016, negative for E < 2016, which wraps to the cache tail; the prefix sums are "
                    "non-decreasing so r2s[E]-r2s[wrapped] <= 0, v7 collapses to 0 and no name clears v7 >= 1e-4. This "
                    "holds for ANY cache with T+1 > 2016, so the deletion is unconditional, not fixture-specific."
                    % (len(want), len(miss_rows), miss_rows[:40])), tail=so)


# ------------------------------------------------------------------ DL feature builder (FEA-01)
def targets_fixture(d, tag, ts, syms, data, anchors=None):
    """A hand-built, VALID dlw_targets.npz. The code under test in the FEA-01 cases is the FEATURE builder, so the
    targets file is an input fixture, not the object being judged."""
    o = os.path.join(d, "fx%s" % tag)
    os.makedirs(os.path.join(o, "data"), exist_ok=True)
    os.makedirs(os.path.join(o, "results"), exist_ok=True)
    rows = [r for r in grid_rows()] if anchors is None else anchors
    # NOTE: np.array([...], dtype=object) on EQUAL-LENGTH lists builds a 2-D object array, and the builder's `v[i, m]`
    # then raises IndexError. The real targets file is ragged, so allocate 1-D object and assign, and make the member
    # lists genuinely ragged to match the real artifact's shape.
    MS = np.empty(len(rows), dtype=object)
    for k in range(len(rows)):
        MS[k] = np.arange(NW - (k % 3), dtype=np.int64)
    r5 = data[:, :, 0].astype(np.float64)
    y4s = np.stack([r5[r + 1:r + 49].sum(0) for r in rows]).astype(np.float32)
    np.savez(os.path.join(o, "data", "dlw_targets.npz"), E_ts=np.array([int(ts[r]) for r in rows], np.int64),
             E_row=np.array(rows, np.int64), members=MS, y4s=y4s, symbols=syms,
             qvk=np.zeros((len(rows), NW), np.float32), btcv=np.zeros(len(rows), np.float32))
    return o


def run_fea(o, cache, panel):
    ok, so, err = run_builder(DLW_FEA_BUILDER, {"F171_CACHE": cache, "F171_PANEL": panel, "F171_OUT": o})
    return os.path.join(o, "data", "dlw_fea82.npz"), ok, so, err


@case("R-FEA-1", "FEA-01", "fea82 funding columns must distinguish ABSENT from a true zero: absent must not be written as 0.0")
def r_fea_1(d):
    nan_names = (7, 8, 9)
    c, p = os.path.join(d, "c4.npz"), os.path.join(d, "p4.npz")
    ts, syms, data = make_cache(c, seed=3)
    make_panel(p, ts, syms, data, fund_nan_names=nan_names)
    o = targets_fixture(d, "4", ts, syms, data)
    fea, ok, so, err = run_fea(o, c, p)
    if not ok:
        return res("R-FEA-1", "INVALID_CRASH", tail=so, error=err)
    if not os.path.exists(fea):
        return res("R-FEA-1", "INVALID_NOARTIFACT", tail=so)
    F = np.load(fea, allow_pickle=True)
    X, ps = F["X"], F["pair_s"]
    absent_zero = int((X[np.isin(ps, nan_names), 80] == 0).sum())
    genuine_zero = int((X[ps == GENUINE_ZERO_NAME, 80] == 0).sum())
    if absent_zero == 0:
        return res("R-FEA-1", "GREEN", "absent cells not 0.0", absent_zero)
    return res("R-FEA-1", "RED_CORRECT", "absent cells carry a value distinguishable from a true zero",
               {"absent_cells_written_as_0.0": absent_zero, "genuine_zero_cells_also_0.0": genuine_zero},
               why=("pod_dlw_features_ext.py L94 writes nan_to_num(panel, 0.0) into cols 80/81, so a name with NO "
                    "funding in the panel and a name whose funding rate really is 0.0 become the SAME float16 token. "
                    "The availability bit is destroyed at write time and is not recoverable from the artifact -- which "
                    "is why changing the FILL VALUE would not fix FEA-01; the column needs a separate availability bit."))


@case("R-FEA-2", "FEA-01", "fea82 funding must be UNKNOWN, not 0.0, for an anchor that has no panel row at all")
def r_fea_2(d):
    c, p = os.path.join(d, "c5.npz"), os.path.join(d, "p5.npz")
    ts, syms, data = make_cache(c, seed=4)
    rows = grid_rows()
    drop_rows = rows[10:18]
    make_panel(p, ts, syms, data, drop_anchors=[int(ts[r]) for r in drop_rows])
    o = targets_fixture(d, "5", ts, syms, data)
    fea, ok, so, err = run_fea(o, c, p)
    if not ok:
        return res("R-FEA-2", "INVALID_CRASH", tail=so, error=err)
    if not os.path.exists(fea):
        return res("R-FEA-2", "INVALID_NOARTIFACT", tail=so)
    F = np.load(fea, allow_pickle=True)
    T = np.load(os.path.join(o, "data", "dlw_targets.npz"), allow_pickle=True)
    ets = T["E_ts"].astype(np.int64)
    drop_ts = set(int(ts[r]) for r in drop_rows)
    idx = [i for i, t in enumerate(ets) if int(t) in drop_ts]
    sel = np.isin(F["pair_a"], idx)
    zeros = int((F["X"][sel, 80] == 0).sum())
    if zeros == 0:
        return res("R-FEA-2", "GREEN", "unknown", 0)
    return res("R-FEA-2", "RED_CORRECT", "unknown (NaN), distinguishable from a real zero rate",
               {"cells_written_as_0.0": zeros, "anchors_without_a_panel_row": len(idx)},
               why=("pod_dlw_features_ext.py L94 writes `0.0 if j is None`, so an anchor the panel never covered is "
                    "indistinguishable from an anchor whose funding really was zero -- the same collapse as R-FEA-1, "
                    "at anchor granularity rather than name granularity."))


# ------------------------------------------------------------------ DL targets builder (TRN-06 / TIM-01)
@case("R-TRD-1", "TRD-05/TRN-06", "DL membership must not depend on any cache row AFTER the anchor: no look-ahead term")
def r_trd_1(d):
    E, j = 4032, 11
    ca, cb, p = os.path.join(d, "c6a.npz"), os.path.join(d, "c6b.npz"), os.path.join(d, "p6.npz")
    ts, syms, data = make_cache(ca, seed=5)
    make_cache(cb, seed=5, nan_from=(E + 1, j))          # name j has NO data strictly AFTER the anchor
    make_panel(p, ts, syms, data)
    _, ta, oka, soa, erra = dl_targets(d, "6a", ca, p)
    _, tb, okb, sob, errb = dl_targets(d, "6b", cb, p)
    if not (oka and okb):
        return res("R-TRD-1", "INVALID_CRASH", tail=soa + sob, error=erra or errb)
    if not (os.path.exists(ta) and os.path.exists(tb)):
        return res("R-TRD-1", "INVALID_NOARTIFACT", tail=soa + sob)
    A, B = np.load(ta, allow_pickle=True), np.load(tb, allow_pickle=True)
    ia = np.where(A["E_ts"].astype(np.int64) == int(ts[E]))[0]
    ib = np.where(B["E_ts"].astype(np.int64) == int(ts[E]))[0]
    if not (len(ia) and len(ib)):
        return res("R-TRD-1", "INVALID_NOARTIFACT", why="the anchor under test is absent from one axis", tail=soa + sob)
    ma = set(int(x) for x in A["members"][int(ia[0])])
    mb = set(int(x) for x in B["members"][int(ib[0])])
    if ma == mb:
        return res("R-TRD-1", "GREEN", "identical member sets", "identical")
    return res("R-TRD-1", "RED_CORRECT", "identical member sets (only rows > E differ between the two caches)",
               {"symdiff": sorted(ma ^ mb), "j_member_in_A": j in ma, "j_member_in_B": j in mb},
               why=("the two caches are bitwise identical on every row <= E and differ ONLY on rows AFTER the anchor, "
                    "yet the member set changed. Cause: the isfinite(y4s) term in the screen "
                    "(pod_dlw_targets_raw.py L107) lets a property of the FUTURE decide whether a row is trained on. "
                    "Production's screen (shadow_loop_v3.py L374) has no forward term at all. Interventional, not "
                    "correlational: nothing else differs."), tail=soa + sob)


@case("R-TRD-2", "TRD-05/TRN-06", "a contract with no traded bar after the anchor must not be a member with a label of exactly 0")
def r_trd_2(d):
    E, j = 4032, 12
    c, p = os.path.join(d, "c7.npz"), os.path.join(d, "p7.npz")
    ts, syms, data = make_cache(c, seed=6, freeze_from=(E + 1, j))   # delisted: frozen rows are finite 0, not NaN
    make_panel(p, ts, syms, data)
    _, t, ok, so, err = dl_targets(d, "7", c, p)
    if not ok:
        return res("R-TRD-2", "INVALID_CRASH", tail=so, error=err)
    if not os.path.exists(t):
        return res("R-TRD-2", "INVALID_NOARTIFACT", tail=so)
    A = np.load(t, allow_pickle=True)
    hit = np.where(A["E_ts"].astype(np.int64) == int(ts[E]))[0]
    if not len(hit):
        return res("R-TRD-2", "INVALID_NOARTIFACT", why="anchor absent", tail=so)
    i = int(hit[0])
    members = set(int(x) for x in A["members"][i])
    lab = float(A["y4s"][i, j])
    if j not in members:
        return res("R-TRD-2", "GREEN", "dead name excluded", {"member": False, "label": lab})
    return res("R-TRD-2", "RED_CORRECT", "the dead name is not a training member",
               {"member": True, "label_exactly_zero": lab == 0.0, "label": lab},
               why=("name %d has no traded bar after the anchor -- its rows are frozen at exactly 0, which is FINITE, "
                    "not NaN. So coverage stays 1.0 and isfinite(y4s) is TRUE, and the name enters training with a "
                    "label of exactly 0. This is TRD-05's channel A: the row is kept and teaches the model that a dead "
                    "contract returns zero. Note it is the opposite direction to R-TRD-1's channel B." % j), tail=so)


@case("R-TIM-5", "TIM-01", "DL member statistics must include row E, matching the producer's [E-2015, E] window")
def r_tim_5(d):
    E, j = 4032, 13
    ca, cb, p = os.path.join(d, "c8a.npz"), os.path.join(d, "c8b.npz"), os.path.join(d, "p8.npz")
    ts, syms, data = make_cache(ca, seed=7)
    make_cache(cb, seed=7, qv_bump=(E, j, 25.0))         # change ONLY log_qv on the anchor bar
    make_panel(p, ts, syms, data)
    _, ta, oka, soa, erra = dl_targets(d, "8a", ca, p)
    _, tb, okb, sob, errb = dl_targets(d, "8b", cb, p)
    if not (oka and okb):
        return res("R-TIM-5", "INVALID_CRASH", tail=soa + sob, error=erra or errb)
    if not (os.path.exists(ta) and os.path.exists(tb)):
        return res("R-TIM-5", "INVALID_NOARTIFACT", tail=soa + sob)
    A, B = np.load(ta, allow_pickle=True), np.load(tb, allow_pickle=True)
    ia = np.where(A["E_ts"].astype(np.int64) == int(ts[E]))[0]
    ib = np.where(B["E_ts"].astype(np.int64) == int(ts[E]))[0]
    if not (len(ia) and len(ib)):
        return res("R-TIM-5", "INVALID_NOARTIFACT", why="anchor absent from one axis", tail=soa + sob)
    qa = float(A["qvk"][int(ia[0]), j])
    qb = float(B["qvk"][int(ib[0]), j])
    # control: the NEXT anchor's window does contain row E under BOTH definitions, so it must move either way
    nxt = int(np.where(A["E_ts"].astype(np.int64) == int(ts[E + 48]))[0][0])
    ctrl_a, ctrl_b = float(A["qvk"][nxt, j]), float(B["qvk"][nxt, j])
    if qa != qb:
        return res("R-TIM-5", "GREEN", "row E moves the anchor's own member statistic", {"qvk_a": qa, "qvk_b": qb})
    return res("R-TIM-5", "RED_CORRECT", "row E moves the anchor's own member statistic qvk",
               {"qvk_a": qa, "qvk_b": qb, "control_next_anchor_a": ctrl_a, "control_next_anchor_b": ctrl_b,
                "control_moved": ctrl_a != ctrl_b},
               why=("log_qv was raised on the anchor bar E of one name and NOTHING else changed, yet that anchor's own "
                    "qvk is bit-identical: the legacy member window is rows [E-2016, E-1] (pod_dlw_targets_raw.py L88, "
                    "S = max(E-TRAIL, 0), half-open at E), so the bar closing AT the anchor -- which the producer does "
                    "use (shadow_loop_v3.py L365, rows [E-2015, E]) -- is invisible to it. Positive control: the NEXT "
                    "anchor, whose window contains row E under both definitions, does move."), tail=soa + sob)


def main():
    rc = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.abspath(__file__)),
          "utc_start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
          "python": sys.version.split()[0], "numpy": np.__version__,
          "builders_under_test": {os.path.relpath(p, REPO): sha(p) for p in (KING_BUILDER, DLW_FEA_BUILDER, DLW_TGT_BUILDER)},
          "fixture_spec": {"T_rows": T_ROWS, "NW": NW, "bar_s": BAR_S, "anchor_s": ANCHOR_S, "epoch0": EPOCH0,
                           "channels": CHN, "cache_dtype": "float16", "n_grid_anchors": len(grid_rows()),
                           "note": "real-shape, synthetic values; BTCUSDT present; panel Y4 derived from the cache"},
          "shells_out": False, "network": False, "cases": []}
    for cid, item, statement, fn in CASES:
        try:
            r = fn(TMP)
        except BaseException:
            r = res(cid, "INVALID_CRASH", error=traceback.format_exc())
        r["item"] = item
        r["asserted_correct_behaviour"] = statement
        rc["cases"].append(r)
        print("%-10s %-16s %s" % (cid, item, r["outcome"]), flush=True)
    tally = {}
    for c in rc["cases"]:
        tally[c["outcome"]] = tally.get(c["outcome"], 0) + 1
    rc["tally"] = tally
    rc["valid_reds"] = [c["case"] for c in rc["cases"] if c["outcome"] == "RED_CORRECT"]
    rc["green"] = [c["case"] for c in rc["cases"] if c["outcome"] == "GREEN"]
    rc["invalid"] = [c["case"] for c in rc["cases"] if c["outcome"].startswith("INVALID")]
    rc["utc_end"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rc["wall_s"] = round(time.time() - T0, 1)
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    json.dump(rc, open(OUT, "w"), indent=1, default=float)
    print("SUMMARY tally=%s valid_reds=%s green=%s invalid=%s wall=%.1fs"
          % (tally, rc["valid_reds"], rc["green"], rc["invalid"], rc["wall_s"]), flush=True)
    return 0   # the assertion matrix is the result, not the exit code


if __name__ == "__main__":
    sys.exit(main())
