"""NC history replay core — the NEW-CONTRACT producer's own code, run anchor by anchor on history (DESIGN §A9, FREEZE b30e4afa5 + amendment 1).

Never re-implements a feature. Two blocks are EXECUTED from the patched tree (nc_derive_producer.py output, every file sha-pinned by
its PATCH_RECEIPT):
  pass 1  shadow_loop_v3.py 'diag.phase("feature_inference")' .. 'X = FE_ANCH[:, keep]'  (King block: rr channel, legal AND crypto AND
          fetched candidates, D5/D6/D14 member screen, member history record, fund as-of, fund rank base)
  pass 2  combo_stage.py 'if need:' body  (the F10 mini pipeline: member history, ret_f32, btcv on rr, fund panel as-of, the
          subprocess runs of dlw_features.py / f8_higher_order_features.py with F8_TREND_ROWS as the file declares it)
Inputs are nc_prep.py's: the rolling window = cache_crypto rows (A-40d, A] scattered onto the 829 axis (non-crypto columns NaN: the
contract never reads them), the sparse boundary table rows inside the window, the funding state as-of A (last event row + EMA state).
Replay fetch list = every crypto column: serving fetches TRADING ∩ axis ∩ crypto, which contains legal ∧ crypto (C2a), and every
read of the contract is inside legal ∧ crypto or the members' own history (DESIGN §A1; named residual: a name halted within 24 h is
legal on history but not TRADING live).
Per-anchor assertion (G3-1 continuous): the King block's rr window equals the researcher's R window bitwise."""
import os, sys, io, ast, json, time, hashlib, subprocess, tempfile, shutil, types
import numpy as np

W = os.environ.get("NC_W", "/dev/shm/nc_2026-09-23")
WK = f"{W}/work"
CACHE_ROWS = 11520
TREE = None; REC = None; SHADOW_SRC = COMBO_SRC = None; KING_SPAN = MINI_SPAN = None
_G = {}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def set_tree(tree):
    global TREE, REC, SHADOW_SRC, COMBO_SRC
    TREE = tree; REC = json.load(open(f"{tree}/PATCH_RECEIPT.json"))
    for k, h in REC["outputs"].items():
        assert sha(f"{tree}/{k}") == h, ("tree file does not match its PATCH_RECEIPT", k)
    SHADOW_SRC = f"{tree}/shadow_loop_v3.py"; COMBO_SRC = f"{tree}/fea171/combo_stage.py"
    sys.path.insert(0, f"{tree}/fea171")
    import nc_contract, tradability
    assert sha(nc_contract.__file__) == REC["outputs"]["fea171/nc_contract.py"] and sha(tradability.__file__) == REC["outputs"]["fea171/tradability.py"]
    _G["NC"], _G["TR"] = nc_contract, tradability
    return REC


def _king_block():
    global KING_SPAN
    src = open(SHADOW_SRC, "rb").read(); assert hashlib.sha256(src).hexdigest() == REC["outputs"]["shadow_loop_v3.py"]
    lines = src.decode().split("\n")
    b = [i for i, l in enumerate(lines) if l.strip() == 'diag.phase("feature_inference")']
    e = [i for i, l in enumerate(lines) if l.strip() == "X = FE_ANCH[:, keep]"]
    assert len(b) == 1 and len(e) == 1, (b, e)
    KING_SPAN = (b[0] + 1, e[0] + 1)
    code = ("def king_block(st, anchor, P, cfg, row_of, base, diag, append_log):\n" + "\n".join(lines[b[0]:e[0] + 1]) +
            "\n    return {'m': m, 'FE_ANCH': FE_ANCH, 'X': X, 'fe_v': fe_v, 'fn_v': fn_v, 'iv_v': iv_v, 'base_vals': base_vals, 'qvm': qvm,"
            " 'ai': ai, 'wstat': wstat, 'legal_now': legal_now, 'cand_now': cand_now, 'CDf0': CDf[:, :, 0], 'c7': c7, 'v7': v7, 'covr': covr}\n")
    ns = {"np": np, "NC": _G["NC"], "TR": _G["TR"]}
    wl = [l for l in lines if l.startswith("WINS = ")]; assert wl == ["WINS = (48, 288, 864, 2016, 8640)"], wl
    exec(wl[0], ns)
    exec(compile(code, SHADOW_SRC + f":L{KING_SPAN[0]}-L{KING_SPAN[1]}", "exec"), ns)
    return ns["king_block"]


def _mini_block():
    """combo_stage.py 'if need:' body, dedented, compiled with its file:line span."""
    global MINI_SPAN
    txt = open(COMBO_SRC).read(); assert hashlib.sha256(txt.encode()).hexdigest() == REC["outputs"]["fea171/combo_stage.py"]
    B = "if need:\n"; E = "# Always validate again after construction; never score a partial generation.\n"
    assert txt.count(B) == 1 and txt.count(E) == 1
    b = txt.index(B) + len(B); e = txt.index(E)
    body = "\n".join(l[4:] if l.startswith("    ") else l for l in txt[b:e].split("\n"))
    MINI_SPAN = (txt[:b].count("\n") + 1, txt[:e].count("\n"))
    return compile(body, COMBO_SRC + f":need@L{MINI_SPAN[0]}-L{MINI_SPAN[1]}", "exec")


