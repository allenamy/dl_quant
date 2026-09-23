#!/usr/bin/env python3
"""NC parity gate — FREEZE b30e4afa5 §3.3 pre-deploy hard gate, DESIGN §A9-3 "one implementation (bitwise)". Mac, production venv, heavy:
each anchor starts only with >= 15 min left in the Mac window [N+1:00, N+3:40]. Never calls the exchange, never writes ~/wide_shadow or
~/dl_quant_live (one sandbox per run under <out>).
For every reference anchor A of the parity pack (pod2 export; the training replay's inputs and its NC_FEATURES rows):
  state at A-4h, ALL feature inputs from the pack: the 11,520 window rows (crypto columns = pack rows; other columns NaN — the replay
      never reads them), the sparse table cells inside the window, the member history inside the window, funding ledger_tail = the last
      <= 400 events <= A-4h with the pack's interval, EMA = the pack's per-event (acc, last_ts) after the last event <= A-4h.
      Feature-free fields (H, prev_rec, last_anchor, prev_close, leg returns, weights, combo H files) from the production snapshot
      snap/<A-4h> (read-only copy). fetch_syms = base_syms = every crypto name (no new-name backfill). Signed by the tree's own module.
  fake fetcher: exchangeInfo lists only the crypto names with a bar in the legal_live window (--exinfo w24h, the DEFAULT — lead 2026-09-23)
      or every crypto name (--exinfo all). WHY w24h: history has no per-anchor exchangeInfo; 'traded recently' is the TRADING proxy
      §E4-(b) already uses (legal(A-4h) for fetch(A-4h)); the list is a superset of every legal name, so m and base_val are unaffected
      by construction; live, TRADING names almost all carry bars so the serving coverage gate (< 0.80 ⇒ SKIP) never fires, whereas
      'all' invents a list no anchor ever had (0.66 coverage on the machine pack ⇒ every anchor skipped). Residual risk: funding is not
      advanced for unlisted names (non-member columns of the combo funding panel only); a member-row difference shows as RED and is
      attributed cell by cell, never waived; K-line requests return [] (the 48 bars (A-4h, A] are pre-filled from the
      pack rows, all 7 channels as stored, and their sparse-table cells appended); fundingRate (per name and bulk) = the pack's events in
      (A-4h, A], rate float64 as stored.
  run the tree's run_anchor(A) (booster.predict wrapped: the King X it receives + a snapshot of run_anchor's locals at that call —
      m, fe_v, fn_v, iv_v, qvm, base_vals; rev24 and m again from run_anchor's frame at return), then the tree's combo_stage.py under
      sandbox-exec through a wrapper that replaces feature_cache_identity.fresh_feature_workspace with a persistent directory before
      exec'ing combo_stage.py; X82 / X89 / btcv are read from that workspace exactly as the replay's pass 2 reads its own
      (dlw_fea82.npz / f8_fea89.npz rows of anchor A, member order asserted; dlw_targets.npz btcv of A).
  compare with ref_*: m identical; X78, fe_v, fn_v, iv_v, qvm, rev24 (member order), base_val (829 axis, NaN elsewhere), btcv, X82, X89:
      the server value cast to the reference's dtype, equal element for element with the same NaN positions (bitwise differences are
      counted separately). Per anchor per quantity: n, n_differing, max|diff|, first differing (name, column).
VERDICT = PASS iff >= 6 anchors, every quantity 0 differing, AND both negative controls detected (counted only on a green baseline):
  NC-F  one funding rate of a member name in (A-4h, A] moved by 1 ulp -> fe_v or fn_v must differ;
  NC-R  one ch0 cell of a member in the last 4 h (not a sparse-table cell) moved by one float16 step -> X78, X82 or X89 must differ.
Modes: --emit-ref F writes the server's outputs as ref_* into a copy of the pack (machinery: a pack whose reference is the server's own
first pass); --machinery prefixes the verdict MACHINERY_DRY_RUN_ (never a deployment receipt).
usage: ~/wide_shadow/venv/bin/python nc_parity_gate.py <NC tree> <parity pack npz> <out dir> [--exinfo all|w24h] [--anchors A,..] [--emit-ref F] [--machinery] [--keep]
output: <out>/NC_PARITY_GATE.json"""
import os, sys, json, time, shutil, argparse, traceback
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import nc_sandbox_lib as L

