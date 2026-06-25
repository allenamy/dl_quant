"""GATE the regime-MoE premise with DATA (Ridge-before-DL).

MoE premise = "each regime needs a DIFFERENT function (strong=momentum, choppy=reversion)".
3 decisive tests (snapshot Ridge, leak-safe within-regime CV):
  1. PER-REGIME-fit (within-regime CV) vs SHARED-fit (all-regime), tested in-regime.
     per-regime >> shared => distinct functions help => MoE VALIDATED.
  2. COEFFICIENT DIVERGENCE: cosine-sim of per-regime Ridge coef vectors. Low => relationship varies.
  3. CROSS-REGIME: strong-fit->choppy-test vs choppy-fit->choppy-test. Much worse cross => functions differ.

Regimes: strong=2025-04 (npzv4_dual), choppy=2026-05 (npz_v2arch), drift=2025-12 (npz_v2arch).
For each regime use that month's days; within-regime 5-fold CV by day-block (leak-safe: train/test day-disjoint).
Run: PYTHONPATH=. python multi_asset/data/moe_premise_test.py
"""
from __future__ import annotations
import numpy as np, glob, warnings
warnings.filterwarnings("ignore"); warnings.simplefilter("ignore")
from sklearn.linear_model import Ridge
from scipy.stats import pearsonr

def dd(p): return p.split("/")[-1][:-4]
def load_days(cache, mon):
    fs=sorted(glob.glob(f"data/{cache}/*.npz")); days=[f for f in fs if dd(f)[:7]==mon]
    per=[]
    for f in days:
        d=np.load(f,allow_pickle=True); m=d["y_mask_600"].astype(bool)
        X=d["X"][m]; snap=np.concatenate([X[:,-1,:],X[:,-60:,:].mean(1)],1)
        per.append((np.nan_to_num(snap.astype(np.float32)), d["y_600"][m].astype(np.float32),
                    d["timestamps"][m].astype(np.int64)))
    return per  # list of (X,y,ts) per day

def cleanp(p,y,ts):
    o=np.argsort(ts);ts=ts[o];p=p[o];y=y[o];Ps=[]
    for off in range(2):
        keep=[];last=-1e18
        for i in range(off,len(ts)):
            if ts[i]-last>=600*1_000_000: keep.append(i);last=ts[i]
        keep=np.array(keep)
        if len(keep)>20: Ps.append(pearsonr(p[keep],y[keep])[0])
    return np.mean(Ps) if Ps else 0.0

# ALL regimes from npz_v2arch (X=88) so feature space matches across regimes (concat-valid).
# npz_v2arch covers 2025-04 (strong) + 2026-05 (choppy) + 2025-12 (drift) -- same dims.
REG={"strong":("npz_v2arch","2025-04"),"choppy":("npz_v2arch","2026-05"),"drift":("npz_v2arch","2025-12")}

# fit a regime's coef on ALL its data (for divergence + cross-regime)
def fit_coef(per, alpha=100.0):
    X=np.concatenate([d[0] for d in per]); y=np.concatenate([d[1] for d in per])
    mu=X.mean(0);sd=X.std(0)+1e-8
    r=Ridge(alpha=alpha).fit((X-mu)/sd,y)
    return r,mu,sd

def predict(r,mu,sd,X): return r.predict((X-mu)/sd)

data={k:load_days(c,m) for k,(c,m) in REG.items()}
print("loaded:", {k:f"{len(v)}days/{sum(len(d[1]) for d in v)}win" for k,v in data.items()})

# ---- TEST 1: per-regime-fit (day-block CV) vs shared-fit, tested in-regime ----
print("\n=== TEST 1: PER-REGIME-fit (within-regime day-CV) vs SHARED-fit, in-regime ===")
# shared fit = all 3 regimes pooled
allper=[d for k in data for d in data[k]]
rsh,msh,ssh=fit_coef(allper)
for k,per in data.items():
    nd=len(per);
    # 5 day-blocks CV: train on 4/5 days, test on 1/5 (day-disjoint, leak-safe)
    import math; nb=min(5,nd);
    perreg_ps=[]; shared_ps=[]
    blocks=np.array_split(np.arange(nd), nb)
    for b in blocks:
        te=[per[i] for i in b]; tr=[per[i] for i in range(nd) if i not in set(b.tolist())]
        if not tr or not te: continue
        r,mu,sd=fit_coef(tr)
        Xte=np.concatenate([d[0] for d in te]); yte=np.concatenate([d[1] for d in te]); tte=np.concatenate([d[2] for d in te])
        perreg_ps.append(cleanp(predict(r,mu,sd,Xte),yte,tte))
        shared_ps.append(cleanp(predict(rsh,msh,ssh,Xte),yte,tte))
    print(f"  {k:7s}: per-regime-CV P={np.mean(perreg_ps):+.4f}  shared-fit P={np.mean(shared_ps):+.4f}  delta={np.mean(perreg_ps)-np.mean(shared_ps):+.4f}")

# ---- TEST 2: coefficient divergence (cosine-sim of per-regime coefs) ----
print("\n=== TEST 2: per-regime coefficient cosine-similarity (low => functions differ) ===")
coefs={}
for k,per in data.items():
    r,mu,sd=fit_coef(per); coefs[k]=r.coef_
import itertools
for a,b in itertools.combinations(coefs,2):
    ca,cb=coefs[a],coefs[b]; cos=float(ca@cb/(np.linalg.norm(ca)*np.linalg.norm(cb)+1e-12))
    print(f"  cos({a},{b}) = {cos:+.3f}")

# ---- TEST 3: cross-regime fit->test ----
print("\n=== TEST 3: cross-regime (fit X -> test Y) vs in-regime ===")
fits={k:fit_coef(per) for k,per in data.items()}
for tek,per in data.items():
    Xte=np.concatenate([d[0] for d in per]); yte=np.concatenate([d[1] for d in per]); tte=np.concatenate([d[2] for d in per])
    row=[]
    for frk,(r,mu,sd) in fits.items():
        row.append(f"{frk[:3]}->{tek[:3]}={cleanp(predict(r,mu,sd,Xte),yte,tte):+.4f}")
    print("  "+"  ".join(row))
print("\nVERDICT: per-regime>>shared AND low cos AND cross<<in-regime => MoE REAL. Else MoE premise WRONG (SNR not function).")
