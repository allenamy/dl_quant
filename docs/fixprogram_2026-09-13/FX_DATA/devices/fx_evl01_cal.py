#!/usr/bin/env python3
"""fx_evl01_cal.py — FX-DATA EVL-01 (pod2, CPU, read-only on every input). Committed before it is run.

EVL-01 (AUDIT_DATA bb8a2806, P3, status VERIFIED_IMMATERIAL): the w10 sleeve devices read `CAL = os.environ.get("CAL", "simple")`,
and `CAL == "simple"` applies `np.expm1` to the accounting `y4`. That `y4` comes from the pod 5m cache lineage, where it is already
a SUM of simple 5-minute returns (memory `live_seat_seed_is_in_sample` / E-0904-F: expm1 belongs only to the `build_wide_dl.py` L151
log lineage). So the default is wrong for this lineage and every committed run since 09-09 overrides it with CAL=log.

The audit closed it as "a latent trap; no affected run found". That is half the statement. The half nobody wrote down is what it
would cost if it ever fired, in the unit the programme judges book changes in (bps / 4h anchor / unit gross, the D1 delta unit).
This device measures that half. It changes no code and writes no artifact anyone else reads.

  P  positive control FIRST: rebuild the A0 arm's own recorded price channel from its stored weights and the meta y4 —
     pnl_ex[k] must equal sum_j W[k, j] * y4[i, j] within the arm's own float32 storage. If it does not, the alignment is not the
     device's and no delta is printed.
  D  the delta a forgotten CAL would put on the price channel with the weights HELD FIXED:
     d[k] = sum_j W[k, j] * (expm1(y4) - y4)[i, j] / gross_total[k] * 1e4      (bps / anchor / unit gross)
     reported per year and over the judge's windows, with the D1 equivalence delta (0.05) beside it.
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

M = np.load(META, allow_pickle=True); ets = M["E_ts"].astype(np.int64); Y = np.asarray(M["y4"], np.float64)
out = {}
for s, p in ARMS.items():
    Z = np.load(p, allow_pickle=False); cols = [str(c) for c in Z["cols"]]
    R = np.asarray(Z["rec"], np.float64); Wt = np.asarray(Z["W"], np.float64)
    cfg = json.loads(str(Z["config_json"]))
    ts = R[:, cols.index("ts")].astype(np.int64)
    assert np.array_equal(ets[META_OFF:META_OFF + N_REC], ts), ("meta offset", s)
    y = Y[META_OFF:META_OFF + N_REC]
    gt = R[:, cols.index("gross_total")]
    pnl_ex = R[:, cols.index("pnl_ex")]
    yy = np.nan_to_num(y, nan=0.0)
    rebuilt = (Wt * yy).sum(1)
    fin = np.isfinite(pnl_ex) & np.isfinite(rebuilt)
    denom = np.maximum(np.abs(pnl_ex[fin]), 1e-12)
    relmax = float((np.abs(rebuilt[fin] - pnl_ex[fin]) / denom).max())
    absmax = float(np.abs(rebuilt[fin] - pnl_ex[fin]).max())
    check("P.s%s.price_channel_rebuilt_from_W_and_y4" % s, relmax < 1e-6,
          {"cells": int(fin.sum()), "max_rel": relmax, "max_abs": absmax, "CAL_of_arm": cfg.get("CAL")})
    check("P.s%s.arm_is_CAL_log" % s, cfg.get("CAL") == "log", {"CAL": cfg.get("CAL")})
    log("P s%s rel %.3e abs %.3e CAL %s" % (s, relmax, absmax, cfg.get("CAL")))
    d = np.where(gt > 1e-12, (Wt * (np.expm1(yy) - yy)).sum(1) / np.maximum(gt, 1e-12) * 1e4, np.nan)
    yrs = np.array([yr(t) for t in ts])
    byy = {}
    for y_ in sorted(set(yrs.tolist())):
        m = (yrs == y_) & np.isfinite(d)
        byy[str(y_)] = {"anchors": int(m.sum()), "mean_bps": float(d[m].mean()), "median_bps": float(np.median(d[m])),
                        "max_abs_bps": float(np.abs(d[m]).max()), "share_over_D1": float((np.abs(d[m]) > D1_DELTA).mean())}
    wf = np.isfinite(d); wa = wf.copy(); wa[:ALPHA0] = False
    out[s] = {"config_CAL": cfg.get("CAL"), "anchors": int(wf.sum()),
              "W_FULL": {"n": int(wf.sum()), "mean_bps": float(d[wf].mean()), "median_bps": float(np.median(d[wf])),
                         "max_abs_bps": float(np.abs(d[wf]).max()), "share_over_D1": float((np.abs(d[wf]) > D1_DELTA).mean())},
              "W_ALPHA": {"n": int(wa.sum()), "mean_bps": float(d[wa].mean()), "median_bps": float(np.median(d[wa])),
                          "max_abs_bps": float(np.abs(d[wa]).max()), "share_over_D1": float((np.abs(d[wa]) > D1_DELTA).mean())},
              "by_year": byy,
              "worst_anchors": [{"ts": utc(ts[i]), "bps": float(d[i])} for i in np.argsort(-np.nan_to_num(np.abs(d)))[:10]]}
    log("D s%s W_ALPHA mean %.4f bps max|%.3f|" % (s, out[s]["W_ALPHA"]["mean_bps"], out[s]["W_ALPHA"]["max_abs_bps"]))
rec["D_price_channel_delta_bps"] = out
rec["B_not_measured"] = ("CAL also enters legs(), whose leg returns set the msharpe seat weights over LOOK=900, so a real CAL=simple "
                         "run would carry different W. The numbers above hold W at the CAL=log arm and change only the accounting, "
                         "so they size the accounting channel, not the whole trap. A paired CAL=simple arm run is NOT part of this device.")
rec["checks"] = CHECKS; rec["n_checks"] = len(CHECKS); rec["n_failed"] = len(FAILS); rec["failed"] = FAILS
rec["runtime_s"] = round(time.time() - T0, 1); rec["utc_end"] = utc(time.time())
json.dump(rec, open(OUT, "w"), indent=1)
print("FX_EVL01_DONE", json.dumps({"failed": len(FAILS), "s42_W_ALPHA_mean_bps": out["42"]["W_ALPHA"]["mean_bps"],
                                   "s42_W_ALPHA_max_abs_bps": out["42"]["W_ALPHA"]["max_abs_bps"],
                                   "s42_share_over_D1": out["42"]["W_ALPHA"]["share_over_D1"]}), flush=True)
sys.exit(1 if FAILS else 0)
