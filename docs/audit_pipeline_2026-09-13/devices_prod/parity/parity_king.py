#!/usr/bin/env python3
"""parity_king.py -- AUDIT_PROD P4 (king 78-column train/serve parity) + P10 (king trained on float16, served float32). Mac, production interpreter
(~/wide_shadow/venv/bin/python, lightgbm 4.7.0 = the serving process's library). Measurement only, no P&L. Every input is read-only; the device
writes only /Users/haosiyu/Desktop/quant_research/docs/audit_pipeline_2026-09-13/receipts_prod/parity_king.{json,csv}.

Objects
  S      served king input X (78 keep columns) and pred for 47 anchors 2026-09-05 16Z .. 2026-09-13 08Z: T4 served-arm records (41 anchors, king L-inf vs live
         <= 9.3e-10 per T4 PC1) + T4b served-arm records (6 anchors, bitwise live per T4b PCB). Re-verified here by G-PRED and G-SREP.
  S_rep  production feature code, executed from the production file text (~/wide_shadow/shadow_loop_v3.py e9c98374 lines 355-404, members + 80 kline columns),
         on a read-only copy of the live rolling cache (state/rolling.npz after the 12Z anchor) truncated at each anchor; cols 80/81 taken from S.
  T      stored king training features wide_fea_v4_x0910.npy (builder pod_fea_ext_clamp.py b9f9c728 = in-service builder pod_fea_ext.py 02157bda + E-0909-A clamp),
         members K, 33 anchors 09-05 12Z .. 09-10 20Z (overlap with S: 32 anchors).
  T_rep  builder formula (pod_fea_ext_clamp.py L13-17, L43-58, L67-76 logic: float64 cumsum, window rows [E-w, E-1], float32, stored float16, ranks over members)
         on the pod holefix2_x0910 cache slice, members K -> must equal T (G-TREP).
  T_P    same, members P (served member set)                                  -> universe effect  = T_rep vs T_P (rank columns)
  T_PE   same with the production clock (rows [E-w+1, E]), members P, float16 -> clock effect     = T_P vs T_PE
  T_PE32 T_PE before the float16 store                                        -> storage effect   = T_PE vs T_PE32
                                                                              -> reduction effect = T_PE32 vs S_rep (float64 vs float32 window sums)
  S16    S cast to float16 and back before predict (P10 counterfactual)
Gates (all must pass before any comparison is reported as valid): G-PRED booster(S) == recorded pred bitwise; G-SREP S_rep keep columns 0..75 == S bitwise and
S_rep members == recorded members; G-TREP T_rep == T bitwise on >= 99.99% of cells per column with |diff| <= 1 float16 ulp elsewhere; G-DATA S_rep on the pod slice
(live450 only) == S bitwise for the 32 overlap anchors.
Launch (verbatim): see devices_prod/parity/parity_run_mac.sh king
"""
import os, sys, json, time, hashlib, stat, csv
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "env whitelist argv[1] required"
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
from types import SimpleNamespace
from scipy.stats import rankdata, spearmanr
import lightgbm as lgb
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
HOME = "/Users/haosiyu"; STG = HOME + "/cc_tmp/aud_prod/parity_stage"; REPO = HOME + "/Desktop/quant_research"
OUTJ = REPO + "/docs/audit_pipeline_2026-09-13/receipts_prod/parity_king.json"; OUTC = REPO + "/docs/audit_pipeline_2026-09-13/receipts_prod/parity_king_columns.csv"
INPUTS = {
    "shadow_loop_v3.py": (HOME + "/wide_shadow/shadow_loop_v3.py", "e9c9837412130884bc72d4bbcb52b33e9dc8660274b76ae68f46639d2d21b36e"),
    "config.json": (HOME + "/wide_shadow/shadow_bundle/config.json", "3a8422f377519cac77b0c42305d2ba40a4b7a42a830f0542bda844f66647c94e"),
    "slow2026.txt": (HOME + "/wide_shadow/shadow_bundle/slow2026.txt", "8d79186b6380132cb67684acf1ebfcdb2c53261c850f46a4908b06bfa7a81282"),
    "T4_served": (STG + "/T4_replay_rec_served.npy", "942d20a91496f60b626a18cac13185b00f5ac2cd26c5300c7d57e5fefcb3c92f"),
    "T4b_served": (STG + "/T4b_replay_rec_served.npy", "6f121afe2228d318ea9458926bb1c5760b55f31db63f9e7a9a35ea0e4641971e"),
    "rolling_live_copy": (STG + "/rolling_live_copy.npz", "9ef804fea8b34f6c86f21f637d6dce82637cb1c6e15f322cfde4d6c586034ea4"),
    "cache_slice_x0910": (STG + "/cache_slice_x0910.npz", "5103279047b2db7b2f446aa0812048cd29c97b96390669e2658aa58b76d7ae68"),
    "king_x0910_rows": (STG + "/king_x0910_rows.npz", "14c8f0ef92fa093e5a91e3a47b252a4b47a6605a05cd0a2addf51dd5f3a37942"),
}
RC = {"self_sha256": gsha(os.path.abspath(__file__)), "env": {"whitelist": sorted(WHITE), "actual": {k: os.environ[k] for k in sorted(os.environ)}}, "argv": sys.argv,
      "python": sys.version.split()[0], "numpy": np.__version__, "lightgbm": lgb.__version__, "inputs": {}, "gates": {}, "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
for k, (p, h) in INPUTS.items():
    g = gsha(p); RC["inputs"][k] = {"path": p, "sha256": g}; assert g == h, ("INPUT SHA MISMATCH", k, g)
log("inputs verified")
cfg = json.load(open(INPUTS["config.json"][0])); KEEP = [int(k) for k in cfg["keep_idx"]]; KNAMES = [str(n) for n in cfg["keep_names"]]; P = cfg["params"]
SYMS = [str(s) for s in cfg["symbols_panel"]]; LIVE = set(cfg["symbols_live"]); LIVEM = np.array([s in LIVE for s in SYMS])
assert KEEP == list(range(4, 82)) and len(KNAMES) == 78

# ---------------- production feature code, executed from the production file text
SRC = open(INPUTS["shadow_loop_v3.py"][0], encoding="utf-8").read().split("\n")
assert SRC[182] == "WINS = (48, 288, 864, 2016, 8640)", SRC[182]
BLK = SRC[354:404]
assert BLK[0] == "    CDf = st.cd.astype(np.float32)" and BLK[-1] == "        FE_ANCH[:, col] = rr; col += 1", (BLK[0], BLK[-1])
FN_SRC = "def _prod_feat(st, row_of, anchor, P, append_log):\n" + "\n".join(BLK) + "\n    return m, FE_ANCH, names_order\n"
NS = {"np": np, "WINS": (48, 288, 864, 2016, 8640)}
exec(compile(FN_SRC, "shadow_loop_v3.py[L355-404]", "exec"), NS); PROD_FEAT = NS["_prod_feat"]
RC["production_block"] = {"file_lines": "355-404", "block_sha256": hashlib.sha256("\n".join(BLK).encode()).hexdigest()}
def prod_features(C16, TS, A):
    ai = int(np.where(TS == A)[0][0]); skips = []
    st = SimpleNamespace(cd=C16[:ai + 1]); row_of = {int(t): i for i, t in enumerate(TS[:ai + 1])}
    out = PROD_FEAT(st, row_of, int(A), P, lambda r: skips.append(r))
    assert out is not None and not skips, ("production block skipped", U(A), skips)
    m, FE, names_order = out; return np.asarray(m, np.int64), FE, names_order

# ---------------- served records
REC = {}
for key in ("T4_served", "T4b_served"):
    for r in np.load(INPUTS[key][0], allow_pickle=True):
        a = int(r["anchor"]); assert a not in REC; REC[a] = {"members": np.asarray(r["members"], np.int64), "X": np.asarray(r["X"], np.float32), "pred": np.asarray(r["pred"], np.float64),
                                                          "w3m": [float(x) for x in r["w3_masked"]], "src": key}
SA = sorted(REC); assert len(SA) == 47 and SA[0] == 1788624000 and SA[-1] == 1789286400 and all(b - a == 14400 for a, b in zip(SA, SA[1:])), (len(SA), SA[:2], SA[-2:])
booster = lgb.Booster(model_file=INPUTS["slow2026.txt"][0])
assert booster.num_feature() == 78 and booster.num_trees() == 400, (booster.num_feature(), booster.num_trees())
g = {"anchors": len(SA), "bitwise_equal": 0, "max_abs": 0.0}
for a in SA:
    p = booster.predict(REC[a]["X"]); d = float(np.max(np.abs(p - REC[a]["pred"]))); g["max_abs"] = max(g["max_abs"], d); g["bitwise_equal"] += int(np.array_equal(p, REC[a]["pred"]))
g["PASS"] = g["bitwise_equal"] == len(SA); RC["gates"]["G-PRED"] = g; log("G-PRED", g); assert g["PASS"]

# ---------------- S_rep on the live rolling copy
RZ = np.load(INPUTS["rolling_live_copy"][0]); RTS = RZ["ts"].astype(np.int64); RD = RZ["data"]; assert RD.dtype == np.float16 and RD.shape[1:] == (829, 7)
SREP = {}; g = {"anchors": 0, "members_equal": 0, "keep0_75_bitwise_equal": 0, "max_abs_keep0_75": 0.0}
for a in SA:
    m, FE, names_order = prod_features(RD, RTS, a); SREP[a] = (m, FE)
    X = FE[:, KEEP]; g["anchors"] += 1
    me = np.array_equal(m, REC[a]["members"]); g["members_equal"] += int(me)
    if me:
        eq = np.array_equal(X[:, :76], REC[a]["X"][:, :76]); g["keep0_75_bitwise_equal"] += int(eq)
        g["max_abs_keep0_75"] = max(g["max_abs_keep0_75"], float(np.max(np.abs(X[:, :76].astype(np.float64) - REC[a]["X"][:, :76]))))
g["names_order_head"] = list(names_order)[:3]
g["PASS"] = g["members_equal"] == len(SA) and g["keep0_75_bitwise_equal"] == len(SA); RC["gates"]["G-SREP"] = g; log("G-SREP", g); assert g["PASS"]
del RD

# ---------------- pod slice: builder formula arms + production code on live450
CZ = np.load(INPUTS["cache_slice_x0910"][0], allow_pickle=True); CTS = CZ["ts"].astype(np.int64); CD = CZ["data"]
assert [str(s) for s in CZ["symbols"]] == SYMS and CD.dtype == np.float16 and (np.diff(CTS) == 300).all()
KR = np.load(INPUTS["king_x0910_rows"][0], allow_pickle=True); KE = KR["E_ts"].astype(np.int64); KOFF = KR["offsets"]; KMEM = KR["members"]; KX = KR["X"]; KN = [str(n) for n in KR["names"]]
assert KN[4:] == KNAMES, "x0910 names != keep_names"
OV = [int(a) for a in KE if int(a) in REC]; assert len(OV) == 32 and OV[0] == 1788624000 and OV[-1] == 1789070400, (len(OV), OV[:1], OV[-1:])
K_OF = {int(a): (np.asarray(KMEM[KOFF[i]:KOFF[i + 1]], np.int64), np.asarray(KX[KOFF[i]:KOFF[i + 1]], np.float16)) for i, a in enumerate(KE)}
CHN = ["ret5", "range", "cpos", "log_qv", "log_cnt", "log_avgsz", "tbf"]; WINS = (48, 288, 864, 2016, 8640); NW = 829
ERI = {a: int(np.where(CTS == a)[0][0]) for a in KE}
EA = np.array([ERI[int(a)] for a in KE], np.int64)
def cs_pair(x):   # pod_fea_ext_clamp.py L13-17 verbatim
    fin = np.isfinite(x)
    xz = np.where(fin, x, 0).astype(np.float64)
    return (np.concatenate([np.zeros((1, NW)), np.cumsum(xz, 0)]),
            np.concatenate([np.zeros((1, NW), np.int32), np.cumsum(fin, 0, dtype=np.int32)]))
VALS = {"Em1": [], "E": []}   # each: list of 40 arrays (nA, 829) float32, order = builder VAL order
for c, nm in enumerate(CHN):
    s_, f_ = cs_pair(CD[:, :, c].astype(np.float32))
    for clock, HI in (("Em1", EA), ("E", EA + 1)):
        for w in WINS:
            Ew = np.maximum(HI - w, 0); nf = np.maximum(f_[HI] - f_[Ew], 1)
            VALS[clock].append((s_[HI] - s_[Ew]).astype(np.float32) if nm == "ret5" else ((s_[HI] - s_[Ew]) / nf).astype(np.float32))
    if c == 0:
        CS_r = (s_, f_)
    del s_, f_
r2s, r2f = cs_pair((CD[:, :, 0].astype(np.float64)) ** 2)
VOL = {"Em1": [], "E": []}
for clock, HI in (("Em1", EA), ("E", EA + 1)):
    for w in WINS:
        Ew = np.maximum(HI - w, 0)
        nf = np.maximum(CS_r[1][HI] - CS_r[1][Ew], 1)
        mm = (CS_r[0][HI] - CS_r[0][Ew]) / nf
        vv = np.sqrt(np.maximum((r2s[HI] - r2s[Ew]) / nf - mm ** 2, 0))
        VOL[clock].append(vv.astype(np.float32))
for clock in VALS: VALS[clock] = VALS[clock] + VOL[clock]
del r2s, r2f, CS_r, VOL
AIDX = {int(a): i for i, a in enumerate(KE)}
def builder_rows(a, members, clock, store16=True):   # pod_fea_ext_clamp.py L67-76 logic (80 kline columns)
    i = AIDX[a]; m = members; out = np.zeros((len(m), 80), np.float32); col = 0
    for v in VALS[clock]:
        x = v[i, m]
        out[:, col] = np.clip(np.nan_to_num(x, nan=0), -1e4, 1e4); col += 1
        ok = np.isfinite(x); rr = np.zeros(len(m), np.float32)
        if ok.sum() >= 10:
            rr[ok] = rankdata(x[ok]) / max(ok.sum() - 1, 1) - 0.5
        out[:, col] = rr; col += 1
    return out.astype(np.float16) if store16 else out
# G-TREP
ULP16 = lambda v: np.abs(np.nextafter(v.astype(np.float16), np.float16(np.inf)).astype(np.float64) - v.astype(np.float16).astype(np.float64))
g = {"anchors": 0, "cells": 0, "bitwise_equal": 0, "max_abs_over_ulp": 0.0, "per_column_min_equal_share": 1.0}
coleq = np.zeros(80); colcells = 0
for a in KE:
    a = int(a); mK, XK = K_OF[a]; TR = builder_rows(a, mK, "Em1", True)
    eq = (TR.view(np.uint16) == XK[:, :80].view(np.uint16)) | (TR == XK[:, :80])
    g["anchors"] += 1; g["cells"] += int(eq.size); g["bitwise_equal"] += int(eq.sum()); coleq += eq.sum(0); colcells += eq.shape[0]
    if (~eq).any():
        d = np.abs(TR.astype(np.float64) - XK[:, :80].astype(np.float64)); u = np.maximum(ULP16(XK[:, :80]), 1e-30)
        g["max_abs_over_ulp"] = max(g["max_abs_over_ulp"], float(np.max((d / u)[~eq])))
g["per_column_min_equal_share"] = float((coleq / colcells).min()); g["equal_share"] = g["bitwise_equal"] / g["cells"]
g["PASS"] = g["per_column_min_equal_share"] >= 0.9999 and g["max_abs_over_ulp"] <= 1.0 + 1e-9; RC["gates"]["G-TREP"] = g; log("G-TREP", g); assert g["PASS"]
# G-DATA: production code on the pod slice restricted to the live 450
CDL = np.where(LIVEM[None, :, None], CD, np.float16(np.nan))
g = {"anchors": 0, "members_equal": 0, "keep0_75_bitwise_equal": 0}
for a in OV:
    m, FE, _ = prod_features(CDL, CTS, a); g["anchors"] += 1
    if np.array_equal(m, REC[a]["members"]):
        g["members_equal"] += 1; g["keep0_75_bitwise_equal"] += int(np.array_equal(FE[:, KEEP][:, :76], REC[a]["X"][:, :76]))
g["PASS"] = g["members_equal"] == len(OV) and g["keep0_75_bitwise_equal"] == len(OV); RC["gates"]["G-DATA"] = g; log("G-DATA", g); assert g["PASS"]
del CDL

# ---------------- per-column comparison statistics
COLNAMES = [str(n) for n in KN]   # 82 names, index = feature column
assert [n[:-2] for n in COLNAMES[0:80:2]] == list(names_order), "production value-name order != builder column order"
assert COLNAMES[80:] == ["fund_ema", "fund_now"]
def is_rank(j): return COLNAMES[j].endswith("_r")
def pair_stats(pairs, cols):
    """pairs: list of (A, B) arrays (n_i, 82-or-80 aligned rows, same names); returns per column dict."""
    res = {}
    for j in cols:
        a = np.concatenate([p[0][:, j].astype(np.float64) for p in pairs]); b = np.concatenate([p[1][:, j].astype(np.float64) for p in pairs])
        d = np.abs(a - b); eqb = int((a.astype(np.float32) == b.astype(np.float32)).sum())
        if is_rank(j):
            metric = d; kind = "abs_rank_units"
        else:
            den = np.maximum(np.abs(a), np.abs(b)); metric = np.where(den > 0, d / np.where(den > 0, den, 1), 0.0); kind = "rel"
        sp = []
        for p in pairs:
            x, y = p[0][:, j].astype(np.float64), p[1][:, j].astype(np.float64)
            if np.ptp(x) > 0 and np.ptp(y) > 0: sp.append(spearmanr(x, y).correlation)
        res[j] = {"name": COLNAMES[j], "kind": kind, "cells": int(len(a)), "bitwise_equal_share": round(eqb / max(len(a), 1), 6), "max": float(metric.max()), "median": float(np.median(metric)),
                  "p99": float(np.percentile(metric, 99)), "n_gt_1e-3": int((metric > 1e-3).sum()), "share_gt_1e-3": round(float((metric > 1e-3).mean()), 6),
                  "spearman_median": (float(np.median(sp)) if sp else None), "spearman_min": (float(np.min(sp)) if sp else None), "anchors_spearman": len(sp)}
    return res
FULL = lambda FE82: FE82   # S_rep FE_ANCH is 82 columns (80/81 NaN until serving fills them)
P_TOTAL, P_UNIV, P_CLOCK, P_STORE, P_RED = [], [], [], [], []
ARMS = {}
for a in OV:
    mP = REC[a]["members"]; mK, XK = K_OF[a]
    S82 = SREP[a][1].copy(); S82[:, 80] = REC[a]["X"][:, 76]; S82[:, 81] = REC[a]["X"][:, 77]
    TP = builder_rows(a, mP, "Em1", True); TPE = builder_rows(a, mP, "E", True); TPE32 = builder_rows(a, mP, "E", False); TREP = builder_rows(a, mK, "Em1", True)
    ARMS[a] = {"TP": TP, "TPE": TPE, "TPE32": TPE32, "TREP": TREP, "mK": mK}
    common = np.intersect1d(mP, mK); iP = np.searchsorted(mP, common); iK = np.searchsorted(mK, common)
    Tfull = XK.astype(np.float32)                      # 82 stored columns (80 kline + fund v0 + fund_now)
    P_TOTAL.append((S82[iP], Tfull[iK]))
    P_UNIV.append((TREP[iK].astype(np.float32), TP[iP].astype(np.float32)))
    P_CLOCK.append((TP.astype(np.float32), TPE.astype(np.float32)))
    P_STORE.append((TPE.astype(np.float32), TPE32))
    P_RED.append((TPE32, S82[:, :80]))
COLS82 = list(range(82)); COLS80 = list(range(80))
ST = {"total_S_vs_T": pair_stats(P_TOTAL, COLS82), "universe_Trep_vs_TP": pair_stats(P_UNIV, COLS80), "clock_TP_vs_TPE": pair_stats(P_CLOCK, COLS80),
      "store_TPE_vs_TPE32": pair_stats(P_STORE, COLS80), "reduction_TPE32_vs_S": pair_stats(P_RED, COLS80)}
RC["common_names_per_anchor"] = {"median": float(np.median([len(p[0]) for p in P_TOTAL])), "min": int(min(len(p[0]) for p in P_TOTAL))}
log("pair stats done")

# ---------------- score level
def xz(v):   # shadow_loop_v3.py L464-468
    okz = np.isfinite(v); out = np.full(len(v), np.nan)
    if okz.sum() >= 10: out[okz] = rankdata(v[okz]) / max(okz.sum() - 1, 1) - 0.5
    return out
def decile(v): r = rankdata(v); return np.minimum((10 * (r - 1) / len(v)).astype(int), 9)
def cmp_scores(p0, p1, w3m0=None):
    z0, z1 = xz(p0), xz(p1); d0, d1 = decile(p0), decile(p1); top0, top1 = set(np.where(d0 == 9)[0]), set(np.where(d1 == 9)[0]); bot0, bot1 = set(np.where(d0 == 0)[0]), set(np.where(d1 == 0)[0])
    o = {"spearman": float(spearmanr(p0, p1).correlation), "max_abs_dpred": float(np.max(np.abs(p1 - p0))), "sd_pred": float(np.std(p0)), "n": int(len(p0)),
         "n_rank_changed": int((np.abs(z1 - z0) > 1e-12).sum()), "n_decile_changed": int((d0 != d1).sum()),
         "top_decile_overlap": len(top0 & top1) / max(len(top0), 1), "bottom_decile_overlap": len(bot0 & bot1) / max(len(bot0), 1), "max_abs_dlegz": float(np.max(np.abs(z1 - z0)))}
    if w3m0 is not None: o["max_abs_dz_kc"] = float(w3m0 * o["max_abs_dlegz"]); o["l1_dz_kc"] = float(w3m0 * np.abs(z1 - z0).sum())
    return o
def summarize(rows, keys=("spearman", "max_abs_dpred", "n_rank_changed", "n_decile_changed", "top_decile_overlap", "bottom_decile_overlap", "max_abs_dlegz", "max_abs_dz_kc", "l1_dz_kc", "leaf_rows_changed", "leaf_pairs_changed")):
    out = {"anchors": len(rows)}
    for k in keys:
        v = [r[k] for r in rows if k in r]
        if v: out[k] = {"median": float(np.median(v)), "min": float(np.min(v)), "max": float(np.max(v)), "sum": float(np.sum(v))}
    return out
# P10: serving casts to float16 before predict (all 47 served anchors)
p10 = []; percol_flip_rows = np.zeros(78, np.int64); percol_flip_pairs = np.zeros(78, np.int64); percol_rank_changed = np.zeros(78, np.int64); percol_maxd = np.zeros(78)
for a in SA:
    X = REC[a]["X"]; X16 = X.astype(np.float16).astype(np.float32); p0 = REC[a]["pred"]; p1 = booster.predict(X16)
    L0 = booster.predict(X, pred_leaf=True); L1 = booster.predict(X16, pred_leaf=True)
    o = cmp_scores(p0, p1, REC[a]["w3m"][0]); o["anchor"] = U(a); o["leaf_rows_changed"] = int((L0 != L1).any(1).sum()); o["leaf_pairs_changed"] = int((L0 != L1).sum())
    o["cells_changed_by_cast"] = int((X16 != X).sum()); p10.append(o)
    z0 = xz(p0)
    for k in range(78):
        Xk = X.copy(); Xk[:, k] = X16[:, k]
        if np.array_equal(Xk[:, k], X[:, k]): continue
        Lk = booster.predict(Xk, pred_leaf=True); ch = (Lk != L0)
        if ch.any():
            percol_flip_rows[k] += int(ch.any(1).sum()); percol_flip_pairs[k] += int(ch.sum())
            pk = booster.predict(Xk); percol_maxd[k] = max(percol_maxd[k], float(np.max(np.abs(pk - p0)))); percol_rank_changed[k] += int((np.abs(xz(pk) - z0) > 1e-12).sum())
RC["P10_f16_cast"] = {"per_anchor": p10, "summary": summarize(p10)}
log("P10 done", RC["P10_f16_cast"]["summary"])
# thresholds and the float16 risk intervals
def walk(node, acc):
    if "split_feature" in node:
        acc.append((int(node["split_feature"]), float(node["threshold"]), node.get("decision_type"), node.get("missing_type"), bool(node.get("default_left")))); walk(node["left_child"], acc); walk(node["right_child"], acc)
dm = booster.dump_model(); SPL = []
for t in dm["tree_info"]: walk(t["tree_structure"], SPL)
assert all(s[2] == "<=" for s in SPL), "non-numerical decision types present"
def f16_risk(t):
    """width of the float32 interval whose float16 round-trip lands on the other side of threshold t (LightGBM rule: x <= t goes left)."""
    if not np.isfinite(t) or abs(t) > 65504: return 0.0, None, None
    f = np.float16(t); fv = float(f)
    if fv <= t: a_ = fv; b_ = float(np.nextafter(f, np.float16(np.inf)))
    else: b_ = fv; a_ = float(np.nextafter(f, np.float16(-np.inf)))
    if a_ == t: b_ = float(np.nextafter(np.float16(a_), np.float16(np.inf)))
    mid = (a_ + b_) / 2.0
    return abs(t - mid), (min(t, mid), max(t, mid)), b_ - a_
THR = {}
for (fj, t, dt, mt, dl) in SPL:
    w, iv, ulp = f16_risk(t); d = THR.setdefault(fj, {"thr": [], "risk_iv": [], "risk_rel": [], "missing_types": set()})
    d["thr"].append(t); d["missing_types"].add(str(mt))
    if w > 0: d["risk_iv"].append(iv); d["risk_rel"].append(w / ulp)
ALLX = np.concatenate([REC[a]["X"] for a in SA])
imp_gain = booster.feature_importance("gain"); imp_split = booster.feature_importance("split")
gain_rank = {int(k): r + 1 for r, k in enumerate(np.argsort(-imp_gain))}
THR_TAB = {}
for k in range(78):
    d = THR.get(k, {"thr": [], "risk_iv": [], "risk_rel": [], "missing_types": set()}); thr = np.array(d["thr"]) if d["thr"] else np.array([])
    exposure = 0
    if d["risk_iv"]:
        ivs = sorted(set((float(x[0]), float(x[1])) for x in d["risk_iv"])); merged = []
        for lo_, hi_ in ivs:
            if merged and lo_ <= merged[-1][1]: merged[-1][1] = max(merged[-1][1], hi_)
            else: merged.append([lo_, hi_])
        lo = np.array([x[0] for x in merged]); hi = np.array([x[1] for x in merged]); col = ALLX[:, k].astype(np.float64)
        idx = np.searchsorted(lo, col, side="right") - 1; okc = idx >= 0; j2 = np.clip(idx, 0, len(lo) - 1)
        exposure = int((okc & (col >= lo[j2]) & (col <= hi[j2])).sum())
    THR_TAB[k] = {"name": KNAMES[k], "gain": float(imp_gain[k]), "gain_rank": gain_rank[k], "split": int(imp_split[k]), "n_thresholds": int(len(thr)),
                  "thr_abs_min": (float(np.min(np.abs(thr))) if len(thr) else None), "thr_abs_max": (float(np.max(np.abs(thr))) if len(thr) else None),
                  "n_thr_with_f16_risk": len(d["risk_iv"]), "median_risk_width_over_ulp": (float(np.median(d["risk_rel"])) if d["risk_rel"] else 0.0),
                  "served_cells_in_risk_interval": int(exposure), "served_cells": int(ALLX.shape[0]), "missing_types": sorted(d["missing_types"]),
                  "P10_leaf_rows_changed_single_col": int(percol_flip_rows[k]), "P10_leaf_pairs_changed_single_col": int(percol_flip_pairs[k]),
                  "P10_rank_changed_single_col": int(percol_rank_changed[k]), "P10_max_abs_dpred_single_col": float(percol_maxd[k])}
RC["thresholds_f16"] = {"n_splits": len(SPL), "per_column": THR_TAB}
log("thresholds done")
# training representation at the served universe (overlap anchors)
clk = {"TP": [], "TPE": [], "TPE32": [], "Tstored_common_fund_from_S": [], "Tstored_common_as_stored": [], "universe_common": []}
percol_clock = {k: [] for k in range(76)}
for a in OV:
    X = REC[a]["X"]; p0 = REC[a]["pred"]; mP = REC[a]["members"]; w0 = REC[a]["w3m"][0]; A_ = ARMS[a]
    for arm in ("TP", "TPE", "TPE32"):
        F = A_[arm].astype(np.float32); assert F.shape[1] == 80; Xa = X.copy(); Xa[:, :76] = F[:, KEEP[:76]]
        o = cmp_scores(p0, booster.predict(Xa), w0); o["anchor"] = U(a); clk[arm].append(o)
    mK, XK = K_OF[a]; common = np.intersect1d(mP, mK); iP = np.searchsorted(mP, common); iK = np.searchsorted(mK, common)
    XT = XK[iK][:, KEEP].astype(np.float32); pT_as = booster.predict(XT); XTf = XT.copy(); XTf[:, 76:78] = X[iP, 76:78]; pT_f = booster.predict(XTf)
    o = cmp_scores(p0[iP], pT_f); o["anchor"] = U(a); clk["Tstored_common_fund_from_S"].append(o)
    o = cmp_scores(p0[iP], pT_as); o["anchor"] = U(a); clk["Tstored_common_as_stored"].append(o)
    XU = A_["TREP"][iK][:, KEEP[:76]].astype(np.float32); XU = np.concatenate([XU, X[iP, 76:78]], 1)
    XV = A_["TP"][iP][:, KEEP[:76]].astype(np.float32); XV = np.concatenate([XV, X[iP, 76:78]], 1)
    o = cmp_scores(booster.predict(XV), booster.predict(XU)); o["anchor"] = U(a); clk["universe_common"].append(o)
    TPk = A_["TP"].astype(np.float32)[:, KEEP[:76]]
    for k in range(76):
        Xk = X.copy(); Xk[:, k] = TPk[:, k]; pk = booster.predict(Xk)
        percol_clock[k].append((float(spearmanr(p0, pk).correlation), int((decile(p0) != decile(pk)).sum()), float(np.max(np.abs(pk - p0)))))
RC["score_arms"] = {k: {"summary": summarize(v), "per_anchor": v} for k, v in clk.items()}
RC["score_clock_substitution_per_column"] = {KNAMES[k]: {"spearman_median": float(np.median([x[0] for x in v])), "spearman_min": float(np.min([x[0] for x in v])),
                                                         "decile_changed_median": float(np.median([x[1] for x in v])), "max_abs_dpred": float(np.max([x[2] for x in v]))} for k, v in percol_clock.items()}
log("score arms done", {k: RC["score_arms"][k]["summary"].get("spearman") for k in RC["score_arms"]})

# ---------------- write receipt + per-column CSV
RC["pair_stats"] = {pk: {COLNAMES[j]: v for j, v in pv.items()} for pk, pv in ST.items()}
with open(OUTC, "w", newline="") as f:
    wr = csv.writer(f)
    hdr = ["model", "col_idx", "keep_pos", "name", "gain", "gain_rank", "split"]
    for pk in ST: hdr += [f"{pk}:{x}" for x in ("kind", "bitwise_equal_share", "max", "median", "n_gt_1e-3", "share_gt_1e-3", "spearman_median", "spearman_min")]
    hdr += ["P10:n_thresholds", "P10:n_thr_with_f16_risk", "P10:served_cells_in_risk_interval", "P10:leaf_rows_changed_single_col", "P10:rank_changed_single_col", "P10:max_abs_dpred_single_col",
            "clock_subst:spearman_median", "clock_subst:decile_changed_median", "clock_subst:max_abs_dpred"]
    wr.writerow(hdr)
    for j in range(82):
        kp = j - 4 if j >= 4 else None
        row = ["king", j, kp, COLNAMES[j]] + ([round(THR_TAB[kp]["gain"], 3), THR_TAB[kp]["gain_rank"], THR_TAB[kp]["split"]] if kp is not None else ["", "", ""])
        for pk, pv in ST.items():
            v = pv.get(j)
            row += ([v["kind"], v["bitwise_equal_share"], v["max"], v["median"], v["n_gt_1e-3"], v["share_gt_1e-3"], v["spearman_median"], v["spearman_min"]] if v else [""] * 8)
        if kp is not None:
            t = THR_TAB[kp]; row += [t["n_thresholds"], t["n_thr_with_f16_risk"], t["served_cells_in_risk_interval"], t["P10_leaf_rows_changed_single_col"], t["P10_rank_changed_single_col"], t["P10_max_abs_dpred_single_col"]]
            c = RC["score_clock_substitution_per_column"].get(KNAMES[kp]) if kp < 76 else None
            row += ([c["spearman_median"], c["decile_changed_median"], c["max_abs_dpred"]] if c else ["", "", ""])
        else:
            row += [""] * 9
        wr.writerow(row)
RC["outputs"] = {"csv": OUTC, "csv_sha256": gsha(OUTC)}
RC["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()); RC["wall_s"] = round(time.time() - T0, 1)
json.dump(RC, open(OUTJ, "w"), indent=1, default=str)
log("DONE parity_king wall_s", RC["wall_s"])