CACHE_ROWS = 11520
PER_MEMBER = ("X78", "fe_v", "fn_v", "iv_v", "qvm", "rev24", "X82", "X89")
PACK_KEYS = ("rts", "rows", "crypto_cols", "symbols", "axis_end", "bnd_ts", "bnd_col", "bnd_raw", "m_anchors", "m_off", "m_idx",
             "f_sym", "f_n", "f_ft", "f_rate", "f_iv", "f_acc_ev", "f_prev_ev")
REF_KEYS = ("ref_anchors", "ref_off", "ref_m", "ref_X78", "ref_X82", "ref_X89", "ref_fe_v", "ref_fn_v", "ref_iv_v", "ref_qvm", "ref_rev24",
            "ref_base_val", "ref_btcv")
WRAP = '''import os, sys, types, runpy
HERE = os.path.join(os.environ["WIDE_SHADOW_HOME"], "fea171"); sys.path.insert(0, HERE)
import feature_cache_identity as F
P = os.environ["PARITY_FEATURE_WS"]; os.makedirs(P)          # must be new: a fresh, persistent workspace
F.fresh_feature_workspace = lambda: types.SimpleNamespace(name=P, cleanup=lambda: None)
sys.argv = [os.path.join(HERE, "combo_stage.py")]
runpy.run_path(sys.argv[0], run_name="__main__")
'''


class Pack:
    def __init__(self, path, syms, crypto, need_ref):
        with np.load(path, allow_pickle=True) as z:
            self.z = {k: z[k] for k in z.files}
        miss = [k for k in PACK_KEYS + (REF_KEYS if need_ref else ()) if k not in self.z]
        assert not miss, f"parity pack lacks {miss}"
        z = self.z
        assert [str(s) for s in z["symbols"]] == syms, "pack symbols differ from the bundle symbols_panel"
        self.cols = z["crypto_cols"].astype(np.int64)
        assert np.array_equal(np.flatnonzero(crypto), np.sort(self.cols)) and np.array_equal(self.cols, np.sort(self.cols)), \
            "pack crypto_cols differ from the sandbox crypto_axis (crypto_P1): the producer's crypto mask would not be the replay's"
        self.E = int(z["axis_end"]); self.rts = z["rts"].astype(np.int64); self.rows = z["rows"]
        assert self.rows.shape == (len(self.rts), len(self.cols), 7) and self.rows.dtype == np.float16
        assert np.all(np.diff(self.rts) == 300), "pack rows are not a contiguous 5-minute grid"
        self.bt, self.bc, self.br = z["bnd_ts"].astype(np.int64), z["bnd_col"].astype(np.int64), z["bnd_raw"].astype(np.float32)
        self.mh = {int(z["m_anchors"][k]): z["m_idx"][z["m_off"][k]:z["m_off"][k + 1]].astype(np.int64) for k in range(len(z["m_anchors"]))}
        self.f_off = np.concatenate([[0], np.cumsum(z["f_n"])]).astype(np.int64)
        assert len(z["f_acc_ev"]) == len(z["f_prev_ev"]) == len(z["f_ft"]) == int(self.f_off[-1])
        self.syms = syms

    def funding_at(self, t):
        """ledger_tail (last <= 400 events <= t, pack intervals) and EMA state after the last event <= t, per crypto name."""
        z = self.z; ema, led, short = {}, {}, 0
        for k, j in enumerate(z["f_sym"]):
            b0, b1 = int(self.f_off[k]), int(self.f_off[k + 1]); ft = z["f_ft"][b0:b1].astype(np.int64)
            assert np.all(np.diff(ft) > 0)
            kk = int(np.searchsorted(ft, t, side="right"))
            if kk == 0: continue
            lo = max(0, kk - 400); short += int(kk - lo < 400 and b1 - b0 >= 400)
            s = self.syms[int(j)]
            led[s] = [[int(ft[q]), float(z["f_rate"][b0 + q]), (None if np.isnan(z["f_iv"][b0 + q]) else float(z["f_iv"][b0 + q]))] for q in range(lo, kk)]
            acc = float(z["f_acc_ev"][b0 + kk - 1]); pv = int(z["f_prev_ev"][b0 + kk - 1])
            ema[s] = {"acc": None if np.isnan(acc) else acc, "last_ts": None if pv < 0 else pv}
        return ema, led, short

    def events(self, lo, hi):
        """{name: [[ft, rate_float64], ...]} for lo < ft <= hi."""
        z = self.z; out = {}
        for k, j in enumerate(z["f_sym"]):
            b0, b1 = int(self.f_off[k]), int(self.f_off[k + 1]); ft = z["f_ft"][b0:b1].astype(np.int64)
            sel = np.flatnonzero((ft > lo) & (ft <= hi))
            if len(sel): out[self.syms[int(j)]] = [[int(ft[q]), float(z["f_rate"][b0 + q])] for q in sel]
        return out

    def ref(self, A):
        z = self.z; ra = z["ref_anchors"].astype(np.int64); i = int(np.flatnonzero(ra == A)[0]); s = slice(int(z["ref_off"][i]), int(z["ref_off"][i + 1]))
        r = {k: z["ref_" + k][s] for k in ("m",) + PER_MEMBER}
        r["base_val"] = z["ref_base_val"][i]; r["btcv"] = z["ref_btcv"][i]
        return r


