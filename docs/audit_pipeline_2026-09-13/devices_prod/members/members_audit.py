#!/usr/bin/env python3
"""members_audit.py -- AUDIT_PROD item 3: membership and liquidity gates, production vs research (pod2, CPU only).
Measurement only (no P&L). Read-only on every input; writes only /workspace/aud_prod_2026-09-13/members/receipts/members_audit.json.

Definitions reproduced (code facts quoted in the audit):
  P  production  ~/wide_shadow/shadow_loop_v3.py e9c98374 L365-380: window rows [ai-2015, ai] (incl. the bar closing at the anchor),
     covr = finite(ret5)/2016 >= 0.95, v7 (divisor finite ret5) >= 1e-4, qvm = sum log1p(qv)/finite(lqv), NTOP 400 by qvm, float32 sums,
     universe = the 450 names the producer fetches (others NaN in its cache); sel = expm1(clip(qvm,0,30))*48 >= 2.5e5 (L473-474).
  K  king training  pod_fea_ext.py 02157bda L24-41 / pod_fea_ext_clamp.py b9f9c728 (x0910): rows [E-2016, E-1], v7 divisor finite(lqv),
     look-ahead: >=46 finite ret5 in rows [E, E+47], universe 829, float64.
  D  DL training  pod_dlw_targets_ext.py c21683ee / pod_dlw_targets_raw.py d7c52823 L79-106: rows [E-2016, E-1], qvm = zero-filled lqv sum / finite(ret5),
     v7 divisor finite(ret5), look-ahead: >=46 finite ret5 in rows [E+1, E+48], universe 829, float64.
  R  research replay A0 (r18_drive.py A0(): MEMBERS_TOPN=829, UMASK_SCOPE=m1, w10_sleeve_r18.py 9b8a6323 L77-83, L162-167, L244-245):
     members = all names with finite meta qvk (rebuilt ranking, top 829) masked by umask_UPIT_CRYPTO row of the panel ts;
     sel = finite meta y4 (RAW, rows [E+1,E+48]) & expm1(clip(qvk,0,30))*48 >= 2.5e5 (look-ahead finiteness).
Gates (reported, all computed before any comparison is summarised):
  DP  data parity: production snapshot rolling.npz (09-13 04Z) vs pod holefix2_x0910 cache on common rows, live450 columns, per channel
  V1  P rule (verbatim float32 code) on the production snapshot reproduces weights/<A>.npz members exactly (every anchor with a full window)
  V2  same rule on the pod cache restricted to live450 reproduces them for anchors <= cache end
  V3  K rule reproduces the stored x0910 king-meta members; V4 D rule reproduces the stored x0910 DL-target members
  VS  P sel rule reproduces prev_rec sel_idx of the snapshot anchor 1789272000
Launch: device/members_run_pod2.sh (verbatim command inside).
"""
import os, sys, json, time, hashlib, zipfile, calendar, subprocess
from collections import Counter
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "env whitelist argv[1] required"
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
T0 = time.time()
def log(*a): print("[%7.1fs]" % (time.time() - T0), *a, flush=True)
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()
def U(t): return time.strftime("%Y-%m-%d %HZ", time.gmtime(int(t)))
P = "/workspace/aud_prod_2026-09-13/members"; ST = P + "/stage"; OUT = P + "/receipts/members_audit.json"
INPUTS = {
    "cache": ("/workspace/data/dlnative_5m_wide829_f16_holefix2_x0910.npz", "8115299410cd5e8df46ecc5ac7baf312d9f593d94f3b4c3dc46471bd37e00336"),
    "kmeta": ("/workspace/uplift_2026-09-11/r6/out/wide_fea_v4_meta_x0910.npz", "ec791d1f2fb455c3e73381b7f5f828384ed65dbd3c5e1ab3c62ea9f3d182f21d"),
    "tgt": ("/workspace/uplift_2026-09-11/r6/out/dlw_targets_x0910.npz", "5b628413d0c06d2a989c1ab624783238e7871a9f6a84675be372901a5fbb27de"),
    "npmeta": ("/workspace/uplift_2026-09-11/r6/out/meta_newprod_v4_x0910.npz", "a8eb359701c71acfe853a295eb055bdbb04e1c29b6534ccdf23aeaff69907245"),
    "panel_x": ("/workspace/uplift_2026-09-11/r6/out/wide_panel_4h_v2ext_x0910.npz", "042478f7d8e9f9476341a2acb310828fcf1f5d4a855c2ad0105a08e78f604549"),
    "umask": ("/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz", "47d87b5165b695a7d9b340134a189dd6a2165c837bab35808b699ffac3f7f1b5"),
    "umask_cf": ("/workspace/uplift_r2_2026-09-13/T5c/masks/umask_UPIT_CRYPTO_cf_x0910.npz", "60e25a184da5f88e76826935646368b384dd6e0b244506b849260daacf4ff0e4"),
    "slow_a0": ("/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy", "647673183e6af44ac5b2570b856692c9d2d51ab9f17194bfebb7a0d3dbbd9009"),
}
RC = {"self_sha256": sha(os.path.abspath(__file__)), "env": {"whitelist": sorted(WHITE), "actual": {k: os.environ[k] for k in sorted(os.environ)}},
      "python": sys.version.split()[0], "numpy": np.__version__, "argv": sys.argv, "inputs": {}, "gates": {}, "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
RC["launcher"] = {"path": P + "/device/members_run_pod2.sh", "sha256": sha(P + "/device/members_run_pod2.sh")}
def sh(cmd):
    try: return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as e: return "ERR %s" % e
RC["pids_before"] = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); RC["load_before"] = open("/proc/loadavg").read().split()[:3]
for k, (p, h) in INPUTS.items():
    g = sha(p); RC["inputs"][k] = {"path": p, "sha256": g}
    assert g == h, ("INPUT SHA MISMATCH", k, g)
