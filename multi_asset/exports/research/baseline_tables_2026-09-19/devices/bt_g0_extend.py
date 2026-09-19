#!/usr/bin/env python3
"""bt_g0_extend.py — the G0 regime state variables and labels EXTENDED to 2026-09-18T20Z on the stream-D axis (axis_0919), definitions
unchanged (docs/PROGRAM_credible_replay_regime_optimization_2026-09-19.md §4; baseline-tables prereg §3.2 "状态量装置延伸到 09-18").

Derived line by line from regime_g0_2026-09-19/devices/g0_state_build.py (72f38514; variables, windows, eligibility, EXCL/INCL, NMIN, VOL
rule, fund_8h — all verbatim) and g0_regime_tables.py (6f448750) `expanding_labels` (verbatim: expanding np.quantile [1/3, 2/3], closed middle
bucket, WARM 1,080). What changes is ONLY where each input row comes from (append-only splice at the published axis end E_pub = 2026-09-10T00Z):
  cache ret5 / log_cnt  x0918 (1db49ce6); its first 493,633 rows asserted bitwise = x0910 (81152994) — the published device's cache.
  tradability           axis_0919 tradability_v1 (bebf69ab); state_W24H asserted bitwise = the published 54d409d0 on every common anchor.
  members               U-PIT crypto row ∧ W24H TRADABLE (published construction). Anchors ≤ E_pub: the published September mask file
                        (de7c34d7) rows; anchors after E_pub (all in September 2026): its SEPTEMBER row — the monthly rule (fx_uni03_sep_mask.py:
                        "first panel anchor of each month … held for the month"), asserted identical on every September row of the file.
  funding 8h-eq.        ≤ E_pub: the published ivfix panel (a5d7fb97); (E_pub, 2026-09-18T00Z]: stream-D v2ext_x0918 panel (e5fcb419),
                        f_fund_now / f_fund_iv asserted bitwise = ivfix on their overlap; 09-18T04Z..20Z: stream-D funding_4h_accounting
                        (2838e5f6; same "last settlement ≤ anchor, >12 h ⇒ NaN" rule), asserted bitwise = the x0918 panel on their overlap.
  clip replacement      intervals ending ≤ E_pub: the published meta (e1cf515e) exactly as published (a clipped interval without a meta value
                        stays NaN — the three September cells AKE 09-03, BULLA 09-05, WOO 09-06); intervals ending after E_pub: stream-D
                        meta_newprod_v4_x0918 (22e990f8), and its y4 is gated against the cache compound off-clip on those intervals (≤ 1e-6).
PREFIX PROOF (the exit code depends on it): on the published 10,099 anchors, state variables (EXCL, INCL, N_*) and labels (LAB_*, Q_*, PR_*)
are compared BITWISE with the published g0_state_vars.npz (52a9e89e) and g0_labels.npz (04cb06f4). Sensitivity (reported, not used): the
same prefix computed with the stream-D meta also on intervals ending in (2026-09-01, E_pub] — the number of state values / labels that move.
Outputs: <OUT>/g0_state_vars_x0918.npz, <OUT>/g0_labels_x0918.npz, <OUT>/RECEIPT_bt_g0_extend.json. pod2, CPU, read-only on every input.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_g0_extend.py PATH,HOME,LC_CTYPE <OUT_DIR>
"""
import hashlib, json, os, sys, time, zipfile, calendar
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "4"
import numpy as np