def build_state(pk, A, ws, tree, NW):
    """<ws>/state at A-4h from the pack (+ feature-free template fields from snap/<A-4h>); signed by the tree's module."""
    t0 = A - 14400; snap = f"{L.WS}/state/snap/{t0}"; st = f"{ws}/state"
    assert os.path.exists(f"{snap}/COMPLETE"), f"no production snapshot at {t0}"
    ia = int(np.searchsorted(pk.rts, t0)); assert pk.rts[ia] == t0 and ia + 1 >= CACHE_ROWS, "pack does not cover the A-4h window"
    i0 = ia + 1 - CACHE_ROWS; ts = pk.rts[i0:ia + 1]
    D = np.full((CACHE_ROWS, NW, 7), np.nan, np.float16); D[:, pk.cols, :] = pk.rows[i0:ia + 1]
    np.savez(f"{st}/rolling.npz", ts=ts, data=D); del D
    k = (pk.bt >= ts[0]) & (pk.bt <= t0); o = np.lexsort((pk.bc[k], pk.bt[k]))
    np.savez(f"{st}/boundary_raw.npz", ts=pk.bt[k][o], col=pk.bc[k][o].astype(np.int32), raw=pk.br[k][o])
    anc = sorted(a for a in pk.mh if ts[0] <= a <= t0); off = np.concatenate([[0], np.cumsum([len(pk.mh[a]) for a in anc])]).astype(np.int64)
    np.savez(f"{st}/members_hist.npz", anchors=np.array(anc, np.int64), off=off,
             idx=(np.concatenate([pk.mh[a] for a in anc]) if anc else np.zeros(0)).astype(np.int16))
    ema, led, short = pk.funding_at(t0)
    aux = json.load(open(f"{snap}/aux.json")); assert int(aux["last_anchor"]) == t0 == int(aux["prev_rec"]["anchor_ts"])
    crypto_names = [pk.syms[j] for j in pk.cols]
    aux.update({"ema": ema, "ledger_tail": led, "fetch_syms": crypto_names, "base_syms": sorted(crypto_names), "prev_close_ts": {},
                "nc_backfill_residual": []})
    json.dump(aux, open(f"{st}/aux.json", "w"))
    shutil.copy2(f"{snap}/leg_returns_live.json", f"{st}/leg_returns_live.json")
    M = L.load_producer(ws, f"sign_{A}")
    M.atomic_json(f"{st}/generation.json", M.build_generation_record(st, t0))
    return {"window": [int(ts[0]), int(ts[-1])], "boundary_cells": int(k.sum()), "member_hist_anchors": len(anc), "funding_names": len(led),
            "ledger_short_of_400_by_pack_coverage": short, "carry_prior": L.carry_prior(ws, t0)}


