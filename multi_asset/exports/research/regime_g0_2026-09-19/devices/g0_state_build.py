#!/usr/bin/env python3
"""g0_state_build.py — stream G0 of docs/PROGRAM_credible_replay_regime_optimization_2026-09-19.md §4 (FROZEN): the seven regime state
variables at every 4h anchor, causal (only data with bar close <= anchor E). pod2, CPU, read-only on every input; writes only OUT_DIR.

Variables (verbatim §4; nothing added, dropped or tuned):
  RG-TREND    BTC past-30-day return
  RG-BREADTH  share of members whose past-7-day return > 0
  RG-DISP     cross-sectional std (ddof=0) of members' past-24h returns
  RG-FLEVEL   cross-sectional median of members' current funding rate, 8h-equivalent = f_fund_now * 8 / f_fund_iv
  RG-FDISP    cross-sectional std (ddof=0) of the same 8h-equivalent rates (sigma_fund)
  RG-VOL      BTC realised volatility of 5-minute returns over the past 7 days = sqrt(mean(r5^2) * 105120) (annualised; monotone, so labels
              are the same as for any other scaling)
  RG-ALT      median of members' past-30-day returns minus BTC past-30-day return
Returns are simple compounded returns Π(1+r)−1 (RAW accounting caliber, the same as the arms' y4).

Universe ("该锚研究成员集") = the arms' member set: w10_health.py with MEMBERS_TOPN=829 + UMASK_SCOPE=m1 uses m = {finite qvk} ∩ umask row, and
umask ⊆ {finite qvk} on every anchor (checked below), so members = umask_UPIT_CRYPTO_tradable_W24H row (3badc4b6) for anchors <= 2026-08-31 00Z.
After that the same construction is rebuilt from its two parents: UPIT_CRYPTO (September row from fx_uni03_sep_mask.py, de7c34d7) AND
tradability_v1 W24H state == TRADABLE (54d409d0); the rebuild is required to equal 3badc4b6 bitwise on the overlap, else the device refuses.

Data pitfalls (memory notes; handled, not ignored):
  * ret5 channel hard-clipped at ±0.30 (float16): a 4h interval containing a bar with |ret5| >= 0.2999 takes the UNCLIPPED accounting value
    y4 from meta_newprod_v4 (e1cf515e; y4 at E = Π(1+r)−1 over bars with close in (E, E+4h]) when available, else the interval is NaN.
    Unclipped-equality of every other interval against meta y4 is measured and gated.
  * dead contracts write frozen rows (ret5 == 0, log_cnt == 0) and keep funding records: a name enters a cross-section at anchor E only if
    it is a member at E (the member mask carries tradable W24H), and for window returns it must be TRADABLE (>= 1 traded bar in the trailing
    24h) at the end of EVERY 4h interval of the window and have no NODATA bar in it. A frozen stretch longer than 24h therefore never enters.
  * holefix-filled bars (holefix2_cells 6156f97a: 2022-02-26..03-01, 2022-04-01..03, 2026-08-12..08-24 04:00 (348 non-live names),
    2026-08-31 00:05..09-01 00:00 (798 names)) are official data.binance.vision klines but NOT live-collected data. Two variants:
      EXCL (primary): a name with any filled bar inside a window is dropped from that window's cross-section; BTC-return variables are NaN
                      when BTC's window contains a filled bar; RG-VOL uses only non-filled bars (needs >= 50% of the 2016 bars).
      INCL (sensitivity): filled bars used as ordinary price data.
    Funding variables do not read the cache and are identical in both variants.
  Cross-sectional statistics need >= 30 names, else NaN (a NaN guard, not a cut point).
Outputs: OUT_DIR/g0_state_vars.npz + OUT_DIR/RECEIPT_g0_state_build.json. Exit 0 only if every check passes.
usage: python g0_state_build.py <OUT_DIR>
"""
import hashlib, json, os, sys, time, zipfile
import numpy as np

