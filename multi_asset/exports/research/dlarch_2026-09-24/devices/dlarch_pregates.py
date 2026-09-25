#!/usr/bin/env python3
"""dlarch_pregates.py — PREREG docs/PREREG_dlarch_pregates_2026-09-25.md.

Four CPU pre-gates for the design document's step-3 / step-2 candidates. A pre-gate answers ONE question:
"is the information this candidate wants visible to a cheap model?" Per lead's ruling at the top of the
design document, a pre-gate is NECESSARY-BUT-NOT-SUFFICIENT evidence: passing does not admit a candidate
and failing does not reject one (it only means "I have no cheap evidence"). None of these produce an
admission, and none of them is a book-layer number.

  BASE  X171                                                      171 cols
  A4a   X171 minus the 40 raw-value columns of X82                 131 cols   (REVERSE gate: >= -0.001)
  A4b   X171 + 10 "this name vs its own trailing 540 anchors" z     181 cols
  A1    X171 + 6 within-comparable-group rank columns              177 cols
  A2    X171 + 6 shape columns                                     177 cols
  T6a   X171 + King's within-anchor rank                           172 cols
  PL    X171 + A1's 6 columns permuted within the anchor, 3 seeds   177 cols  (column-count placebo)

Target, folds, model params and the IC readout are imported or copied verbatim from existing pinned
devices (news2_train_king.py L47/L49, king_folds.fold_rows, news2_diag1_score_ic.ic_series). Test years
2023/2024/2025 only — 2026 is excluded because it overlaps the selection sample, so these numbers can be
compared with F8's 4-fold numbers only qualitatively, never cell by cell.

Caliber: y4s, SCORE layer. NOT the v4 RAW accounting caliber (KB-05). Never quote as a return.

READ-ONLY. No GPU, no venue calls, no writes under /dev/shm.

usage: env -i PATH=/usr/bin:/bin HOME=/root OMP_NUM_THREADS=8 /workspace/venv/bin/python -B \
         dlarch_pregates.py PATH,HOME,LC_CTYPE,OMP_NUM_THREADS <outdir> [arms]
"""
import os, sys, ast, json, time, hashlib, calendar, gc

import numpy as np

W = "/dev/shm/news2_2026-09-23"
TREE = f"{W}/treeNC5_deploy/fea171"
LAB = "/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz"
LAB_SHA = "ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62"
H4 = 14400
EMBARGO = 60                     # king_folds default, same as news2_train_king.py
MIN_GOOD = 50                    # news2_train_king.py L47
MIN_NAMES = 20                   # news2_diag1_score_ic.py
TEST_YEARS = (2023, 2024, 2025)  # 2026 excluded on purpose (selection overlap)
RIDGE_ALPHA = 1.0
LGB_PARAMS = dict(n_estimators=400, learning_rate=.05, num_leaves=63, subsample=.8,
                  colsample_bytree=.8, random_state=0, n_jobs=8, verbose=-1)
SELF_WIN = 540                   # 90 days of 4h anchors
SELF_MIN = 120
GROUP_DECILES = 10
GROUP_MIN = 8
PL_SEEDS = 3
RNG_BASE = 20260925
GATE_DELTA = 0.003               # F8 family gate
GATE_A4A = -0.001                # reverse gate for the column-dropping arm
BASE_IC_SANITY = (0.03, 0.09)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))
def log(*a): print(time.strftime("%H:%M:%S", time.gmtime()), *a, flush=True)


def literals_from(path, want_sha, names, fn=None):
    """Evaluate named module-level (or in-function) literal assignments from a sha-pinned source."""
    got = sha(path)
    assert got == want_sha, f"{os.path.basename(path)} sha {got[:16]} != pinned {want_sha[:16]}"
    tree = ast.parse(open(path, "rb").read(), path)
    scope = tree
    if fn is not None:
        f = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == fn]
        assert len(f) == 1, f"{fn}() not found"
        scope = f[0]
    found = {}
    for node in ast.walk(scope):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            nm = node.targets[0].id
            if nm in names and nm not in found: found[nm] = node.value
    ns = {"__builtins__": {}}
    for nm in names:
        assert nm in found, f"assignment {nm} not found in {os.path.basename(path)}"
        ns[nm] = eval(compile(ast.Expression(found[nm]), path, "eval"), ns)
    return ns, got


def x82_names():
    """Rebuild X82's 82 column names exactly as dlw_features.py L47-L76 builds them."""
    want = json.load(open(f"{W}/receipts/P2B_FEATURES.json"))["tree_outputs"]["fea171/dlw_features.py"]
    ns, got = literals_from(f"{TREE}/dlw_features.py", want, ["CHN", "WINS"])
    CHN, WINS = ns["CHN"], list(ns["WINS"])
    val = []
    for nm in CHN:
        for w in WINS: val.append(f"{nm}_sum_{w}" if nm == CHN[0] else f"{nm}_mean_{w}")
    for w in WINS: val.append(f"vol_{w}")
    names = [n + s for n in val for s in ("_v", "_r")] + ["fund_ema", "fund_now"]
    assert len(names) == 82, len(names)
    return names, got, CHN, WINS