T0 = time.time()
OUT_DIR = sys.argv[2]; os.makedirs(OUT_DIR, exist_ok=True)
W = "/workspace"; AXR = f"{W}/axis_0919"
INPUTS = {
    "CACHE_X0918": (f"{AXR}/data/dlnative_5m_wide829_f16_holefix2_x0918.npz", "1db49ce6f5ca3431e99ce5abb630b296d2effbb130dfe17974d2b5319f926d2e"),
    "CACHE_X0910": (f"{W}/data/dlnative_5m_wide829_f16_holefix2_x0910.npz", "8115299410cd5e8df46ecc5ac7baf312d9f593d94f3b4c3dc46471bd37e00336"),
    "HOLE_CELLS": (f"{W}/fp2_2026-09/holefix2_cells.npz", "6156f97a0709f073147e392d5b0cb542f6b6d463cc3be2500f8791a0d1a8dfda"),
    "TRADABILITY_PUB": (f"{W}/fx_data_2026-09-13/out/trd/tradability_v1.npz", "54d409d0ddf695f497d8b27fb5bdee960deda763250d530a16bd7cf506205302"),
    "TRADABILITY_X0918": (f"{AXR}/trd/tradability_v1.npz", "bebf69ab9ddb3b05b49552e66dccf9b8cde3caee0593b14e1b3fe1a4c93c9db8"),
    "UMASK_ARM": (f"{W}/fx_data_2026-09-13/out/inject/umask_UPIT_CRYPTO_tradable_W24H.npz", "3badc4b6a4fcbc5935f66f29c065ffd7ab500cb6876bdf53ce491b2d9056024c"),
    "UPIT_CRYPTO_SEP": (f"{W}/fx_data_2026-09-13/out/uni03/umask_UPIT_CRYPTO_x0910_sep.npz", "de7c34d79d7047e34f577abd2ef825554e064193fda757f6857e352596e0e77b"),
    "PANEL_IVFIX": (f"{W}/uplift_r2_2026-09-13/T5d/panel/wide_panel_4h_v2ext_x0910_ivfix.npz", "a5d7fb9731b259e875d1d5229e23005c524635452d95c142e2c0d3aab2881f4e"),
    "PANEL_ARM": (f"{W}/data/wide_panel_4h_v2ext.npz", "5e67c0559daa904d8f0526b6e268e93dcb45aab89d82646cf79a794445481116"),
    "PANEL_X0918": (f"{AXR}/panels/wide_panel_4h_v2ext_x0918.npz", "e5fcb4198ddebb52fe6e92438c5111ed22f41dbacbd9ec9af459c9ac6c40b47c"),
    "FUND4H_X0918": (f"{AXR}/funding/funding_4h_accounting.npz", "2838e5f6cf42fff5619460f64708d952cd56e23e6621195d8e3d8bd5466aca72"),
    "META_V4": (f"{W}/fp2_2026-09/refute_C6_2/altrun/meta_newprod_v4.npz", "e1cf515eca46b0a1a7afe2bd6e89039cb68f4eea1a0428353e2f3aac989890a7"),
    "META_X0918": (f"{AXR}/meta/meta_newprod_v4_x0918.npz", "22e990f86babd64a30801992627ee2f175e0c920aa442943629f200f16406d1e"),
    "ARM_A0_S42": (f"{W}/fp2_2026-09/realcost/arms/w10_ablation_series_V4_A0_dyn_s42.npz", "634f7c55ba730520371aab64b64b3b2b5c211422af6ab7b8bacb78e4d706060b"),
    "PUB_STATE": (f"{W}/regime_g0_2026-09-19/out/g0_state_vars.npz", "52a9e89eb6de6d83b5d79cb9b8b6a7ab768bd31b89644a5590ae7fb8b7fb2fa0"),
    "PUB_LABELS": (f"{W}/regime_g0_2026-09-19/out/g0_labels.npz", "04cb06f47c15a4102a97d18a8a1061098507a6a422ed4a93cee221b695a414bb"),
    "PUB_STATE_DEVICE": (f"{W}/regime_g0_2026-09-19/devices/g0_state_build.py", "72f385147e80633f9fffb6ca202ee2f3d18e505b696b7ee2d0c946b602c4b5a0"),
    "PUB_TABLES_DEVICE": (f"{W}/regime_g0_2026-09-19/devices/g0_regime_tables.py", "6f4487509df13e74f963b46fa0daba2c8382b52996474d860d641802053e9e00"),
}
VARS = ["RG-TREND", "RG-BREADTH", "RG-DISP", "RG-FLEVEL", "RG-FDISP", "RG-VOL", "RG-ALT"]
NMIN = 30; CLIP = 0.2999; BARS_YEAR = 105120.0; VOL_MIN_BARS = 1008; WARM = 1080
E_PUB = calendar.timegm((2026, 9, 10, 0, 0, 0)); E_LAST = calendar.timegm((2026, 9, 18, 20, 0, 0)); SEP1 = calendar.timegm((2026, 9, 1, 0, 0, 0))


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