T0 = time.time()
OUT_DIR = sys.argv[1]
os.makedirs(OUT_DIR, exist_ok=True)
W = "/workspace"
INPUTS = {   # name: (path, expected sha256) — pinned; any mismatch refuses
    "CACHE_X0910": (f"{W}/data/dlnative_5m_wide829_f16_holefix2_x0910.npz", "8115299410cd5e8df46ecc5ac7baf312d9f593d94f3b4c3dc46471bd37e00336"),
    "CACHE_HOLEFIX2": (f"{W}/data/dlnative_5m_wide829_f16_holefix2.npz", "1d7f459dee434ec49e7714a2a612807f2e38e97f35c6c39471a8a4aaa7452488"),
    "HOLE_CELLS": (f"{W}/fp2_2026-09/holefix2_cells.npz", "6156f97a0709f073147e392d5b0cb542f6b6d463cc3be2500f8791a0d1a8dfda"),
    "TRADABILITY": (f"{W}/fx_data_2026-09-13/out/trd/tradability_v1.npz", "54d409d0ddf695f497d8b27fb5bdee960deda763250d530a16bd7cf506205302"),
    "UMASK_ARM": (f"{W}/fx_data_2026-09-13/out/inject/umask_UPIT_CRYPTO_tradable_W24H.npz", "3badc4b6a4fcbc5935f66f29c065ffd7ab500cb6876bdf53ce491b2d9056024c"),
    "UPIT_CRYPTO_SEP": (f"{W}/fx_data_2026-09-13/out/uni03/umask_UPIT_CRYPTO_x0910_sep.npz", "de7c34d79d7047e34f577abd2ef825554e064193fda757f6857e352596e0e77b"),
    "PANEL_IVFIX": (f"{W}/uplift_r2_2026-09-13/T5d/panel/wide_panel_4h_v2ext_x0910_ivfix.npz", "a5d7fb9731b259e875d1d5229e23005c524635452d95c142e2c0d3aab2881f4e"),
    "PANEL_ARM": (f"{W}/data/wide_panel_4h_v2ext.npz", "5e67c0559daa904d8f0526b6e268e93dcb45aab89d82646cf79a794445481116"),
    "META_V4": (f"{W}/fp2_2026-09/refute_C6_2/altrun/meta_newprod_v4.npz", "e1cf515eca46b0a1a7afe2bd6e89039cb68f4eea1a0428353e2f3aac989890a7"),
    "ARM_A0_S42": (f"{W}/fp2_2026-09/realcost/arms/w10_ablation_series_V4_A0_dyn_s42.npz", "634f7c55ba730520371aab64b64b3b2b5c211422af6ab7b8bacb78e4d706060b"),
}
VARS = ["RG-TREND", "RG-BREADTH", "RG-DISP", "RG-FLEVEL", "RG-FDISP", "RG-VOL", "RG-ALT"]
NMIN = 30; CLIP = 0.2999; BARS_YEAR = 105120.0; VOL_MIN_BARS = 1008
WIN = {"24h": 6, "7d": 42, "30d": 180}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def utc(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)


CHECKS = []; FAILS = []
def check(name, ok, detail=None):
    CHECKS.append({"check": name, "ok": bool(ok), **({"detail": detail} if detail is not None else {})})
    if not ok: FAILS.append(name)
    log("CHECK", name, "OK" if ok else "FAIL", json.dumps(detail, default=str)[:400] if detail is not None else "")
    return ok


rec = {"device": "g0_state_build.py", "self_sha256": sha(os.path.abspath(__file__)), "numpy": np.__version__, "argv": sys.argv,
       "env": {k: os.environ[k] for k in sorted(os.environ)}, "utc_start": utc(time.time()), "inputs": {}, "definitions": {
           "variables": VARS, "returns": "simple compounded Π(1+r)−1 over 4h intervals (E−4h, E] built from cache ret5; clip intervals replaced by meta_newprod_v4 y4",
           "members": "umask_UPIT_CRYPTO_tradable_W24H row (<= 2026-08-31 00Z) = UPIT_CRYPTO_x0910_sep AND tradability W24H == TRADABLE (rebuilt, bitwise-gated on the overlap)",
           "window_return_eligibility": "member at E; every interval of the window finite (no NODATA bar); TRADABLE W24H at every interval end; EXCL: no filled bar in the window",
           "vol": "sqrt(mean(r5^2)*105120) over BTC 5m bars with close in (E-7d, E]; EXCL uses non-filled bars only; >= 1008 bars", "nmin_cross_section": NMIN,
           "fund_8h": "f_fund_now * 8 / f_fund_iv (iv <= 0 or NaN -> 8.0, same as w10_health _IVf)"}}
for k, (p, s) in INPUTS.items():
    got = sha(p); rec["inputs"][k] = {"path": p, "sha256": got}
    check(f"input_sha.{k}", got == s, {"expected": s[:12], "got": got[:12]})
