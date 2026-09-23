"""NEW_S2 historical feature build — the PATCHED producer feature code run anchor by anchor on history.

Same contract as news_2026-09-23/devices/news_hist_features.py (AMENDMENT 1: never re-implement a
feature; run the producer's own source lines). Three differences, all of them consequences of the
NEW_S2 scope:

 1. The tree is a news2_derive_producer.py output (PATCH_RECEIPT.json in it pins every file's sha and
    every edit). TREE is set by the NEWS2_TREE env var or set_tree().
 2. The King block is located by BOUNDARY TEXT, not by hard line numbers: the ed11d731 base shifts the
    block by +2 lines and the patch changes its length. The measured span is exported for the receipt.
 3. The F10 fund panel is no longer re-implemented here. news_hist_features.py L120-L130 was a hand
    written twin of combo_stage.py L161-L173; a twin is exactly where a fix gets applied on one side
    only. This module now EXECUTES the producer's own text for that block, so D11 cannot diverge.

usage: imported by news2_global_gate.py / the P2 build; see those for the anchor loop.
"""
import os, sys, io, ast, json, time, hashlib, subprocess, tempfile, shutil, types
import numpy as np

W = os.environ.get("NEWS2_W", "/dev/shm/news2_2026-09-23")
TREE = os.environ.get("NEWS2_TREE", f"{W}/producer_v2")
CACHE_ROWS = 11520  # shadow_loop_v3.py L207

SHADOW_SRC = COMBO_SRC = DLW_SRC = F8_SRC = XSYMS = XREF = None
SHADOW_SHA = COMBO_SHA = DLW_SHA = F8_SHA = None
KING_SPAN = None


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def set_tree(tree):
    """Point the module at a patched tree and pin every source sha from its own PATCH_RECEIPT."""
    global TREE, SHADOW_SRC, COMBO_SRC, DLW_SRC, F8_SRC, XSYMS, XREF, SHADOW_SHA, COMBO_SHA, DLW_SHA, F8_SHA
    TREE = tree
    rec = json.load(open(f"{tree}/PATCH_RECEIPT.json"))
    SHADOW_SRC = f"{tree}/shadow_loop_v3.py"; SHADOW_SHA = rec["outputs"]["shadow_loop_v3.py"]
    COMBO_SRC = f"{tree}/fea171/combo_stage.py"; COMBO_SHA = rec["outputs"]["fea171/combo_stage.py"]
    DLW_SRC = f"{tree}/fea171/dlw_features.py"; DLW_SHA = rec["outputs"]["fea171/dlw_features.py"]
    F8_SRC = f"{tree}/fea171/f8_higher_order_features.py"; F8_SHA = rec["outputs"]["fea171/f8_higher_order_features.py"]
    XSYMS = f"{tree}/fea171/xfer_syms.npz"; XREF = f"{tree}/fea171/xfer_ref.npz"
    for p, h in ((SHADOW_SRC, SHADOW_SHA), (COMBO_SRC, COMBO_SHA), (DLW_SRC, DLW_SHA), (F8_SRC, F8_SHA)):
        assert sha(p) == h, ("tree file does not match its PATCH_RECEIPT", p)
    return rec


set_tree(TREE) if os.path.exists(f"{TREE}/PATCH_RECEIPT.json") else None


def _king_block():
    """Compile shadow_loop_v3 L(feature_inference)..L(X = FE_ANCH[:, keep]) verbatim."""
    global KING_SPAN
    src = open(SHADOW_SRC, "rb").read(); assert hashlib.sha256(src).hexdigest() == SHADOW_SHA
    lines = src.decode().split("\n")
    b = [i for i, l in enumerate(lines) if l.strip() == 'diag.phase("feature_inference")']
    e = [i for i, l in enumerate(lines) if l.strip() == "X = FE_ANCH[:, keep]"]
    assert len(b) == 1 and len(e) == 1, (b, e)
    KING_SPAN = (b[0] + 1, e[0] + 1)
    body = "\n".join(lines[b[0]:e[0] + 1])
    code = ("def king_block(st, anchor, P, cfg, row_of, base, diag, append_log):\n" + body +
            "\n    return {'m': m, 'FE_ANCH': FE_ANCH, 'X': X, 'fe_v': fe_v, 'fn_v': fn_v, 'iv_v': iv_v, 'base_vals': base_vals, 'qvm': qvm, 'ai': ai, 'wstat': wstat}\n")
    ns = {"np": np}
    wl = [l for l in lines if l.startswith("WINS = ")]; assert wl == ["WINS = (48, 288, 864, 2016, 8640)"], wl
    exec(wl[0], ns)
    exec(compile(code, SHADOW_SRC + f":L{KING_SPAN[0]}-L{KING_SPAN[1]}", "exec"), ns)
    return ns["king_block"]


