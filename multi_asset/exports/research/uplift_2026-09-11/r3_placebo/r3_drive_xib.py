"""CORRECTION RUN. The pinned XIB_LAG50 (infra2/run_xib_bitwise.py, the arm the round-2 integrator
judged) is  blend(0.5*xz(f_fund_ema_v1), 0.5*xz(f_amihud_24h)[t-1])  -- NO orthogonalisation, and
`blend` NaNs a name unless BOTH components are finite.  The first r3 batch built the r2_attack
variant 0.5*ZF + 0.5*orth(lag1(rz(AMI))) instead (corr 0.9929 to the archived arm, max|dg| 53 bps).
This run rebuilds the pinned form, tag XIB50.  Same nulls, same device, same env.
"""
import numpy as np, os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r3_drive as B                      # reuse tree, env, runner, feature loads
from null_families import NULLS, availability_receipt
from scipy.stats import rankdata

def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 10: out[ok] = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
    return out
def RZ(M, mask):
    M = np.where(mask, np.asarray(M, float), np.nan)
    out = np.full(M.shape, np.nan)
    for i in range(M.shape[0]): out[i] = xz(M[i])
    return out
def blend(*parts):
    out = np.zeros(parts[0][1].shape); ok = np.ones(parts[0][1].shape, bool)
    for w, Z in parts:
        Z = np.asarray(Z, float); out = out + w * np.nan_to_num(Z, nan=0.0); ok &= np.isfinite(Z)
    return np.where(ok, out, np.nan)

ZF = RZ(B.FE1, B.BASE)
def pipe(X):
    ZA = RZ(X, B.BASE)
    L = np.full_like(ZA, np.nan); L[1:] = ZA[:-1]; L = np.where(B.BASE, L, np.nan)
    return blend((0.5, ZF), (0.5, L))

NT = ["R1", "R2", "R3", "O1", "O2", "T1", "T2", "T3", "P1"]
if __name__ == "__main__":
    from concurrent.futures import ThreadPoolExecutor
    J = []
    for seed in (42, 2027):
        env = B.IB(seed)
        J.append(("XIB50_s%d__REAL" % seed, pipe(B.AMI), env))
    AV = {}
    for nt in NT:
        Xn = NULLS[nt](np.asarray(B.AMI, float))
        AV[nt] = availability_receipt(np.asarray(B.AMI, float), Xn)
        m = pipe(Xn)
        for seed in (42, 2027):
            J.append(("XIB50_s%d__%s" % (seed, nt), m, B.IB(seed)))
    json.dump(AV, open(B.R + "/AVAIL_xib50.json", "w"), indent=1)
    t0 = time.time(); print("jobs", len(J), flush=True)
    with ThreadPoolExecutor(max_workers=8) as ex:
        for r in ex.map(lambda j: B.run(*j), J):
            print("%-36s %6.0fs" % (r, time.time() - t0), flush=True)
    print("BATCH_DONE xib50", round(time.time() - t0, 1))
