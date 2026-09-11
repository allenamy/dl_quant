"""R5/ND1: TURNOVER-MATCHED NULLS.  Construction copied verbatim from r3_attack_b9646/null.py
(sha 91d4c91cb92a6440): RELAB_k = one FIXED symbol permutation applied at EVERY anchor;
SHIFT_k = the whole score matrix advanced by k anchors.  Both preserve the per-anchor rank
distribution AND the lag-1 persistence, hence the turnover.  The OLD per-anchor permutation placebo is
DEFECTIVE (raises turnover 2.6-7.7x) and is NOT used."""
import numpy as np, json, sys, os
R="/workspace/uplift_2026-09-11/r5_basis"
ARM=sys.argv[1]          # e.g. BGAPT_LAG
Z=np.load(R+"/dev/sig/R5_%s.npz"%ARM,allow_pickle=True)
ts=Z["ts"].astype(np.int64); sym=Z["symbols"]; M=np.asarray(Z["mat"],float)
MAN={}
for d in (1,2,3):
    rng=np.random.default_rng([4242,d]); pi=rng.permutation(M.shape[1])
    p=R+"/dev/sig/NULL_%s_RELAB%d.npz"%(ARM,d); np.savez(p,symbols=sym,ts=ts,mat=np.asarray(M[:,pi],np.float32))
    MAN["NULL_%s_RELAB%d"%(ARM,d)]=p
for k in (101,503,1009):
    Q=np.full_like(M,np.nan); Q[k:]=M[:-k]
    p=R+"/dev/sig/NULL_%s_SHIFT%d.npz"%(ARM,k); np.savez(p,symbols=sym,ts=ts,mat=np.asarray(Q,np.float32))
    MAN["NULL_%s_SHIFT%d"%(ARM,k)]=p
json.dump(MAN,open(R+"/NULL_MANIFEST.json","w"),indent=1)
print(json.dumps(MAN,indent=1))