def _combo_funcs():
    raw = open(COMBO_SRC, "rb").read(); assert hashlib.sha256(raw).hexdigest() == COMBO_SHA
    t = ast.parse(raw)
    t.body = [x for x in t.body if isinstance(x, ast.FunctionDef) and x.name == "_btcv_series"]
    assert len(t.body) == 1
    ns = {"np": np}
    exec(compile(t, COMBO_SRC, "exec"), ns)
    return ns


_FUND_BEGIN = 'scol_of = {s_: j for j, s_ in enumerate(syms_all)}\n'
_FUND_END = '    np.savez(f"{_feature_workspace.name}/xfer_panel_live.npz"'


def _fund_panel_block():
    """The producer's OWN fund-panel text (combo_stage.py), dedented; never a twin of it."""
    txt = open(COMBO_SRC).read()
    assert txt.count(_FUND_BEGIN) == 1 and txt.count(_FUND_END) == 1
    b = txt.index(_FUND_BEGIN) + len(_FUND_BEGIN)
    e = txt.index(_FUND_END, b)
    body = "\n".join(l[4:] if l.startswith("    ") else l for l in txt[b:e].split("\n"))
    first = txt[:b].count("\n") + 1
    return compile(body, COMBO_SRC + f":fund_panel@L{first}", "exec"), (first, txt[:e].count("\n"))


class _Diag:
    def phase(self, name): pass


class _St:
    pass


def replay_anchor(A, cd, ts, syms, chn, cand, ema, ledger, P, cfg, work, holes=None, keep_mini=False, cols=None):
    """Features the patched producer would compute at anchor A with fetch list = candidates."""
    king_block = _king_block(); cf = _combo_funcs(); fund_code, fund_span = _fund_panel_block()
    ia = int(np.searchsorted(ts, A)); assert ts[ia] == A
    i0 = max(ia + 1 - CACHE_ROWS, 0)
    RD = np.array(cd[i0:ia + 1], dtype=np.float16)
    if holes is not None:
        hr, hc = holes; k0 = int(np.searchsorted(hr, i0)); k1 = int(np.searchsorted(hr, ia + 1))
        RD[hr[k0:k1] - i0, hc[k0:k1], :] = np.nan
    RD[:, ~cand, :] = np.nan
    rts = ts[i0:ia + 1].astype(np.int64)
    # ---- King (shadow_loop_v3 feature block verbatim) ----
    st = _St(); st.cd = RD
    st.live = [syms[j] for j in np.flatnonzero(cand)]
    st.fetch = list(st.live)                       # ed11d731 reads st.fetch; replay fetch == candidates
    st.sym_idx = {s: j for j, s in enumerate(syms)}
    st.ledger = ledger; st.ema = ema; st.NW = len(syms)
    row_of = {int(t): i for i, t in enumerate(rts)}
    logs = []
    out = king_block(st, A, P, cfg, row_of, list(st.live), _Diag(), logs.append)
    if out is None:
        return {"skip": logs}
    m = out["m"]
    # ---- F10 mini (combo_stage.py mini pipeline) ----
    mini_root = tempfile.mkdtemp(prefix=f"mini-{A}-", dir=work); MINI = f"{mini_root}/mini"
    try:
        pm = np.array(m, np.int64)
        _symbols = np.load(XSYMS, allow_pickle=True)["symbols"]; _channels = np.load(XSYMS, allow_pickle=True)["ch"]
        assert [str(s) for s in _symbols] == syms and [str(c) for c in _channels] == chn
        if cols == "members":
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
        # fund panel: run the producer's own block (D11 lives in it)
        fe = np.zeros((len(e_rows), len(keep)), np.float32); fn = np.zeros((len(e_rows), len(keep)), np.float32)
        fns = {"np": np, "A": int(A), "NW": len(keep), "syms_all": [str(s_) for s_ in sy_m],
               "scol_of": {str(s_): j for j, s_ in enumerate(sy_m)}, "fe": fe, "fn": fn,
               "aux": {"ema": ema, "ledger_tail": ledger}}
        exec(fund_code, fns)
        fe = fns["fe"]; fn = fns["fn"]
        np.savez(f"{mini_root}/xfer_panel_live.npz", ts=rts[e_rows], f_fund_ema=fe, f_fund_now=fn)
        env = dict(os.environ)
        env.update({"F171_CACHE": f"{MINI}/cache.npz", "F171_TARGETS": f"{MINI}/data/dlw_targets.npz", "F171_OUT": MINI,
                    "F171_FEA82": f"{MINI}/data/dlw_fea82.npz", "F171_PANEL": f"{mini_root}/xfer_panel_live.npz"})
        HERE = f"{TREE}/fea171"; PY = sys.executable
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
               "base_vals": out["base_vals"], "X82": X82, "X89": X89,
               "f89_names": m89["names"], "f89_finite_share_raw": m89["finite_share_raw"],
               "btcv_anchor": float(T9["btcv"][a_i]), "btcv_nan_rows": int((~np.isfinite(T9["btcv"])).sum()),
               "king_span": KING_SPAN, "fund_span": fund_span}
        return res
    finally:
        if not keep_mini:
            shutil.rmtree(mini_root, ignore_errors=True)