man = json.load(open(ST + "/manifest.json"))
STAGED = {"config.json": ST + "/config.json", "prod_members.npz": ST + "/prod_members.npz", "prod_prev_rec_1789272000.json": ST + "/prod_prev_rec_1789272000.json",
          "snapshot_rolling.npz": ST + "/snapshot_rolling_1789272000.npz"}
for k, p in STAGED.items():
    g = sha(p); RC["inputs"]["staged:" + k] = {"path": p, "sha256": g}
    assert g == man["staged"][k], ("STAGED SHA MISMATCH", k, g)
RC["inputs"]["staged:manifest.json"] = {"path": ST + "/manifest.json", "sha256": sha(ST + "/manifest.json"), "sources": man["sources"]}
log("inputs verified")

# ---------------- axes
cfg = json.load(open(STAGED["config.json"])); SYMS = [str(s) for s in cfg["symbols_panel"]]; LIVE = [str(s) for s in cfg["symbols_live"]]; PR = cfg["params"]
NW = len(SYMS); assert NW == 829
SIDX = {s: j for j, s in enumerate(SYMS)}; LIVE_MASK = np.zeros(NW, bool); LIVE_MASK[[SIDX[s] for s in LIVE]] = True
assert int(LIVE_MASK.sum()) == 450, "symbols_live not a subset of symbols_panel"
zf = zipfile.ZipFile(INPUTS["cache"][0])
with zf.open("symbols.npy") as f: CSYM = [str(s) for s in np.lib.format.read_array(f, allow_pickle=True)]
with zf.open("ch.npy") as f: CCH = [str(s) for s in np.lib.format.read_array(f, allow_pickle=True)]
with zf.open("ts.npy") as f: CTS_ALL = np.lib.format.read_array(f).astype(np.int64)
assert CSYM == SYMS, "pod cache symbol order != production symbols_panel"
assert CCH == ["ret5", "range", "cpos", "log_qv", "log_cnt", "log_avgsz", "tbf"], CCH
assert (np.diff(CTS_ALL) == 300).all()
TG = np.load(INPUTS["tgt"][0], allow_pickle=True); assert [str(s) for s in TG["symbols"]] == SYMS, "DL targets symbol order"
UMr = np.load(INPUTS["umask"][0], allow_pickle=True); UMc = np.load(INPUTS["umask_cf"][0], allow_pickle=True)
assert [str(s) for s in UMr["symbols"]] == SYMS and [str(s) for s in UMc["symbols"]] == SYMS, "umask symbol order"
RC["axes"] = {"symbols_panel_equal_cache_targets_umask": True, "live450": 450, "cache_rows": int(len(CTS_ALL)), "cache_first": U(CTS_ALL[0]), "cache_last_utc": time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(CTS_ALL[-1]))),
              "umask_raw_last": U(UMr["ts"].astype(np.int64)[-1]), "umask_cf_last": U(UMc["ts"].astype(np.int64)[-1])}

# ---------------- pod cache tail (streaming decompress, keep rows >= T_START)
T_START = calendar.timegm((2026, 8, 4, 0, 0, 0)); START_ROW = int(np.searchsorted(CTS_ALL, T_START)); assert CTS_ALL[START_ROW] == T_START
with zf.open("data.npy") as f:
    ver = np.lib.format.read_magic(f)
    shape, fortran, dtype = (np.lib.format.read_array_header_1_0(f) if ver == (1, 0) else np.lib.format.read_array_header_2_0(f))
    assert (not fortran) and dtype == np.float16 and shape[0] == len(CTS_ALL) and tuple(shape[1:]) == (829, 7), (shape, fortran, dtype)
    rowb = 829 * 7 * 2; skip = START_ROW * rowb
    while skip > 0:
        b = f.read(min(1 << 26, skip)); assert len(b) > 0; skip -= len(b)
    nrows = shape[0] - START_ROW; buf = bytearray(nrows * rowb); mv = memoryview(buf); got = 0
    while got < len(buf):
        b = f.read(min(1 << 26, len(buf) - got)); assert len(b) > 0; mv[got:got + len(b)] = b; got += len(b)
CD = np.frombuffer(buf, np.float16).reshape(nrows, 829, 7); CTS = CTS_ALL[START_ROW:]; del CTS_ALL
CROW = {int(t): i for i, t in enumerate(CTS)}
log("pod cache tail", CD.shape, U(CTS[0]), U(CTS[-1]))

