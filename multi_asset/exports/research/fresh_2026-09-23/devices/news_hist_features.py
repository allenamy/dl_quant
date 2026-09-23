"""NEWS historical feature build — the PRODUCER'S OWN feature code run anchor by anchor on history.

AMENDMENT 1 (lead, 2026-09-23): training features = the feature code production runs today, unmodified,
replayed on history; D2/D3/D10 reproduced as production does. This module never re-implements a feature:
  * King 82 columns / member screen / fund values: the literal source lines of
    ~/wide_shadow/shadow_loop_v3.py (sha 6080073b) L486-L553 are compiled into a function body
    (lines asserted by sha + boundary text); inputs = the 40-day rolling window the producer would hold
    at A (11520 rows ending at A), f16 cache values exactly as stored.
  * F10 171 columns: the production mini pipeline of fea171/combo_stage.py (sha fb5a9407) L147-L185:
    same mini cache (the same 11520-row window), same targets (members = current pm for every anchor,
    D2), same btcv function (_btcv_series, AST-extracted verbatim), same funding panel (last row only),
    then the production dlw_features.py (29ae6a98) and f8_higher_order_features.build (2c500c7a) run
    as subprocesses with the same F171_* environment, exactly like combo_stage L174-178.
  * Candidates (AMENDMENT 1 item 3): columns outside (legal mask at A ∧ crypto) are NaN in the window,
    i.e. the producer is replayed with fetch list = candidates; the member screen is the producer's.
Hole cells (holefix2r list: bars with no official source, synthetic in the research cache) are NaN:
a live producer never ingests synthetic bars.
"""
import os, sys, io, ast, json, time, hashlib, subprocess, tempfile, shutil, types
import numpy as np

W = "/dev/shm/news_2026-09-23"
PROD = f"{W}/producer"
SHADOW_SRC = f"{PROD}/shadow_loop_v3.py"; SHADOW_SHA = "6080073964bffc621c893915b16f71ecafe093194f0b99a66a4463ee12c74e61"
COMBO_SRC = f"{PROD}/fea171/combo_stage.py"; COMBO_SHA = "fb5a94074583b328b949cd08767c031d9eb705fbdc23d6a371d9bd657b3ca4a8"
DLW_SRC = f"{PROD}/fea171/dlw_features.py"; DLW_SHA = "29ae6a985d891e56340378bb432c0370e914b93709eec44f54592472e4d20a76"
F8_SRC = f"{PROD}/fea171/f8_higher_order_features.py"; F8_SHA = "2c500c7ad2bb0f5ddccf431021df50a106a39f4d228bd6cf2d074c5c12f66a5f"
XSYMS = f"{PROD}/fea171/xfer_syms.npz"; XREF = f"{PROD}/fea171/xfer_ref.npz"
CACHE_ROWS = 11520  # shadow_loop_v3.py L207


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def _king_block():
    src = open(SHADOW_SRC, "rb").read(); assert hashlib.sha256(src).hexdigest() == SHADOW_SHA
    lines = src.decode().split("\n")
    # L486..L553 (1-based): 'diag.phase("feature_inference")' .. 'X = FE_ANCH[:, keep]'
    assert lines[485].strip() == 'diag.phase("feature_inference")' and lines[552].strip() == "X = FE_ANCH[:, keep]", (lines[485], lines[552])
    body = "\n".join(lines[485:553])
    code = ("def king_block(st, anchor, P, cfg, row_of, base, diag, append_log):\n" + body +
            "\n    return {'m': m, 'FE_ANCH': FE_ANCH, 'X': X, 'fe_v': fe_v, 'fn_v': fn_v, 'iv_v': iv_v, 'base_vals': base_vals, 'qvm': qvm, 'ai': ai, 'wstat': wstat}\n")
    ns = {"np": np}
    wl = [l for l in lines if l.startswith("WINS = ")]; assert wl == ["WINS = (48, 288, 864, 2016, 8640)"], wl
    exec(wl[0], ns)
    exec(compile(code, SHADOW_SRC + ":L486-L553", "exec"), ns)
    return ns["king_block"]


