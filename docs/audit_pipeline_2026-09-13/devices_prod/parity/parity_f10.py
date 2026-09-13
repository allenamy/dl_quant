#!/usr/bin/env python3
"""parity_f10.py -- AUDIT_PROD P4 for V2MAIN/F10 (171 columns = dlw 82 + f8 89): train/serve parity measured with the production feature code itself.
Mac, production interpreter (~/wide_shadow/venv). Measurement only, no P&L. Inputs read-only; production feature files are sha-checked and COPIED to
~/cc_tmp/aud_prod/f10_code (never run in ~/wide_shadow); per-run scratch in ~/cc_tmp/aud_prod/f10_runs (deleted after each run); receipt to
docs/audit_pipeline_2026-09-13/receipts_prod/parity_f10.json (+ parity_f10_columns.csv).

A pipeline run = exactly what combo_stage.py (b5c698f9) L118-159 does: cache.npz(ts,data,symbols,ch) + dlw_targets.npz(E_row,E_ts,members,zeros,yrs,btcv,...)
+ panel(ts,f_fund_ema,f_fund_now) -> dlw_features.py (29ae6a98) -> f8_higher_order_features.build() (2c500c7a) -> X171 rows of the scored anchor.
Production cache at anchor A = 11,520 rows ending at A: rows >= 2026-08-04 12:05Z from a read-only copy of the live rolling cache (after the 12Z anchor), rows before
that from the 08-16 bundle cache_tail_40d.npz (the producer's bootstrap source; rows before 08-16 were never re-fetched).
Arms
  F_S(A)  production approximation: members pm(A) for every history row (combo_stage L121-123), btcv = combo_stage _btcv_series (AST-extracted), panel last row = served fund.
  F_T(A)  F_S with the cache truncated at the Phase-1 replay start 2026-08-03 08:05Z (tests the open G-P2 residual mechanism: history-dependent columns).
  F_H     one long run (cache 07-29 00:05Z .. 09-10 20Z): every history row has its own production member set (weights/<A>.npz members; production member code
          shadow_loop_v3.py L355-377 executed from the file text before 08-17 04Z); otherwise as F_S.            -> history-member approximation = F_S vs F_H
  F_D     one long run on the pod holefix2_x0910 slice (all 829 names): per-row training members D and training btcv from dlw_targets_x0910, panel = stored
          training fund columns.                                                                                   -> should reproduce the stored training rows (G-F10CODE)
  T171    stored training rows: dlw_hf3_x0910 fea82 (pod_dlw_features_ext.py e86725cc) + f8_v4_x0910 fea89 (pod_f8_build_ext.py f606bffa), members D.
Gates: G-F10SREP F_S reproduces the T4b served combo_X171/scol/f10 bitwise at all 6 T4b anchors (09-12 12Z..09-13 08Z; live bitwise per T4b PCB);
       G-F10CODE F_D == T171 on >= 99.99% of cells for every column except the two global-cumsum trend columns (reported, AUDIT_TRAIN TRN-16).
Launch (verbatim): devices_prod/parity/parity_run_mac.sh f10
"""
import os, sys, json, time, hashlib, stat, ast, shutil, subprocess, csv, calendar
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "env whitelist argv[1] required"
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
from types import SimpleNamespace
from scipy.stats import spearmanr, rankdata
from scipy.special import erf
from concurrent.futures import ThreadPoolExecutor
T0 = time.time()
def log(*a): print("[%7.1fs]" % (time.time() - T0), *a, flush=True)
SF_DATALESS = getattr(stat, "SF_DATALESS", 0x40000000)
def gsha(p):
    st = os.stat(p); assert not (st.st_flags & SF_DATALESS), ("dataless", p)
    h = hashlib.sha256(); n = 0
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b); n += len(b)
    assert n == st.st_size, ("short read", p); return h.hexdigest()