if FAILS:
    json.dump(rec | {"checks": CHECKS, "failed": FAILS, "VERDICT": "REFUSED"}, open(f"{OUT_DIR}/RECEIPT_g0_state_build.json", "w"), indent=1); sys.exit(3)
log("input shas verified")


def stream_channels(path, chans, block=8000):
    """read data.npy of a (T, N, C) float16 npz member in row blocks and keep only `chans` (fx_uni03_sep_mask.py pattern)"""
    zf = zipfile.ZipFile(path)
    with zf.open("data.npy") as fh:
        ver = np.lib.format.read_magic(fh)
        shape, fort, dt = (np.lib.format.read_array_header_1_0(fh) if ver == (1, 0) else np.lib.format.read_array_header_2_0(fh))
        assert not fort and len(shape) == 3
        rowb = int(np.prod(shape[1:])) * dt.itemsize
        out = np.empty((shape[0], shape[1], len(chans)), dt); r = 0
        while r < shape[0]:
            k = min(block, shape[0] - r); buf = fh.read(k * rowb); assert len(buf) == k * rowb
            out[r:r + k] = np.frombuffer(buf, dtype=dt).reshape((k,) + tuple(shape[1:]))[:, :, chans]; r += k
    return out


# ---------------- cache (x0910 = holefix2 prefix + 10 days) ----------------
ZX = np.load(INPUTS["CACHE_X0910"][0]); CTS = ZX["ts"].astype(np.int64); SYM = [str(s) for s in ZX["symbols"]]; CH = [str(c) for c in ZX["ch"]]
check("cache.channels", CH[0] == "ret5" and CH[4] == "log_cnt", CH)
check("cache.grid", bool((np.diff(CTS) == 300).all() and CTS[0] % 14400 == 0 and (len(CTS) - 1) % 48 == 0), {"first": utc(CTS[0]), "last": utc(CTS[-1]), "rows": len(CTS)})
NW = len(SYM); IB = SYM.index("BTCUSDT")
DX = stream_channels(INPUTS["CACHE_X0910"][0], [0, 4]); log("x0910 channels loaded", DX.shape)
ZH = np.load(INPUTS["CACHE_HOLEFIX2"][0]); HTS = ZH["ts"].astype(np.int64)
check("cache.holefix2_symbols_and_ts_prefix", [str(s) for s in ZH["symbols"]] == SYM and np.array_equal(HTS, CTS[:len(HTS)]), {"holefix2_rows": len(HTS), "last": utc(HTS[-1])})
DH = stream_channels(INPUTS["CACHE_HOLEFIX2"][0], [0, 4]); log("holefix2 channels loaded", DH.shape)
check("cache.x0910_prefix_equals_holefix2_ret5_logcnt", bool(np.array_equal(DX[:len(HTS)], DH, equal_nan=True)), {"rows": len(HTS)})
del DH
R5 = DX[:, :, 0]; LC = DX[:, :, 1]
check("cache.btc_never_at_clip_bound", bool(np.nanmax(np.abs(R5[:, IB].astype(np.float64))) < CLIP), {"btc_max_abs_ret5": float(np.nanmax(np.abs(R5[:, IB].astype(np.float64))))})

# ---------------- holefix cells ----------------
HC = np.load(INPUTS["HOLE_CELLS"][0])
check("holes.symbols", [str(s) for s in HC["symbols"]] == SYM)
hrow = HC["row"].astype(np.int64); hcol = HC["col"].astype(np.int64)
check("holes.ts_match_cache_rows", bool(np.array_equal(HC["ts"].astype(np.int64), CTS[hrow])), {"cells": int(len(hrow))})
FILLED_BTC = np.zeros(len(CTS), bool); FILLED_BTC[hrow[hcol == IB]] = True