# ---------------- production snapshot + members
SZ = np.load(STAGED["snapshot_rolling.npz"]); STS = SZ["ts"].astype(np.int64); SD = SZ["data"]; assert SD.dtype == np.float16 and SD.shape[1:] == (829, 7) and (np.diff(STS) == 300).all()
SROW = {int(t): i for i, t in enumerate(STS)}
PM = np.load(STAGED["prod_members.npz"], allow_pickle=True); PANCH = PM["anchors"].astype(np.int64); PMEM = {int(a): np.asarray(m, np.int64) for a, m in zip(PANCH, PM["members"])}
PREV = json.load(open(STAGED["prod_prev_rec_1789272000.json"]))
log("snapshot", SD.shape, U(STS[0]), U(STS[-1]), "prod anchors", len(PANCH), U(PANCH[0]), U(PANCH[-1]))

# ---------------- DP: data parity on common rows, live450 columns
com = np.array(sorted(set(CROW) & set(SROW)), np.int64); ic = np.array([CROW[int(t)] for t in com]); isn = np.array([SROW[int(t)] for t in com])
DP = {"common_rows": int(len(com)), "first": time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(com[0]))), "last": time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(com[-1]))), "channels": {}}
lj = np.where(LIVE_MASK)[0]; nlj = np.where(~LIVE_MASK)[0]
for c, nm in enumerate(CCH):
    a = CD[ic][:, lj, c]; b = SD[isn][:, lj, c]; fa = np.isfinite(a); fb = np.isfinite(b); both = fa & fb
    bit_eq = int((a[both].view(np.uint16) == b[both].view(np.uint16)).sum())
    DP["channels"][nm] = {"cells": int(a.size), "nan_pattern_diff": int((fa != fb).sum()), "pod_finite_prod_nan": int((fa & ~fb).sum()), "prod_finite_pod_nan": int((~fa & fb).sum()),
                          "both_finite": int(both.sum()), "bitwise_equal": bit_eq, "bitwise_diff": int(both.sum()) - bit_eq}
    del a, b, fa, fb, both
DP["snapshot_nonlive_cells_finite"] = int(np.isfinite(SD[:, nlj, :]).sum())
# rows after 09-01 00Z (the r6 extension rows) split out
ext = com >= calendar.timegm((2026, 9, 1, 0, 0, 0))
if ext.any():
    a = CD[ic[ext]][:, lj, :]; b = SD[isn[ext]][:, lj, :]; fa = np.isfinite(a); fb = np.isfinite(b); both = fa & fb
    DP["rows_from_2026-09-01"] = {"rows": int(ext.sum()), "nan_pattern_diff": int((fa != fb).sum()), "bitwise_diff": int(both.sum() - (a[both].view(np.uint16) == b[both].view(np.uint16)).sum())}
    del a, b, fa, fb, both
DP["PASS"] = all(v["nan_pattern_diff"] == 0 and v["bitwise_diff"] == 0 for v in DP["channels"].values())
RC["gates"]["DP_data_parity_live450"] = DP; log("DP", DP["PASS"], {k: (v["nan_pattern_diff"], v["bitwise_diff"]) for k, v in DP["channels"].items()})

# ---------------- rules
NTOP, COV, VOLMIN, QMIN = int(PR["NTOP"]), float(PR["cov_min"]), float(PR["vol_min"]), float(PR["qv4h_min"])
assert (NTOP, COV, VOLMIN, QMIN) == (400, 0.95, 1e-4, 2.5e5), (NTOP, COV, VOLMIN, QMIN)
def prod_rule(C16, ai, universe=None):
    """VERBATIM shadow_loop_v3.py L355-380 (float32 path). C16 = (T, 829, 7) float16 cache whose row ai is the anchor.
    Only rows [ai-2015, ai] are read (as production); the view passed on is that contiguous block, so the float32 reductions see the
    same memory layout/strides as production CDf[max(ai+1-2016,0):ai+1, :, ch]. universe (bool 829) optional: names outside set NaN
    (= a producer that fetched only those names)."""
    lo = max(ai + 1 - 2016, 0); W16 = C16[lo:ai + 1]
    X = W16 if universe is None else np.where(universe[None, :, None], W16, np.float16(np.nan))
    CDf = np.ascontiguousarray(X).astype(np.float32); a2 = CDf.shape[0] - 1
    r5seg = CDf[max(a2 + 1 - 2016, 0):a2 + 1, :, 0]
    fin5 = np.isfinite(r5seg)
    covr = fin5.sum(0) / 2016
    m7 = np.where(fin5, r5seg, 0).sum(0)
    n7 = np.maximum(fin5.sum(0), 1)
    v7 = np.sqrt(np.maximum(np.where(fin5, r5seg**2, 0).sum(0) / n7 - (m7 / n7) ** 2, 0))
    qseg = CDf[max(a2 + 1 - 2016, 0):a2 + 1, :, 3]
    finq = np.isfinite(qseg)
    qvm = np.where(finq, qseg, 0).sum(0) / np.maximum(finq.sum(0), 1)
    ok = (covr >= COV) & (v7 >= VOLMIN)
    m = np.where(ok)[0]
    if len(m) > NTOP:
        m = np.sort(m[np.argsort(-qvm[m])[:NTOP]])
    if len(m) < 50: return None, qvm
    return m, qvm
