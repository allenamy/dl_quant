#!/usr/bin/env python3
"""fx_evl01_cal.py — FX-DATA EVL-01 (pod2, CPU, read-only on every input). Committed before it is run.

EVL-01 (AUDIT_DATA bb8a2806, P3, status VERIFIED_IMMATERIAL): the w10 sleeve devices read `CAL = os.environ.get("CAL", "simple")`,
and `CAL == "simple"` applies `np.expm1` to the accounting `y4`. That `y4` comes from the pod 5m cache lineage, where it is already
a SUM of simple 5-minute returns (memory `live_seat_seed_is_in_sample` / E-0904-F: expm1 belongs only to the `build_wide_dl.py` L151
log lineage). So the default is wrong for this lineage and every committed run since 09-09 overrides it with CAL=log.

The audit closed it as "a latent trap; no affected run found". That is half the statement. The half nobody wrote down is what it
would cost if it ever fired, in the unit the programme judges book changes in (bps / 4h anchor / unit gross, the D1 delta unit).
This device measures that half. It changes no code and writes no artifact anyone else reads.

  P  positive control FIRST, and run 9 shows why it is not optional. Run 9 (rc=1, log
     `receipts/fx_evl01_run9_rc1_wrong_control.log`) assumed pnl_ex[k] == sum_j W[k, j] * y4[i, j] and the control refused it at a
     relative error of 3.17. Reading the A0 device (`/workspace/uplift_2026-09-11/w10_sleeve.py`, sha b88e35a4) gives three reasons
     at once: the stored W is `sm`, the PRE-reshape weight vector (L344 `WS.append(sm...)`); `pnl` and `pnl_ex` are both already in
     bps (x 1e4); and both sum over the MEMBER SET m only, not over all 829 (L329, L352). This device therefore rebuilds the member
     set the way the device does (MEMBERS_TOPN=829 qvk ranking, then the m1 umask row keyed by panel ts) and rebuilds BOTH channels:
       pnl    [col 2 ] = (sm[m]  * yv).sum() * 1e4          (L329)
       pnl_ex [col 19] = (smr[m] * yv).sum() * 1e4          (L352), smr = the L315-321 reshape of sm
     with yv = nan_to_num(y4[i, m]) and CAL=log, i.e. no expm1 (L324-326). Both must match the stored record or no delta is printed.
  D  the delta a forgotten CAL would put on those channels with the weights HELD FIXED:
     d[k] = (w[m] * (expm1(yv) - yv)).sum() * 1e4 / gross_total[k]            (bps / anchor / unit gross)
     for w = sm and w = smr, per year and over the judge's windows, with the D1 equivalence delta (0.05) beside it.
  B  the bound this is and is not: CAL also enters `legs()`, whose leg returns set the msharpe seat weights over LOOK=900, so a real
     CAL=simple run would have different W. D is therefore the accounting-only channel with W pinned to the CAL=log arm, not the
     full effect of the trap. The full effect needs a paired arm run and is NOT measured here.

Usage: python3 fx_evl01_cal.py <out_receipt.json>
Exit 0 only if the positive control reproduced.
"""
import os, sys, json, time, calendar
import numpy as np

ENV_WHITELIST = {"PATH", "HOME", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "PYTHONPATH"}
EXTRA = sorted(k for k in os.environ if k not in ENV_WHITELIST and k not in ("PWD", "SHLVL", "_", "OLDPWD", "LC_CTYPE"))
assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
os.nice(19)
OUT = sys.argv[1]
sys.path.insert(0, os.environ["PYTHONPATH"].split(":")[0])
import tradability as T

W = "/workspace"
ARMS = {s: f"{W}/uplift_2026-09-11/r3k/arms/A0_PWR230k_s{s}.npz" for s in ("42", "2027")}
META = f"{W}/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"
META_OFF = 138; N_REC = 10039; ALPHA0 = 900
D1_DELTA = 0.05                      # DELTA_TABLE_K2 key D1, bps / anchor / unit gross (FIXPROGRAM section 4.1)
T0 = time.time()
def utc(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
def yr(t): return time.gmtime(int(t)).tm_year
def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)

FAILS = []; CHECKS = []
def check(name, ok, detail=None):
    CHECKS.append({"check": name, "ok": bool(ok), **({"detail": detail} if detail is not None else {})})
    if not ok: FAILS.append(name)
    return ok

