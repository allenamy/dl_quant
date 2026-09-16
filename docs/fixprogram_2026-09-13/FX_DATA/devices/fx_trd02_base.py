#!/usr/bin/env python3
"""fx_trd02_base.py — FX-DATA TRD-02 (pod2, CPU, read-only on every input). Committed before it is run.

TRD-02 (AUDIT_DATA bb8a2806, P2): the fund leg's rank base in research ranks each member's funding EMA among EVERY finite value on
the panel row, and dead contracts keep finite funding EMAs because their settlement records continue. P2's TRADING proxy
(>= 1 settlement in (A-24h, A]) has the same contamination. Production's base is exchangeInfo TRADING plus the pinned live list.
The audit measured the contamination with a DESCRIPTIVE flag (DEAD = never trades again inside the cache; and Z24 = has data in
the window but no trade). Neither is causal. This device measures it with the CAUSAL flag, tradable(A) from the TRD-01 artifact,
and hands P2 the per-anchor deviation series it asked for.

  C   positive control, FIRST: reproduce the audit's H3 (fund rank base) and H5.P2_base_proxy_on_king_axis per-year numbers with
      the audit's own definitions, including rebuilding Z24 from ret5 exactly as ad_tradability.py does. If any of them differs,
      the device stops before printing a single new number: the axis / panel / ledger alignment would not be the audit's.
  N   the new causal numbers on both axes (king meta E_ts, and the v2ext panel ts = the A0 / umask axis):
        base_fzb            = # finite f_fund_ema_v1 on the panel row            (the w10 m1 rank base)
        base_fzb_untradable = # of those with no trade in (A-24h, A]
        base_proxy          = # names with >= 1 settlement in (A-24h, A]         (P2's TRADING proxy)
        base_proxy_untradable, and the same split by state (UNTRADED vs NODATA)
  Z   what the contamination does to the LIVE names' fund z: z = rankdata(finite FE)/ (n-1) - 0.5 over the base. Dropping the
      untradable names changes the denominator and every live name's rank position. Reported per anchor: max and mean |dz| over
      tradable members with a finite EMA, the number of members whose z moves by more than 1e-12, and the number of members whose
      z becomes undefined (they were untradable and are now out of the base).
  S   per-anchor series written to an npz for P2 (TRD-02 deviation sizing) and for the A0 arm that follows.

Usage: python3 fx_trd02_base.py <artifact.npz> <artifact_sha256> <AD_H.json> <AD_H_sha256> <out_receipt.json> <out_series.npz>
Exit 0 only if every positive control matched.
"""
import os, sys, json, time, zipfile, calendar
import numpy as np
from scipy.stats import rankdata

ENV_WHITELIST = {"PATH", "HOME", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "PYTHONPATH"}
EXTRA = sorted(k for k in os.environ if k not in ENV_WHITELIST and k not in ("PWD", "SHLVL", "_", "OLDPWD", "LC_CTYPE"))
assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
os.nice(19)
ART, ART_SHA, ADH, ADH_SHA, OUT, OUTNPZ = sys.argv[1:7]
sys.path.insert(0, os.environ["PYTHONPATH"].split(":")[0])
import tradability as T
assert T.SPEC_SHA256 == "99ae35e01ec3dd06ba7bf69ea62de8f36cfd2695492ccf53757d985b8a0946b2"