def win_stats(e, clock, univ):
    """float64 window statistics on the pod cache tail for anchor row e. clock 'E' rows [e-2015, e]; 'E-1' rows [e-2016, e-1]."""
    lo, hi = (e - 2015, e + 1) if clock == "E" else (e - 2016, e)
    assert lo >= 0 and e + 49 <= CD.shape[0], (e, lo, hi)
    r = CD[lo:hi, :, 0].astype(np.float32); q = CD[lo:hi, :, 3].astype(np.float32)
    fr = np.isfinite(r); fq = np.isfinite(q)
    r64 = np.where(fr, r, 0).astype(np.float64); q64 = np.where(fq, q, 0).astype(np.float64)
    st = dict(c5=fr.sum(0), cq=fq.sum(0), sr=r64.sum(0), sr2=(r64 ** 2).sum(0), sq=q64.sum(0))
    fwd = np.isfinite(CD[e:e + 49, :, 0])
    st["laK"] = fwd[0:48].sum(0) >= 46; st["laD"] = fwd[1:49].sum(0) >= 46
    if univ is not None:
        for k in ("c5", "cq"): st[k] = np.where(univ, st[k], 0)
        for k in ("sr", "sr2", "sq"): st[k] = np.where(univ, st[k], 0.0)
    return st
def rule64(st, la, v7div, qdiv):
    covr = st["c5"] / 2016
    dv = np.maximum(st["c5"] if v7div == "r" else st["cq"], 1); dq = np.maximum(st["c5"] if qdiv == "r" else st["cq"], 1)
    v7 = np.sqrt(np.maximum(st["sr2"] / dv - (st["sr"] / dv) ** 2, 0)); qvm = st["sq"] / dq
    ok = (covr >= COV) & (v7 >= VOLMIN)
    if la == "K": ok &= st["laK"]
    elif la == "D": ok &= st["laD"]
    m = np.where(ok)[0]
    if len(m) > NTOP:
        m = np.sort(m[np.argsort(-qvm[m])[:NTOP]])
    if len(m) < 50: return None, qvm
    return m, qvm
def symd(a, b):
    if a is None or b is None: return None
    return int(len(np.setxor1d(a, b)))

# ---------------- V1 / V2 / VS : production rule validation
V1 = {"anchors": 0, "exact": 0, "mismatch": []}
for a in PANCH:
    a = int(a); ai = SROW.get(a)
    if ai is None or ai - 2015 < 0: continue
    m, _ = prod_rule(SD[:ai + 1], ai)
    V1["anchors"] += 1
    if m is not None and np.array_equal(m, PMEM[a]): V1["exact"] += 1
    else: V1["mismatch"].append({"anchor": U(a), "symdiff": symd(m, PMEM[a])})
V1["first"] = U(max(PANCH[0], STS[2015])); V1["last"] = U(min(PANCH[-1], STS[-1])); V1["PASS"] = V1["anchors"] >= 5 and V1["exact"] == V1["anchors"]
RC["gates"]["V1_prod_rule_on_snapshot"] = V1; log("V1", V1["exact"], "/", V1["anchors"])
V2 = {"anchors": 0, "exact": 0, "mismatch": []}
for a in PANCH:
    a = int(a); ai = CROW.get(a)
    if ai is None or ai - 2015 < 0: continue
    m, _ = prod_rule(CD[:ai + 1], ai, universe=LIVE_MASK)
    V2["anchors"] += 1
    if m is not None and np.array_equal(m, PMEM[a]): V2["exact"] += 1
    else: V2["mismatch"].append({"anchor": U(a), "symdiff": symd(m, PMEM[a])})
V2["PASS"] = V2["anchors"] >= 5 and V2["exact"] == V2["anchors"]
RC["gates"]["V2_prod_rule_on_pod_cache_live450"] = V2; log("V2", V2["exact"], "/", V2["anchors"])
ai = SROW[PREV["anchor_ts"]]; m, qvm = prod_rule(SD[:ai + 1], ai); qv4h = np.expm1(np.clip(qvm[m], 0, 30)) * 48; sel_idx = np.where(qv4h >= QMIN)[0]
RC["gates"]["VS_prod_sel_rule"] = {"anchor": U(PREV["anchor_ts"]), "members_equal": bool(np.array_equal(m, np.array(PREV["members"]))), "sel_idx_equal": bool(np.array_equal(sel_idx, np.array(PREV["sel_idx"]))),
                                    "n_sel": int(len(sel_idx))}
RC["gates"]["VS_prod_sel_rule"]["PASS"] = RC["gates"]["VS_prod_sel_rule"]["members_equal"] and RC["gates"]["VS_prod_sel_rule"]["sel_idx_equal"]
log("VS", RC["gates"]["VS_prod_sel_rule"])