rec = {"device": "bt_g0_extend.py", "self_sha256": sha(os.path.abspath(__file__)), "numpy": np.__version__, "python": sys.version.split()[0], "argv": sys.argv,
       "env": dict(os.environ), "utc_start": utc(time.time()), "inputs": {}, "E_pub": utc(E_PUB), "E_last": utc(E_LAST)}
def finish(code, line):
    rec.update({"checks": CHECKS, "n_checks": len(CHECKS), "failed": FAILS, "runtime_s": round(time.time() - T0, 1)})
    rp = f"{OUT_DIR}/RECEIPT_bt_g0_extend.json"; json.dump(rec, open(rp + ".tmp", "w"), indent=1, default=str); os.replace(rp + ".tmp", rp)
    print(line + " receipt_sha256=" + sha(rp), flush=True); sys.exit(code)


for k, (p, s) in INPUTS.items():
    got = sha(p); rec["inputs"][k] = {"path": p, "sha256": got}
    check(f"input_sha.{k}", got == s, {"expected": s[:12], "got": got[:12]})
if FAILS: finish(3, "BT_G0_EXTEND VERDICT=REFUSED")


def stream_channels(path, chans, block=8000):
    """verbatim from g0_state_build.py"""
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


# ---------------- cache: x0918 (prefix = x0910 = the published device's cache) ----------------
ZX = np.load(INPUTS["CACHE_X0918"][0]); CTS = ZX["ts"].astype(np.int64); SYM = [str(s) for s in ZX["symbols"]]; CH = [str(c) for c in ZX["ch"]]
check("cache.channels", CH[0] == "ret5" and CH[4] == "log_cnt", CH)
check("cache.grid", bool((np.diff(CTS) == 300).all() and CTS[0] % 14400 == 0 and (len(CTS) - 1) % 48 == 0), {"first": utc(CTS[0]), "last": utc(CTS[-1]), "rows": len(CTS)})
NW = len(SYM); IB = SYM.index("BTCUSDT")
DX = stream_channels(INPUTS["CACHE_X0918"][0], [0, 4]); log("x0918 channels loaded", DX.shape)
Z10 = np.load(INPUTS["CACHE_X0910"][0]); T10 = Z10["ts"].astype(np.int64)
check("cache.x0910_symbols_and_ts_prefix", [str(s) for s in Z10["symbols"]] == SYM and np.array_equal(T10, CTS[:len(T10)]), {"x0910_rows": len(T10)})
D10 = stream_channels(INPUTS["CACHE_X0910"][0], [0, 4])
check("cache.x0918_prefix_equals_x0910_ret5_logcnt_bitwise", bool(np.array_equal(DX[:len(T10)].view(np.uint16), D10.view(np.uint16))), {"rows": len(T10)})
del D10
R5 = DX[:, :, 0]; LC = DX[:, :, 1]
check("cache.btc_never_at_clip_bound", bool(np.nanmax(np.abs(R5[:, IB].astype(np.float64))) < CLIP))

# ---------------- holefix cells (verbatim) ----------------
HC = np.load(INPUTS["HOLE_CELLS"][0])
check("holes.symbols", [str(s) for s in HC["symbols"]] == SYM)
hrow = HC["row"].astype(np.int64); hcol = HC["col"].astype(np.int64)
check("holes.ts_match_cache_rows", bool(np.array_equal(HC["ts"].astype(np.int64), CTS[hrow])), {"cells": int(len(hrow))})
FILLED_BTC = np.zeros(len(CTS), bool); FILLED_BTC[hrow[hcol == IB]] = True