class RecBooster:
    def __init__(self, b, code):
        self._b, self._code, self.snaps = b, code, []

    def predict(self, X, *a, **k):
        f = sys._getframe(1)
        if f.f_code is self._code:
            loc = f.f_locals
            self.snaps.append({"X": np.array(X, copy=True), "X_is_local_X": loc.get("X") is X,
                               **{n: np.array(loc[n], copy=True) for n in ("m", "fe_v", "fn_v", "iv_v", "qvm")},
                               "base_vals": {s: float(v) for s, v in loc["base_vals"].items()}})
        return self._b.predict(X, *a, **k)

    def __getattr__(self, n):
        return getattr(self._b, n)


def run_one(a, tree, pk, A, out, tag, NW, sidx, mutate_rate=None, mutate_cell=None):
    """one sandbox run at A. mutate_rate = (name, ft) -> that event's rate +1 ulp; mutate_cell = (ts, col) -> ch0 +1 float16 step."""
    res = {"anchor": A, "tag": tag, "window_at_start": L.quiet_window_guard(15)}
    root = f"{out}/sb_{tag}"; ws, exe = L.build_sandbox(root, "new", tree)
    res["state"] = build_state(pk, A, ws, tree, NW)
    t0 = A - 14400
    evs = pk.events(t0, A)
    if mutate_rate:
        s, ft = mutate_rate; row = [r for r in evs[s] if r[0] == ft][0]; old = row[1]; row[1] = float(np.nextafter(old, np.inf))
        res["mutation"] = {"kind": "funding_rate_ulp", "name": s, "ft": ft, "rate": repr(old), "rate_mutated": repr(row[1])}
    # exchangeInfo TRADING list. 'all' = every crypto name (the lead's spec: fetch list = the replay's, every crypto column); 'w24h' = crypto
    # names with any bar (finite ch3/ch4) in the rows [A-290 rows, A] the legal_live window reads — a superset of every legal name.
    ia_ = int(np.searchsorted(pk.rts, A)); seg = pk.rows[max(ia_ - 290, 0):ia_ + 1]
    w24 = np.isfinite(seg[:, :, 3].astype(np.float32)).any(0) | np.isfinite(seg[:, :, 4].astype(np.float32)).any(0)
    listed = [pk.syms[j] for j in pk.cols] if a.exinfo == "all" else [pk.syms[j] for p_, j in enumerate(pk.cols) if w24[p_]]
    at_A = {pk.syms[j] for p_, j in enumerate(pk.cols) if np.isfinite(float(pk.rows[ia_, p_, 3]))}
    res["exinfo"] = {"mode": a.exinfo, "listed": len(listed), "coverage_at_A": round(sum(s_ in at_A for s_ in listed) / max(len(listed), 1), 4),
                     "note": "the producer SKIPs the anchor below 0.80 (serving coverage gate; the replay has none)"}
    fake = L.NCFake({"ledger_tail": evs, "base_syms": listed})
    M = L.load_producer(ws, f"run_{tag}")
    cfg, booster, man = M.load_bundle(); cfg["_booster_sha"] = man.get("slow2026.txt", "")
    st = M.ShadowState(cfg); assert int(st.cts[-1]) == t0
    # pre-fill (A-4h, A] from the pack rows (7 channels as stored) + their sparse-table cells
    i1 = int(np.searchsorted(pk.rts, t0)) + 1; ia = int(np.searchsorted(pk.rts, A)); assert pk.rts[ia] == A and ia - i1 + 1 == 48
    new = np.full((48, NW, 7), np.nan, np.float16); new[:, pk.cols, :] = pk.rows[i1:ia + 1]
    if mutate_cell:
        t, j = mutate_cell; r = int(np.flatnonzero(pk.rts[i1:ia + 1] == t)[0]); old = new[r, j, 0]
        new[r, j, 0] = np.nextafter(old, np.float16(np.inf))
        res["mutation"] = {"kind": "ch0_f16_step", "name": pk.syms[j], "ts": int(t), "ch0": float(old), "ch0_mutated": float(new[r, j, 0])}
    st.cts = np.concatenate([st.cts, pk.rts[i1:ia + 1]]); st.cd = np.concatenate([st.cd, new])
    kb = (pk.bt > t0) & (pk.bt <= A)
    st.bnd_ts = np.append(st.bnd_ts, pk.bt[kb]); st.bnd_col = np.append(st.bnd_col, pk.bc[kb].astype(np.int32)); st.bnd_raw = np.append(st.bnd_raw, pk.br[kb])
    res["prefill"] = {"rows": 48, "boundary_cells": int(kb.sum()), "funding_names_served": len(evs)}
    code = M._run_anchor.__code__; rb = RecBooster(booster, code); ret = {}

    def prof(frame, event, arg):
        if event == "return" and frame.f_code is code:
            loc = frame.f_locals
            if "rev24" in loc: ret["rev24"] = np.array(loc["rev24"], copy=True); ret["m"] = np.array(loc["m"], copy=True)
    la0 = os.getloadavg(); tt = time.time(); sys.setprofile(prof)
    try:
        M.run_anchor(st, fake, cfg, rb, A); res["producer"] = {"outcome": "returned"}
    except Exception as e:
        res["producer"] = {"outcome": "raised", "error": f"{type(e).__name__}: {str(e)[:300]}", "tb": traceback.format_exc()[-1500:]}
    finally:
        sys.setprofile(None)
    res["producer"].update(wall_s=round(time.time() - tt, 2), loadavg=[la0, os.getloadavg()], diag=L.last_diag(ws, A),
                           predict_calls_from_run_anchor=len(rb.snaps))
    if os.path.exists(f"{ws}/shadow_log.jsonl"):
        sk = [json.loads(l) for l in open(f"{ws}/shadow_log.jsonl") if '"anchor_skip"' in l]
        if sk: res["producer"]["anchor_skip"] = sk[-1]
    srv = {}
    if res["producer"]["outcome"] == "returned" and len(rb.snaps) == 1 and "rev24" in ret:
        sn = rb.snaps[0]; m = sn["m"].astype(np.int64)
        assert np.array_equal(m, ret["m"]), "run_anchor's m changed between predict and return"
        res["producer"]["X_is_local_X"] = sn["X_is_local_X"]
        srv = {"m": m, "X78": sn["X"], "fe_v": sn["fe_v"][m], "fn_v": sn["fn_v"][m], "iv_v": sn["iv_v"][m], "qvm": sn["qvm"][m], "rev24": ret["rev24"]}
        bv = np.full(NW, np.nan); [bv.__setitem__(sidx[s], v) for s, v in sn["base_vals"].items()]; srv["base_val"] = bv
        # combo_stage through the persistent-workspace wrapper
        open(f"{root}/combo_parity_wrap.py", "w").write(WRAP); fws = f"{root}/feature_ws"
        c = L.run_combo(root, ws, exe, tag, script=f"{root}/combo_parity_wrap.py", extra_env={"PARITY_FEATURE_WS": fws})
        res["combo"] = c
        mini = f"{fws}/mini"
        if os.path.exists(f"{mini}/data/f8_fea89.npz"):
            F82 = np.load(f"{mini}/data/dlw_fea82.npz", allow_pickle=True); F89 = np.load(f"{mini}/data/f8_fea89.npz", allow_pickle=True)
            T9 = np.load(f"{mini}/data/dlw_targets.npz", allow_pickle=True)
            ets = T9["E_ts"].astype(np.int64); a_i = int(np.where(ets == A)[0][0])
            pa2 = F82["pair_a"].astype(np.int64); ps2 = F82["pair_s"].astype(np.int64); rowm = pa2 == a_i
            assert np.array_equal(F89["pair_a"], F82["pair_a"]) and np.array_equal(F89["pair_s"], F82["pair_s"])
            scol = ps2[rowm]; res["combo"]["f10_rows_in_member_order"] = bool(np.array_equal(scol, m))
            if res["combo"]["f10_rows_in_member_order"]:
                srv.update(X82=F82["X"][rowm], X89=F89["X"][rowm], btcv=np.float64(T9["btcv"][a_i]))
            res["combo"]["feature_workspace"] = fws
    os.makedirs(f"{out}/logs", exist_ok=True)
    for src, dst in ((f"{ws}/shadow_log.jsonl", f"shadow_log_{tag}.jsonl"), ((res.get("combo") or {}).get("log"), f"combo_{tag}.log")):
        if src and os.path.exists(src): shutil.copy2(src, f"{out}/logs/{dst}")
    res["sandbox"] = root if a.keep else None
    if not a.keep: shutil.rmtree(root, ignore_errors=True)
    return res, srv