# ---------------- research sets on the overlap axis
KM = np.load(INPUTS["kmeta"][0], allow_pickle=True); KE = KM["E_ts"].astype(np.int64); KMEMS = KM["members"]; KMEM = {int(t): np.asarray(m, np.int64) for t, m in zip(KE, KMEMS)}   # NpzFile re-reads a key on every access: load once
DE = TG["E_ts"].astype(np.int64); DMEM = {int(t): np.asarray(m, np.int64) for t, m in zip(DE, TG["members"])}
NM = np.load(INPUTS["npmeta"][0], allow_pickle=True); NE = NM["E_ts"].astype(np.int64); assert np.array_equal(NE, KE), "meta_newprod axis != king meta axis"
NROW = {int(t): i for i, t in enumerate(NE)}; NQVK = NM["qvk"]; NY4 = NM["y4"]
NMEMS = NM["members"]; assert all(np.array_equal(np.asarray(KMEMS[i]), np.asarray(NMEMS[i])) for i in range(len(KE))), "meta_newprod members != king meta members"
PXTS = set(int(t) for t in np.load(INPUTS["panel_x"][0], allow_pickle=True)["ts"].astype(np.int64))
UMR_ROW = {int(t): k for k, t in enumerate(UMr["ts"].astype(np.int64))}; UMC_ROW = {int(t): k for k, t in enumerate(UMc["ts"].astype(np.int64))}
UMR = np.asarray(UMr["mask"]); UMC = np.asarray(UMc["mask"])
SLOW = np.load(INPUTS["slow_a0"][0], mmap_mode="r"); assert SLOW.shape[1] == 829
RC["axes"].update({"king_meta_last": U(KE[-1]), "dl_targets_last": U(DE[-1]), "panel_x_last": U(max(PXTS)), "slow_a0_rows": int(SLOW.shape[0]), "slow_a0_last": U(KE[SLOW.shape[0] - 1])})
OV_ANCH = [int(a) for a in PANCH if int(a) in KMEM and int(a) in DMEM and int(a) in CROW and CROW[int(a)] - 2016 >= 0 and CROW[int(a)] + 49 <= CD.shape[0]]
log("overlap anchors", len(OV_ANCH), U(OV_ANCH[0]), U(OV_ANCH[-1]))

