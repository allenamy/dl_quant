#!/usr/bin/env python3
"""t1_states.py — pod2 (PREREG_T1 §4, GATE X, GATE S).
Causal state variables at every anchor of the x0910 accounting meta that has a panel row:
  R24/R72 = compounded trailing returns from the accounting meta y4 rows k-6..k-1 / k-18..k-1 (RAW, never the 5m cache),
  DISP24/72, BREADTH24/72, BTC24/72, SIGF, MUF, PUMP72, PUMPSPR72 on m = members[k] ∩ CRYPTO m1 umask (last mask row carried forward).
GATE X: x0910 meta / panel equal the pinned meta / v2ext panel on overlapping rows. GATE S: perturbing y4[k:] leaves states at k unchanged.
Launch: env -i PATH=... HOME=/root /workspace/venv/bin/python devices/t1_states.py PATH,HOME,LC_CTYPE
"""
import os, sys, json, time, hashlib
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "whitelist argv[1]"
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
R = "/workspace/uplift_r2_2026-09-13/T1"
PREREG_SHA = "9548214267b5a44900ba90fee6b2fb2bbeb77964d562628b77678b16c56777f6"; AMEND_SHA = "a7628a7268cad50976470e5b6334c9086af9805bf786dac0ed51f496374da373"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
assert sha(R + "/PREREG_T1_edge_diagnosis_2026-09-13.md") == PREREG_SHA and sha(R + "/PREREG_AMENDMENT_1_T1_2026-09-13.md") == AMEND_SHA
AMEND2_SHA = "12b262fd5b5ec47b7741c10b500baa9bc726cfc873ef7c5b07edf39b897e7207"; assert sha(R + "/PREREG_AMENDMENT_2_T1_2026-09-13.md") == AMEND2_SHA
MX = "/workspace/uplift_2026-09-11/r6/out/meta_newprod_v4_x0910.npz"; M0 = "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"
PX = "/workspace/uplift_2026-09-11/r6/out/wide_panel_4h_v2ext_x0910.npz"; P0 = "/workspace/data/wide_panel_4h_v2ext.npz"
UMP = "/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"
INPUTS = {p: sha(p) for p in (MX, M0, PX, P0, UMP)}
t0 = time.time()
ZX = np.load(MX, allow_pickle=True); Z0 = np.load(M0, allow_pickle=True)
PXz = np.load(PX, allow_pickle=True); P0z = np.load(P0, allow_pickle=True); UM = np.load(UMP, allow_pickle=True)
E = ZX["E_ts"].astype(np.int64); MEM = ZX["members"]; QVK = ZX["qvk"]; Y = ZX["y4"].astype(np.float64)   # AMENDMENT 2: state member set = finite qvk ∩ umask
SYM = [str(s) for s in PXz["symbols"]]; assert SYM == [str(s) for s in P0z["symbols"]] == [str(s) for s in UM["symbols"]]
# ---------------- GATE X ----------------
GX = {}
E0 = Z0["E_ts"].astype(np.int64); n0 = len(E0)
GX["meta_ts_prefix_equal"] = bool(np.array_equal(E[:n0], E0))
MEM0 = Z0["members"]   # load once (npz item access re-reads the array each time)
memeq = [bool(np.array_equal(np.asarray(MEM[k]), np.asarray(MEM0[k]))) for k in range(n0)]
GX["meta_members_equal_rows"] = int(sum(memeq)); GX["meta_members_rows"] = n0
Y0 = Z0["y4"].astype(np.float64); Yx = Y[:n0]
nan0 = np.isnan(Y0); nanx = np.isnan(Yx)
GX["meta_y4_nan_positions_equal"] = bool(np.array_equal(nan0, nanx))
both = ~nan0 & ~nanx
GX["meta_y4_maxabs_on_both_finite"] = float(np.abs(Y0[both] - Yx[both]).max())
d_nan = np.where(nan0 != nanx)
GX["meta_y4_nan_mismatch_cells"] = int(len(d_nan[0]))
if len(d_nan[0]):
    rows = np.unique(d_nan[0])
    GX["meta_y4_nan_mismatch_rows_utc"] = [time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(E0[r]))) for r in rows[:20]]
    GX["meta_y4_nan_mismatch_orig_nan_x0910_finite"] = int((nan0 & ~nanx).sum()); GX["meta_y4_nan_mismatch_orig_finite_x0910_nan"] = int((~nan0 & nanx).sum())
Q0 = Z0["qvk"].astype(np.float64); Qx = QVK[:n0].astype(np.float64); _nq0, _nqx = np.isnan(Q0), np.isnan(Qx)
GX["meta_qvk_nan_positions_equal"] = bool(np.array_equal(_nq0, _nqx)); GX["meta_qvk_maxabs_on_both_finite"] = float(np.abs(Q0[~_nq0 & ~_nqx] - Qx[~_nq0 & ~_nqx]).max())
tsP = PXz["ts"].astype(np.int64); tsP0 = P0z["ts"].astype(np.int64); nP0 = len(tsP0)
GX["panel_ts_prefix_equal"] = bool(np.array_equal(tsP[:nP0], tsP0))
for key in ("f_fund_now", "f_fund_iv", "f_fund_ema_v1", "f_fund_ema"):
    a = PXz[key][:nP0].astype(np.float64); b = P0z[key].astype(np.float64)
    na, nb = np.isnan(a), np.isnan(b); bf = ~na & ~nb
    GX[key] = dict(nan_positions_equal=bool(np.array_equal(na, nb)), maxabs_both_finite=float(np.abs(a[bf] - b[bf]).max()), nan_mismatch_cells=int((na != nb).sum()),
                   nan_mismatch_rows_utc=[time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(tsP0[r]))) for r in np.unique(np.where(na != nb)[0])[:20]])