rec = {"device": "fx_evl01_cal.py", "self_sha256": T.guarded_sha256(os.path.abspath(__file__)),
       "module_sha256": T.guarded_sha256(os.path.join(os.environ["PYTHONPATH"].split(":")[0], "tradability.py")),
       "numpy": np.__version__, "argv": sys.argv, "env": {k: os.environ[k] for k in sorted(os.environ)},
       "inputs": {p: T.guarded_sha256(p) for p in list(ARMS.values()) + [META]}, "utc_start": utc(time.time()),
       "d1_delta_bps_per_anchor_per_gross": D1_DELTA}

PANEL = f"{W}/data/wide_panel_4h_v2ext.npz"
UMASK = f"{W}/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"
rec["inputs"].update({p: T.guarded_sha256(p) for p in (PANEL, UMASK)})
rec["a0_device"] = {"path": f"{W}/uplift_2026-09-11/w10_sleeve.py", "sha256": T.guarded_sha256(f"{W}/uplift_2026-09-11/w10_sleeve.py")}
M = np.load(META, allow_pickle=True); ets = M["E_ts"].astype(np.int64); Y = np.asarray(M["y4"], np.float64); QVK = np.asarray(M["qvk"])
P = np.load(PANEL, allow_pickle=True); pts = P["ts"].astype(np.int64)
Uz = np.load(UMASK, allow_pickle=True); uts = Uz["ts"].astype(np.int64); UM = np.asarray(Uz["mask"])
umap = {int(t): k for k, t in enumerate(uts)}
UMASK_ROW = {j: UM[umap[int(t)]] for j, t in enumerate(pts) if int(t) in umap}      # w10_sleeve.py L103-106, keyed by panel row
NW = UM.shape[1]

def member_set(i, j):
    """w10_sleeve.py L70-77 (MEMBERS_TOPN=829 qvk rebuild) then L211-214 (UMASK_SCOPE=m1 applies the mask to the members)"""
    q = np.nan_to_num(QVK[i], nan=-1.0); o = np.argsort(-q); o = o[q[o] > -0.5]
    m = np.sort(o[:829]).astype(np.int64)
    mk = UMASK_ROW.get(j)
    return m[mk[m]] if mk is not None else m

def reshape(sm):
    """w10_sleeve.py L314-321"""
    nz = np.abs(sm) > 1e-12
    smr = sm.copy()
    if nz.any():
        smr[nz] -= smr[nz].mean()
        g0 = np.abs(sm).sum(); g1 = np.abs(smr).sum()
        if g1 > 1e-9: smr *= g0 / g1
    return smr

