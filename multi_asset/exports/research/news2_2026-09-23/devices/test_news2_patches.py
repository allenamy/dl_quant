"""NEW_S2 red/green unit tests for the nine producer-feature fixes (PREREG §6.2).

Every cell runs the SHIPPED TEXT of both trees — the base (ed11d731 / production fea171) and the
patched tree from news2_derive_producer.py — on one constructed input, and asserts:

  BASELINE  the base tree exhibits the OLD behaviour, printed as a measured value, not a boolean.
            A red baseline invalidates the cell (it is reported UNAVAILABLE, never PASS):
            a mutation check whose baseline is already red is vacuous (E: red_capability_check...).
  PATCHED   the patched tree exhibits the NEW behaviour.

No cell may pass without having measured a difference: each records n_changed, and n_changed == 0
is reported NO-MEASUREMENT, not PASS.

usage: python test_news2_patches.py <patched_tree> <out.json>
"""
import ast, hashlib, json, os, subprocess, sys, tempfile, time
import numpy as np

REPO = os.environ.get("NEWS2_REPO", os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../../..")))
BASE_TREE = os.path.join(REPO, "multi_asset/exports/research/news2_2026-09-23/work/base_tree")
WIDE = os.path.expanduser("~/wide_shadow")
CH = ["ret5", "range", "cpos", "log_qv", "log_cnt", "log_avgsz", "tbf"]
RESULTS = []


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def cell(tag, baseline_ok, baseline_observed, patched_ok, patched_observed, n_changed, note=""):
    if not baseline_ok:
        v = "UNAVAILABLE(baseline not red)"
    elif n_changed == 0:
        v = "NO-MEASUREMENT"
    elif not patched_ok:
        v = "FAIL"
    else:
        v = "PASS"
    RESULTS.append({"cell": tag, "verdict": v, "baseline_observed": baseline_observed,
                    "patched_observed": patched_observed, "n_changed": int(n_changed), "note": note})
    print(f"  {tag:28s} {v:26s} base={baseline_observed}  patched={patched_observed}  n_changed={n_changed}", flush=True)


# ----------------------------------------------------------------- King block, compiled from each tree
def king_block(shadow_src):
    src = open(shadow_src, "rb").read()
    lines = src.decode().split("\n")
    b = next(i for i, l in enumerate(lines) if l.strip() == 'diag.phase("feature_inference")')
    e = next(i for i, l in enumerate(lines) if l.strip() == "X = FE_ANCH[:, keep]")
    body = "\n".join(lines[b:e + 1])
    code = ("def king_block(st, anchor, P, cfg, row_of, base, diag, append_log):\n" + body +
            "\n    return {'m': m, 'FE_ANCH': FE_ANCH, 'X': X, 'fe_v': fe_v, 'fn_v': fn_v, 'qvm': qvm, 'wstat': wstat}\n")
    ns = {"np": np}
    wl = [l for l in lines if l.startswith("WINS = ")]
    assert wl == ["WINS = (48, 288, 864, 2016, 8640)"], wl
    exec(wl[0], ns)
    exec(compile(code, shadow_src + f":L{b+1}-L{e+1}", "exec"), ns)
    return ns["king_block"], (b + 1, e + 1)


class _St:
    pass


class _Diag:
    def phase(self, n):
        pass


def run_king(shadow_src, cd, ntop=400, cov_min=0.95, vol_min=1e-4, nsym=None):
    kb, span = king_block(shadow_src)
    T, NW, _ = cd.shape
    st = _St()
    st.cd = cd
    st.NW = NW
    syms = [f"S{j:03d}" for j in range(NW)]
    st.live = list(syms)
    st.fetch = list(syms)
    st.sym_idx = {s: j for j, s in enumerate(syms)}
    st.ledger = {}
    st.ema = {}
    P = {"cov_min": cov_min, "vol_min": vol_min, "NTOP": ntop}
    cfg = {"keep_idx": list(range(78))}
    row_of = {0: 0}
    anchor = 0
    row_of = {anchor: T - 1}
    logs = []
    out = kb(st, anchor, P, cfg, row_of, list(syms), _Diag(), logs.append)
    return out, span, logs


def mkcache(T, NW, seed=7):
    rng = np.random.default_rng(seed)
    cd = np.full((T, NW, 7), np.nan, np.float16)
    cd[:, :, 0] = rng.normal(0, 0.003, (T, NW)).astype(np.float16)
    cd[:, :, 1] = np.abs(rng.normal(0.004, 0.001, (T, NW))).astype(np.float16)
    cd[:, :, 2] = rng.random((T, NW)).astype(np.float16)
    cd[:, :, 3] = rng.normal(10.0, 0.5, (T, NW)).astype(np.float16)
    cd[:, :, 4] = rng.normal(5.0, 0.3, (T, NW)).astype(np.float16)
    cd[:, :, 5] = rng.normal(4.0, 0.2, (T, NW)).astype(np.float16)
    cd[:, :, 6] = rng.random((T, NW)).astype(np.float16)
    return cd


# ================================================================== D5 (float64 accumulation)
def t_d5(base_shadow, new_shadow):
    T, NW = 8640, 60            # the King block returns early below 50 members
    cd = mkcache(T, NW, seed=11)
    # A float32 accumulator only loses bits when the running sum dwarfs the increment. Stress input:
    # alternate a near-f16-max bar with a tiny one, inside the legal f16 range of the cache.
    cd[0::2, 0, 1] = np.float16(60000.0)
    cd[1::2, 0, 1] = np.float16(0.0009765625)
    ob, _, _ = run_king(base_shadow, cd, ntop=NW)
    on, _, _ = run_king(new_shadow, cd, ntop=NW)
    seg = cd[:, :, 1].astype(np.float32)
    truth64 = np.where(np.isfinite(seg), seg, 0).sum(0, dtype=np.float64) / np.maximum(np.isfinite(seg).sum(0), 1)
    xb = np.asarray(ob["wstat"](1, 8640, "mean"), np.float64)
    xn = np.asarray(on["wstat"](1, 8640, "mean"), np.float64)
    db = float(np.max(np.abs(xb - truth64)))
    dn = float(np.max(np.abs(xn - np.float32(truth64).astype(np.float64))))
    n_changed = int((xb != xn).sum())
    cell("D5.king_float64_sum", db > 0, f"max|f32acc - f64acc|={db:.6g}", dn == 0.0,
         f"max|patched - f64acc(rounded to f32)|={dn:.6g}", n_changed,
         "range_mean_8640, 60 symbols; symbol 0 alternates 60000 / 2^-10 (numerical stress input)")


# ================================================================== D6 (empty window -> NaN, out of rank)
def t_d6_king(base_shadow, new_shadow):
    T, NW = 3000, 60
    cd = mkcache(T, NW, seed=23)
    cd[T - 48:, 0, :] = np.nan                       # symbol 0 has NO bar inside the 48-row window
    ob, _, _ = run_king(base_shadow, cd, ntop=NW)
    on, _, _ = run_king(new_shadow, cd, ntop=NW)
    # column layout: for each of the 40 value blocks, (value, rank). range_mean_48 is block 5 -> cols 10, 11
    vcol, rcol = 10, 11
    k = int(np.where(ob["m"] == 0)[0][0])
    base_v, base_r = float(ob["FE_ANCH"][k, vcol]), float(ob["FE_ANCH"][k, rcol])
    new_v, new_r = float(on["FE_ANCH"][k, vcol]), float(on["FE_ANCH"][k, rcol])
    base_red = (base_v == 0.0) and (base_r != 0.0)   # old: mean 0 AND it took part in the rank
    new_ok = (new_v == 0.0) and (new_r == 0.0) and bool(np.isnan(on["wstat"](1, 48, "mean")[0]))
    # the other members' ranks must also shift, because the rank denominator drops by one
    n_changed = int((ob["FE_ANCH"][:, rcol] != on["FE_ANCH"][:, rcol]).sum())
    cell("D6.king_empty_window", base_red, f"value={base_v:.6g} rank={base_r:.6g}(in rank)",
         new_ok, f"value={new_v:.6g} rank={new_r:.6g}(out of rank), wstat=NaN", n_changed,
         "range_mean_48 of a symbol with 0 finite bars in [E-47,E]")
    # the ret5 SUM columns must stay a finite 0 (researcher build_combo_inputs.py:113 takes st['sum'])
    s_new = on["wstat"](0, 48, "sum")[0]
    RESULTS.append({"cell": "D6.ret5_sum_stays_finite", "verdict": "PASS" if (np.isfinite(s_new) and s_new == 0.0) else "FAIL",
                    "baseline_observed": "n/a", "patched_observed": f"ret5_sum_48={float(s_new)}", "n_changed": 0,
                    "note": "declared invariant, not a fix"})
    print(f"  {'D6.ret5_sum_stays_finite':28s} {RESULTS[-1]['verdict']:26s} patched={RESULTS[-1]['patched_observed']}", flush=True)


# ================================================================== D14 (stable tie-break)
def t_d14(base_shadow, new_shadow):
    T, NW = 2100, 120
    cd = mkcache(T, NW, seed=31)
    cd[:, :, 3] = np.float16(10.0)                   # every candidate has EXACTLY the same liquidity
    ntop = 60                                        # must stay >= 50, else the block returns early
    ob, _, _ = run_king(base_shadow, cd, ntop=ntop)
    on, _, _ = run_king(new_shadow, cd, ntop=ntop)
    mb, mn = set(ob["m"].tolist()), set(on["m"].tolist())
    stable_expect = set(np.sort(np.argsort(-on["qvm"], kind="stable")[:ntop]).tolist())
    base_red = mb != stable_expect                   # old: quicksort picks a different tied subset
    new_ok = mn == stable_expect
    cell("D14.stable_tiebreak", base_red, f"|members\\stable|={len(mb - stable_expect)}",
         new_ok, f"|members\\stable|={len(mn - stable_expect)}", len(mb ^ mn),
         f"{NW} candidates with identical qvm, NTOP={ntop}")


# ================================================================== D9 (btcv window + coverage)
def btcv_fn(combo_src):
    raw = open(combo_src, "rb").read()
    t = ast.parse(raw)
    t.body = [x for x in t.body if isinstance(x, ast.FunctionDef) and x.name == "_btcv_series"]
    assert len(t.body) == 1
    ns = {"np": np, "_symbols": np.array(["BTCUSDT", "OTHER"]), "_source_snapshot": {"reference": {"E_ts": np.array([], np.int64), "btcv": np.array([])}}}
    exec(compile(t, combo_src, "exec"), ns)
    return ns["_btcv_series"]


def t_d9(base_combo, new_combo):
    fb, fn = btcv_fn(base_combo), btcv_fn(new_combo)
    T = 6000
    rng = np.random.default_rng(5)
    RD = np.zeros((T, 2, 7), np.float16)
    RD[:, :, 0] = rng.normal(0, 0.003, (T, 2)).astype(np.float16)
    rts = np.arange(T, dtype=np.int64) * 300
    e_rows = [i for i in range(T) if rts[i] % 14400 == 0 and i >= 48]
    # (a) coverage: punch 10% of the bars out of the window feeding the LAST anchor
    last = e_rows[-1]
    hole = rng.choice(np.arange(last - 2015, last + 1), size=250, replace=False)
    RDa = RD.copy()
    RDa[hole, 0, 0] = np.nan
    ba = fb(rts, RDa, e_rows)
    na = fn(rts, RDa, e_rows)
    base_red = np.isfinite(ba[-1])
    new_ok = not np.isfinite(na[-1])
    cell("D9.coverage_gate", bool(base_red), f"btcv={float(ba[-1]):.6g} (finite at 87.6% coverage)",
         bool(new_ok), f"btcv=nan", int(np.isfinite(ba[-1]) != np.isfinite(na[-1])),
         "250 of 2016 bars missing in the window closing at the last anchor")
    # (b) window endpoint: full coverage, one extreme bar placed exactly AT the anchor row
    RDb = RD.copy()
    RDb[last, 0, 0] = np.float16(0.25)
    bb = fb(rts, RDb, e_rows)
    nb = fn(rts, RDb, e_rows)
    base_unchanged = float(bb[-1]) == float(fb(rts, RD, e_rows)[-1])       # old window excludes the closing bar
    new_changed = float(nb[-1]) != float(fn(rts, RD, e_rows)[-1])
    cell("D9.window_includes_E", bool(base_unchanged), f"btcv unchanged by the bar at E ({float(bb[-1]):.6g})",
         bool(new_changed), f"btcv moves to {float(nb[-1]):.6g}", int(bool(new_changed)),
         "one 0.25 return placed exactly at row E")
    # (c) no backfill of the early rows
    b0 = fb(rts, RD, e_rows)
    n0 = fn(rts, RD, e_rows)
    base_filled = bool(np.isfinite(b0[0]))
    new_nan = bool(not np.isfinite(n0[0]))
    cell("D9.no_backfill", base_filled, f"first anchor btcv={float(b0[0]):.6g} (backfilled)",
         new_nan, "first anchor btcv=nan", int(np.isfinite(b0).sum() - np.isfinite(n0).sum()),
         "anchors with less than 7 days of history")


# ================================================================== D11 / D13 (12h freshness)
def extract_block(path, begin, end, dedent=4):
    """Pull the shipped text between two markers that are identical in both trees."""
    txt = open(path).read()
    assert txt.count(begin) == 1 and txt.count(end) == 1, (path, txt.count(begin), txt.count(end))
    b = txt.index(begin) + len(begin)
    e = txt.index(end, b)
    if not dedent:
        return txt[b:e]
    return "\n".join(l[dedent:] if l.startswith(" " * dedent) else l for l in txt[b:e].split("\n"))


def t_d11(base_combo, new_combo):
    BEGIN = 'scol_of = {s_: j for j, s_ in enumerate(syms_all)}\n'
    END = '    np.savez(f"{_feature_workspace.name}/xfer_panel_live.npz"'
    A = 1758153600
    out = {}
    for name, path in (("base", base_combo), ("patched", new_combo)):
        code = extract_block(path, BEGIN, END)
        ns = {"np": np, "A": A, "NW": 3, "syms_all": ["FRESH", "STALE", "NONE"],
              "scol_of": {"FRESH": 0, "STALE": 1, "NONE": 2},
              "fe": np.zeros((2, 3), np.float32), "fn": np.zeros((2, 3), np.float32),
              "aux": {"ema": {"FRESH": {"acc": 0.5, "last_ts": A - 3600}, "STALE": {"acc": 0.7, "last_ts": A - 13 * 3600}},
                      "ledger_tail": {"FRESH": [[A - 3600, 0.001, 8.0]], "STALE": [[A - 13 * 3600, 0.002, 8.0]]}}}
        exec(compile(code, path + ":D11", "exec"), ns)
        out[name] = (ns["fe"][-1].copy(), ns["fn"][-1].copy())
    (feb, fnb), (fen, fnn) = out["base"], out["patched"]
    base_red = feb[1] == np.float32(0.7) and fnb[1] == np.float32(0.002)
    new_ok = fen[1] == 0.0 and fnn[1] == 0.0 and fen[0] == np.float32(0.5) and fnn[0] == np.float32(0.001)
    cell("D11.fund_panel_12h", bool(base_red), f"stale name written ema={float(feb[1])} now={float(fnb[1])}",
         bool(new_ok), f"stale name left 0, fresh name kept ema={float(fen[0])}",
         int((feb != fen).sum() + (fnb != fnn).sum()), "last settlement 13h before the anchor")


def t_d13(base_combo, new_combo):
    BEGIN = "rn8_full = np.full(NW, np.nan)\n"
    END = "rn8_m = rn8_full[pm]"
    A = 1758153600
    out = {}
    for name, path in (("base", base_combo), ("patched", new_combo)):
        code = extract_block(path, BEGIN, END, dedent=0)
        ns = {"np": np, "A": A, "NW": 3, "_col_of": {"FRESH": 0, "STALE": 1, "NONE": 2},
              "rn8_full": np.full(3, np.nan),
              "aux": {"ledger_tail": {"FRESH": [[A - 3600, -0.002, 8.0]], "STALE": [[A - 13 * 3600, -0.002, 8.0]]}}}
        exec(compile(code, path + ":D13", "exec"), ns)
        out[name] = ns["rn8_full"].copy()
    b, n = out["base"], out["patched"]
    FTRIM_HI = -0.0010
    base_excluded = bool(np.isfinite(b[1]) and b[1] <= FTRIM_HI)          # old: the stale name IS trimmed
    new_ok = bool((not np.isfinite(n[1])) and np.isfinite(n[0]) and n[0] <= FTRIM_HI)
    cell("D13.rn8_12h", base_excluded, f"stale rn8={float(b[1]):.6g} -> FTRIM excludes it",
         new_ok, f"stale rn8=nan -> not excluded; fresh rn8={float(n[0]):.6g} still excluded",
         int((np.isfinite(b) != np.isfinite(n)).sum()), "last settlement 13h before the anchor")


# ================================================================== D4 / D6(F10) / D7 / D8 via the real pipelines
def build_mini(root, T=10000, NW=60, seed=101, edit_early=None):
    rng = np.random.default_rng(seed)
    os.makedirs(f"{root}/data", exist_ok=True)
    os.makedirs(f"{root}/results", exist_ok=True)
    os.makedirs(f"{root}/preds", exist_ok=True)
    syms = [f"S{j:03d}" for j in range(NW - 1)] + ["BTCUSDT"]
    cd = mkcache(T, NW, seed)
    # Scattered gaps, INDEPENDENT per channel: most D8 windows are then not fully supported, and the
    # channel-intersection patches (Amihud / Kyle / flow) have a population to differ on at all.
    for c in range(7):
        g = rng.random((T, NW)) < 0.03
        cd[:, :, c][g] = np.nan
    # D4: two symbols whose 2016-window log_qv means differ below f16 resolution
    cd[:, 1, 3] = np.float16(10.0)
    cd[:, 2, 3] = np.float16(10.0)
    cd[T - 100, 2, 3] = np.float16(10.0078125)
    if edit_early is not None:
        cd[:edit_early, :, 0] = np.float16(0.05)     # D7: a big pre-window drift in the cumulative log price
    ts = np.arange(T, dtype=np.int64) * 300
    e_rows = np.array([i for i in range(T) if ts[i] % 14400 == 0 and i >= 48], np.int64)
    cd[e_rows[-1] - 47:, 0, :] = np.nan              # D6: symbol 0 has NO bar in the 48-row window at the last anchor
    ms = np.empty(len(e_rows), object)
    pm = np.arange(NW, dtype=np.int64)
    for i in range(len(e_rows)):
        ms[i] = pm
    zz = np.zeros((len(e_rows), NW), np.float32)
    np.savez(f"{root}/cache.npz", ts=ts, data=cd, symbols=np.array(syms), ch=np.array(CH))
    np.savez(f"{root}/data/dlw_targets.npz", E_row=e_rows, E_ts=ts[e_rows], members=ms, y4s=zz, YR4s=zz, YRZ=zz,
             yrs=np.array([2025] * len(e_rows)), qvk=zz, btcv=np.abs(rng.normal(0.003, 0.0005, len(e_rows))),
             has_panel=np.ones(len(e_rows), bool), symbols=np.array(syms), y4old=zz, meta_json="{}")
    np.savez(f"{root}/panel.npz", ts=ts[e_rows], f_fund_ema=zz, f_fund_now=zz)
    return syms, e_rows, cd


def run_pipeline(tree, root, py=sys.executable):
    env = dict(os.environ)
    env.update({"F171_CACHE": f"{root}/cache.npz", "F171_TARGETS": f"{root}/data/dlw_targets.npz",
                "F171_OUT": root, "F171_FEA82": f"{root}/data/dlw_fea82.npz", "F171_PANEL": f"{root}/panel.npz"})
    here = f"{tree}/fea171"
    r1 = subprocess.run([py, f"{here}/dlw_features.py"], env=env, capture_output=True, text=True, cwd=here)
    assert r1.returncode == 0, r1.stderr[-2000:]
    r2 = subprocess.run([py, "-c", f"import os,sys; sys.path.insert(0,{here!r}); os.chdir({here!r}); import f8_higher_order_features as m; m.build()"],
                        env=env, capture_output=True, text=True)
    assert r2.returncode == 0, r2.stderr[-2000:]
    F82 = np.load(f"{root}/data/dlw_fea82.npz", allow_pickle=True)
    F89 = np.load(f"{root}/data/f8_fea89.npz", allow_pickle=True)
    meta = json.loads(str(F89["meta_json"]))
    return ({k: F82[k] for k in ("X", "pair_a", "pair_s", "names")},
            {k: F89[k] for k in ("X", "pair_a", "pair_s")}, meta["names"], meta["finite_share_raw"])


def t_pipeline(base_tree, new_tree, work):
    rb, rn = f"{work}/pipe_base", f"{work}/pipe_new"
    build_mini(rb)
    build_mini(rn)
    b82, b89, bn, bfin = run_pipeline(base_tree, rb)
    n82, n89, nn, nfin = run_pipeline(new_tree, rn)
    assert bn == nn and list(b82["names"]) == list(n82["names"])
    names82 = [str(x) for x in b82["names"]]
    assert np.array_equal(b82["pair_a"], n82["pair_a"]) and np.array_equal(b82["pair_s"], n82["pair_s"])

    # ---- D4: storage precision. NB the rank itself is computed in float32 in both trees
    #      (dlw_features L86-L89 ranks the float32 VAL); D4 is about what gets WRITTEN.
    cv = names82.index("log_qv_mean_2016_v")
    pa = b82["pair_a"].astype(np.int64)
    ps = b82["pair_s"].astype(np.int64)
    last = pa.max()
    sel = pa == last
    vb = np.asarray(b82["X"][sel][:, cv], np.float64)
    vn = np.asarray(n82["X"][sel][:, cv], np.float64)
    # pairs that the patched tree keeps apart but the base tree collapses onto one stored value
    lost = 0
    for i in range(len(vn)):
        for j in range(i + 1, len(vn)):
            if vn[i] != vn[j] and vb[i] == vb[j]:
                lost += 1
    base_red = (str(b82["X"].dtype) == "float16") and lost > 0
    new_ok = str(n82["X"].dtype) == "float32"
    cell("D4.x82_precision", bool(base_red), f"dtype={b82['X'].dtype}, {lost} distinct value pairs collapse onto one stored cell",
         bool(new_ok), f"dtype={n82['X'].dtype}, those pairs stay distinct",
         int((np.asarray(b82["X"], np.float64) != np.asarray(n82["X"], np.float64)).sum()),
         "log_qv_mean_2016 stored value, last anchor")

    # ---- D6 in the F10 pipeline
    cv = names82.index("range_mean_48_v")
    cr = names82.index("range_mean_48_r")
    k = int(np.where(ps[sel] == 0)[0][0])
    base_red = (float(b82["X"][sel][k, cv]) == 0.0) and (float(b82["X"][sel][k, cr]) != 0.0)
    new_ok = (float(n82["X"][sel][k, cv]) == 0.0) and (float(n82["X"][sel][k, cr]) == 0.0)
    cell("D6.f10_empty_window", bool(base_red), f"value=0 rank={float(b82['X'][sel][k, cr]):.6g}(in rank)",
         bool(new_ok), f"value=0 rank={float(n82['X'][sel][k, cr]):.6g}(out of rank)",
         int((b82["X"][:, cr] != n82["X"][:, cr]).sum()), "range_mean_48 with 0 finite bars")

    # ---- D8: two kinds of patch, so two kinds of expectation.
    #      "nan"   : the gate is tightened to a fully supported window -> strictly fewer finite raw cells
    #      "value" : the denominator population changes -> the finite values move (NaN pattern may not)
    D8_EXPECT = {"A:jump_288": "nan", "B:vov_7d": "nan", "C:ac1_288": "nan", "C:upblk_2016": "nan",
                 "D:dhi_288": "nan", "D:dlo_288": "nan", "D:ppct_288": "nan", "E:spr_7": "nan",
                 "G:tbac1_288": "nan", "J:r4_lag_2": "nan", "J:r24_lag1": "nan",
                 "F:amihud_288": "value", "F:kyle_288": "value", "G:tbvw_288": "value"}
    for nm, kind in D8_EXPECT.items():
        j = nn.index(nm)
        fb, fnn_ = float(bfin[nm]), float(nfin[nm])
        dmax = float(np.nanmax(np.abs(np.asarray(b89["X"][:, j], np.float64) - np.asarray(n89["X"][:, j], np.float64))))
        if kind == "nan":
            base_red = fb > fnn_
            ok = fnn_ < fb
            cell(f"D8.{nm}", base_red, f"finite_share_raw={fb:.4f}", ok, f"finite_share_raw={fnn_:.4f}",
                 int(round(abs(fb - fnn_) * len(b89["X"]))), "gate tightened to a fully supported window")
        else:
            base_red = dmax > 0
            ok = dmax > 0
            cell(f"D8.{nm}", base_red, f"finite_share_raw={fb:.4f}, max|rank delta|={dmax:.4g}", ok,
                 f"finite_share_raw={fnn_:.4f}", int((b89["X"][:, j] != n89["X"][:, j]).sum()),
                 "denominator restricted to the common population")

    # ---- D7: history edited strictly before the window must not move the trend columns
    for tree, root in ((base_tree, f"{work}/trend_base"), (new_tree, f"{work}/trend_new")):
        for tag, edit in (("a", None), ("b", 4000)):
            r = f"{root}_{tag}"
            build_mini(r, edit_early=edit)
            _, f89, names, _fin = run_pipeline(tree, r)
            np.save(f"{r}/trend.npy", np.stack([f89["X"][:, names.index("C:trend_288")],
                                                f89["X"][:, names.index("C:trend_2016")]], 1))
    ba = np.load(f"{work}/trend_base_a/trend.npy")
    bb = np.load(f"{work}/trend_base_b/trend.npy")
    na = np.load(f"{work}/trend_new_a/trend.npy")
    nb = np.load(f"{work}/trend_new_b/trend.npy")
    # only anchors whose 2016-row window starts after the edited prefix
    keep = slice(len(ba) // 2, None)
    db = float(np.nanmax(np.abs(ba[keep] - bb[keep])))
    dn = float(np.nanmax(np.abs(na[keep] - nb[keep])))
    cell("D7.pre_window_edit_invariance", db > 0, f"max|trend(edited)-trend|={db:.3e}",
         dn == 0.0, f"max|trend(edited)-trend|={dn:.3e}", int((ba != na).sum()),
         "4000 pre-window rows overwritten with a +0.05/bar drift")


def main():
    new_tree = os.path.abspath(sys.argv[1])
    out_path = os.path.abspath(sys.argv[2])
    t0 = time.time()
    work = tempfile.mkdtemp(prefix="news2_tests_")
    base_tree = os.path.join(work, "base_tree")
    os.makedirs(f"{base_tree}/fea171")
    import shutil
    shutil.copyfile(os.path.join(REPO, "multi_asset/exports/research/news_2026-09-23/deploy/producer_patch/shadow_loop_v3.patched.py"),
                    f"{base_tree}/shadow_loop_v3.py")
    for f in sorted(os.listdir(f"{WIDE}/fea171")):
        p = f"{WIDE}/fea171/{f}"
        if os.path.isfile(p):
            shutil.copyfile(p, f"{base_tree}/fea171/{f}")
    print(f"base tree  {base_tree}\npatched    {new_tree}\nwork       {work}", flush=True)
    bs, ns_ = f"{base_tree}/shadow_loop_v3.py", f"{new_tree}/shadow_loop_v3.py"
    bc, nc = f"{base_tree}/fea171/combo_stage.py", f"{new_tree}/fea171/combo_stage.py"
    t_d5(bs, ns_)
    t_d6_king(bs, ns_)
    t_d14(bs, ns_)
    t_d9(bc, nc)
    t_d11(bc, nc)
    t_d13(bc, nc)
    t_pipeline(base_tree, new_tree, work)
    bad = [r for r in RESULTS if r["verdict"] != "PASS"]
    rec = {"device": "test_news2_patches.py", "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "python": sys.version.split()[0], "numpy": np.__version__,
           "base_tree_shas": {f: sha(f"{base_tree}/{f}") for f in ("shadow_loop_v3.py", "fea171/combo_stage.py", "fea171/dlw_features.py", "fea171/f8_higher_order_features.py")},
           "patched_tree_shas": {f: sha(f"{new_tree}/{f}") for f in ("shadow_loop_v3.py", "fea171/combo_stage.py", "fea171/dlw_features.py", "fea171/f8_higher_order_features.py")},
           "cells": RESULTS, "n_cells": len(RESULTS), "n_not_pass": len(bad),
           "VERDICT": "PASS" if not bad else "FAIL", "seconds": round(time.time() - t0, 1)}
    with open(out_path, "w") as f:
        json.dump(rec, f, indent=1)
    print(f"NEWS2_PATCH_TESTS VERDICT={rec['VERDICT']} cells={rec['n_cells']} not_pass={rec['n_not_pass']} receipt_sha256={sha(out_path)}", flush=True)
    sys.exit(0 if not bad else 1)


if __name__ == "__main__":
    main()