GX["PASS_strict"] = bool(GX["meta_ts_prefix_equal"] and GX["meta_members_equal_rows"] == n0 and GX["meta_y4_nan_positions_equal"] and GX["meta_y4_maxabs_on_both_finite"] == 0.0 and GX["panel_ts_prefix_equal"] and GX["meta_qvk_nan_positions_equal"] and GX["meta_qvk_maxabs_on_both_finite"] == 0.0
                         and all(GX[k]["nan_positions_equal"] and GX[k]["maxabs_both_finite"] == 0.0 for k in ("f_fund_now", "f_fund_iv", "f_fund_ema_v1", "f_fund_ema")))
print("GATE_X", json.dumps(GX), flush=True)
# ---------------- states ----------------
prow = {int(t): j for j, t in enumerate(tsP)}
umts = UM["ts"].astype(np.int64); umask = np.asarray(UM["mask"]); umap = {int(t): k for k, t in enumerate(umts)}
FN = PXz["f_fund_now"].astype(np.float64); IV = PXz["f_fund_iv"].astype(np.float64)
IVf = np.where(np.isfinite(IV) & (IV > 0), IV, 8.0); RN8 = FN * (8.0 / IVf)
ibtc = SYM.index("BTCUSDT")
COLS = ["ts", "k_meta", "j_panel", "umask_carried", "nmem", "n24", "n72", "nfund", "DISP24", "DISP72", "BREADTH24", "BREADTH72", "BTC24", "BTC72", "SIGF", "MUF", "PUMP72", "PUMPSPR72"]
def trail(Yarr, k, n, cols):
    if k < n: return np.full(len(cols), np.nan)
    assert all(E[k] - E[k - q] == 14400 * q for q in (1, n)), ("non-contiguous meta rows", k)
    return np.prod(1.0 + Yarr[k - n:k][:, cols], axis=0) - 1.0
def state_at(Yarr, k):
    j = prow.get(int(E[k]))
    if j is None: return None
    _q = np.nan_to_num(QVK[k], nan=-1.0); m = np.sort(np.where(_q > -0.5)[0]).astype(np.int64)   # AMENDMENT 2 (device L77-83 semantics)
    u = umap.get(int(E[k])); carried = 0
    if u is None:
        prior = umts[umts <= E[k]]
        if len(prior) == 0: return None
        u = umap[int(prior.max())]; carried = 1
    m = m[umask[u][m]]
    r24 = trail(Yarr, k, 6, m); r72 = trail(Yarr, k, 18, m)
    f24 = r24[np.isfinite(r24)]; f72 = r72[np.isfinite(r72)]
    rn = RN8[j, m]; rn = rn[np.isfinite(FN[j, m])]
    out = [float(E[k]), float(k), float(j), float(carried), float(len(m)), float(len(f24)), float(len(f72)), float(len(rn))]
    out += [float(np.std(f24)) if len(f24) >= 50 else np.nan, float(np.std(f72)) if len(f72) >= 50 else np.nan,
            float(np.mean(f24 > 0)) if len(f24) >= 50 else np.nan, float(np.mean(f72 > 0)) if len(f72) >= 50 else np.nan]
    b24 = trail(Yarr, k, 6, np.array([ibtc]))[0]; b72 = trail(Yarr, k, 18, np.array([ibtc]))[0]
    out += [float(b24), float(b72)]
    out += [float(1e4 * np.std(rn)) if len(rn) >= 10 else np.nan, float(1e4 * np.mean(rn)) if len(rn) >= 10 else np.nan]
    if len(f72) >= 50:
        nd = int(np.ceil(0.1 * len(f72))); srt = np.sort(f72)[::-1]; top = srt[:nd]
        den = np.maximum(f72, 0).sum()
        out += [float(np.maximum(top, 0).sum() / den) if den > 0 else np.nan, float(top.mean() - np.median(f72))]
    else:
        out += [np.nan, np.nan]
    return out
rows = []
for k in range(len(E)):
    s = state_at(Y, k)
    if s is not None: rows.append(s)
S = np.array(rows, dtype=np.float64)
print("states", S.shape, "first", time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(S[0, 0]))), "last", time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(S[-1, 0]))), round(time.time() - t0, 1), "s", flush=True)
# ---------------- GATE S ----------------
rng = np.random.default_rng([20260905, 99])
ks = np.sort(rng.choice(np.arange(100, len(E)), 60, replace=False))
bad = []
for k in ks:
    Yp = Y.copy(); Yp[k:] = rng.normal(0, 0.5, size=Yp[k:].shape)
    a = state_at(Y, k); b = state_at(Yp, k)
    if a is None: continue
    aa = np.array(a); bb = np.array(b)
    if not (np.array_equal(np.isnan(aa), np.isnan(bb)) and np.array_equal(aa[~np.isnan(aa)], bb[~np.isnan(bb)])): bad.append(int(k))
GS = dict(n_tested=int(len(ks)), n_bad=len(bad), bad_k=bad[:10], PASS=bool(len(bad) == 0))
print("GATE_S", json.dumps(GS), flush=True)
np.savez_compressed(R + "/receipts/T1_states.npz", cols=np.array(COLS), S=S)
RC = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, amendment1_sha256=AMEND_SHA, amendment2_sha256=AMEND2_SHA, inputs=INPUTS, gate_X=GX, gate_S=GS, cols=COLS, n=int(S.shape[0]),
          out=R + "/receipts/T1_states.npz", out_sha256=sha(R + "/receipts/T1_states.npz"), env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}),
          built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), wall_s=round(time.time() - t0, 1))
json.dump(RC, open(R + "/receipts/RECEIPT_T1_states.json", "w"), indent=1, default=str)
print("DONE_t1_states", RC["wall_s"])