out = {}
for s, p in ARMS.items():
    Z = np.load(p, allow_pickle=False); cols = [str(c) for c in Z["cols"]]
    R = np.asarray(Z["rec"], np.float64); Wt = np.asarray(Z["W"], np.float64)
    cfg = json.loads(str(Z["config_json"]))
    ts = R[:, cols.index("ts")].astype(np.int64)
    assert np.array_equal(ets[META_OFF:META_OFF + N_REC], ts), ("meta offset", s)
    assert np.array_equal(pts, ts), ("panel ts vs arm ts", s)
    check("P.s%s.arm_is_CAL_log" % s, cfg.get("CAL") == "log", {"CAL": cfg.get("CAL")})
    check("P.s%s.arm_is_MEMBERS_TOPN_829_m1" % s,
          cfg.get("MEMBERS_TOPN") == 829 and cfg.get("UMASK_SCOPE") == "m1",
          {"MEMBERS_TOPN": cfg.get("MEMBERS_TOPN"), "UMASK_SCOPE": cfg.get("UMASK_SCOPE")})
    gt = R[:, cols.index("gross_total")]
    pnl_rec = R[:, cols.index("pnl")]; pnlex_rec = R[:, cols.index("pnl_ex")]
    n = len(ts)
    pnl_b = np.full(n, np.nan); pnlex_b = np.full(n, np.nan)
    d_sm = np.full(n, np.nan); d_smr = np.full(n, np.nan)
    for k in range(n):
        i = k + META_OFF; j = k
        m = member_set(i, j)
        if not len(m): continue
        sm = Wt[k]; smr = reshape(sm)
        yv = np.nan_to_num(Y[i, m], nan=0.0)
        pnl_b[k] = float((sm[m] * yv).sum() * 1e4)
        pnlex_b[k] = float((smr[m] * yv).sum() * 1e4)
        dy = np.expm1(yv) - yv
        if gt[k] > 1e-12:
            d_sm[k] = float((sm[m] * dy).sum() * 1e4) / gt[k]
            d_smr[k] = float((smr[m] * dy).sum() * 1e4) / gt[k]
    for nm, b, r in (("pnl", pnl_b, pnl_rec), ("pnl_ex", pnlex_b, pnlex_rec)):
        fin = np.isfinite(b) & np.isfinite(r)
        den = np.maximum(np.abs(r[fin]), 1e-9)
        relmax = float((np.abs(b[fin] - r[fin]) / den).max()); absmax = float(np.abs(b[fin] - r[fin]).max())
        check("P.s%s.%s_rebuilt_from_W_and_y4" % (s, nm), relmax < 1e-6,
              {"cells": int(fin.sum()), "max_rel": relmax, "max_abs_bps": absmax})
        log("P s%s %s rel %.3e abs %.3e" % (s, nm, relmax, absmax))
    yrs = np.array([yr(t) for t in ts])
    def summarise(d):
        wf = np.isfinite(d); wa = wf.copy(); wa[:ALPHA0] = False
        byy = {}
        for y_ in sorted(set(yrs.tolist())):
            m_ = (yrs == y_) & wf
            if not m_.any(): continue
            byy[str(y_)] = {"anchors": int(m_.sum()), "mean_bps": float(d[m_].mean()), "median_bps": float(np.median(d[m_])),
                            "max_abs_bps": float(np.abs(d[m_]).max()), "share_over_D1": float((np.abs(d[m_]) > D1_DELTA).mean())}
        def blk(mask):
            return {"n": int(mask.sum()), "mean_bps": float(d[mask].mean()), "median_bps": float(np.median(d[mask])),
                    "max_abs_bps": float(np.abs(d[mask]).max()), "share_over_D1": float((np.abs(d[mask]) > D1_DELTA).mean())}
        return {"W_FULL": blk(wf), "W_ALPHA": blk(wa), "by_year": byy,
                "worst_anchors": [{"ts": utc(ts[i2]), "bps": float(d[i2])} for i2 in np.argsort(-np.nan_to_num(np.abs(d)))[:10]]}
    out[s] = {"config_CAL": cfg.get("CAL"), "anchors": int(np.isfinite(d_smr).sum()),
              "delta_on_pnl_sm": summarise(d_sm), "delta_on_pnl_ex_smr": summarise(d_smr)}
    log("D s%s pnl_ex W_ALPHA mean %.4f bps max %.3f share>D1 %.3f"
        % (s, out[s]["delta_on_pnl_ex_smr"]["W_ALPHA"]["mean_bps"], out[s]["delta_on_pnl_ex_smr"]["W_ALPHA"]["max_abs_bps"],
           out[s]["delta_on_pnl_ex_smr"]["W_ALPHA"]["share_over_D1"]))
rec["D_price_channel_delta_bps"] = out
rec["B_not_measured"] = ("CAL also enters legs(), whose leg returns set the msharpe seat weights over LOOK=900, so a real CAL=simple "
                         "run would carry different W. The numbers above hold W at the CAL=log arm and change only the accounting, "
                         "so they size the accounting channel, not the whole trap. A paired CAL=simple arm run is NOT part of this device.")
rec["checks"] = CHECKS; rec["n_checks"] = len(CHECKS); rec["n_failed"] = len(FAILS); rec["failed"] = FAILS
rec["runtime_s"] = round(time.time() - T0, 1); rec["utc_end"] = utc(time.time())
json.dump(rec, open(OUT, "w"), indent=1)
print("FX_EVL01_DONE", json.dumps({"failed": len(FAILS), "failed_names": FAILS[:6],
                                   "s42_pnl_ex_W_ALPHA_mean_bps": out["42"]["delta_on_pnl_ex_smr"]["W_ALPHA"]["mean_bps"],
                                   "s42_pnl_ex_W_ALPHA_max_abs_bps": out["42"]["delta_on_pnl_ex_smr"]["W_ALPHA"]["max_abs_bps"],
                                   "s42_share_over_D1": out["42"]["delta_on_pnl_ex_smr"]["W_ALPHA"]["share_over_D1"]}), flush=True)
sys.exit(1 if FAILS else 0)