# ---------------- 4h intervals ----------------
K = (len(CTS) - 1) // 48                       # interval k (1..K) = bars rows 48(k-1)+1 .. 48k, closes in (CTS[48(k-1)], CTS[48k]]
ITS = CTS[48 * np.arange(0, K + 1)]            # ITS[k] = end time of interval k (ITS[0] = cache start, no interval)
r4 = np.full((K + 1, NW), np.nan); nan_any = np.ones((K + 1, NW), bool); clip_any = np.zeros((K + 1, NW), bool)
fill_any = np.zeros((K + 1, NW), bool)
fill_any[(hrow + 47) // 48, hcol] = True        # row r belongs to interval ceil(r/48)
check("holes.row0_not_filled", bool((hrow >= 1).all()))
for c0 in range(0, NW, 64):
    c1 = min(NW, c0 + 64)
    X = R5[1:1 + 48 * K, c0:c1].astype(np.float64).reshape(K, 48, c1 - c0)
    nan_any[1:, c0:c1] = np.isnan(X).any(1); clip_any[1:, c0:c1] = (np.abs(X) >= CLIP).any(1)
    r4[1:, c0:c1] = np.prod(1.0 + X, axis=1) - 1.0
del X
log("4h intervals built", K)

# ---------------- unclipped accounting y4 (meta) : gate + clip replacement ----------------
MT = np.load(INPUTS["META_V4"][0], allow_pickle=True); ME = MT["E_ts"].astype(np.int64); Y4 = np.asarray(MT["y4"], np.float64)
kpos = {int(t): k for k, t in enumerate(ITS)}
mk = np.array([kpos.get(int(t) + 14400, -1) for t in ME]); okm = mk > 0
check("meta.every_row_maps_to_an_interval", bool(okm.all()), {"meta_rows": len(ME), "unmapped": int((~okm).sum())})
RC = r4[mk[okm]]; YM = Y4[okm]; CL = clip_any[mk[okm]]
both = np.isfinite(RC) & np.isfinite(YM)
dif = np.abs(RC - YM)[both & ~CL]
nan_mis_c = int((np.isfinite(RC) & ~np.isfinite(YM)).sum()); nan_mis_m = int((~np.isfinite(RC) & np.isfinite(YM)).sum())
clip_cells_meta = int((CL & np.isfinite(YM)).sum()); clip_anchor_meta = int((CL & np.isfinite(YM)).any(1).sum())
clip_diff_max = float(np.abs(RC - YM)[both & CL].max()) if (both & CL).any() else 0.0
check("meta.cache_intervals_equal_accounting_y4_off_clip", bool(dif.max() < 1e-6), {"cells_compared": int(dif.size), "max_abs_diff": float(dif.max()), "n_gt_1e-7": int((dif > 1e-7).sum()),
      "finite_cache_nan_meta": nan_mis_c, "nan_cache_finite_meta": nan_mis_m, "clip_cells_in_meta_span": clip_cells_meta, "clip_anchors_in_meta_span": clip_anchor_meta,
      "max_abs_clip_vs_unclipped": clip_diff_max})
# replace clip intervals by the unclipped value (meta) where available; elsewhere NaN
rep = np.zeros((K + 1, NW), bool); rows_m = mk[okm]
for kk, i in zip(rows_m, np.nonzero(okm)[0]):
    cl = clip_any[kk]
    if cl.any():
        y = Y4[i, cl]; r4[kk, cl] = np.where(np.isfinite(y), y, np.nan); rep[kk, cl] = True
tail_clip = clip_any & ~rep
tail_clip_cells = [(utc(ITS[k]), SYM[j]) for k, j in zip(*np.nonzero(tail_clip))]
r4[tail_clip] = np.nan
rec["clip"] = {"replaced_by_meta_y4_cells": int(rep.sum()), "clip_cells_without_meta_set_nan": len(tail_clip_cells), "examples_without_meta": tail_clip_cells[:40]}
log("clip handling", rec["clip"]["replaced_by_meta_y4_cells"], "replaced,", len(tail_clip_cells), "NaN")
del RC, YM, CL, both, Y4

# ---------------- tradability on the interval grid ----------------
TR = np.load(INPUTS["TRADABILITY"][0]); ATS = TR["anchor_ts"].astype(np.int64)
check("trd.grid_equals_interval_ends", bool(np.array_equal(ATS, ITS)) and [str(s) for s in TR["symbols"]] == SYM and np.array_equal(TR["ts5"], CTS))
TRADABLE = np.asarray(TR["state_W24H"]) == 2                          # (K+1, NW)

# ---------------- members on the output axis ----------------
UP = np.load(INPUTS["UPIT_CRYPTO_SEP"][0]); AX = UP["ts"].astype(np.int64)
check("axis.upit_symbols", [str(s) for s in UP["symbols"]] == SYM)
kax = np.array([kpos.get(int(t), -1) for t in AX]); check("axis.every_anchor_on_interval_grid", bool((kax > 0).all()), {"anchors": len(AX), "first": utc(AX[0]), "last": utc(AX[-1])})
MEM = np.asarray(UP["mask"]) & TRADABLE[kax]
UA = np.load(INPUTS["UMASK_ARM"][0]); uts = UA["ts"].astype(np.int64); NA = len(uts)
check("members.rebuild_equals_arm_umask_bitwise", bool(np.array_equal(AX[:NA], uts) and [str(s) for s in UA["symbols"]] == SYM and np.array_equal(MEM[:NA], np.asarray(UA["mask"]))),
      {"arm_anchors": NA, "cells_differ": int((MEM[:NA] != np.asarray(UA["mask"])).sum()) if np.array_equal(AX[:NA], uts) else None})
MTq = MT["qvk"]; mrow = {int(t): i for i, t in enumerate(ME)}
bad_q = 0
for a in range(NA):
    q = np.nan_to_num(MTq[mrow[int(AX[a])]], nan=-1.0) > -0.5; bad_q += int((MEM[a] & ~q).sum())
check("members.umask_subset_of_finite_qvk", bad_q == 0, {"cells_member_without_qvk": bad_q})
ARM = np.load(INPUTS["ARM_A0_S42"][0], allow_pickle=True); acols = [str(c) for c in ARM["cols"]]; AR = np.asarray(ARM["d30_n2_c42_rec"])
check("members.arm_nmember_equals_member_count", bool(np.array_equal(AR[:, 0].astype(np.int64), AX[:NA]) and np.array_equal(AR[:, acols.index("nmember")].astype(np.int64), MEM[:NA].sum(1))),
      {"anchors": NA})

# ---------------- funding ----------------
PX = np.load(INPUTS["PANEL_IVFIX"][0]); PA = np.load(INPUTS["PANEL_ARM"][0])
check("fund.ivfix_axis", bool(np.array_equal(PX["ts"].astype(np.int64), AX)) and [str(s) for s in PX["symbols"]] == SYM)
FN = np.asarray(PX["f_fund_now"], np.float64); IV = np.asarray(PX["f_fund_iv"], np.float64)
check("fund.ivfix_prefix_equals_arm_panel", bool(np.array_equal(PA["ts"].astype(np.int64), AX[:NA]) and np.array_equal(np.asarray(PA["f_fund_now"], np.float64), FN[:NA], equal_nan=True)
      and np.array_equal(np.asarray(PA["f_fund_iv"], np.float64), IV[:NA], equal_nan=True)), {"rows": NA})
F8 = FN * (8.0 / np.where(np.isfinite(IV) & (IV > 0), IV, 8.0))
del PA

# ---------------- window returns ----------------
L = np.where(np.isfinite(r4), np.log1p(np.where(np.isfinite(r4), r4, 0.0)), 0.0)
BAD = (~np.isfinite(r4)) | (~TRADABLE) | nan_any
BAD[0] = True
cL = np.vstack([np.zeros((1, NW)), np.cumsum(L, 0)]); cB = np.vstack([np.zeros((1, NW), np.int64), np.cumsum(BAD, 0)]); cF = np.vstack([np.zeros((1, NW), np.int64), np.cumsum(fill_any, 0)])


def wret(k, n, excl):
    """per-name return over intervals k-n+1..k (NaN where ineligible); cumsum index i covers intervals 0..i-1"""
    lo = k - n + 1
    if lo < 1: return np.full(NW, np.nan)
    s = cL[k + 1] - cL[lo]; b = cB[k + 1] - cB[lo]; f = cF[k + 1] - cF[lo]
    ok = (b == 0) & ((f == 0) if excl else True)
    return np.where(ok, np.expm1(s), np.nan)


r5b = R5[:, IB].astype(np.float64); r5b_ok = np.isfinite(r5b)
cQ = {}; cN = {}
for v, fm in (("INCL", np.zeros(len(CTS), bool)), ("EXCL", FILLED_BTC)):
    use = r5b_ok & ~fm
    cQ[v] = np.concatenate([[0.0], np.cumsum(np.where(use, r5b * r5b, 0.0))]); cN[v] = np.concatenate([[0], np.cumsum(use.astype(np.int64))])
NAX = len(AX)
OUT = {v: np.full((NAX, 7), np.nan) for v in ("EXCL", "INCL")}
NN = {v: np.zeros((NAX, 7), np.int64) for v in ("EXCL", "INCL")}
census = {v: {"member_name_anchors": 0, "r7_ineligible": 0} for v in ("EXCL", "INCL")}
for a in range(NAX):
    k = int(kax[a]); m = MEM[a]; row5 = 48 * k
    for v in ("EXCL", "INCL"):
        ex = v == "EXCL"
        r24 = wret(k, 6, ex); r7 = wret(k, 42, ex); r30 = wret(k, 180, ex)
        btc30 = r30[IB]
        x7 = r7[m]; x7 = x7[np.isfinite(x7)]; x24 = r24[m]; x24 = x24[np.isfinite(x24)]; x30 = r30[m]; x30 = x30[np.isfinite(x30)]
        f8 = F8[a, m]; f8 = f8[np.isfinite(f8)]
        lo5 = row5 - 2016 + 1
        nq = int(cN[v][row5 + 1] - cN[v][lo5]) if lo5 >= 1 else 0
        vol = float(np.sqrt((cQ[v][row5 + 1] - cQ[v][lo5]) / nq * BARS_YEAR)) if nq >= VOL_MIN_BARS else np.nan
        vals = [btc30, np.mean(x7 > 0) if len(x7) >= NMIN else np.nan, np.std(x24) if len(x24) >= NMIN else np.nan,
                np.median(f8) if len(f8) >= NMIN else np.nan, np.std(f8) if len(f8) >= NMIN else np.nan, vol,
                (np.median(x30) - btc30) if (len(x30) >= NMIN and np.isfinite(btc30)) else np.nan]
        OUT[v][a] = vals; NN[v][a] = [1 if np.isfinite(btc30) else 0, len(x7), len(x24), len(f8), len(f8), nq, len(x30)]
        census[v]["member_name_anchors"] += int(m.sum()); census[v]["r7_ineligible"] += int(m.sum() - len(x7))
    if a % 2000 == 0: log("anchor", a, "/", NAX, utc(AX[a]))
# census of what each exclusion removes (7-day window, member cells)
rec["census_7d_window"] = census
rec["axis"] = {"anchors": int(NAX), "first": utc(AX[0]), "last": utc(AX[-1]), "arm_anchors": int(NA), "arm_last": utc(AX[NA - 1])}
rec["defined_share"] = {v: {VARS[j]: float(np.isfinite(OUT[v][:, j]).mean()) for j in range(7)} for v in OUT}
rec["first_defined"] = {v: {VARS[j]: (utc(AX[np.argmax(np.isfinite(OUT[v][:, j]))]) if np.isfinite(OUT[v][:, j]).any() else None) for j in range(7)} for v in OUT}
rec["undefined_after_arm"] = {v: {VARS[j]: int((~np.isfinite(OUT[v][NA:, j])).sum()) for j in range(7)} for v in OUT}
rec["members_per_anchor"] = {"min": int(MEM.sum(1).min()), "median": float(np.median(MEM.sum(1))), "max": int(MEM.sum(1).max())}
rec["variant_diff"] = {VARS[j]: {"anchors_both_defined": int((np.isfinite(OUT["EXCL"][:, j]) & np.isfinite(OUT["INCL"][:, j])).sum()),
                                 "anchors_value_differs": int((np.isfinite(OUT["EXCL"][:, j]) & np.isfinite(OUT["INCL"][:, j]) & (OUT["EXCL"][:, j] != OUT["INCL"][:, j])).sum())} for j in range(7)}
out_npz = f"{OUT_DIR}/g0_state_vars.npz"
np.savez_compressed(out_npz, ts=AX, vars=np.array(VARS), EXCL=OUT["EXCL"], INCL=OUT["INCL"], N_EXCL=NN["EXCL"], N_INCL=NN["INCL"], n_members=MEM.sum(1),
                    arm_anchors=np.array(NA), definitions_json=np.array(json.dumps(rec["definitions"])))
rec["outputs"] = {"state_vars": {"path": out_npz, "sha256": sha(out_npz)}}
rec.update({"checks": CHECKS, "n_checks": len(CHECKS), "failed": FAILS, "VERDICT": "PASS" if not FAILS else "FAIL", "runtime_s": round(time.time() - T0, 1), "utc_end": utc(time.time())})
json.dump(rec, open(f"{OUT_DIR}/RECEIPT_g0_state_build.json", "w"), indent=1, default=str)
log("VERDICT", rec["VERDICT"], "failed", FAILS)
sys.exit(0 if not FAILS else 3)