# ---------------- 4h intervals (verbatim) ----------------
K = (len(CTS) - 1) // 48
ITS = CTS[48 * np.arange(0, K + 1)]
r4 = np.full((K + 1, NW), np.nan); nan_any = np.ones((K + 1, NW), bool); clip_any = np.zeros((K + 1, NW), bool)
fill_any = np.zeros((K + 1, NW), bool)
fill_any[(hrow + 47) // 48, hcol] = True
check("holes.row0_not_filled", bool((hrow >= 1).all()))
for c0 in range(0, NW, 64):
    c1 = min(NW, c0 + 64)
    X = R5[1:1 + 48 * K, c0:c1].astype(np.float64).reshape(K, 48, c1 - c0)
    nan_any[1:, c0:c1] = np.isnan(X).any(1); clip_any[1:, c0:c1] = (np.abs(X) >= CLIP).any(1)
    r4[1:, c0:c1] = np.prod(1.0 + X, axis=1) - 1.0
del X
kpos = {int(t): k for k, t in enumerate(ITS)}
log("4h intervals built", K)

# ---------------- clip replacement: published meta for intervals ending <= E_pub, stream-D meta after (splice) ----------------
def meta_replace(r4_in, meta_path, end_lo, end_hi, tag):
    """g0_state_build.py's meta block, restricted to intervals whose END is in (end_lo, end_hi]; returns (r4_out, replaced mask, gate detail)"""
    r4o = r4_in.copy()
    MT = np.load(meta_path, allow_pickle=True); ME = MT["E_ts"].astype(np.int64); Y4 = np.asarray(MT["y4"], np.float64)
    mk = np.array([kpos.get(int(t) + 14400, -1) for t in ME]); okm = mk > 0
    ends = np.where(okm, ITS[np.maximum(mk, 0)], -1); inwin = okm & (ends > end_lo) & (ends <= end_hi)
    RC = r4_in[mk[inwin]]; YM = Y4[inwin]; CL = clip_any[mk[inwin]]
    both = np.isfinite(RC) & np.isfinite(YM); dif = np.abs(RC - YM)[both & ~CL]
    gate = {"meta": tag, "rows_in_window": int(inwin.sum()), "cells_compared": int(dif.size), "max_abs_diff": float(dif.max()) if dif.size else 0.0,
            "clip_cells_with_meta": int((CL & np.isfinite(YM)).sum())}
    rep = np.zeros_like(clip_any)
    for kk, i in zip(mk[inwin], np.nonzero(inwin)[0]):
        cl = clip_any[kk]
        if cl.any():
            y = Y4[i, cl]; r4o[kk, cl] = np.where(np.isfinite(y), y, np.nan); rep[kk, cl] = True
    return r4o, rep, gate, MT


r4_pub, rep_pub, gate_pub, MT_PUB = meta_replace(r4, INPUTS["META_V4"][0], -1, E_PUB, "e1cf515e (published)")
check("meta.pub.cache_intervals_equal_accounting_y4_off_clip", gate_pub["max_abs_diff"] < 1e-6, gate_pub)
r4_new, rep_new, gate_new, _ = meta_replace(r4, INPUTS["META_X0918"][0], E_PUB, E_LAST + 14400, "22e990f8 (stream D, after E_pub)")
check("meta.x0918.cache_intervals_equal_accounting_y4_off_clip_after_E_pub", gate_new["max_abs_diff"] < 1e-6 and gate_new["rows_in_window"] > 0, gate_new)
post = ITS > E_PUB
r4s = np.where(post[:, None], r4_new, r4_pub); rep = np.where(post[:, None], rep_new, rep_pub)
tail_clip = clip_any & ~rep
rec["clip"] = {"replaced_published_meta": int(rep_pub[~post].sum()), "replaced_x0918_meta": int(rep_new[post].sum()), "clip_cells_without_meta_set_nan": int(tail_clip.sum()),
               "without_meta": [(utc(ITS[k]), SYM[j]) for k, j in zip(*np.nonzero(tail_clip))][:40]}
log("clip", rec["clip"])
# sensitivity: stream-D meta also on (2026-09-01, E_pub]
r4_sen, rep_sen, gate_sen, _ = meta_replace(r4, INPUTS["META_X0918"][0], SEP1, E_LAST + 14400, "22e990f8 on (09-01, end] (sensitivity)")
mid = (ITS > SEP1) & ~post
r4_sens = np.where(mid[:, None], r4_sen, r4s); rep_sens = np.where(mid[:, None], rep_sen, rep)


def finalize_r4(r4x, repx):
    out = r4x.copy(); out[clip_any & ~repx] = np.nan; return out


R4 = {"primary": finalize_r4(r4s, rep), "sensitivity": finalize_r4(r4_sens, rep_sens)}
del r4, r4_pub, r4_new, r4_sen, r4s, r4_sens

# ---------------- tradability (x0918, prefix = published) ----------------
TR = np.load(INPUTS["TRADABILITY_X0918"][0]); ATS = TR["anchor_ts"].astype(np.int64)
check("trd.grid_equals_interval_ends", bool(np.array_equal(ATS, ITS)) and [str(s) for s in TR["symbols"]] == SYM and np.array_equal(TR["ts5"], CTS))
TRP = np.load(INPUTS["TRADABILITY_PUB"][0]); APS = TRP["anchor_ts"].astype(np.int64)
check("trd.published_state_W24H_is_a_bitwise_prefix", bool(np.array_equal(ATS[:len(APS)], APS)) and bool(np.array_equal(np.asarray(TR["state_W24H"])[:len(APS)], np.asarray(TRP["state_W24H"]))),
      {"published_anchors": len(APS), "x0918_anchors": len(ATS)})
TRADABLE = np.asarray(TR["state_W24H"]) == 2

# ---------------- members on the extended axis ----------------
UP = np.load(INPUTS["UPIT_CRYPTO_SEP"][0]); AXP = UP["ts"].astype(np.int64); UPM = np.asarray(UP["mask"])
check("axis.upit_symbols", [str(s) for s in UP["symbols"]] == SYM)
check("axis.published_axis_ends_at_E_pub", int(AXP[-1]) == E_PUB, utc(AXP[-1]))
sep_rows = np.nonzero(AXP >= SEP1)[0]
check("members.september_rows_identical_monthly_rule", len(sep_rows) > 0 and all(np.array_equal(UPM[sep_rows[0]], UPM[i]) for i in sep_rows), {"september_rows": int(len(sep_rows))})
EXT = np.arange(E_PUB + 14400, E_LAST + 1, 14400, dtype=np.int64)
check("axis.extension_all_in_september", bool(np.all((EXT >= SEP1) & (EXT < calendar.timegm((2026, 10, 1, 0, 0, 0))))), {"n": len(EXT)})
AX = np.concatenate([AXP, EXT]); NAX = len(AX); NPUB = len(AXP)
UPX = np.vstack([UPM, np.repeat(UPM[sep_rows[0]][None, :], len(EXT), 0)])
kax = np.array([kpos.get(int(t), -1) for t in AX]); check("axis.every_anchor_on_interval_grid", bool((kax > 0).all()), {"anchors": NAX, "last": utc(AX[-1])})
MEM = UPX & TRADABLE[kax]
UA = np.load(INPUTS["UMASK_ARM"][0]); uts = UA["ts"].astype(np.int64); NA = len(uts)
check("members.rebuild_equals_arm_umask_bitwise", bool(np.array_equal(AX[:NA], uts) and np.array_equal(MEM[:NA], np.asarray(UA["mask"]))))
ARM = np.load(INPUTS["ARM_A0_S42"][0], allow_pickle=True); acols = [str(c) for c in ARM["cols"]]; AR = np.asarray(ARM["d30_n2_c42_rec"])
check("members.arm_nmember_equals_member_count", bool(np.array_equal(AR[:, 0].astype(np.int64), AX[:NA]) and np.array_equal(AR[:, acols.index("nmember")].astype(np.int64), MEM[:NA].sum(1))))

# ---------------- funding 8h-equivalent (ivfix ≤ E_pub; x0918 panel; 4h accounting table for the last anchors) ----------------
PX = np.load(INPUTS["PANEL_IVFIX"][0]); PA = np.load(INPUTS["PANEL_ARM"][0])
check("fund.ivfix_axis_is_published_axis", bool(np.array_equal(PX["ts"].astype(np.int64), AXP)) and [str(s) for s in PX["symbols"]] == SYM)
FN = np.asarray(PX["f_fund_now"], np.float64); IV = np.asarray(PX["f_fund_iv"], np.float64)
check("fund.ivfix_prefix_equals_arm_panel", bool(np.array_equal(PA["ts"].astype(np.int64), AXP[:NA]) and np.array_equal(np.asarray(PA["f_fund_now"], np.float64), FN[:NA], equal_nan=True)
      and np.array_equal(np.asarray(PA["f_fund_iv"], np.float64), IV[:NA], equal_nan=True)))
PQ = np.load(INPUTS["PANEL_X0918"][0]); pqts = PQ["ts"].astype(np.int64); pqi = {int(t): i for i, t in enumerate(pqts)}
check("fund.x0918_panel_symbols", [str(s) for s in PQ["symbols"]] == SYM)
QN = np.asarray(PQ["f_fund_now"], np.float64); QV = np.asarray(PQ["f_fund_iv"], np.float64)
ov = [a for a in AXP if int(a) in pqi]
ia = np.array([np.nonzero(AXP == a)[0][0] for a in ov]); iq = np.array([pqi[int(a)] for a in ov])
check("fund.x0918_panel_equals_ivfix_on_overlap_bitwise", len(ov) >= NA and bool(np.array_equal(QN[iq], FN[ia], equal_nan=True)) and bool(np.array_equal(QV[iq], IV[ia], equal_nan=True)), {"overlap_anchors": len(ov)})
F4 = np.load(INPUTS["FUND4H_X0918"][0]); f4ts = F4["ts"].astype(np.int64); f4i = {int(t): i for i, t in enumerate(f4ts)}
check("fund.4h_table_symbols", [str(s) for s in F4["symbols"]] == SYM)
F4N = np.asarray(F4["f_fund_now"], np.float64); F4V = np.asarray(F4["f_fund_iv"], np.float64)
ov2 = [int(a) for a in pqts if int(a) in f4i]
check("fund.4h_table_equals_x0918_panel_on_overlap_bitwise", len(ov2) > 0 and bool(np.array_equal(F4N[[f4i[a] for a in ov2]], QN[[pqi[a] for a in ov2]], equal_nan=True))
      and bool(np.array_equal(F4V[[f4i[a] for a in ov2]], QV[[pqi[a] for a in ov2]], equal_nan=True)), {"overlap_anchors": len(ov2), "first": utc(ov2[0]) if ov2 else None})
FNX = np.full((NAX, NW), np.nan); IVX = np.full((NAX, NW), np.nan); src = []
for a in range(NAX):
    t = int(AX[a])
    if a < NPUB: FNX[a] = FN[a]; IVX[a] = IV[a]; src.append("ivfix")
    elif t in pqi: FNX[a] = QN[pqi[t]]; IVX[a] = QV[pqi[t]]; src.append("x0918_panel")
    elif t in f4i: FNX[a] = F4N[f4i[t]]; IVX[a] = F4V[f4i[t]]; src.append("x0918_4h_accounting")
    else: src.append("missing")
check("fund.every_extension_anchor_has_a_source", "missing" not in src, {k: src.count(k) for k in set(src)})
rec["fund_source_counts"] = {k: src.count(k) for k in set(src)}
F8 = FNX * (8.0 / np.where(np.isfinite(IVX) & (IVX > 0), IVX, 8.0))
del PA, PQ

# ---------------- state variables (verbatim loop), primary + sensitivity ----------------
r5b = R5[:, IB].astype(np.float64); r5b_ok = np.isfinite(r5b)
cQ = {}; cN = {}
for v, fm in (("INCL", np.zeros(len(CTS), bool)), ("EXCL", FILLED_BTC)):
    use = r5b_ok & ~fm
    cQ[v] = np.concatenate([[0.0], np.cumsum(np.where(use, r5b * r5b, 0.0))]); cN[v] = np.concatenate([[0], np.cumsum(use.astype(np.int64))])


def state_vars(r4):
    L = np.where(np.isfinite(r4), np.log1p(np.where(np.isfinite(r4), r4, 0.0)), 0.0)
    BAD = (~np.isfinite(r4)) | (~TRADABLE) | nan_any
    BAD[0] = True
    cL = np.vstack([np.zeros((1, NW)), np.cumsum(L, 0)]); cB = np.vstack([np.zeros((1, NW), np.int64), np.cumsum(BAD, 0)]); cF = np.vstack([np.zeros((1, NW), np.int64), np.cumsum(fill_any, 0)])

    def wret(k, n, excl):
        lo = k - n + 1
        if lo < 1: return np.full(NW, np.nan)
        s = cL[k + 1] - cL[lo]; b = cB[k + 1] - cB[lo]; f = cF[k + 1] - cF[lo]
        ok = (b == 0) & ((f == 0) if excl else True)
        return np.where(ok, np.expm1(s), np.nan)
    OUT = {v: np.full((NAX, 7), np.nan) for v in ("EXCL", "INCL")}; NN = {v: np.zeros((NAX, 7), np.int64) for v in ("EXCL", "INCL")}
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
        if a % 2500 == 0: log("anchor", a, "/", NAX, utc(AX[a]))
    return OUT, NN


def expanding_labels(x):
    """verbatim from g0_regime_tables.py (6f448750)"""
    lab = np.full(len(x), -1, np.int8); q = np.full((len(x), 2), np.nan); pr = np.full(len(x), np.nan)
    fin = np.isfinite(x); cnt = np.cumsum(fin)
    for t in range(len(x)):
        if not fin[t] or cnt[t] <= WARM: continue
        h = x[:t + 1][fin[:t + 1]]; q1, q2 = np.quantile(h, [1 / 3, 2 / 3]); q[t] = (q1, q2)
        lab[t] = 0 if x[t] < q1 else (2 if x[t] > q2 else 1); pr[t] = float(np.mean(h <= x[t]))
    return lab, q, pr


def labels(OUT):
    LB = {}; QQ = {}; PR = {}
    for v in OUT:
        LB[v] = np.full((NAX, 7), -1, np.int8); QQ[v] = np.full((NAX, 7, 2), np.nan); PR[v] = np.full((NAX, 7), np.nan)
        for j in range(7): LB[v][:, j], QQ[v][:, j], PR[v][:, j] = expanding_labels(OUT[v][:, j])
    return LB, QQ, PR


OUTp, NNp = state_vars(R4["primary"]); LBp, QQp, PRp = labels(OUTp); log("primary state + labels")
# ---------------- prefix proof (bitwise vs the published files) ----------------
PS = np.load(INPUTS["PUB_STATE"][0], allow_pickle=True); PL = np.load(INPUTS["PUB_LABELS"][0], allow_pickle=True)
check("prefix.axis", bool(np.array_equal(PS["ts"].astype(np.int64), AXP)) and bool(np.array_equal(PL["ts"].astype(np.int64), AXP)))
proof = {}
for key, mine, pub in (("EXCL", OUTp["EXCL"], PS["EXCL"]), ("INCL", OUTp["INCL"], PS["INCL"]), ("N_EXCL", NNp["EXCL"], PS["N_EXCL"]), ("N_INCL", NNp["INCL"], PS["N_INCL"]),
                       ("LAB_EXCL", LBp["EXCL"], PL["LAB_EXCL"]), ("LAB_INCL", LBp["INCL"], PL["LAB_INCL"]), ("Q_EXCL", QQp["EXCL"], PL["Q_EXCL"]),
                       ("Q_INCL", QQp["INCL"], PL["Q_INCL"]), ("PR_EXCL", PRp["EXCL"], PL["PR_EXCL"]), ("PR_INCL", PRp["INCL"], PL["PR_INCL"])):
    a_ = np.asarray(mine)[:NPUB]; b_ = np.asarray(pub)
    eq = bool(np.array_equal(a_, b_, equal_nan=True)) if a_.dtype.kind == "f" else bool(np.array_equal(a_, b_))
    proof[key] = {"cells": int(a_.size), "equal_bitwise": eq, "n_differ": int((~((a_ == b_) | (np.isnan(a_) & np.isnan(b_)))).sum()) if a_.dtype.kind == "f" else int((a_ != b_).sum())}
    check(f"prefix.{key}_bitwise_equal_published", eq, proof[key])
rec["prefix_proof"] = proof
# ---------------- sensitivity (reported only) ----------------
OUTs, NNs = state_vars(R4["sensitivity"]); LBs, _, _ = labels(OUTs)
rec["sensitivity_stream_D_meta_from_0901"] = {v: {"state_values_differ_prefix": int((~((OUTs[v][:NPUB] == OUTp[v][:NPUB]) | (np.isnan(OUTs[v][:NPUB]) & np.isnan(OUTp[v][:NPUB])))).sum()),
                                                  "labels_differ_prefix": int((LBs[v][:NPUB] != LBp[v][:NPUB]).sum()),
                                                  "labels_differ_extension": int((LBs[v][NPUB:] != LBp[v][NPUB:]).sum()),
                                                  "labels_differ_prefix_by_var": {VARS[j]: int((LBs[v][:NPUB, j] != LBp[v][:NPUB, j]).sum()) for j in range(7)}} for v in ("EXCL", "INCL")}
log("sensitivity", rec["sensitivity_stream_D_meta_from_0901"])
rec["extension"] = {"anchors": int(len(EXT)), "first": utc(EXT[0]), "last": utc(EXT[-1]),
                    "labelled_EXCL_by_var": {VARS[j]: int((LBp["EXCL"][NPUB:, j] >= 0).sum()) for j in range(7)},
                    "undefined_EXCL_by_var": {VARS[j]: int((~np.isfinite(OUTp["EXCL"][NPUB:, j])).sum()) for j in range(7)}}
if FAILS: finish(3, "BT_G0_EXTEND VERDICT=RED")
sp = f"{OUT_DIR}/g0_state_vars_x0918.npz"; lp = f"{OUT_DIR}/g0_labels_x0918.npz"
np.savez_compressed(sp, ts=AX, vars=np.array(VARS), EXCL=OUTp["EXCL"], INCL=OUTp["INCL"], N_EXCL=NNp["EXCL"], N_INCL=NNp["INCL"], n_members=MEM.sum(1), n_published=np.array(NPUB))
np.savez_compressed(lp, ts=AX, vars=np.array(VARS), LAB_EXCL=LBp["EXCL"], LAB_INCL=LBp["INCL"], Q_EXCL=QQp["EXCL"], Q_INCL=QQp["INCL"], PR_EXCL=PRp["EXCL"], PR_INCL=PRp["INCL"],
                    n_published=np.array(NPUB))
rec["outputs"] = {"state_vars": {"path": sp, "sha256": sha(sp)}, "labels": {"path": lp, "sha256": sha(lp)}}
rec["VERDICT"] = "PASS"
finish(0, "BT_G0_EXTEND VERDICT=PASS anchors=%d (published %d + extension %d) prefix_bitwise=%d/%d" % (NAX, NPUB, len(EXT), sum(v["equal_bitwise"] for v in proof.values()), len(proof)))