# ---------------- V3/V4 reproduction + M1/M2 per anchor
ROWS = []; CNT = {k: Counter() for k in ("P_not_K", "K_not_P", "P_not_D", "D_not_P", "K_not_P_live450", "D_not_P_live450", "Psel_not_Rsel", "Rsel_not_Psel")}
V3 = {"anchors": 0, "exact": 0, "mismatch": []}; V4 = {"anchors": 0, "exact": 0, "mismatch": []}
PATHK = ["K0_rule_829_laK_Em1_divK_f64", "K1_live450", "K2_no_lookahead", "K3_clock_E", "K4_divP", "K5_float32_eq_P"]
PATHD = ["D0_rule_829_laD_Em1_divD_f64", "D1_live450", "D2_no_lookahead", "D3_clock_E", "D4_divP", "D5_float32_eq_P"]
ONE = ["P_univ829_vs_P", "P_lookaheadK_vs_Pf64", "P_lookaheadD_vs_Pf64", "P_clockEm1_vs_Pf64", "P_divK_vs_Pf64", "P_divD_vs_Pf64", "Pf64_vs_P"]
QV = {"dlog_P_vs_R": [], "dlog_r17_vs_R": [], "tier_agree_P_R": [0, 0], "tier_agree_r17_R": [0, 0], "cross_thr_P_R": 0, "n_common": 0}
def tier(q): return np.where(q >= 5e6, 0, np.where(q >= 1e6, 1, 2))
for a in OV_ANCH:
    e = CROW[a]; row = {"anchor": U(a), "ts": a}
    if len(ROWS) % 20 == 0: log("anchor", U(a), len(ROWS), "/", len(OV_ANCH))
    Pm = PMEM[a]; Km = KMEM[a]; Dm = DMEM[a]
    sKf = win_stats(e, "E-1", None); sKl = win_stats(e, "E-1", LIVE_MASK); sEl = win_stats(e, "E", LIVE_MASK); sEf = win_stats(e, "E", None)
    k0, _ = rule64(sKf, "K", "q", "q"); d0, _ = rule64(sKf, "D", "r", "r")
    V3["anchors"] += 1; V4["anchors"] += 1
    if k0 is not None and np.array_equal(k0, Km): V3["exact"] += 1
    else: V3["mismatch"].append({"anchor": U(a), "symdiff": symd(k0, Km)})
    if d0 is not None and np.array_equal(d0, Dm): V4["exact"] += 1
    else: V4["mismatch"].append({"anchor": U(a), "symdiff": symd(d0, Dm)})
    pP, qvmP = prod_rule(CD[:e + 1], e, universe=LIVE_MASK)
    k1, _ = rule64(sKl, "K", "q", "q"); k2, _ = rule64(sKl, None, "q", "q"); k3, _ = rule64(sEl, None, "q", "q"); k4, _ = rule64(sEl, None, "r", "q")
    d1, _ = rule64(sKl, "D", "r", "r"); d2, _ = rule64(sKl, None, "r", "r"); d3, _ = rule64(sEl, None, "r", "r"); d4, _ = rule64(sEl, None, "r", "q")
    pathK = [k0, k1, k2, k3, k4, pP]; pathD = [d0, d1, d2, d3, d4, pP]
    row["pathK_step_symdiff"] = [None] + [symd(pathK[i - 1], pathK[i]) for i in range(1, 6)]
    row["pathD_step_symdiff"] = [None] + [symd(pathD[i - 1], pathD[i]) for i in range(1, 6)]
    row["pathK_symdiff_to_P"] = [symd(x, Pm) for x in pathK]; row["pathD_symdiff_to_P"] = [symd(x, Pm) for x in pathD]
    # one-at-a-time from P (each toggles one factor; P itself = live450, no look-ahead, clock E, divP, float32)
    u829, _ = prod_rule(CD[:e + 1], e, universe=None)
    stE_l = sEl
    o_laK, _ = rule64(stE_l, "K", "r", "q"); o_laD, _ = rule64(stE_l, "D", "r", "q"); o_c1, _ = rule64(sKl, None, "r", "q")
    o_dK, _ = rule64(stE_l, None, "q", "q"); o_dD, _ = rule64(stE_l, None, "r", "r"); o_f64, _ = rule64(stE_l, None, "r", "q")
    row["one_at_a_time_symdiff_vs_P"] = dict(zip(ONE, [symd(u829, pP), symd(o_laK, o_f64), symd(o_laD, o_f64), symd(o_c1, o_f64), symd(o_dK, o_f64), symd(o_dD, o_f64), symd(o_f64, pP)]))
    row["P_eq_prod_members"] = bool(pP is not None and np.array_equal(pP, Pm))
    if pP is not None:   # NTOP cut margin: qvm gap between the 400th member and the best excluded eligible candidate (float32 production qvm)
        _st = sEl; _ok = (_st["c5"] / 2016 >= COV) & (np.sqrt(np.maximum(_st["sr2"] / np.maximum(_st["c5"], 1) - (_st["sr"] / np.maximum(_st["c5"], 1)) ** 2, 0)) >= VOLMIN)
        _out = np.setdiff1d(np.where(_ok)[0], pP)
        row["ntop_cut_gap_qvm"] = (float(qvmP[pP].min() - qvmP[_out].max()) if len(_out) else None)
    # M1 counts
    for nm, X, Y in (("PK", Pm, Km), ("PD", Pm, Dm), ("KD", Km, Dm)):
        inter = np.intersect1d(X, Y); row[nm] = {"nX": int(len(X)), "nY": int(len(Y)), "inter": int(len(inter)), "X_not_Y": int(len(np.setdiff1d(X, Y))), "Y_not_X": int(len(np.setdiff1d(Y, X))),
                                                  "jaccard": round(float(len(inter) / max(len(np.union1d(X, Y)), 1)), 6)}
    kn = np.setdiff1d(Km, Pm); dn = np.setdiff1d(Dm, Pm)
    row["K_not_P_outside_live450"] = int((~LIVE_MASK[kn]).sum()); row["D_not_P_outside_live450"] = int((~LIVE_MASK[dn]).sum())
    for s in np.setdiff1d(Pm, Km): CNT["P_not_K"][SYMS[s]] += 1
    for s in kn: CNT["K_not_P"][SYMS[s]] += 1
    for s in kn[LIVE_MASK[kn]]: CNT["K_not_P_live450"][SYMS[s]] += 1
    for s in np.setdiff1d(Pm, Dm): CNT["P_not_D"][SYMS[s]] += 1
    for s in dn: CNT["D_not_P"][SYMS[s]] += 1
    for s in dn[LIVE_MASK[dn]]: CNT["D_not_P_live450"][SYMS[s]] += 1
    # R (A0) sets
    i = NROW.get(a); row["panel_row_exists"] = a in PXTS; row["umask_raw_row_exists"] = a in UMR_ROW; row["umask_cf_row_exists"] = a in UMC_ROW
    if i is not None and a in UMC_ROW:
        qv = NQVK[i]; fq = np.isfinite(qv)
        Rm = np.where(fq & UMC[UMC_ROW[a]])[0]; Rnomask = np.where(fq)[0]
        qv4hR = np.expm1(np.clip(np.nan_to_num(qv, nan=0.0), 0, 30)) * 48
        Rsel = Rm[np.isfinite(NY4[i, Rm]) & (qv4hR[Rm] >= QMIN)]
        Psel = Pm[(np.expm1(np.clip(qvmP[Pm], 0, 30)) * 48) >= QMIN] if pP is not None else None
        row["R"] = {"nR": int(len(Rm)), "n_finite_qvk": int(fq.sum()), "n_if_no_mask": int(len(Rnomask)), "R_inter_P": int(len(np.intersect1d(Rm, Pm))), "P_not_R": int(len(np.setdiff1d(Pm, Rm))),
                    "R_not_P": int(len(np.setdiff1d(Rm, Pm))), "R_not_P_outside_live450": int((~LIVE_MASK[np.setdiff1d(Rm, Pm)]).sum()), "K_inter_mask": int(len(np.intersect1d(Km, Rm))),
                    "nRsel": int(len(Rsel)), "nPsel": (int(len(Psel)) if Psel is not None else None)}
        if i < SLOW.shape[0]:
            kf = np.where(np.isfinite(np.asarray(SLOW[i])))[0]; row["R"]["king_rank_base_n"] = int(len(np.intersect1d(kf, Rm))); row["R"]["king_rank_base_inter_P"] = int(len(np.intersect1d(np.intersect1d(kf, Rm), Pm)))
        if Psel is not None:
            isel = np.intersect1d(Psel, Rsel); row["SEL"] = {"inter": int(len(isel)), "Psel_not_Rsel": int(len(np.setdiff1d(Psel, Rsel))), "Rsel_not_Psel": int(len(np.setdiff1d(Rsel, Psel))),
                                                              "jaccard": round(float(len(isel) / max(len(np.union1d(Psel, Rsel)), 1)), 6)}
            ps_nr = np.setdiff1d(Psel, Rsel); rs_np = np.setdiff1d(Rsel, Psel)
            row["SEL"]["Psel_not_Rsel_why"] = {"not_in_R_members": int(len(np.setdiff1d(ps_nr, Rm))), "y4_nan": int((~np.isfinite(NY4[i, ps_nr]) & np.isin(ps_nr, Rm)).sum()),
                                               "qv4hR_below": int(((qv4hR[ps_nr] < QMIN) & np.isfinite(NY4[i, ps_nr]) & np.isin(ps_nr, Rm)).sum())}
            row["SEL"]["Rsel_not_Psel_why"] = {"outside_live450": int((~LIVE_MASK[rs_np]).sum()), "live450_not_P_member": int((LIVE_MASK[rs_np] & ~np.isin(rs_np, Pm)).sum()),
                                               "P_member_qv4hP_below": int((np.isin(rs_np, Pm) & ((np.expm1(np.clip(qvmP[rs_np], 0, 30)) * 48) < QMIN)).sum())}
            for s in ps_nr: CNT["Psel_not_Rsel"][SYMS[s]] += 1
            for s in rs_np: CNT["Rsel_not_Psel"][SYMS[s]] += 1
            # qv4h definitions on common names (P members and R members)
            cm = np.intersect1d(Pm, Rm); qP = np.expm1(np.clip(qvmP[cm], 0, 30)) * 48; qR = qv4hR[cm]
            okc = (qP > 0) & (qR > 0); QV["dlog_P_vs_R"].extend((np.log(qP[okc]) - np.log(qR[okc])).tolist()); QV["n_common"] += int(okc.sum())
            QV["tier_agree_P_R"][0] += int((tier(qP[okc]) == tier(qR[okc])).sum()); QV["tier_agree_P_R"][1] += int(okc.sum())
            QV["cross_thr_P_R"] += int(((qP[okc] >= QMIN) != (qR[okc] >= QMIN)).sum())
            seg = CD[e - 47:e + 1, :, 3][:, cm].astype(np.float64); fin = np.isfinite(seg); qe = np.where(fin, np.expm1(np.clip(seg, 0, 30)), 0.0)
            q17 = np.where(fin.sum(0) >= 40, qe.sum(0), np.nan); ok17 = np.isfinite(q17) & (q17 > 0) & (qR > 0)
            QV["dlog_r17_vs_R"].extend((np.log(q17[ok17]) - np.log(qR[ok17])).tolist())
            QV["tier_agree_r17_R"][0] += int((tier(q17[ok17]) == tier(qR[ok17])).sum()); QV["tier_agree_r17_R"][1] += int(ok17.sum())
    ROWS.append(row)