def cmp(name, srv, ref, row_names, NW_syms):
    out = {"quantity": name}
    if srv is None:
        return {**out, "n": int(np.asarray(ref).size), "n_differing": None, "why": "server value unavailable"}
    s = np.asarray(srv); r = np.asarray(ref)
    out.update(n=int(r.size), server_dtype=str(s.dtype), ref_dtype=str(r.dtype))
    if s.shape != r.shape:
        return {**out, "n_differing": None, "why": f"shape {s.shape} vs ref {r.shape}"}
    if r.dtype.kind == "f":
        if s.dtype.kind == "f" and s.dtype.itemsize > r.dtype.itemsize: out["note"] = "server narrowed to the reference dtype for the comparison"
        sc = s.astype(r.dtype); ns, nr = np.isnan(sc), np.isnan(r)
        eq = (sc == r) | (ns & nr)
        ui = {2: np.uint16, 4: np.uint32, 8: np.uint64}[r.dtype.itemsize]
        out["n_bitwise_differing"] = int((sc.view(ui) != r.view(ui)).sum())
        d = np.where(eq, 0.0, np.abs(sc.astype(np.float64) - r.astype(np.float64)))
        d = np.where(~eq & (ns != nr), np.inf, d)
        out["max_abs_diff"] = float(d.max()) if d.size else 0.0
    else:
        eq = s.astype(np.int64) == r.astype(np.int64)
    bad = np.argwhere(~eq); out["n_differing"] = int(len(bad))
    if len(bad):
        ix = tuple(int(x) for x in bad[0])
        out["first"] = {"name": (row_names[ix[0]] if row_names is not None and ix else None), "col": (ix[1] if len(ix) > 1 else None),
                        "server": repr(s[ix] if ix else s), "ref": repr(r[ix] if ix else r)}
    return out