def _combo_funcs():
    raw = open(COMBO_SRC, "rb").read()
    t = ast.parse(raw); t.body = [x for x in t.body if isinstance(x, ast.FunctionDef) and x.name == "_btcv_series"]; assert len(t.body) == 1
    ns = {"np": np}; exec(compile(t, COMBO_SRC, "exec"), ns); return ns


class Inputs:
    """nc_prep.py outputs, memory-mapped once per worker."""
    def __init__(self):
        ax = np.load(f"{WK}/axes.npz", allow_pickle=True)
        self.ts = ax["ts"].astype(np.int64); self.syms = [str(s) for s in ax["symbols"]]; self.cols = ax["crypto_cols"].astype(np.int64)
        self.anchors = ax["anchors"].astype(np.int64); self.NW = len(self.syms)
        self.C = np.load(f"{WK}/cache_crypto.npy", mmap_mode="r"); self.R = np.load(f"{WK}/R_crypto.npy", mmap_mode="r")
        b = np.load(f"{WK}/boundary.npz"); self.bt, self.bc, self.br = b["ts"].astype(np.int64), b["col"].astype(np.int32), b["raw"].astype(np.float32)
        f = np.load(f"{WK}/fund_state.npz")
        self.f_off = f["ev_off"]; self.kidx = f["kidx"]; self.f = {k: f[k] for k in ("ft", "rate", "iv", "ema", "prev")}
        self.crypto = np.zeros(self.NW, bool); self.crypto[self.cols] = True

    def window(self, A):
        ia = int(np.searchsorted(self.ts, A)); assert self.ts[ia] == A
        i0 = max(ia + 1 - CACHE_ROWS, 0)
        cd = np.full((ia + 1 - i0, self.NW, 7), np.nan, np.float16); cd[:, self.cols, :] = self.C[i0:ia + 1]
        R = np.full((ia + 1 - i0, self.NW), np.nan, np.float32); R[:, self.cols] = self.R[i0:ia + 1]
        rts = self.ts[i0:ia + 1]
        k0, k1 = np.searchsorted(self.bt, rts[0]), np.searchsorted(self.bt, rts[-1], side="right")
        return rts, cd, R, (self.bt[k0:k1], self.bc[k0:k1], self.br[k0:k1])

    def funding(self, A):
        """st.ema / st.ledger as the producer would hold them after every event <= A (only the last row is ever read)."""
        ai = int(np.searchsorted(self.anchors, A)); assert self.anchors[ai] == A
        ema, led = {}, {}
        for ci, j in enumerate(self.cols):
            k = int(self.kidx[ai, ci])
            if k < 0: continue
            i = int(self.f_off[ci]) + k
            e = self.f["ema"][i]; pv = int(self.f["prev"][i]); iv = self.f["iv"][i]
            s = self.syms[j]
            ema[s] = {"acc": None if np.isnan(e) else float(e), "last_ts": None if pv < 0 else pv}
            led[s] = [[int(self.f["ft"][i]), float(self.f["rate"][i]), None if np.isnan(iv) else float(iv)]]
        return ema, led


class _Diag:
    def phase(self, name): pass


class _St:
    pass


def pass1_anchor(I, A, P, cfg, king_block):
    """King block at A. Returns the members (also < 50), King features and the fund as-of values."""
    rts, cd, R, (bt, bc, br) = I.window(A)
    st = _St(); st.cd = cd; st.cts = rts; st.bnd_ts, st.bnd_col, st.bnd_raw = bt, bc, br
    st.crypto = I.crypto; st.fetch = [I.syms[j] for j in I.cols]; st.fetch_mask = I.crypto.copy()
    st.sym_idx = {s: j for j, s in enumerate(I.syms)}; st.syms = I.syms; st.NW = I.NW
    st.ema, st.ledger = I.funding(A)
    rec = {}
    st.record_members = lambda a, m: rec.__setitem__("members", np.asarray(m, np.int64).copy())
    row_of = {int(t): i for i, t in enumerate(rts)}; logs = []
    out = king_block(st, A, P, cfg, row_of, list(st.fetch), _Diag(), logs.append)
    res = {"members": rec.get("members"), "skip": logs}
    if out is not None:
        cd0 = out["CDf0"]
        same = (cd0.view(np.uint32) == R.view(np.uint32)) | (np.isnan(cd0) & np.isnan(R))
        assert same.all(), f"G3-1: rr window != R at {A} ({int((~same).sum())} cells)"
        m = out["m"]
        res.update({"m": m, "king_X78": out["X"], "fe_v": out["fe_v"][m], "fn_v": out["fn_v"][m], "iv_v": out["iv_v"][m], "qvm": out["qvm"][m],
                    "rev24": out["wstat"](0, 288, "sum")[m], "base_vals": out["base_vals"], "n_legal": int(out["legal_now"].sum()),
                    "n_cand": int(out["cand_now"].sum()), "screen": {"c7": out["c7"], "v7": out["v7"], "qvm": out["qvm"], "legal": out["legal_now"]}})
    return res