V3["PASS"] = V3["exact"] == V3["anchors"]; V4["PASS"] = V4["exact"] == V4["anchors"]
RC["gates"]["V3_K_rule_reproduces_stored_king_meta_members"] = V3; RC["gates"]["V4_D_rule_reproduces_stored_dl_target_members"] = V4
log("V3", V3["exact"], "/", V3["anchors"], "V4", V4["exact"], "/", V4["anchors"])

# ---------------- summaries
def summ(vals):
    v = np.array([x for x in vals if x is not None], float)
    if len(v) == 0: return None
    return {"n": int(len(v)), "median": float(np.median(v)), "mean": round(float(v.mean()), 4), "min": float(v.min()), "max": float(v.max())}
S = {}
for nm in ("PK", "PD", "KD"):
    S[nm] = {k: summ([r[nm][k] for r in ROWS]) for k in ("nX", "nY", "inter", "X_not_Y", "Y_not_X", "jaccard")}
S["K_not_P_outside_live450"] = summ([r["K_not_P_outside_live450"] for r in ROWS]); S["D_not_P_outside_live450"] = summ([r["D_not_P_outside_live450"] for r in ROWS])
S["pathK_step_symdiff"] = {PATHK[i]: summ([r["pathK_step_symdiff"][i] for r in ROWS]) for i in range(1, 6)}
S["pathD_step_symdiff"] = {PATHD[i]: summ([r["pathD_step_symdiff"][i] for r in ROWS]) for i in range(1, 6)}
S["pathK_symdiff_to_P"] = {PATHK[i]: summ([r["pathK_symdiff_to_P"][i] for r in ROWS]) for i in range(6)}
S["pathD_symdiff_to_P"] = {PATHD[i]: summ([r["pathD_symdiff_to_P"][i] for r in ROWS]) for i in range(6)}
S["one_at_a_time_symdiff_vs_P"] = {k: summ([r["one_at_a_time_symdiff_vs_P"][k] for r in ROWS]) for k in ONE}
RR = [r for r in ROWS if "R" in r]
S["R"] = {k: summ([r["R"].get(k) for r in RR]) for k in ("nR", "n_finite_qvk", "n_if_no_mask", "R_inter_P", "P_not_R", "R_not_P", "R_not_P_outside_live450", "K_inter_mask", "nRsel", "nPsel", "king_rank_base_n", "king_rank_base_inter_P")}
S["R"]["anchors"] = len(RR); S["R"]["anchors_without_raw_umask_row"] = int(sum(1 for r in RR if not r["umask_raw_row_exists"])); S["R"]["anchors_without_panel_row"] = int(sum(1 for r in ROWS if not r["panel_row_exists"]))
SS = [r for r in RR if "SEL" in r]
S["SEL"] = {k: summ([r["SEL"][k] for r in SS]) for k in ("inter", "Psel_not_Rsel", "Rsel_not_Psel", "jaccard")}
S["SEL"]["Psel_not_Rsel_why_total"] = {k: int(sum(r["SEL"]["Psel_not_Rsel_why"][k] for r in SS)) for k in ("not_in_R_members", "y4_nan", "qv4hR_below")}
S["SEL"]["Rsel_not_Psel_why_total"] = {k: int(sum(r["SEL"]["Rsel_not_Psel_why"][k] for r in SS)) for k in ("outside_live450", "live450_not_P_member", "P_member_qv4hP_below")}
dl = np.array(QV["dlog_P_vs_R"]); d17 = np.array(QV["dlog_r17_vs_R"])
S["QV4H"] = {"n_common_name_anchor": QV["n_common"], "P_vs_R_abs_dlog": {"median": float(np.median(np.abs(dl))), "p90": float(np.percentile(np.abs(dl), 90)), "max": float(np.abs(dl).max()), "mean_signed": float(dl.mean())},
             "P_vs_R_tier_agree": round(QV["tier_agree_P_R"][0] / max(QV["tier_agree_P_R"][1], 1), 6), "P_vs_R_threshold_2.5e5_disagree": QV["cross_thr_P_R"],
             "r17_formula_vs_R_abs_dlog": {"n": int(len(d17)), "median": float(np.median(np.abs(d17))), "p90": float(np.percentile(np.abs(d17), 90)), "mean_signed": float(d17.mean())},
             "r17_formula_vs_R_tier_agree": round(QV["tier_agree_r17_R"][0] / max(QV["tier_agree_r17_R"][1], 1), 6)}