def _combo_funcs():
    raw = open(COMBO_SRC, "rb").read(); assert hashlib.sha256(raw).hexdigest() == COMBO_SHA
    t = ast.parse(raw)
    t.body = [x for x in t.body if isinstance(x, ast.FunctionDef) and x.name == "_btcv_series"]
    assert len(t.body) == 1
    ns = {"np": np}
    exec(compile(t, COMBO_SRC, "exec"), ns)
    return ns


class _Diag:
    def phase(self, name): pass


class _St:
    pass


def replay_anchor(A, cd, ts, syms, chn, cand, ema, ledger, P, cfg, work, holes=None, keep_mini=False, cols=None):
    """Features the producer would compute at anchor A with fetch list = candidates.
    cd: full cache (T,829,7) f16 (mmap ok), hole cells already NaN in `cd` view provided by caller.
    ema/ledger: producer-caliber funding state AFTER processing events <= A (dicts name -> state/rows).
    Returns dict with King FE_ANCH/X78, members m, fe_v/fn_v, X82 (f16) and F89 (f32) rows for m."""
    king_block = _king_block(); cf = _combo_funcs()
    ia = int(np.searchsorted(ts, A)); assert ts[ia] == A
    i0 = max(ia + 1 - CACHE_ROWS, 0)                           # producer started at cache start for the first 40 days
    RD = np.array(cd[i0:ia + 1], dtype=np.float16)             # rolling cache the producer holds at A
    if holes is not None:                                      # synthetic hole bars are never ingested live
        hr, hc = holes; k0 = int(np.searchsorted(hr, i0)); k1 = int(np.searchsorted(hr, ia + 1))
        RD[hr[k0:k1] - i0, hc[k0:k1], :] = np.nan
    RD[:, ~cand, :] = np.nan                                   # fetch list = candidates
    rts = ts[i0:ia + 1].astype(np.int64)
    # ---- King (shadow_loop_v3 L486-L553 verbatim) ----
    st = _St(); st.cd = RD; st.live = [syms[j] for j in np.flatnonzero(cand)]; st.sym_idx = {s: j for j, s in enumerate(syms)}
    st.ledger = ledger; st.ema = ema; st.NW = len(syms)
    row_of = {int(t): i for i, t in enumerate(rts)}
    logs = []
    out = king_block(st, A, P, cfg, row_of, list(st.live), _Diag(), logs.append)
    if out is None:
        return {"skip": logs}
    m = out["m"]
    # ---- F10 mini (combo_stage.py L147-L185 verbatim semantics) ----
    mini_root = tempfile.mkdtemp(prefix=f"mini-{A}-", dir=work); MINI = f"{mini_root}/mini"
    try:
        pm = np.array(m, np.int64)
        _symbols = np.load(XSYMS, allow_pickle=True)["symbols"]; _channels = np.load(XSYMS, allow_pickle=True)["ch"]
        assert [str(s) for s in _symbols] == syms and [str(c) for c in _channels] == chn
        if cols == "members":      # column-restricted replay; admissible only after the bitwise check vs full
            keep = np.array(sorted(set(pm.tolist()) | {syms.index("BTCUSDT")}), np.int64)
        else:
            keep = np.arange(len(syms), dtype=np.int64)
        loc = {int(g): i for i, g in enumerate(keep)}
        RDm = RD[:, keep, :] if cols == "members" else RD
        sy_m = _symbols[keep]; pm_l = np.array([loc[int(g)] for g in pm], np.int64)
        e_rows = [i for i in range(len(rts)) if rts[i] % 14400 == 0 and i >= 48]
        ms_arr = np.empty(len(e_rows), object)
        for i in range(len(e_rows)): ms_arr[i] = pm_l
        zz = np.zeros((len(e_rows), len(keep)), np.float32)
        os.makedirs(f"{MINI}/data", exist_ok=True); os.makedirs(f"{MINI}/results", exist_ok=True); os.makedirs(f"{MINI}/preds", exist_ok=True)
        with np.load(XREF, allow_pickle=True) as r:
            cf["_symbols"] = sy_m; cf["_source_snapshot"] = {"reference": {"E_ts": r["E_ts"], "btcv": r["btcv"]}}
        np.savez(f"{MINI}/cache.npz", ts=rts, data=RDm, symbols=sy_m, ch=_channels)
        np.savez(f"{MINI}/data/dlw_targets.npz", E_row=np.array(e_rows), E_ts=rts[e_rows], members=ms_arr,
                 y4s=zz, YR4s=zz, YRZ=zz, yrs=np.array([time.gmtime(int(t)).tm_year for t in rts[e_rows]]),
                 qvk=zz, btcv=cf["_btcv_series"](rts, RDm, e_rows), has_panel=np.ones(len(e_rows), bool),
                 symbols=sy_m, y4old=zz, meta_json="{}")
        fe = np.zeros((len(e_rows), len(keep)), np.float32); fn = np.zeros((len(e_rows), len(keep)), np.float32)
        scol_of = {str(s_): j for j, s_ in enumerate(sy_m)}
        for s_, est in ema.items():
            j = scol_of.get(s_)
            if j is not None and isinstance(est, dict) and "acc" in est:
                fe[-1, j] = float(est["acc"])
        for s_, rows_ in ledger.items():
            j = scol_of.get(s_)
            if j is not None and rows_:
                fn[-1, j] = float(rows_[-1][1])
        np.savez(f"{mini_root}/xfer_panel_live.npz", ts=rts[e_rows], f_fund_ema=fe, f_fund_now=fn)
        env = dict(os.environ)
        env.update({"F171_CACHE": f"{MINI}/cache.npz", "F171_TARGETS": f"{MINI}/data/dlw_targets.npz", "F171_OUT": MINI,
                    "F171_FEA82": f"{MINI}/data/dlw_fea82.npz", "F171_PANEL": f"{mini_root}/xfer_panel_live.npz"})
        HERE = f"{PROD}/fea171"; PY = sys.executable
        r1 = subprocess.run([PY, f"{HERE}/dlw_features.py"], env=env, capture_output=True, text=True, cwd=HERE)
        assert r1.returncode == 0, r1.stderr[-800:]
        r2 = subprocess.run([PY, "-c", f"import os,sys; sys.path.insert(0,'{HERE}'); os.chdir('{HERE}'); import f8_higher_order_features as m; m.build()"], env=env, capture_output=True, text=True)
        assert r2.returncode == 0, r2.stderr[-800:]
        F82 = np.load(f"{MINI}/data/dlw_fea82.npz", allow_pickle=True); F89 = np.load(f"{MINI}/data/f8_fea89.npz", allow_pickle=True)
        T9 = np.load(f"{MINI}/data/dlw_targets.npz", allow_pickle=True)
        m82 = json.loads(str(F82["meta_json"])); m89 = json.loads(str(F89["meta_json"]))
        assert m82["cache_sha256"] == sha(f"{MINI}/cache.npz") and m89["fea82_sha256"] == sha(f"{MINI}/data/dlw_fea82.npz")
        assert m82["self_sha256"] == DLW_SHA and m89["self_sha256"] == F8_SHA
        ets = T9["E_ts"].astype(np.int64); a_i = int(np.where(ets == A)[0][0])
        pa2 = F82["pair_a"].astype(np.int64); ps2 = F82["pair_s"].astype(np.int64); rowm = (pa2 == a_i)
        assert np.array_equal(F89["pair_a"], F82["pair_a"]) and np.array_equal(F89["pair_s"], F82["pair_s"])
        X82 = F82["X"][rowm]; X89 = F89["X"][rowm]; scol = keep[ps2[rowm]]
        assert np.array_equal(scol, pm), "F10 rows not in member order"
        res = {"m": pm, "king_FE": out["FE_ANCH"], "king_X78": out["X"], "fe_v": out["fe_v"][pm], "fn_v": out["fn_v"][pm],
               "iv_v": out["iv_v"][pm], "qvm": out["qvm"][pm], "rev24": out["wstat"](0, 288, "sum")[pm],
               "base_vals": out["base_vals"], "X82": X82, "X89": X89}
        return res
    finally:
        if not keep_mini:
            shutil.rmtree(mini_root, ignore_errors=True)