def U(t): return time.strftime("%Y-%m-%d %HZ", time.gmtime(int(t)))
def TS(y, mo, d, h, mi): return calendar.timegm((y, mo, d, h, mi, 0))
HOME = "/Users/haosiyu"; STG = HOME + "/cc_tmp/aud_prod/parity_stage"; REPO = HOME + "/Desktop/quant_research"; WS = HOME + "/wide_shadow"
CODE = HOME + "/cc_tmp/aud_prod/f10_code"; RUNS = HOME + "/cc_tmp/aud_prod/f10_runs"; PY = WS + "/venv/bin/python"
OUTJ = REPO + "/docs/audit_pipeline_2026-09-13/receipts_prod/parity_f10.json"; OUTC = REPO + "/docs/audit_pipeline_2026-09-13/receipts_prod/parity_f10_columns.csv"
INPUTS = {
    "dlw_features.py": (WS + "/fea171/dlw_features.py", "29ae6a985d891e56340378bb432c0370e914b93709eec44f54592472e4d20a76"),
    "f8_higher_order_features.py": (WS + "/fea171/f8_higher_order_features.py", "2c500c7ad2bb0f5ddccf431021df50a106a39f4d228bd6cf2d074c5c12f66a5f"),
    "combo_stage.py": (WS + "/fea171/combo_stage.py", "b5c698f9d1ee9acb73c9bf5f3a1e15843d3298e95a810ebf0107a7d68c6ee358"),
    "shadow_loop_v3.py": (WS + "/shadow_loop_v3.py", "e9c9837412130884bc72d4bbcb52b33e9dc8660274b76ae68f46639d2d21b36e"),
    "f10_live_s42_np.npz": (WS + "/fea171/f10_live_s42_np.npz", "351ae26bd6b4a203431a280427fc0bbc968c66e903532168765d654e7e57b3a4"),
    "xfer_syms.npz": (WS + "/fea171/xfer_syms.npz", "d187042e60b480d3bb9e2d57757a1000da80428541011eeec67e330748ae1c92"),
    "xfer_ref.npz": (WS + "/fea171/xfer_ref.npz", "33eb713b72a67665faaf72fa071e0a13c7a7a60a9f732f6e99398ae43dd7bfc8"),
    "config.json": (WS + "/shadow_bundle/config.json", "3a8422f377519cac77b0c42305d2ba40a4b7a42a830f0542bda844f66647c94e"),
    "bundle_0816_cache_tail": (WS + "/shadow_bundle.aug20260816_backup/cache_tail_40d.npz", "295f7a622fdb496f87023b95bb2ba668306eb9ae4acc6a363d57de384bede51c"),
    "T4_served": (STG + "/T4_replay_rec_served.npy", "942d20a91496f60b626a18cac13185b00f5ac2cd26c5300c7d57e5fefcb3c92f"),
    "T4b_served": (STG + "/T4b_replay_rec_served.npy", "6f121afe2228d318ea9458926bb1c5760b55f31db63f9e7a9a35ea0e4641971e"),
    "rolling_live_copy": (STG + "/rolling_live_copy.npz", "9ef804fea8b34f6c86f21f637d6dce82637cb1c6e15f322cfde4d6c586034ea4"),
    "cache_slice_x0910": (STG + "/cache_slice_x0910.npz", "5103279047b2db7b2f446aa0812048cd29c97b96390669e2658aa58b76d7ae68"),
    "dl_x0910_rows": (STG + "/dl_x0910_rows.npz", "c03ac4afa04ef61edbb1ad8bb1db6a73afe7535109747a196d9889240c6ed81e"),
}
RC = {"self_sha256": gsha(os.path.abspath(__file__)), "env": {"whitelist": sorted(WHITE), "actual": {k: os.environ[k] for k in sorted(os.environ)}}, "argv": sys.argv,
      "python": sys.version.split()[0], "numpy": np.__version__, "inputs": {}, "gates": {}, "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
for k, (p, h) in INPUTS.items():
    g = gsha(p); RC["inputs"][k] = {"path": p, "sha256": g}; assert g == h, ("INPUT SHA MISMATCH", k, g)
os.makedirs(CODE, exist_ok=True); os.makedirs(RUNS, exist_ok=True)
for k in ("dlw_features.py", "f8_higher_order_features.py", "xfer_syms.npz", "xfer_ref.npz"):
    shutil.copyfile(INPUTS[k][0], CODE + "/" + k); assert gsha(CODE + "/" + k) == INPUTS[k][1]
log("inputs verified, production feature code copied")
cfg = json.load(open(INPUTS["config.json"][0])); SYMS = [str(s) for s in cfg["symbols_panel"]]; NW = 829; P = cfg["params"]
XSYM = np.load(CODE + "/xfer_syms.npz", allow_pickle=True); XREF = np.load(CODE + "/xfer_ref.npz", allow_pickle=True)
assert [str(s) for s in XSYM["symbols"]] == SYMS and [str(s) for s in XREF["symbols"]] == SYMS

# ---- production helpers executed from file text
CSRC = open(INPUTS["combo_stage.py"][0], encoding="utf-8").read(); tree = ast.parse(CSRC)
fn = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_btcv_series"][0]
BTCV_SRC = "\n".join(CSRC.split("\n")[fn.lineno - 1:fn.end_lineno]); assert (fn.lineno, fn.end_lineno) == (49, 75), (fn.lineno, fn.end_lineno)
NSB = {"np": np, "HERE": CODE}; exec(compile(BTCV_SRC, "combo_stage.py[L49-75]", "exec"), NSB); BTCV = NSB["_btcv_series"]
SSRC = open(INPUTS["shadow_loop_v3.py"][0], encoding="utf-8").read().split("\n")
BLKM = SSRC[354:377]; assert BLKM[0] == "    CDf = st.cd.astype(np.float32)" and BLKM[-1] == '        m = np.sort(m[np.argsort(-qvm[m])[:P["NTOP"]]])', BLKM[-1]
NSM = {"np": np}; exec(compile("def _members(st, row_of, anchor, P):\n" + "\n".join(BLKM) + "\n    return m\n", "shadow_loop_v3.py[L355-377]", "exec"), NSM); PMEM = NSM["_members"]
RC["production_blocks"] = {"combo_stage._btcv_series": "L49-75", "shadow_loop_v3.members": "L355-377"}
M = np.load(INPUTS["f10_live_s42_np.npz"][0])
def gelu(x): return 0.5 * x * (1 + erf(x / np.sqrt(2)))
def f10_score(X171):   # combo_stage.py L165-167
    xz_in = np.nan_to_num(np.clip((X171 - M["mu"]) / M["sd_"], -5, 5))
    h = gelu(xz_in @ M["w0"].T + M["b0"]); h = gelu(h @ M["w1"].T + M["b1"])
    return (h @ M["w2"].T + M["b2"]).squeeze(-1)

# ---- caches
RZ = np.load(INPUTS["rolling_live_copy"][0]); R_TS = RZ["ts"].astype(np.int64); R_D = RZ["data"]
BZ = np.load(INPUTS["bundle_0816_cache_tail"][0], allow_pickle=True); B_TS = BZ["ts"].astype(np.int64); B_D = BZ["data"]; assert [str(s) for s in BZ["symbols"]] == SYMS
CZ = np.load(INPUTS["cache_slice_x0910"][0], allow_pickle=True); C_TS = CZ["ts"].astype(np.int64); C_D = CZ["data"]; assert [str(s) for s in CZ["symbols"]] == SYMS
R0 = int(R_TS[0]); assert R0 == TS(2026, 8, 4, 12, 5)
def prod_cache(start, end):
    ts = np.arange(start, end + 1, 300, dtype=np.int64); out = np.empty((len(ts), NW, 7), np.float16)
    rb = ts < R0; ra = ~rb
    if rb.any():
        ib = np.searchsorted(B_TS, ts[rb]); assert np.array_equal(B_TS[ib], ts[rb]), "bundle tail does not cover"; out[rb] = B_D[ib]
    ia = np.searchsorted(R_TS, ts[ra]); assert np.array_equal(R_TS[ia], ts[ra]), "rolling copy does not cover"; out[ra] = R_D[ia]
    return ts, out
LIVE = np.array([s in set(cfg["symbols_live"]) for s in SYMS])
# G-BOOT (information): bundle tail vs pod slice on live450 for the rows taken from the bundle tail by F_S/F_H
com = np.intersect1d(B_TS[B_TS < R0], C_TS); ib = np.searchsorted(B_TS, com); ic = np.searchsorted(C_TS, com)
a_ = B_D[ib][:, LIVE]; b_ = C_D[ic][:, LIVE]; fa = np.isfinite(a_); fb = np.isfinite(b_); both = fa & fb
RC["gates"]["G-BOOT_info"] = {"rows": int(len(com)), "first": U(com[0]), "last": U(com[-1]), "nan_pattern_diff": int((fa != fb).sum()),
                              "bitwise_diff": int(both.sum() - (a_[both].view(np.uint16) == b_[both].view(np.uint16)).sum()), "cells": int(a_.size)}
del a_, b_, fa, fb, both; log("G-BOOT_info", RC["gates"]["G-BOOT_info"])

# ---- served records and weights members
REC = {}
for key in ("T4_served", "T4b_served"):
    for r in np.load(INPUTS[key][0], allow_pickle=True): REC[int(r["anchor"])] = r
def weights_members(A):
    p = f"{WS}/state/weights/{int(A)}.npz"; z = np.load(p); return np.asarray(z["members"], np.int64)
DL = np.load(INPUTS["dl_x0910_rows"][0], allow_pickle=True)
N82 = [str(n) for n in DL["names82"]]; N89 = [str(n) for n in DL["names89"]]; NAMES = N82 + N89; assert len(NAMES) == 171

# ---- one pipeline run (combo_stage.py L121-159 semantics)
def run_pipeline(tag, rts, RD, members_of_row, btcv, fund_rows, want):
    """members_of_row(i_row, ts) -> member index array; fund_rows: {anchor_ts: (fe829, fn829)}; want: anchors to return."""
    d = f"{RUNS}/{tag}"; shutil.rmtree(d, ignore_errors=True); os.makedirs(d + "/data"); os.makedirs(d + "/results")
    e_rows = [i for i in range(len(rts)) if rts[i] % 14400 == 0 and i >= 48]
    ms_arr = np.empty(len(e_rows), object)
    for k, i in enumerate(e_rows): ms_arr[k] = members_of_row(i, int(rts[i]))
    zz = np.zeros((len(e_rows), NW), np.float32)
    bt = btcv(rts, RD, e_rows) if btcv is BTCV else btcv(e_rows)
    np.savez(d + "/cache.npz", ts=rts, data=RD, symbols=XSYM["symbols"], ch=XSYM["ch"])
    np.savez(d + "/data/dlw_targets.npz", E_row=np.array(e_rows), E_ts=rts[e_rows], members=ms_arr, y4s=zz, YR4s=zz, YRZ=zz,
             yrs=np.array([time.gmtime(int(t)).tm_year for t in rts[e_rows]]), qvk=zz, btcv=bt, has_panel=np.ones(len(e_rows), bool), symbols=XREF["symbols"], y4old=zz, meta_json="{}")
    fe = np.zeros((len(e_rows), NW), np.float32); fn_ = np.zeros((len(e_rows), NW), np.float32)
    for k, i in enumerate(e_rows):
        if int(rts[i]) in fund_rows: fe[k], fn_[k] = fund_rows[int(rts[i])]
    np.savez(d + "/panel.npz", ts=rts[e_rows], f_fund_ema=fe, f_fund_now=fn_)
    env = {"PATH": "/usr/bin:/bin", "HOME": HOME, "PYTHONDONTWRITEBYTECODE": "1", "OMP_NUM_THREADS": "2", "F171_CACHE": d + "/cache.npz", "F171_TARGETS": d + "/data/dlw_targets.npz",
           "F171_OUT": d, "F171_FEA82": d + "/data/dlw_fea82.npz", "F171_PANEL": d + "/panel.npz"}
    r1 = subprocess.run([PY, "-B", CODE + "/dlw_features.py"], env=env, capture_output=True, text=True, cwd=CODE); assert r1.returncode == 0, (tag, r1.stderr[-800:])
    r2 = subprocess.run([PY, "-B", "-c", f"import os,sys; sys.path.insert(0,'{CODE}'); os.chdir('{CODE}'); import f8_higher_order_features as m; m.build()"], env=env, capture_output=True, text=True)
    assert r2.returncode == 0, (tag, r2.stderr[-800:])
    F82 = np.load(d + "/data/dlw_fea82.npz", allow_pickle=True); F89 = np.load(d + "/data/f8_fea89.npz", allow_pickle=True)
    assert [str(n) for n in F82["names"]] == N82 and [str(n) for n in F89["names"]] == N89
    ets = rts[e_rows]; pa = F82["pair_a"].astype(np.int64); ps = F82["pair_s"].astype(np.int64); out = {}
    for A in want:
        a_i = int(np.where(ets == A)[0][0]); rowm = pa == a_i
        out[int(A)] = (np.concatenate([F82["X"][rowm].astype(np.float32), F89["X"][rowm]], 1), ps[rowm].copy())
    rep = {"n_e_rows": len(e_rows), "first": U(rts[0]), "last": U(rts[-1])}
    shutil.rmtree(d, ignore_errors=True)
    return out, rep

def fund_from_record(A):
    r = REC[int(A)]; fe = np.zeros(NW, np.float32); fn_ = np.zeros(NW, np.float32)
    if "panel_fe_last" in r:
        fe[:] = r["panel_fe_last"]; fn_[:] = r["panel_fn_last"]
    else:
        m = np.asarray(r["members"], np.int64); fe[m] = np.asarray(r["X"])[:, 76]; fn_[m] = np.asarray(r["X"])[:, 77]
    return fe, fn_

def FS_job(A, start=None, members=None, fund=None, tag="FS"):
    A = int(A); start = start if start is not None else A - 11519 * 300
    rts, RD = prod_cache(start, A); pm = members if members is not None else np.asarray(REC[A]["members"], np.int64)
    fr = {A: fund if fund is not None else fund_from_record(A)}
    out, rep = run_pipeline(f"{tag}_{A}", rts, RD, lambda i, t: pm, BTCV, fr, [A])
    return A, out[A], rep

# ---- G-F10SREP: 6 T4b anchors, bitwise
T4B = [1789214400, 1789228800, 1789243200, 1789257600, 1789272000, 1789286400]
T4B_VIEW_START = TS(2026, 8, 4, 8, 5)
def val_job(args):
    a, mode = args
    return (mode,) + FS_job(a, start=(None if mode == "full40d" else T4B_VIEW_START), tag="VAL" + mode)
G = {}
with ThreadPoolExecutor(3) as ex:
    for mode, A, (X, sc), rep in ex.map(val_job, [(a, m_) for a in T4B for m_ in ("full40d", "t4b_view")]):
        r = REC[A]; g = G.setdefault(mode, {"anchors": 0, "X171_bitwise": 0, "scol_equal": 0, "f10_bitwise": 0, "max_abs_X171": 0.0, "n_e_rows": {}})
        g["anchors"] += 1; g["n_e_rows"][U(A)] = rep["n_e_rows"]
        g["scol_equal"] += int(np.array_equal(sc, np.asarray(r["combo_scol"], np.int64)))
        g["X171_bitwise"] += int(np.array_equal(X, np.asarray(r["combo_X171"], np.float32)))
        if X.shape == r["combo_X171"].shape: g["max_abs_X171"] = max(g["max_abs_X171"], float(np.nanmax(np.abs(X.astype(np.float64) - np.asarray(r["combo_X171"], np.float64)))))
        g["f10_bitwise"] += int(np.array_equal(f10_score(X), np.asarray(r["combo_f10"], np.float64)))
for mode, g in G.items(): g["PASS"] = g["X171_bitwise"] == 6 and g["scol_equal"] == 6 and g["f10_bitwise"] == 6
RC["gates"]["G-F10SREP"] = G; log("G-F10SREP", G); assert G["full40d"]["PASS"], "production 40-day cache does not reproduce the served X171"

# ---- overlap anchors: F_S
OVL = [1788624000 + 28800 * k for k in range(16)] + [1789070400]
FS = {}
with ThreadPoolExecutor(3) as ex:
    for A, (X, sc), rep in ex.map(lambda a: FS_job(a), OVL):
        assert np.array_equal(sc, np.asarray(REC[A]["members"], np.int64)); FS[A] = X
log("F_S overlap done", len(FS))
# ---- stored training rows T171
PT = DL["pair_ts"].astype(np.int64); PSD = DL["pair_s"].astype(np.int64); X82T = DL["X82"]; X89T = DL["X89"]
def T171(A):
    rm = PT == A; return np.concatenate([X82T[rm].astype(np.float32), X89T[rm]], 1), PSD[rm]
# ---- F_H: one long run, per-row production members
H_START = TS(2026, 7, 29, 0, 5); H_END = 1789070400
rts_h, RD_h = prod_cache(H_START, H_END); W0 = TS(2026, 8, 17, 4, 0)
H_FALLBACK = {}
def members_prod_row(i, t):
    """production member set of history row i; rows without a full 7-day window (first 2015 rows of this cache, all outside every scored anchor's
    180-anchor causal window and 6-anchor drank lag) get the member set of the first full-window row, so that no row is empty (recorded)."""
    if t >= W0: return weights_members(t)
    if i < 2015:
        if "m" not in H_FALLBACK:
            i2 = next(k for k in range(2015, len(rts_h)) if rts_h[k] % 14400 == 0); H_FALLBACK["row"] = U(rts_h[i2]); H_FALLBACK["m"] = members_prod_row(i2, int(rts_h[i2]))
        H_FALLBACK.setdefault("rows_filled", []).append(U(t)); return H_FALLBACK["m"]
    lo = i - 2015; st = SimpleNamespace(cd=RD_h[lo:i + 1]); return np.asarray(PMEM(st, {int(x): j for j, x in enumerate(rts_h[lo:i + 1])}, int(t), P), np.int64)
g = {"checked_anchors": 0, "equal": 0}
for t in [x for x in [W0, W0 + 14400, W0 + 28800] if x <= H_END]:
    i = int(np.where(rts_h == t)[0][0]); lo = max(i - 2015, 0); st = SimpleNamespace(cd=RD_h[lo:i + 1])
    mm = np.asarray(PMEM(st, {int(x): j for j, x in enumerate(rts_h[lo:i + 1])}, int(t), P), np.int64); g["checked_anchors"] += 1; g["equal"] += int(np.array_equal(mm, weights_members(t)))
g["PASS"] = g["equal"] == g["checked_anchors"]; RC["gates"]["G-MEMBERCODE"] = g; log("G-MEMBERCODE", g); assert g["PASS"]
FH_out, FH_rep = run_pipeline("FH", rts_h, RD_h, members_prod_row, BTCV, {A: fund_from_record(A) for A in OVL}, OVL); RC["FH_run"] = FH_rep
RC["FH_early_rows_fallback"] = {"first_full_window_row": H_FALLBACK.get("row"), "n_rows_filled": len(H_FALLBACK.get("rows_filled", [])), "last_filled": (H_FALLBACK.get("rows_filled") or [None])[-1]}
log("F_H done", FH_rep)
del rts_h, RD_h
# ---- F_D: one long run on the pod slice with training members and training btcv
TE = DL["E_ts"].astype(np.int64); TOFF = DL["offsets"]; TMEM = DL["members"]; TBT = DL["btcv"]
DMEM = {int(t): np.asarray(TMEM[TOFF[k]:TOFF[k + 1]], np.int64) for k, t in enumerate(TE)}; DBT = {int(t): float(TBT[k]) for k, t in enumerate(TE)}
rts_d = C_TS[C_TS <= 1789070400]; RD_d = C_D[:len(rts_d)]
e_rows_d = [i for i in range(len(rts_d)) if rts_d[i] % 14400 == 0 and i >= 48]
missing = [U(rts_d[i]) for i in e_rows_d if int(rts_d[i]) not in DMEM]
RC["FD_anchor_axis"] = {"e_rows": len(e_rows_d), "not_in_training_targets": missing[:10], "n_missing": len(missing)}
assert not missing, ("F_D anchors absent from training targets", missing[:5])
fund_D = {}
for A in OVL:
    X, sc = T171(A); fe = np.zeros(NW, np.float32); fn_ = np.zeros(NW, np.float32); fe[sc] = X[:, 80]; fn_[sc] = X[:, 81]; fund_D[A] = (fe, fn_)
FD_out, FD_rep = run_pipeline("FD", rts_d, RD_d, lambda i, t: DMEM[t], lambda e_rows: np.array([DBT[int(rts_d[i])] for i in e_rows], np.float32), fund_D, OVL); RC["FD_run"] = FD_rep
log("F_D done", FD_rep)
# ---- F_T: Phase-1 truncated cache vs F_S
PH1 = [1788624000, 1788710400, 1788768000, 1788825600, 1788940800, 1788998400, 1789070400, 1789195200]
PH1_START = TS(2026, 8, 3, 8, 5)
def FT_job(A):
    A = int(A); pm = np.asarray(REC[A]["members"], np.int64) if A in REC else weights_members(A)
    fund = fund_from_record(A) if A in REC else (np.zeros(NW, np.float32), np.zeros(NW, np.float32))
    _, (XT_, scT), repT = FS_job(A, start=PH1_START, members=pm, fund=fund, tag="FT")
    if A in FS: XS_ = FS[A]; scS = np.asarray(REC[A]["members"], np.int64); repS = None
    else: _, (XS_, scS), repS = FS_job(A, members=pm, fund=fund, tag="FSx")
    return A, XT_, scT, XS_, scS, repT, repS
FT = {}
with ThreadPoolExecutor(3) as ex:
    for A, XT_, scT, XS_, scS, repT, repS in ex.map(FT_job, PH1):
        assert np.array_equal(scT, scS); FT[A] = (XT_, XS_, repT["n_e_rows"], (repS or {}).get("n_e_rows"))
log("F_T done", {U(a): (v[2], v[3]) for a, v in FT.items()})

# ---- statistics
RANKLIKE = lambda j: (NAMES[j].endswith("_r") or (j >= 82 and not NAMES[j].startswith("H:")) or NAMES[j].startswith("I:"))
def pair_stats(pairs, cols):
    res = {}
    for j in cols:
        a = np.concatenate([p[0][:, j].astype(np.float64) for p in pairs]); b = np.concatenate([p[1][:, j].astype(np.float64) for p in pairs])
        d = np.abs(a - b); eqb = int((a.astype(np.float32) == b.astype(np.float32)).sum())
        if RANKLIKE(j): metric = d; kind = "abs"
        else:
            den = np.maximum(np.abs(a), np.abs(b)); metric = np.where(den > 0, d / np.where(den > 0, den, 1), 0.0); kind = "rel"
        sp = []
        for p in pairs:
            x, y = p[0][:, j].astype(np.float64), p[1][:, j].astype(np.float64)
            if np.ptp(x) > 0 and np.ptp(y) > 0: sp.append(spearmanr(x, y).correlation)
        res[NAMES[j]] = {"col": j, "kind": kind, "cells": int(len(a)), "bitwise_equal_share": round(eqb / max(len(a), 1), 6), "max": float(metric.max()), "median": float(np.median(metric)),
                         "n_gt_1e-3": int((metric > 1e-3).sum()), "share_gt_1e-3": round(float((metric > 1e-3).mean()), 6),
                         "spearman_median": (float(np.median(sp)) if sp else None), "spearman_min": (float(np.min(sp)) if sp else None)}
    return res
def align(XA, sA, XB, sB):
    c = np.intersect1d(sA, sB); ia = np.searchsorted(sA, c); ib = np.searchsorted(sB, c)
    oa = np.argsort(sA); ob = np.argsort(sB); ia = oa[np.searchsorted(sA[oa], c)]; ib = ob[np.searchsorted(sB[ob], c)]
    return XA[ia], XB[ib], c
C171 = list(range(171))
P_ST, P_SH, P_HD, P_DT, P_TS_ = [], [], [], [], []
SC = {"FS_vs_T171": [], "FS_vs_FH": [], "FH_vs_FD": [], "FD_vs_T171": [], "FT_vs_FS": []}
def scmp(xa, xb):
    fa, fb = f10_score(xa), f10_score(xb)
    za, zb = rankdata(fa) / max(len(fa) - 1, 1), rankdata(fb) / max(len(fb) - 1, 1)
    return {"spearman": float(spearmanr(fa, fb).correlation), "max_abs_dscore": float(np.max(np.abs(fa - fb))), "sd_score": float(np.std(fa)), "max_abs_drank": float(np.max(np.abs(za - zb))), "n": int(len(fa))}
fam_sub = {}
FAMS = {"x82_value": [j for j in range(80) if NAMES[j].endswith("_v")], "x82_rank": [j for j in range(80) if NAMES[j].endswith("_r")], "fund": [80, 81]}
for f_ in "ABCDEFGHIJ": FAMS[f_] = [j for j in range(82, 171) if NAMES[j].startswith(f_ + ":")]
FAMS["C_trend"] = [j for j in range(171) if NAMES[j] in ("C:trend_288", "C:trend_2016")]
FAMS["H_btcv"] = [j for j in range(171) if NAMES[j] in ("H:btcv_z", "H:r4xbtcv", "H:r24xbtcv", "H:m7xbtcv", "H:v7xbtcv")]
FAMS["H_disp"] = [j for j in range(171) if NAMES[j] in ("H:disp_z", "H:r4xdisp", "H:r24xdisp", "H:m7xdisp", "H:v7xdisp")]
FAMS["J_drank"] = [j for j in range(171) if NAMES[j].startswith("J:drank")]
for A in OVL:
    XS_, sS = FS[A], np.asarray(REC[A]["members"], np.int64); XT_, sT = T171(A); XH_, sH = FH_out[A]; XD_, sD = FD_out[A]
    a, b, c = align(XS_, sS, XT_, sT); P_ST.append((a, b)); SC["FS_vs_T171"].append(scmp(a, b))
    for fam, cols in FAMS.items():
        xs = a.copy(); xs[:, cols] = b[:, cols]; fam_sub.setdefault(fam, []).append(float(spearmanr(f10_score(a), f10_score(xs)).correlation))
    a, b, c = align(XS_, sS, XH_, sH); P_SH.append((a, b)); SC["FS_vs_FH"].append(scmp(a, b))
    a, b, c = align(XH_, sH, XD_, sD); P_HD.append((a, b)); SC["FH_vs_FD"].append(scmp(a, b))
    a, b, c = align(XD_, sD, XT_, sT); P_DT.append((a, b)); SC["FD_vs_T171"].append(scmp(a, b))
for A, (XT_, XS_, nT, nS) in FT.items():
    P_TS_.append((XT_, XS_)); o = scmp(XS_, XT_); o["anchor"] = U(A); o["n_e_rows_truncated"] = nT; o["n_e_rows_full"] = nS; SC["FT_vs_FS"].append(o)
ST = {"total_FS_vs_T171": pair_stats(P_ST, C171), "history_members_FS_vs_FH": pair_stats(P_SH, C171), "universe_btcv_FH_vs_FD": pair_stats(P_HD, C171),
      "code_identity_FD_vs_T171": pair_stats(P_DT, C171), "phase1_truncation_FT_vs_FS": pair_stats(P_TS_, C171)}
# G-F10CODE
bad = {n: v["bitwise_equal_share"] for n, v in ST["code_identity_FD_vs_T171"].items() if v["bitwise_equal_share"] < 0.9999 and n not in ("C:trend_288", "C:trend_2016")}
RC["gates"]["G-F10CODE"] = {"columns_below_0.9999_excluding_trend": bad, "trend": {n: ST["code_identity_FD_vs_T171"][n]["bitwise_equal_share"] for n in ("C:trend_288", "C:trend_2016")}, "PASS": not bad}
log("G-F10CODE", RC["gates"]["G-F10CODE"])
def summ(rows, keys=("spearman", "max_abs_dscore", "max_abs_drank")):
    o = {"n": len(rows)}
    for k in keys:
        v = [r[k] for r in rows]; o[k] = {"median": float(np.median(v)), "min": float(np.min(v)), "max": float(np.max(v))}
    return o
RC["score"] = {k: {"summary": summ(v), "per_anchor": v} for k, v in SC.items()}
RC["score_family_substitution_FS_with_T171"] = {f: {"spearman_median": float(np.median(v)), "spearman_min": float(np.min(v))} for f, v in fam_sub.items()}
RC["families"] = {f: [NAMES[j] for j in cols] for f, cols in FAMS.items()}
RC["pair_stats"] = ST
with open(OUTC, "w", newline="") as f:
    wr = csv.writer(f); hdr = ["model", "col_idx", "name"]
    for pk in ST: hdr += [f"{pk}:{x}" for x in ("kind", "bitwise_equal_share", "max", "median", "n_gt_1e-3", "share_gt_1e-3", "spearman_median", "spearman_min")]
    wr.writerow(hdr)
    for j in range(171):
        row = ["f10", j, NAMES[j]]
        for pk, pv in ST.items():
            v = pv[NAMES[j]]; row += [v["kind"], v["bitwise_equal_share"], v["max"], v["median"], v["n_gt_1e-3"], v["share_gt_1e-3"], v["spearman_median"], v["spearman_min"]]
        wr.writerow(row)
RC["outputs"] = {"csv": OUTC, "csv_sha256": gsha(OUTC)}
RC["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()); RC["wall_s"] = round(time.time() - T0, 1)
json.dump(RC, open(OUTJ, "w"), indent=1, default=str)
log("DONE parity_f10 wall_s", RC["wall_s"], json.dumps({k: RC["score"][k]["summary"]["spearman"] for k in RC["score"]}))
