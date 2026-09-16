#!/usr/bin/env python3
"""fx_trd04_probe_outliers.py — FX-DATA TRD-04 follow-up probe (pod2, CPU, read-only). Committed before it is run.

fx_trd04_states.py reported that removing untradable names moves T1's DISP72 by up to 8.66x that column's own cross-anchor
standard deviation (and PUMPSPR72 by 3.23x, SIGF by 1.32x). A ratio that large has two very different explanations and the
receipt cannot tell them apart: either a genuinely extreme stale value was dominating the cross-section, or my injection made
the member set small enough that the statistic is no longer meaningful. This probe names the anchors and the contracts.

For the largest |delta| anchors of the named T1 columns it reports: the anchor, the control and treated values, the control and
treated member counts, and every contract dropped at that anchor with its trailing 72h compounded return, its 8h-equivalent
funding rate, its last traded bar and its anchor state. Descriptive only; no decision reads it.

Usage: python3 fx_trd04_probe_outliers.py <artifact.npz> <artifact_sha256> <series.npz> <series_sha256> <out_receipt.json>
"""
import os, sys, json, time
import numpy as np

ENV_WHITELIST = {"PATH", "HOME", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "PYTHONPATH"}
EXTRA = sorted(k for k in os.environ if k not in ENV_WHITELIST and k not in ("PWD", "SHLVL", "_", "OLDPWD", "LC_CTYPE"))
assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
os.nice(19)
ART, ART_SHA, SER, SER_SHA, OUT = sys.argv[1:6]
sys.path.insert(0, os.environ["PYTHONPATH"].split(":")[0])
import tradability as T

W = "/workspace"
MX = f"{W}/uplift_2026-09-11/r6/out/meta_newprod_v4_x0910.npz"; PX = f"{W}/uplift_2026-09-11/r6/out/wide_panel_4h_v2ext_x0910.npz"
UMP = f"{W}/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"
T0 = time.time()
def utc(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)

sser = T.guarded_sha256(SER); assert sser == SER_SHA, ("series sha", sser, SER_SHA)
A = T.Artifact.load(ART, expected_sha256=ART_SHA)
S = np.load(SER, allow_pickle=False)
rec = {"device": "fx_trd04_probe_outliers.py", "self_sha256": T.guarded_sha256(os.path.abspath(__file__)),
       "module_sha256": T.guarded_sha256(os.path.join(os.environ["PYTHONPATH"].split(":")[0], "tradability.py")),
       "numpy": np.__version__, "argv": sys.argv, "env": {k: os.environ[k] for k in sorted(os.environ)},
       "inputs": {SER: sser, ART: A.sha256, MX: T.guarded_sha256(MX), PX: T.guarded_sha256(PX), UMP: T.guarded_sha256(UMP)},
       "utc_start": utc(time.time())}

ZX = np.load(MX, allow_pickle=True); PXz = np.load(PX, allow_pickle=True); UMz = np.load(UMP, allow_pickle=True)
E = ZX["E_ts"].astype(np.int64); QVK = ZX["qvk"]; Y = ZX["y4"].astype(np.float64)
SYM = [str(s) for s in PXz["symbols"]]; tsP = PXz["ts"].astype(np.int64); prow = {int(t): j for j, t in enumerate(tsP)}
umts = UMz["ts"].astype(np.int64); umask = np.asarray(UMz["mask"]); umap = {int(t): k for k, t in enumerate(umts)}
FN = PXz["f_fund_now"].astype(np.float64); IV = PXz["f_fund_iv"].astype(np.float64)
RN8 = FN * (8.0 / np.where(np.isfinite(IV) & (IV > 0), IV, 8.0))
kpos = {int(t): k for k, t in enumerate(E)}

cols = [str(c) for c in S["T1_cols"]]; C = S["T1_control"]; Tt = S["T1_treated"]; ts = S["T1_ts"].astype(np.int64)
rec["columns_probed"] = ["DISP72", "PUMPSPR72", "SIGF", "DISP24"]
out = {}
for name in rec["columns_probed"]:
    c = cols.index(name)
    d = np.abs(Tt[:, c] - C[:, c]); d[~np.isfinite(d)] = 0.0
    top = np.argsort(-d)[:5]
    rowsout = []
    for r in top:
        t = int(ts[r]); k = kpos[t]; j = prow[t]
        q = np.nan_to_num(QVK[k], nan=-1.0); m = np.sort(np.where(q > -0.5)[0]).astype(np.int64)
        u = umap.get(t)
        if u is None:
            prior = umts[umts <= t]; u = umap[int(prior.max())]
        m = m[umask[u][m]]
        st = A._z["state_W24H"][A.rows([t])[0]]
        keep = st[m] == T.TRADABLE
        dropped = m[~keep]
        r72 = np.prod(1.0 + Y[k - 18:k][:, dropped], axis=0) - 1.0 if k >= 18 else np.full(len(dropped), np.nan)
        r72_all = np.prod(1.0 + Y[k - 18:k][:, m], axis=0) - 1.0 if k >= 18 else np.full(len(m), np.nan)
        rowsout.append({"ts": utc(t), "control": float(C[r, c]), "treated": float(Tt[r, c]), "abs_delta": float(d[r]),
                        "members_control": int(len(m)), "members_treated": int(keep.sum()),
                        "n_finite_r72_control": int(np.isfinite(r72_all).sum()),
                        "dropped": sorted(({"symbol": SYM[int(s)], "state": int(st[int(s)]),
                                            "r72": (None if not np.isfinite(r72[i]) else float(r72[i])),
                                            "rn8_bps": (None if not np.isfinite(RN8[j, int(s)]) else float(1e4 * RN8[j, int(s)])),
                                            "last_traded": (utc(A.last_traded_ts[int(s)]) if A.last_traded_ts[int(s)] >= 0 else None)}
                                           for i, s in enumerate(dropped)), key=lambda x: -(abs(x["r72"]) if x["r72"] is not None else -1))[:12]})
    out[name] = rowsout
    log(name, "top delta", round(float(d[top[0]]), 6), utc(int(ts[top[0]])))
rec["T1_outliers"] = out
rec["runtime_s"] = round(time.time() - T0, 1); rec["utc_end"] = utc(time.time())
json.dump(rec, open(OUT, "w"), indent=1)
print("FX_TRD04_PROBE_DONE", json.dumps({k: (v[0]["ts"], round(v[0]["abs_delta"], 6)) for k, v in out.items()}), flush=True)