def x89_names():
    want = json.load(open(f"{W}/receipts/P2B_FEATURES.json"))["tree_outputs"]["fea171/f8_higher_order_features.py"]
    ns, got = literals_from(f"{TREE}/f8_higher_order_features.py", want,
                            ["order", "all_rank_names", "H_names", "I_names", "names"], fn="build")
    nm = list(ns["names"]); assert len(nm) == 89, len(nm)
    return nm, got


def anchor_rank(v, ok):
    """within-anchor uniform rank in [-0.5, 0.5] over ok entries; 0 elsewhere."""
    from scipy.stats import rankdata
    out = np.zeros(len(v), np.float32)
    n = int(ok.sum())
    if n >= 2: out[ok] = (rankdata(v[ok]) / (n - 1) - .5).astype(np.float32)
    return out


REVERSE_ARMS = ("A4a",)          # arms that REMOVE columns: "not worse" is the bar, not "positive"


def gate_verdict(arm, r, b, pl, test_years):
    """The gate EXACTLY as the pre-registration words it (docs/PREREG_dlarch_pregates_2026-09-25.md §5).

    Forward arms:  delta_all >= +0.003  AND  >= 2/3 years with delta_year > 0  AND beats the placebo.
    Reverse arms (they DROP columns): the prereg says "ΔIC >= -0.001 且逐年 >= 2/3 不劣" -- "不劣"
    ("not worse"), NOT "positive". So the per-year test is `delta_year >= -0.001`, the same threshold,
    and the placebo condition does not apply (a dropped column cannot be a free column).

    E-0924-DLARCH-E: the first implementation used `delta_year > 0` for BOTH directions. On a forward
    gate the two readings coincide; on a reverse gate they do not, and A4a was judged FAIL on a test its
    own pre-registered wording did not ask for. lead ruled (2026-09-24) that the frozen WORDS are the
    criterion and the code is its implementation, so the code is the defect. Fixed here, one place only.
    """
    rev = arm in REVERSE_ARMS
    thr = GATE_A4A if rev else GATE_DELTA
    g = {"direction": "reverse (drops columns)" if rev else "forward (adds columns)",
         "per_year_test": f"delta_year >= {GATE_A4A}" if rev else "delta_year > 0"}
    for mdl in ("ridge", "lgbm"):
        d = r[f"{mdl}_ic_all"] - b[f"{mdl}_ic_all"]
        yrs = [r["years"][str(y)][f"{mdl}_ic"] - b["years"][str(y)][f"{mdl}_ic"] for y in test_years]
        ok_year = [(v >= GATE_A4A) if rev else (v > 0) for v in yrs]
        g[mdl] = {"delta_ic_all": d, "delta_by_year": yrs, "threshold": thr,
                  "years_positive": int(sum(1 for v in yrs if v > 0)),
                  "years_meeting_per_year_test": int(sum(ok_year)),
                  "meets": bool(d >= thr), "years_ok": bool(sum(ok_year) >= 2)}
        if pl:
            pld = [q[f"{mdl}_ic_all"] - b[f"{mdl}_ic_all"] for q in pl]
            g[mdl]["placebo_deltas"] = pld; g[mdl]["placebo_max"] = max(pld)
            g[mdl]["beats_placebo"] = bool(d > max(pld))
    both = all(g[m]["meets"] and g[m]["years_ok"] for m in ("ridge", "lgbm"))
    allyr = all(g[m]["years_meeting_per_year_test"] == len(test_years) for m in ("ridge", "lgbm"))
    bp = True if rev else all(g[m].get("beats_placebo", True) for m in ("ridge", "lgbm"))
    g["VERDICT"] = ("PASS" if (both and allyr and bp) else
                    "PASS_CONDITIONAL" if (both and bp) else
                    "INDISTINGUISHABLE_FROM_PLACEBO" if (both and not bp) else "FAIL")
    return g