def pass2_anchor(I, A, members_hist, work, mini_code, cf, keep_mini=False, cols="members"):
    """combo_stage mini pipeline at A with the as-of member history. members_hist: {anchor: int64 array (829 axis)}."""
    NC = _G["NC"]
    rts, cd, R, (bt, bc, br) = I.window(A)
    pm = members_hist[A]
    e_rows = [i for i in range(len(rts)) if rts[i] % 14400 == 0 and i >= 48]
    btc = I.syms.index("BTCUSDT")
    if cols == "members":
        u = set(pm.tolist()) | {btc}
        for i in e_rows:
            a_ = int(rts[i])
            if a_ in members_hist: u |= set(members_hist[a_].tolist())
        keep = np.array(sorted(u), np.int64)
    else:
        keep = np.arange(I.NW, dtype=np.int64)
    loc = np.full(I.NW, -1, np.int64); loc[keep] = np.arange(len(keep))
    RDm = cd[:, keep, :]
    kb = np.isin(bc, keep)
    RRm = NC.rr_from_ch0(rts, RDm[:, :, 0], bt[kb], loc[bc[kb]], br[kb])
    sy_all = np.load(f"{TREE}/fea171/xfer_syms.npz", allow_pickle=True); _symbols = sy_all["symbols"][keep]; _channels = sy_all["ch"]
    assert [str(s) for s in sy_all["symbols"]] == I.syms
    MH = {a: loc[v] for a, v in members_hist.items() if a in {int(rts[i]) for i in e_rows}}
    for a, v in MH.items(): assert (v >= 0).all()
    ema, led = I.funding(A)
    kept = {I.syms[j] for j in keep}
    aux = {"ema": {s: v for s, v in ema.items() if s in kept}, "ledger_tail": {s: v for s, v in led.items() if s in kept}}
    mini_root = tempfile.mkdtemp(prefix=f"mini-{A}-", dir=work); MINI = f"{mini_root}/mini"
    try:
        with np.load(f"{TREE}/fea171/xfer_ref.npz", allow_pickle=True) as r:
            cf["_symbols"] = _symbols; cf["_source_snapshot"] = {"reference": {"E_ts": r["E_ts"], "btcv": r["btcv"]}}
        ns = {"np": np, "os": os, "time": time, "subprocess": subprocess, "log": (lambda *a: None), "rts": rts, "A": int(A), "pm": loc[pm],
              "MEMBERS_HIST": MH, "NW": len(keep), "MINI": MINI, "_symbols": _symbols, "_channels": _channels, "RD": RDm, "RR": RRm,
              "_btcv_series": cf["_btcv_series"], "_feature_workspace": types.SimpleNamespace(name=mini_root), "aux": aux, "NC": NC,
              "WS": os.environ["NC_WS"], "HERE": f"{TREE}/fea171"}
        exec(mini_code, ns)
        F82 = np.load(f"{MINI}/data/dlw_fea82.npz", allow_pickle=True); F89 = np.load(f"{MINI}/data/f8_fea89.npz", allow_pickle=True)
        T9 = np.load(f"{MINI}/data/dlw_targets.npz", allow_pickle=True)
        m82 = json.loads(str(F82["meta_json"])); m89 = json.loads(str(F89["meta_json"]))
        assert m82["cache_sha256"] == sha(f"{MINI}/cache.npz") and m89["fea82_sha256"] == sha(f"{MINI}/data/dlw_fea82.npz")
        assert m82["self_sha256"] == REC["outputs"]["fea171/dlw_features.py"] and m89["self_sha256"] == REC["outputs"]["fea171/f8_higher_order_features.py"]
        ets = T9["E_ts"].astype(np.int64); a_i = int(np.where(ets == A)[0][0])
        pa2 = F82["pair_a"].astype(np.int64); ps2 = F82["pair_s"].astype(np.int64); rowm = (pa2 == a_i)
        assert np.array_equal(F89["pair_a"], F82["pair_a"]) and np.array_equal(F89["pair_s"], F82["pair_s"])
        X82 = F82["X"][rowm]; X89 = F89["X"][rowm]; scol = keep[ps2[rowm]]
        assert np.array_equal(scol, pm), "F10 rows not in member order"
        return {"X82": X82, "X89": X89, "btcv_anchor": float(T9["btcv"][a_i]), "mh_missing": int(ns.get("MH_MISSING", -1)),
                "n_keep": int(len(keep)), "f89_finite_share_raw": m89.get("finite_share_raw")}
    finally:
        if not keep_mini:
            shutil.rmtree(mini_root, ignore_errors=True)