# T5 window (27 combo anchors 08-26 04Z..08-30 20Z excluding 08-29 20Z and 08-30 00Z)
T5A = set(range(calendar.timegm((2026, 8, 26, 4, 0, 0)), calendar.timegm((2026, 8, 30, 20, 0, 0)) + 1, 14400)) - {calendar.timegm((2026, 8, 29, 20, 0, 0)), calendar.timegm((2026, 8, 30, 0, 0, 0))}
T5R = [r for r in RR if r["ts"] in T5A]
S["T5_window"] = {"anchors": len(T5R), "P_not_R": summ([r["R"]["P_not_R"] for r in T5R]), "R_not_P": summ([r["R"]["R_not_P"] for r in T5R]), "nR": summ([r["R"]["nR"] for r in T5R]),
                  "PK_X_not_Y": summ([r["PK"]["X_not_Y"] for r in T5R]), "PK_Y_not_X": summ([r["PK"]["Y_not_X"] for r in T5R]), "K_inter_mask": summ([r["R"]["K_inter_mask"] for r in T5R])}
S["ntop_cut_gap_qvm"] = summ([r.get("ntop_cut_gap_qvm") for r in ROWS])
S["top_symbols"] = {k: CNT[k].most_common(15) for k in CNT}
RC["summary"] = S; RC["rows"] = ROWS
RC["pids_after"] = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); RC["load_after"] = open("/proc/loadavg").read().split()[:3]
RC["wall_s"] = round(time.time() - T0, 1); RC["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
RC["gates_pass"] = {k: v.get("PASS") for k, v in RC["gates"].items()}
os.makedirs(os.path.dirname(OUT), exist_ok=True); json.dump(RC, open(OUT, "w"), indent=1, default=str)
log("GATES", json.dumps(RC["gates_pass"]))
log("SUMMARY PK", json.dumps(S["PK"]["jaccard"]), "PD", json.dumps(S["PD"]["jaccard"]), "R", json.dumps(S["R"]["nR"]), "QV4H", json.dumps(S["QV4H"]))
log("DONE members_audit wall_s", RC["wall_s"])