W = "/workspace"
CACHE = f"{W}/data/dlnative_5m_wide829_f16_holefix2.npz"
AMETA = f"{W}/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"
UMASK = f"{W}/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"
PANEL = f"{W}/data/wide_panel_4h_v2ext.npz"
LEDGER = f"{W}/uplift_r2_2026-09-13/P2/work/ledger_full.npz"
T0 = time.time()
def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)
def utc(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
def yr(t): return time.gmtime(int(t)).tm_year

CHECKS = []; FAILS = []
def check(name, got, expected, tol=0.0):
    if expected is None: ok = False
    elif isinstance(got, float) or isinstance(expected, float): ok = abs(float(got) - float(expected)) <= tol
    else: ok = got == expected
    CHECKS.append({"check": name, "ok": bool(ok), "got": got, "expected": expected})
    if not ok: FAILS.append(name)
    return ok

rec = {"device": "fx_trd02_base.py", "self_sha256": T.guarded_sha256(os.path.abspath(__file__)),
       "module_sha256": T.guarded_sha256(os.path.join(os.environ["PYTHONPATH"].split(":")[0], "tradability.py")),
       "spec_sha256": T.SPEC_SHA256, "numpy": np.__version__, "argv": sys.argv,
       "env": {k: os.environ[k] for k in sorted(os.environ)}, "utc_start": utc(time.time())}
adh = T.guarded_sha256(ADH); assert adh == ADH_SHA, ("AD_H sha", adh, ADH_SHA)
AD = json.load(open(ADH))
rec["inputs"] = {p: T.guarded_sha256(p) for p in (ADH, CACHE, AMETA, UMASK, PANEL, LEDGER)}
for p in (CACHE, AMETA, UMASK, PANEL, LEDGER):
    if p in AD["inputs"]: assert rec["inputs"][p] == AD["inputs"][p], ("input changed since the audit", p)
A = T.Artifact.load(ART, expected_sha256=ART_SHA)
rec["artifact"] = {"path": ART, "sha256": A.sha256, "data_end": utc(A.data_end_ts)}
log("guards ok")

# ---------------- load axes ----------------
Z = np.load(CACHE, allow_pickle=True); CTS = Z["ts"].astype(np.int64); syms = [str(s) for s in Z["symbols"]]; TTc = len(CTS)
assert syms == A.symbols
AM = np.load(AMETA, allow_pickle=True); aE = AM["E_ts"].astype(np.int64); aMem = AM["members"]; aQ = AM["qvk"]
P = np.load(PANEL, allow_pickle=True); pts = P["ts"].astype(np.int64); psym = [str(s) for s in P["symbols"]]
assert psym == syms, "panel symbol axis differs from the cache axis"
FE1 = np.asarray(P["f_fund_ema_v1"]); prow = {int(t): j for j, t in enumerate(pts)}
UZ = np.load(UMASK, allow_pickle=True); UTS = {int(t): k for k, t in enumerate(UZ["ts"].astype(np.int64))}; UM = np.asarray(UZ["mask"])
L = np.load(LEDGER, allow_pickle=True); off = L["off"].astype(np.int64); lft = L["ft"].astype(np.int64)
assert [str(x) for x in L["symbols"]] == syms
NW = len(syms)
rec["axes"] = {"king_meta_E_ts": len(aE), "panel_ts": len(pts), "umask_ts": len(UTS), "cache_rows": int(TTc),
               "panel_first": utc(pts[0]), "panel_last": utc(pts[-1]), "king_first": utc(aE[0]), "king_last": utc(aE[-1])}
log("axes", json.dumps(rec["axes"]))

# ---------------- rebuild the audit's Z24 / DEAD from ret5, exactly as ad_tradability.py does ----------------
def stream_channels(path, chans, block=20000):
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
    return out, shape
DAT, shp = stream_channels(CACHE, [0, 4]); R0 = DAT[:, :, 0]; C4 = DAT[:, :, 1]
fin = np.isfinite(R0); traded = fin & (C4 > 0)
has_tr = traded.any(0); last_tr = np.where(has_tr, TTc - 1 - np.argmax(traded[::-1], 0), -1)
dead_sym = has_tr & (last_tr < TTc - 1 - 288)
arow = np.searchsorted(CTS, aE); on_cache = (arow < TTc) & (CTS[np.minimum(arow, TTc - 1)] == aE)
assert on_cache.all(), "king anchors off the cache grid: %d" % int((~on_cache).sum())
def cs_rows(flag, idx):
    out = np.empty((TTc + 1, NW), np.int32); out[0] = 0; np.cumsum(flag, axis=0, dtype=np.int32, out=out[1:]); g = out[idx]; del out; return g
hiE = arow + 1; loE = np.maximum(arow + 1 - 288, 0); n = len(aE)
TRc = cs_rows(traded, np.concatenate([hiE, loE])); tr24 = TRc[:n] - TRc[n:]; del TRc
FIc = cs_rows(fin, np.concatenate([hiE, loE])); fi24 = FIc[:n] - FIc[n:]; del FIc
Z24 = (fi24 > 0) & (tr24 == 0)
DEAD = (arow[:, None] > last_tr[None, :]) & dead_sym[None, :]
del DAT, R0, C4, fin, traded
log("audit flags rebuilt", int(Z24.sum()), int(DEAD.sum()))

# ---------------- C. positive control: H3 and H5 P2 proxy, the audit's way ----------------
h3 = {}
for i, t in enumerate(aE):
    j = prow.get(int(t))
    if j is None: continue
    y = str(yr(t)); base = np.isfinite(FE1[j])
    b = h3.setdefault(y, {"anchors": 0, "base_sum": 0, "base_DEAD_sum": 0, "base_Z24_sum": 0, "base_DEAD_max": 0})
    b["anchors"] += 1; b["base_sum"] += int(base.sum()); nd = int((base & DEAD[i]).sum())
    b["base_DEAD_sum"] += nd; b["base_Z24_sum"] += int((base & Z24[i]).sum()); b["base_DEAD_max"] = max(b["base_DEAD_max"], nd)
for b in h3.values():
    b["base_mean"] = b["base_sum"] / max(b["anchors"], 1); b["base_DEAD_mean"] = b["base_DEAD_sum"] / max(b["anchors"], 1)
    b["base_Z24_mean"] = b["base_Z24_sum"] / max(b["anchors"], 1)
EXP3 = AD["H3_fund_rank_base_v2ext_f_fund_ema_v1"]
check("C.H3.years", sorted(h3), sorted(EXP3))
for y in sorted(set(h3) | set(EXP3)):
    g = h3.get(y) or {}; e = EXP3.get(y) or {}
    for k in ("base_mean", "base_DEAD_mean", "base_Z24_mean"): check("C.H3.%s.%s" % (y, k), g.get(k), e.get(k), tol=1e-9)
    check("C.H3.%s.base_DEAD_max" % y, g.get("base_DEAD_max"), e.get("base_DEAD_max"))
# P2 base proxy, the audit's loop, on the king axis
p2 = {}
proxy_cnt = np.zeros(n, np.int32); proxy_dead = np.zeros(n, np.int32)
proxy_bits = np.zeros((n, NW), bool)
for jj in range(NW):
    a_, c_ = off[jj], off[jj + 1]
    if c_ <= a_: continue
    ftj = lft[a_:c_]
    k = np.searchsorted(ftj, aE, side="right")
    hit = (k > 0) & (ftj[np.maximum(k - 1, 0)] > aE - 86400)
    proxy_bits[:, jj] = hit
proxy_cnt = proxy_bits.sum(1).astype(np.int32)
proxy_dead = (proxy_bits & DEAD).sum(1).astype(np.int32)
for i, t in enumerate(aE):
    y = str(yr(t)); b = p2.setdefault(y, {"anchors": 0, "base_proxy_sum": 0, "base_proxy_DEAD_sum": 0, "base_proxy_DEAD_max": 0})
    b["anchors"] += 1; b["base_proxy_sum"] += int(proxy_cnt[i]); b["base_proxy_DEAD_sum"] += int(proxy_dead[i])
    b["base_proxy_DEAD_max"] = max(b["base_proxy_DEAD_max"], int(proxy_dead[i]))
for b in p2.values():
    b["base_proxy_mean"] = b["base_proxy_sum"] / max(b["anchors"], 1); b["base_proxy_DEAD_mean"] = b["base_proxy_DEAD_sum"] / max(b["anchors"], 1)
EXPP = AD["H5_funding_after_death"]["P2_base_proxy_on_king_axis"]
check("C.P2proxy.years", sorted(p2), sorted(EXPP))
for y in sorted(set(p2) | set(EXPP)):
    g = p2.get(y) or {}; e = EXPP.get(y) or {}
    for k in ("base_proxy_mean", "base_proxy_DEAD_mean"): check("C.P2proxy.%s.%s" % (y, k), g.get(k), e.get(k), tol=1e-9)
    check("C.P2proxy.%s.base_proxy_DEAD_max" % y, g.get("base_proxy_DEAD_max"), e.get("base_proxy_DEAD_max"))
rec["C_positive_control"] = {"H3": h3, "P2_base_proxy_on_king_axis": p2, "failed": list(FAILS)}
log("C done; fails", len(FAILS))
if FAILS:
    rec["checks"] = CHECKS; rec["n_failed"] = len(FAILS); rec["stopped_before_new_numbers"] = True
    json.dump(rec, open(OUT, "w"), indent=1)
    print("FX_TRD02_STOPPED_POSITIVE_CONTROL", json.dumps(FAILS[:20]), flush=True); sys.exit(1)

# ---------------- N / Z / S. the causal flag on both axes ----------------
STATE = A._z["state_W24H"]                                    # [10285, 829] 0 NODATA / 1 UNTRADED / 2 TRADABLE
arow_art = A.rows(aE); prow_art = A.rows(pts)
TRD_a = STATE[arow_art] == T.TRADABLE; UNT_a = STATE[arow_art] == T.UNTRADED; NOD_a = STATE[arow_art] == T.NODATA
out = {}
def series(axis_name, ts_axis, trd, unt, nod):
    K = len(ts_axis)
    s = {k: np.zeros(K, np.int32) for k in ("base_fzb", "base_fzb_untradable", "base_fzb_untraded", "base_fzb_nodata",
                                            "base_proxy", "base_proxy_untradable", "base_proxy_untraded", "base_proxy_nodata",
                                            "members", "members_untradable", "n_z_moved", "n_z_dropped")}
    s["dz_max"] = np.zeros(K); s["dz_mean_abs"] = np.zeros(K); s["ts"] = ts_axis.astype(np.int64)
    for i, t in enumerate(ts_axis):
        j = prow.get(int(t))
        if j is None: continue
        base = np.isfinite(FE1[j]); nt = ~trd[i]
        s["base_fzb"][i] = base.sum(); s["base_fzb_untradable"][i] = (base & nt).sum()
        s["base_fzb_untraded"][i] = (base & unt[i]).sum(); s["base_fzb_nodata"][i] = (base & nod[i]).sum()
        pb = PROXY_OF[axis_name][i]
        s["base_proxy"][i] = pb.sum(); s["base_proxy_untradable"][i] = (pb & nt).sum()
        s["base_proxy_untraded"][i] = (pb & unt[i]).sum(); s["base_proxy_nodata"][i] = (pb & nod[i]).sum()
        # A0 member rule (SPEC section 7 / FACT_TABLE B2): MEMBERS_TOPN=829 qvk ranking, then the m1 umask row
        ia = APOS.get(int(t))
        if ia is not None:
            q = np.nan_to_num(aQ[ia], nan=-1.0); o = np.argsort(-q); o = o[q[o] > -0.5][:829]
            m = np.sort(o).astype(np.int64)
            ur = UTS.get(int(t))
            if ur is not None: m = m[UM[ur][m]]
            s["members"][i] = len(m); s["members_untradable"][i] = int(nt[m].sum())
            v = FE1[j].astype(np.float64)
            z_old = np.full(NW, np.nan); ok = np.isfinite(v)
            if ok.sum() >= 10: z_old[ok] = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
            v2 = np.where(trd[i], v, np.nan); ok2 = np.isfinite(v2)
            z_new = np.full(NW, np.nan)
            if ok2.sum() >= 10: z_new[ok2] = rankdata(v2[ok2]) / max(ok2.sum() - 1, 1) - 0.5
            live = m[np.isfinite(z_old[m]) & np.isfinite(z_new[m])]
            if len(live):
                dz = np.abs(z_new[live] - z_old[live])
                s["dz_max"][i] = dz.max(); s["dz_mean_abs"][i] = dz.mean(); s["n_z_moved"][i] = int((dz > 1e-12).sum())
            s["n_z_dropped"][i] = int((np.isfinite(z_old[m]) & ~np.isfinite(z_new[m])).sum())
    return s
APOS = {int(t): i for i, t in enumerate(aE)}
PROXY_OF = {"king": proxy_bits}
prow_p = np.searchsorted(CTS, pts); assert np.array_equal(CTS[prow_p], pts)
pbits = np.zeros((len(pts), NW), bool)
for jj in range(NW):
    a_, c_ = off[jj], off[jj + 1]
    if c_ <= a_: continue
    ftj = lft[a_:c_]; k = np.searchsorted(ftj, pts, side="right")
    pbits[:, jj] = (k > 0) & (ftj[np.maximum(k - 1, 0)] > pts - 86400)
PROXY_OF["panel"] = pbits
TRD_p = STATE[prow_art] == T.TRADABLE; UNT_p = STATE[prow_art] == T.UNTRADED; NOD_p = STATE[prow_art] == T.NODATA
S_king = series("king", aE, TRD_a, UNT_a, NOD_a); log("N king done")
S_panel = series("panel", pts, TRD_p, UNT_p, NOD_p); log("N panel done")

def summarise(s, ts_axis):
    yrs = np.array([yr(t) for t in ts_axis]); out = {}
    on = s["base_fzb"] > 0
    for y in sorted(set(yrs.tolist())):
        m = (yrs == y) & on
        if not m.any(): continue
        out[str(y)] = {"anchors": int(m.sum()),
                       "base_fzb_mean": float(s["base_fzb"][m].mean()),
                       "base_fzb_untradable_mean": float(s["base_fzb_untradable"][m].mean()),
                       "base_fzb_untradable_max": int(s["base_fzb_untradable"][m].max()),
                       "base_fzb_untradable_share": float(s["base_fzb_untradable"][m].sum() / max(s["base_fzb"][m].sum(), 1)),
                       "of_which_untraded_mean": float(s["base_fzb_untraded"][m].mean()),
                       "of_which_nodata_mean": float(s["base_fzb_nodata"][m].mean()),
                       "base_proxy_mean": float(s["base_proxy"][m].mean()),
                       "base_proxy_untradable_mean": float(s["base_proxy_untradable"][m].mean()),
                       "base_proxy_untradable_max": int(s["base_proxy_untradable"][m].max()),
                       "members_mean": float(s["members"][m].mean()),
                       "members_untradable_mean": float(s["members_untradable"][m].mean()),
                       "members_untradable_max": int(s["members_untradable"][m].max()),
                       "dz_max_over_anchors": float(s["dz_max"][m].max()),
                       "dz_max_mean": float(s["dz_max"][m].mean()),
                       "dz_mean_abs_mean": float(s["dz_mean_abs"][m].mean()),
                       "n_z_moved_mean": float(s["n_z_moved"][m].mean()),
                       "n_z_dropped_mean": float(s["n_z_dropped"][m].mean())}
    return out
rec["N_causal_by_year"] = {"king_meta_axis": summarise(S_king, aE), "panel_A0_axis": summarise(S_panel, pts)}
rec["N_note"] = ("base_fzb_untradable counts names with a finite f_fund_ema_v1 and no trade in (A-24h, A]; it is not the audit's "
                 "DEAD (never trades again) nor its Z24 (has data, no trade) — it is the union of UNTRADED and NODATA states, "
                 "which is the causal condition. The three are reported side by side.")

def det_npz(path, arrays):
    tmp = path + ".tmp"
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for k in sorted(arrays):
            zi = zipfile.ZipInfo(k + ".npy", date_time=(1980, 1, 1, 0, 0, 0)); zi.compress_type = zipfile.ZIP_DEFLATED
            a = np.asarray(arrays[k]); a = a if a.ndim == 0 else np.ascontiguousarray(a)
            with zf.open(zi, "w", force_zip64=True) as fh: np.lib.format.write_array(fh, a, allow_pickle=False)
    os.replace(tmp, path)
arrays = {"spec_sha256": np.array(T.SPEC_SHA256), "artifact_sha256": np.array(A.sha256), "symbols": np.array(syms)}
for nm, s in (("king", S_king), ("panel", S_panel)):
    for k, v in s.items(): arrays["%s_%s" % (nm, k)] = v
det_npz(OUTNPZ, arrays)
rec["series_npz"] = {"path": OUTNPZ, "sha256": T.guarded_sha256(OUTNPZ), "bytes": os.path.getsize(OUTNPZ), "keys": sorted(arrays)}
rec["checks"] = CHECKS; rec["n_checks"] = len(CHECKS); rec["n_failed"] = len(FAILS); rec["failed"] = FAILS
rec["runtime_s"] = round(time.time() - T0, 1); rec["utc_end"] = utc(time.time())
json.dump(rec, open(OUT, "w"), indent=1)
print("FX_TRD02_DONE", json.dumps({"checks": len(CHECKS), "failed": len(FAILS), "series_sha256": rec["series_npz"]["sha256"]}), flush=True)
sys.exit(1 if FAILS else 0)