def compare(srv, ref, syms):
    mref = ref["m"].astype(np.int64); names = [syms[j] for j in mref]
    Q = {"m": cmp("m", srv.get("m"), mref, None, syms)}
    if Q["m"]["n_differing"] == 0:
        for k in PER_MEMBER: Q[k] = cmp(k, srv.get(k), ref[k], names, syms)
    else:
        sm = set(srv.get("m", np.zeros(0)).tolist()); rm = set(mref.tolist())
        Q["m"]["only_server"] = [syms[j] for j in sorted(sm - rm)][:20]; Q["m"]["only_ref"] = [syms[j] for j in sorted(rm - sm)][:20]
        for k in PER_MEMBER: Q[k] = {"quantity": k, "n_differing": None, "why": "member sets differ: rows not aligned"}
    Q["base_val"] = cmp("base_val", srv.get("base_val"), ref["base_val"], syms, syms)
    Q["btcv"] = cmp("btcv", srv.get("btcv"), np.asarray(ref["btcv"]), None, syms)
    return Q


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("tree"); ap.add_argument("pack"); ap.add_argument("out")
    ap.add_argument("--exinfo", choices=("all", "w24h"), default="w24h"); ap.add_argument("--anchors"); ap.add_argument("--emit-ref"); ap.add_argument("--machinery", action="store_true"); ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()
    q = L.quiet_window_guard(15)
    tree = os.path.abspath(a.tree); pkc = L.phase_key_check(tree)
    if pkc["missing"]: raise SystemExit(f"TREE DEFECT: diag.phase names not in _AnchorTiming.phase_s: {pkc['missing']}")
    out = os.path.abspath(a.out); assert not os.path.exists(out), "refusing to overwrite"; os.makedirs(out)
    cfg = json.load(open(f"{L.WS}/shadow_bundle/config.json")); syms = cfg["symbols_panel"]; NW = len(syms); sidx = {s: j for j, s in enumerate(syms)}
    crypto = np.array(L.crypto_axis_json(syms)["crypto"], bool)
    pk = Pack(a.pack, syms, crypto, need_ref=not a.emit_ref)
    anchors = [int(x) for x in a.anchors.split(",")] if a.anchors else (sorted(int(x) for x in pk.z["ref_anchors"]) if "ref_anchors" in pk.z
                                                                          else [pk.E - 14400 * k for k in range(5, -1, -1)])
    rec = {"device_sha256": L.sha(os.path.abspath(__file__)), "lib_sha256": L.sha(L.__file__), "tree": tree,
           "tree_shadow_loop_sha256": L.sha(f"{tree}/shadow_loop_v3.py"), "tree_combo_stage_sha256": L.sha(f"{tree}/fea171/combo_stage.py"),
           "tree_patch_receipt_sha256": L.sha(f"{tree}/PATCH_RECEIPT.json") if os.path.exists(f"{tree}/PATCH_RECEIPT.json") else None,
           "exinfo_mode": a.exinfo, "exinfo_rationale": ("w24h (lead 2026-09-23): no historical exchangeInfo; recent-bar proxy as DESIGN §E4-(b); superset of legal ⇒ m / base_val unaffected; residual = funding of unlisted names not advanced, caught by the gate" if a.exinfo == "w24h" else "all: every crypto name listed (NOT the ruled mode)"), "pack": os.path.abspath(a.pack), "pack_sha256": L.sha(a.pack), "axis_end": pk.E, "anchors": anchors, "window_at_start": q,
           "started_utc": time.strftime("%FT%TZ", time.gmtime()), "runs": {}, "comparison": {}, "negative_controls": {}}

    def dump():
        json.dump(rec, open(f"{out}/NC_PARITY_GATE.json", "w"), indent=1, default=str)

    SRV = {}
    for A in anchors:
        try:
            r, s = run_one(a, tree, pk, A, out, str(A), NW, sidx)
        except SystemExit as e:
            rec["stopped"] = str(e); break
        rec["runs"][str(A)] = r; SRV[A] = s; dump()
        print("NC_PARITY_RUN", A, r["producer"]["outcome"], "combo_rc", (r.get("combo") or {}).get("rc"), flush=True)
    if a.emit_ref:
        done = [A for A in anchors if SRV.get(A) and "X82" in SRV[A]]
        assert done == anchors, f"emit-ref needs every anchor served: {done}"
        cnt = [len(SRV[A]["m"]) for A in anchors]
        ref = {"ref_anchors": np.array(anchors, np.int64), "ref_off": np.concatenate([[0], np.cumsum(cnt)]).astype(np.int64),
               "ref_m": np.concatenate([SRV[A]["m"] for A in anchors]).astype(np.int16),
               **{"ref_" + k: np.concatenate([np.asarray(SRV[A][k]) for A in anchors]) for k in PER_MEMBER},
               "ref_base_val": np.stack([SRV[A]["base_val"] for A in anchors]), "ref_btcv": np.array([SRV[A]["btcv"] for A in anchors], np.float64)}
        ref["ref_X82"] = ref["ref_X82"].astype(np.float32); ref["ref_X89"] = ref["ref_X89"].astype(np.float32); ref["ref_X78"] = ref["ref_X78"].astype(np.float32)
        np.savez(a.emit_ref, **{k: v for k, v in pk.z.items() if not k.startswith("ref_")}, **ref)
        rec["emitted_ref"] = {"path": a.emit_ref, "sha256": L.sha(a.emit_ref), "note": "reference = this server run (machinery only)"}
        rec["VERDICT"] = "EMITTED_REF_NOT_A_GATE"; dump(); print("NC_PARITY_GATE", rec["VERDICT"], flush=True); return
    green = True
    for A in anchors:
        if A not in SRV:
            rec["comparison"][str(A)] = {"why": "not run"}; green = False; continue
        Q = compare(SRV[A], pk.ref(A), syms); rec["comparison"][str(A)] = Q
        green &= all(v.get("n_differing") == 0 for v in Q.values())
    green &= len(SRV) == len(anchors) >= 6
    rec["baseline_green"] = bool(green); dump()
    NEG = rec["negative_controls"]; NEG["counted"] = bool(green)
    neg_ok = False
    if green:
        A = anchors[-1]; ref = pk.ref(A); mref = ref["m"].astype(np.int64); evs = pk.events(A - 14400, A)
        cand = [(syms[j], evs[syms[j]][-1][0]) for k_, j in enumerate(mref) if syms[j] in evs and np.isfinite(ref["fn_v"][k_])]
        i1 = int(np.searchsorted(pk.rts, A - 14400)) + 1; ia = int(np.searchsorted(pk.rts, A)); cpos = {int(c): p for p, c in enumerate(pk.cols)}
        bset = set(zip(pk.bt.tolist(), pk.bc.tolist())); cells = []
        for j in mref:
            for r_ in range(ia, i1 - 1, -1):
                v = float(pk.rows[r_, cpos[int(j)], 0]); t = int(pk.rts[r_])
                if np.isfinite(v) and abs(v) < 0.25 and (t, int(j)) not in bset: cells.append((t, int(j))); break
            if cells: break
        for tag, kw, targets in (("NC_F_funding_rate_ulp", {"mutate_rate": cand[0] if cand else None}, ("fe_v", "fn_v")),
                                 ("NC_R_ch0_f16_step", {"mutate_cell": cells[0] if cells else None}, ("X78", "X82", "X89"))):
            if not list(kw.values())[0]:
                NEG[tag] = {"detected": False, "why": "no eligible cell/event"}; continue
            try:
                r, s = run_one(a, tree, pk, A, out, f"{A}_{tag}", NW, sidx, **kw)
            except SystemExit as e:
                NEG[tag] = {"detected": False, "why": f"window: {e}"}; continue
            Q = compare(s, ref, syms)
            NEG[tag] = {"mutation": r.get("mutation"), "targets": targets, "differing": {k: v.get("n_differing") for k, v in Q.items()},
                        "detected": any((Q[k].get("n_differing") or 0) > 0 for k in targets)}
            dump()
        neg_ok = all(NEG[t]["detected"] for t in ("NC_F_funding_rate_ulp", "NC_R_ch0_f16_step"))
    v = "PASS" if (green and neg_ok) else ("FAIL_NEGATIVE_CONTROL_NOT_DETECTED" if green else
                                           ("INCOMPLETE" if len(SRV) < len(anchors) or len(anchors) < 6 else "FAIL_PARITY"))
    if a.machinery: v = "MACHINERY_DRY_RUN_" + v
    rec["VERDICT"] = v; rec["finished_utc"] = time.strftime("%FT%TZ", time.gmtime()); dump()
    summ = {A: {k: q_.get("n_differing") for k, q_ in rec["comparison"].get(str(A), {}).items() if isinstance(q_, dict)} for A in anchors}
    print("NC_PARITY_GATE", v, json.dumps(summ)[:900], json.dumps({k: NEG[k].get("detected") for k in NEG if k != "counted"}), flush=True)
    sys.exit(0 if v.replace("MACHINERY_DRY_RUN_", "") == "PASS" else 1)


if __name__ == "__main__":
    main()