def main():
    assert not sorted(set(os.environ) - set(sys.argv[1].split(","))), f"env outside whitelist: {sorted(set(os.environ) - set(sys.argv[1].split(',')))}"
    outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
    want_arms = sys.argv[3].split(",") if len(sys.argv) > 3 else None
    sys.path.insert(0, f"{W}/devices")
    from king_folds import fold_rows
    from news2_diag1_score_ic import ic_series
    from scipy.stats import rankdata
    from sklearn.linear_model import Ridge
    import lightgbm as lgb

    rec = {"device": "dlarch_pregates.py", "self_sha256": sha(os.path.abspath(__file__)),
           "prereg": {"path": "docs/PREREG_dlarch_pregates_2026-09-25.md"},
           "caliber": {"label": "dlw_targets.npz y4s, SCORE layer; NOT v4 RAW accounting caliber (KB-05)",
                       "never": "do not quote as a return or as book-layer evidence"},
           "test_years": list(TEST_YEARS), "embargo_anchors": EMBARGO,
           "lgb_params": LGB_PARAMS, "ridge_alpha": RIDGE_ALPHA,
           "note_vs_F8": "3 folds here vs F8's 4 (2026 excluded) -> qualitative comparison only",
           "utc_start": iso(time.time()), "inputs": {}, "arms": {}, "gates": {}, "checks": {}}

    log("hashing inputs")
    fpath = f"{W}/work/NEWS_FEATURES.npz"; kpath = f"{W}/work/king/KING_OOF.npz"
    fsha = sha(fpath)
    assert json.load(open(f"{W}/receipts/P2B_FEATURES.json"))["sha256"] == fsha
    assert sha(LAB) == LAB_SHA
    rec["inputs"].update({fpath: fsha, LAB: LAB_SHA, kpath: sha(kpath),
                          f"{W}/devices/king_folds.py": sha(f"{W}/devices/king_folds.py"),
                          f"{W}/devices/news2_diag1_score_ic.py": sha(f"{W}/devices/news2_diag1_score_ic.py")})

    F = np.load(fpath); lab = np.load(LAB, allow_pickle=True); K = np.load(kpath)
    a = F["anchors"].astype(np.int64); syms = F["symbols"]; NA, NW = len(a), len(syms)
    assert np.all(np.diff(a) == H4), "anchor grid not contiguous 4h"
    ya = lab["E_ts"].astype(np.int64); Y = lab["y4s"]
    assert np.array_equal(lab["symbols"], syms) and np.array_equal(K["E_ts"].astype(np.int64), a)
    off = F["off"]; cnt = F["count"]; ps = F["m"].astype(np.int64)
    pa = np.repeat(np.arange(NA), cnt).astype(np.int64)
    NP = len(pa); assert NP == int(off[-1])
    iy = np.searchsorted(ya, a); lab_ok = (iy < len(ya)) & (ya[np.minimum(iy, len(ya) - 1)] == a)
    n82, sha82, CHN, WINS = x82_names(); n89, sha89 = x89_names()
    rec["inputs"][f"{TREE}/dlw_features.py"] = sha82; rec["inputs"][f"{TREE}/f8_higher_order_features.py"] = sha89
    names171 = n82 + n89
    col = {nm: i for i, nm in enumerate(names171)}

    def vn(ch, w, suf):
        """X82 column name: dlw_features.py L47-L57 uses "_sum_" for CHN[0] (ret5), "_mean_" for the other
        channels, and a bare "vol_{w}" for the five volatility columns; every quantity then gets _v and _r."""
        if ch == "vol": base = f"vol_{w}"
        elif ch == CHN[0]: base = f"{ch}_sum_{w}"
        else: base = f"{ch}_mean_{w}"
        return f"{base}_{suf}"
    log(f"n_pairs {NP} anchors {NA} syms {NW}; CHN {CHN} WINS {WINS}")

    # ── target: news2_train_king.py L44-L47 verbatim ──
    ylong = np.full(NP, np.nan, np.float32)
    good_mask = lab_ok[pa]
    ylong[good_mask] = Y[iy[pa[good_mask]], ps[good_mask]]
    target = np.full(NP, np.nan, np.float32)
    st = off.astype(np.int64)
    for i in range(NA):
        sl = slice(st[i], st[i + 1]); v = ylong[sl]; ok = np.isfinite(v)
        if ok.sum() >= MIN_GOOD:
            idx = np.flatnonzero(ok) + st[i]
            target[idx] = (rankdata(v[ok]) / max(int(ok.sum()) - 1, 1) - .5).astype(np.float32)
    rec["checks"]["target"] = {"finite_pairs": int(np.isfinite(target).sum()), "n_pairs": int(NP),
                              "anchors_with_target": int(sum(1 for i in range(NA) if np.isfinite(target[st[i]:st[i + 1]]).any()))}
    log("target", json.dumps(rec["checks"]["target"]))

    X = np.concatenate([F["X82"], F["X89"]], 1)
    assert X.shape == (NP, 171) and np.isfinite(X).all()
    del F
    gc.collect()

    # ── dense helpers ──
    def dense_from_col(j):
        D = np.full((NA, NW), np.nan, np.float32); D[pa, ps] = X[:, j]; return D

    # ── A4b: 10 self-history z columns (strictly causal: window [i-540, i-1]) ──
    def build_a4b():
        qs = [vn(CHN[0], w, "v") for w in WINS] + [vn("vol", w, "v") for w in WINS]
        assert len(qs) == 10 and all(q in col for q in qs), qs
        out = np.zeros((10, NA, NW), np.float32); nan_cells = 0
        for k, q in enumerate(qs):
            D = dense_from_col(col[q])
            fin = np.isfinite(D)
            V = np.where(fin, D, 0.0).astype(np.float64)
            Cs = np.zeros((NA + 1, NW)); Cs[1:] = np.cumsum(V, 0)
            C2 = np.zeros((NA + 1, NW)); C2[1:] = np.cumsum(V * V, 0)
            Cn = np.zeros((NA + 1, NW)); Cn[1:] = np.cumsum(fin, 0)
            idx = np.arange(NA); lo = np.maximum(idx - SELF_WIN, 0)
            s = Cs[idx] - Cs[lo]; s2 = C2[idx] - C2[lo]; n = Cn[idx] - Cn[lo]   # rows < i only
            with np.errstate(invalid="ignore", divide="ignore"):
                mu = s / np.maximum(n, 1); var = np.maximum(s2 / np.maximum(n, 1) - mu * mu, 0.0)
                z = (D - mu) / (np.sqrt(var) + 1e-12)
            z = np.where((n >= SELF_MIN) & fin, z, np.nan)
            nan_cells += int((~np.isfinite(z) & fin).sum())
            out[k] = z.astype(np.float32)
            del D, fin, V, Cs, C2, Cn, s, s2, n, mu, var, z
            gc.collect()
        # explicit causality check on one random (anchor, name) with an independent slice
        rng = np.random.default_rng([RNG_BASE, 7])
        for _ in range(20):
            i = int(rng.integers(SELF_WIN + 5, NA)); j = int(rng.integers(0, NW))
            D = dense_from_col(col[qs[0]]); h = D[max(i - SELF_WIN, 0):i, j]; h = h[np.isfinite(h)]
            if len(h) >= SELF_MIN and np.isfinite(D[i, j]) and h.std() > 0:
                ref = (D[i, j] - h.mean()) / (h.std() + 1e-12)
                assert abs(ref - out[0, i, j]) <= 3e-3 * max(1.0, abs(ref)), f"A4b causality/arith mismatch {ref} vs {out[0,i,j]}"
                del D; break
            del D
        return out, [f"selfz:{q}" for q in qs], {"cells_without_enough_self_history": nan_cells,
                "finite_source_cells_per_col": int(np.isfinite(dense_from_col(col[qs[0]])).sum()),
                "note": f"a cell needs >= {SELF_MIN} finite anchors in [i-{SELF_WIN}, i-1]; short-history "
                        "cells are set to 0 by nan_to_num and are counted here, not silently zeroed"}

    # ── A1: 6 within-group rank columns (current anchor only) ──
    def build_a1():
        # dlw_features.py names the FIRST channel (ret5) with "_sum_" and every other channel with "_mean_"
        gq = [vn("log_qv", WINS[-1], "r"), vn("vol", WINS[-2], "r")]
        miss = [g for g in gq if g not in col]
        assert not miss, f"group columns missing: {miss}; available sample {names171[:6]}"
        tgt = [(vn("ret5", WINS[1], "r"), 0), (vn("ret5", WINS[3], "r"), 0), (vn("ret5", WINS[0], "r"), 0),
               (vn("ret5", WINS[1], "r"), 1), (vn("ret5", WINS[3], "r"), 1), (vn("vol", WINS[1], "r"), 0)]
        miss = [q for q, _ in tgt if q not in col]
        assert not miss, f"target columns missing: {miss}"
        out = np.zeros((6, NA, NW), np.float32); small = 0
        gcols = [X[:, col[g]] for g in gq]
        for i in range(NA):
            sl = slice(st[i], st[i + 1]); m = ps[sl]; n = m.size
            if n < 2: continue
            dec = []
            for gv in gcols:
                v = gv[sl]; r = rankdata(v) / max(n - 1, 1)
                dec.append(np.minimum((r * GROUP_DECILES).astype(int), GROUP_DECILES - 1))
            for k, (qn, gi) in enumerate(tgt):
                v = X[sl, col[qn]]; d = dec[gi]; res = np.zeros(n, np.float32)
                for g in range(GROUP_DECILES):
                    sel = d == g
                    if sel.sum() >= GROUP_MIN:
                        res[sel] = (rankdata(v[sel]) / max(int(sel.sum()) - 1, 1) - .5).astype(np.float32)
                    else:
                        small += int(sel.sum())
                out[k, i, m] = res
        return out, [f"grp:{q}@{gq[g]}" for q, g in tgt], small

    # ── A2: 6 shape columns (X82 raw values only, no 5m cache) ──
    def build_a2():
        g = lambda nm: X[:, col[nm]]
        r48, r288, r864, r2016, r8640 = [g(vn(CHN[0], w, "v")) for w in WINS]
        v288 = g(vn("vol", WINS[1], "v"))
        a1 = r48; a2 = (r288 - r48) / 5.0; a3 = (r2016 - r288) / 6.0
        raw = np.empty((6, NP), np.float32)
        raw[0] = a1 - a2
        raw[1] = a1 - 2 * a2 + a3
        raw[2] = r48 / (v288 + 1e-9)
        raw[3] = (r864 - r288) / 2.0 - a2
        raw[4] = (r8640 - r2016) / 24.0 - a3
        raw[5] = ((r48 > 0).astype(np.float32) + (r288 > 0) + (r864 > 0) + (r2016 > 0) + (r8640 > 0))
        out = np.zeros((6, NA, NW), np.float32)
        for i in range(NA):
            sl = slice(st[i], st[i + 1]); m = ps[sl]; n = m.size
            if n < 2: continue
            for k in range(6):
                v = raw[k, sl]; ok = np.isfinite(v)
                out[k, i, m] = anchor_rank(v, ok)
        return out, ["shape_accel", "shape_curv", "shape_r48_over_vol", "shape_mid_accel",
                     "shape_long_accel", "shape_nested_sign_count"], 0

    def build_king_col():
        D = np.full((1, NA, NW), np.nan, np.float32)
        P = K["P"]
        for i in range(NA):
            m = ps[st[i]:st[i + 1]]; p = P[i][m]; ok = np.isfinite(p)
            D[0, i, m] = anchor_rank(p, ok)
        return D, ["king_rank"], 0

    BUILD = {"A4b": build_a4b, "A1": build_a1, "A2": build_a2, "T6a": build_king_col}
    dense = {}; extra_names = {}; extra_diag = {}
    for k, fn in BUILD.items():
        t0 = time.monotonic(); D, nms, diag = fn()
        dense[k] = D; extra_names[k] = nms; extra_diag[k] = diag
        nz = [int((np.abs(np.nan_to_num(D[q])) > 0).sum()) for q in range(D.shape[0])]
        rec["checks"].setdefault("extra_columns", {})[k] = {
            "names": nms, "nonzero_cells": dict(zip(nms, nz)),
            "zero_cell_columns": [nms[q] for q, v in enumerate(nz) if v == 0],
            "diag": diag, "seconds": round(time.monotonic() - t0, 1)}
        log("built", k, "nonzero", nz, "diag", diag, f"{time.monotonic()-t0:.0f}s")
        assert not rec["checks"]["extra_columns"][k]["zero_cell_columns"], f"{k} has an all-zero column"

    def long_of(D, shift=0):
        """dense (q, NA, NW) -> long (NP, q); shift>0 takes the value from anchor i-shift (staleness test)."""
        q = D.shape[0]; out = np.zeros((NP, q), np.float32)
        src = pa - shift
        ok = src >= 0
        for k in range(q):
            out[ok, k] = np.nan_to_num(D[k][src[ok], ps[ok]])
        return out

    # ── arm definitions ──
    value_cols = [col[n] for n in n82 if n.endswith("_v")]
    assert len(value_cols) == 40, len(value_cols)
    keep_a4a = [j for j in range(171) if j not in set(value_cols)]
    assert len(keep_a4a) == 131, len(keep_a4a)

    def arm_matrix(arm, shift=0):
        if arm == "BASE": return X, list(range(171)), []
        if arm == "A4a": return X[:, keep_a4a], keep_a4a, []
        if arm == "Z6":
            # RED-CAPABILITY half 1: six all-zero columns. For Ridge this MUST give Delta == 0 (a zero
            # column cannot change a linear fit). For LGBM it need NOT: colsample_bytree=0.8 samples
            # 0.8*177 instead of 0.8*171 columns, so the column COUNT alone perturbs the fit. That
            # perturbation is exactly what a column-count placebo has to absorb, and this arm measures
            # it with zero information present.
            return np.concatenate([X, np.zeros((NP, 6), np.float32)], 1), None, ["zero"] * 6
        if arm == "RC":
            # RED-CAPABILITY half 2: six copies of the LABEL's own within-anchor rank. This is leakage
            # BY CONSTRUCTION and MUST make Delta hugely positive. If it does not, the gate cannot go
            # green and every FAIL above would be uninterpretable.
            E = np.repeat(np.nan_to_num(target)[:, None], 6, 1).astype(np.float32)
            return np.concatenate([X, E], 1), None, ["label_rank"] * 6
        if arm.startswith("PL"):
            s = int(arm[2:]); rng = np.random.default_rng([RNG_BASE, 200 + s])
            E = long_of(dense["A1"])
            for i in range(NA):
                sl = slice(st[i], st[i + 1]); n = st[i + 1] - st[i]
                if n > 1:
                    perm = rng.permutation(n)
                    E[sl] = E[sl][perm]
            return np.concatenate([X, E], 1), None, [f"PL{s}:{q}" for q in extra_names["A1"]]
        E = long_of(dense[arm], shift=shift)
        return np.concatenate([X, E], 1), None, extra_names[arm]

    def run_arm(arm, shift=0):
        XA, _, enames = arm_matrix(arm, shift)
        res = {"n_cols": int(XA.shape[1]), "extra_names": enames, "shift_anchors": shift, "years": {}}
        preds = {"ridge": np.full((NA, NW), np.nan, np.float32), "lgbm": np.full((NA, NW), np.nan, np.float32)}
        for yr in TEST_YEARS:
            s0 = calendar.timegm((yr, 1, 1, 0, 0, 0)); s1 = calendar.timegm((yr + 1, 1, 1, 0, 0, 0))
            tr_a, te_a = fold_rows(a, s0, s1, EMBARGO)
            tr = np.isin(pa, tr_a) & np.isfinite(target); te = np.isin(pa, te_a)
            assert tr.sum() > 1000 and te.sum() > 0
            # explicit out-of-fold leak assertion (fold_rows already guarantees it)
            assert a[pa[tr]].max() + H4 <= a[te_a[0]] - EMBARGO * H4, "out-of-fold leak"
            Xtr = XA[tr]; ytr = target[tr].astype(np.float64); Xte = XA[te]
            mu = Xtr.mean(0, dtype=np.float64); sd = Xtr.std(0, dtype=np.float64) + 1e-9
            t0 = time.monotonic()
            R = Ridge(alpha=RIDGE_ALPHA, fit_intercept=True)
            R.fit(((Xtr - mu) / sd).astype(np.float32), ytr)
            preds["ridge"][pa[te], ps[te]] = R.predict(((Xte - mu) / sd).astype(np.float32)).astype(np.float32)
            t1 = time.monotonic()
            G = lgb.LGBMRegressor(**LGB_PARAMS).fit(Xtr, ytr)
            preds["lgbm"][pa[te], ps[te]] = G.predict(Xte).astype(np.float32)
            t2 = time.monotonic()
            res["years"][str(yr)] = {"train_pairs": int(tr.sum()), "test_pairs": int(te.sum()),
                                     "ridge_s": round(t1 - t0, 1), "lgbm_s": round(t2 - t1, 1)}
            log(f"  {arm}{'' if not shift else f'/shift{shift}'} {yr} tr={int(tr.sum())} te={int(te.sum())} ridge {t1-t0:.0f}s lgbm {t2-t1:.0f}s")
            del Xtr, Xte, R, G; gc.collect()
        for mdl in ("ridge", "lgbm"):
            for yr in TEST_YEARS:
                s0 = calendar.timegm((yr, 1, 1, 0, 0, 0)); s1 = calendar.timegm((yr + 1, 1, 1, 0, 0, 0))
                rws = np.flatnonzero((a >= s0) & (a < s1) & lab_ok)
                ics, nn, sk = ic_series(preds[mdl], Y, rws, iy[rws])
                res["years"][str(yr)][f"{mdl}_ic"] = float(ics.mean()) if len(ics) else None
                res["years"][str(yr)][f"{mdl}_n_anchors"] = int(len(ics))
                res["years"][str(yr)][f"{mdl}_skipped"] = int(sk)
            s0 = calendar.timegm((TEST_YEARS[0], 1, 1, 0, 0, 0)); s1 = calendar.timegm((TEST_YEARS[-1] + 1, 1, 1, 0, 0, 0))
            rws = np.flatnonzero((a >= s0) & (a < s1) & lab_ok)
            ics, nn, sk = ic_series(preds[mdl], Y, rws, iy[rws])
            res[f"{mdl}_ic_all"] = float(ics.mean()) if len(ics) else None
            res[f"{mdl}_n_anchors_all"] = int(len(ics)); res[f"{mdl}_skipped_all"] = int(sk)
        if XA is not X: del XA
        gc.collect()
        return res

    # ── T6a integrity: King's OOF column must be causal per anchor, and its train/test drift reported ──
    if want_arms is None or "T6a" in (want_arms or []):
        prog = json.load(open(f"{W}/work/king/PROGRESS.json"))
        by_sha = {f["model_sha256"]: f for f in prog}
        msha = K["model_sha256"]
        bad = []; unknown = 0
        for i in range(NA):
            s = str(msha[i])
            if not s: continue
            f = by_sha.get(s)
            if f is None: unknown += 1; continue
            if f["max_train_label_end"] > int(a[i]): bad.append(iso(a[i]))
        rec["checks"]["king_column_causality"] = {
            "anchors_with_a_model": int(sum(1 for i in range(NA) if str(msha[i]))),
            "anchors_whose_model_saw_labels_at_or_after_the_anchor": len(bad),
            "first_offenders": bad[:5], "anchors_with_unrecognised_model_sha": unknown,
            "PASS": bool(not bad and unknown == 0)}
        log("king causality", json.dumps(rec["checks"]["king_column_causality"]))
        assert rec["checks"]["king_column_causality"]["PASS"], "King OOF column is not causal per anchor"
        from scipy.stats import ks_2samp
        Kl = long_of(dense["T6a"])[:, 0]
        ksr = {}
        rng = np.random.default_rng([RNG_BASE, 11])
        for yr in TEST_YEARS:
            s0 = calendar.timegm((yr, 1, 1, 0, 0, 0)); s1 = calendar.timegm((yr + 1, 1, 1, 0, 0, 0))
            tr_a, te_a = fold_rows(a, s0, s1, EMBARGO)
            tr = np.isin(pa, tr_a) & np.isfinite(target); te = np.isin(pa, te_a)
            A_ = Kl[tr]; B_ = Kl[te]
            A_ = A_[rng.choice(len(A_), min(len(A_), 200000), replace=False)]
            B_ = B_[rng.choice(len(B_), min(len(B_), 200000), replace=False)]
            ksr[str(yr)] = {"ks_stat": float(ks_2samp(A_, B_).statistic), "n_train_sub": int(len(A_)), "n_test_sub": int(len(B_))}
        rec["checks"]["king_column_train_test_KS"] = {"note": "reported, not a gate; same column produced by DIFFERENT King folds on train vs test", "by_year": ksr}
        log("king KS", json.dumps(ksr))

    ARMS = ["BASE", "A4a", "A4b", "A1", "A2", "T6a"] + [f"PL{s}" for s in range(PL_SEEDS)] + ["Z6", "RC"]
    if want_arms: ARMS = [x for x in ARMS if x in want_arms]
    for arm in ARMS:
        t0 = time.monotonic(); log("ARM", arm)
        rec["arms"][arm] = run_arm(arm)
        rec["arms"][arm]["total_seconds"] = round(time.monotonic() - t0, 1)
        log("ARM", arm, "ridge_all", rec["arms"][arm]["ridge_ic_all"], "lgbm_all", rec["arms"][arm]["lgbm_ic_all"])
        open(os.path.join(outdir, "PREGATES.partial.json"), "w").write(json.dumps(rec, indent=1, allow_nan=False))

    # ── PG-T2: is what King cannot learn still learnable? (different TARGET, same features) ──
    if want_arms is None or "T2" in (want_arms or []):
        log("PG-T2 residual target")
        Kl = long_of(dense["T6a"])[:, 0]
        t_res = np.full(NP, np.nan, np.float32); r2 = []
        for i in range(NA):
            sl = slice(st[i], st[i + 1]); t = target[sl]; k = Kl[sl]
            ok = np.isfinite(t) & np.isfinite(k)
            if ok.sum() < MIN_GOOD: continue
            A_ = np.column_stack([np.ones(int(ok.sum())), k[ok]])
            sol, _, _, _ = np.linalg.lstsq(A_, t[ok].astype(np.float64), rcond=None)
            fit = A_ @ sol; res = t[ok].astype(np.float64) - fit
            idx = np.flatnonzero(ok) + st[i]
            t_res[idx] = res.astype(np.float32)
            vt = float(np.var(t[ok]))
            if vt > 0: r2.append(1.0 - float(np.var(res)) / vt)
        r2 = np.asarray(r2, float)
        out = {"R2_target_on_king_per_anchor": {"n": int(len(r2)), "mean": float(r2.mean()),
                                                "median": float(np.median(r2)), "p90": float(np.percentile(r2, 90))},
               "finite_residual_pairs": int(np.isfinite(t_res).sum()), "years": {}}
        preds = {"ridge": np.full((NA, NW), np.nan, np.float32), "lgbm": np.full((NA, NW), np.nan, np.float32)}
        for yr in TEST_YEARS:
            s0 = calendar.timegm((yr, 1, 1, 0, 0, 0)); s1 = calendar.timegm((yr + 1, 1, 1, 0, 0, 0))
            tr_a, te_a = fold_rows(a, s0, s1, EMBARGO)
            tr = np.isin(pa, tr_a) & np.isfinite(t_res); te = np.isin(pa, te_a)
            Xtr = X[tr]; ytr = t_res[tr].astype(np.float64); Xte = X[te]
            mu = Xtr.mean(0, dtype=np.float64); sd = Xtr.std(0, dtype=np.float64) + 1e-9
            R = Ridge(alpha=RIDGE_ALPHA).fit(((Xtr - mu) / sd).astype(np.float32), ytr)
            preds["ridge"][pa[te], ps[te]] = R.predict(((Xte - mu) / sd).astype(np.float32)).astype(np.float32)
            G = lgb.LGBMRegressor(**LGB_PARAMS).fit(Xtr, ytr)
            preds["lgbm"][pa[te], ps[te]] = G.predict(Xte).astype(np.float32)
            out["years"][str(yr)] = {"train_pairs": int(tr.sum()), "test_pairs": int(te.sum())}
            log(f"  T2 {yr} tr={int(tr.sum())} done")
            del Xtr, Xte, R, G; gc.collect()
        # readout 1: IC of the residual-trained prediction against y4s (the money-relevant ordering)
        # readout 2: IC against the residual target itself (did it learn what it was asked to)
        Rres = np.full((NA, NW), np.nan, np.float32); Rres[pa, ps] = t_res
        s0 = calendar.timegm((TEST_YEARS[0], 1, 1, 0, 0, 0)); s1 = calendar.timegm((TEST_YEARS[-1] + 1, 1, 1, 0, 0, 0))
        rws = np.flatnonzero((a >= s0) & (a < s1) & lab_ok)
        for mdl in ("ridge", "lgbm"):
            i1, _, _ = ic_series(preds[mdl], Y, rws, iy[rws])
            i2, _, _ = ic_series(preds[mdl], Rres, rws, np.arange(NA)[rws])
            out[f"{mdl}_ic_vs_y4s"] = float(i1.mean()) if len(i1) else None
            out[f"{mdl}_ic_vs_residual_target"] = float(i2.mean()) if len(i2) else None
        rec["arms"]["T2_residual"] = out
        log("T2", json.dumps({k: out[k] for k in out if k.startswith(("ridge", "lgbm"))}),
            "R2", round(out["R2_target_on_king_per_anchor"]["mean"], 5))

    # ── gates ──
    if "BASE" in rec["arms"]:
        b = rec["arms"]["BASE"]
        rec["checks"]["base_ic_sanity"] = {"lgbm_ic_all": b["lgbm_ic_all"], "ridge_ic_all": b["ridge_ic_all"],
                                          "expected_range": list(BASE_IC_SANITY),
                                          "in_range": bool(BASE_IC_SANITY[0] <= b["lgbm_ic_all"] <= BASE_IC_SANITY[1])}
        log("BASE sanity", json.dumps(rec["checks"]["base_ic_sanity"]))
        pl = [rec["arms"][f"PL{s}"] for s in range(PL_SEEDS) if f"PL{s}" in rec["arms"]]
        for arm in [x for x in ("A4a", "A4b", "A1", "A2", "T6a") if x in rec["arms"]]:
            g = gate_verdict(arm, rec["arms"][arm], b, pl, TEST_YEARS)
            rec["gates"][arm] = g
            log("GATE", arm, g["VERDICT"], {m: round(g[m]["delta_ic_all"], 5) for m in ("ridge", "lgbm")})

    if all(k in rec["arms"] for k in ("BASE", "Z6", "RC")):
        b = rec["arms"]["BASE"]; z = rec["arms"]["Z6"]; c = rec["arms"]["RC"]
        rc = {}
        for mdl in ("ridge", "lgbm"):
            dz = z[f"{mdl}_ic_all"] - b[f"{mdl}_ic_all"]; dc = c[f"{mdl}_ic_all"] - b[f"{mdl}_ic_all"]
            rc[mdl] = {"zero_columns_delta": dz, "label_rank_columns_delta": dc,
                       "zero_delta_is_exactly_zero": bool(dz == 0.0),
                       "label_arm_goes_hugely_green": bool(dc >= 10 * GATE_DELTA)}
        rc["GATE_CAN_GO_GREEN"] = bool(all(rc[m]["label_arm_goes_hugely_green"] for m in ("ridge", "lgbm")))
        rc["note"] = ("Ridge's zero-column delta must be exactly 0; LGBM's need not be, because "
                      "colsample_bytree samples a fraction of the COLUMN COUNT -- that is the effect the "
                      "permuted-column placebo has to absorb, measured here with zero information present.")
        rec["checks"]["red_capability"] = rc
        log("RED-CAPABILITY", json.dumps(rc))
        assert rc["GATE_CAN_GO_GREEN"], "the gate cannot go green even on leaked labels; every FAIL is uninterpretable"

    rec["utc_end"] = iso(time.time())
    op = os.path.join(outdir, "PREGATES.json")
    tmp = op + ".tmp"; open(tmp, "w").write(json.dumps(rec, indent=1, allow_nan=False)); os.replace(tmp, op)
    v = {k: rec["gates"][k]["VERDICT"] for k in rec["gates"]}
    print(f"PREGATES DONE arms={len(rec['arms'])} verdicts={json.dumps(v)} "
          f"base_lgbm_ic={rec['arms'].get('BASE',{}).get('lgbm_ic_all')} json={sha(op)[:16]}", flush=True)


if __name__ == "__main__":
    main()
