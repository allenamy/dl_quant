"""NON-PREREGISTERED DIAGNOSTIC (dlarch): where does S1's tiny null bias (-0.00066, 7.2 se from 0) come from?
Three shuffle schemes for the SAME quantity. If the bias is a property of my union-support choice,
scheme B/C will show it and scheme A will not. No verdict is drawn; this only names a mechanism."""
import numpy as np, json, calendar, time
W="/dev/shm/news2_2026-09-23"
F=np.load(W+"/work/NEWS_FEATURES.npz"); a=F["anchors"].astype(np.int64)
leg=np.load(W+"/work/legs.npz"); ready=leg["ready"]
lab=np.load("/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz",allow_pickle=True)
ya=lab["E_ts"].astype(np.int64); iy=np.searchsorted(ya,a); lab_ok=(iy<len(ya))&(ya[np.minimum(iy,len(ya)-1)]==a)
def ts(s): return calendar.timegm(time.strptime(s,"%Y-%m-%dT%H:%M:%SZ"))
m_pre=(a>=ts("2023-06-30T04:00:00Z"))&(a<=ts("2025-12-31T20:00:00Z"))
C=np.load(W+"/work/combo_s42/scaled_diagnostic.npz"); ca=C["E_ts"].astype(np.int64)
kc=C["kc"]; fc=C["fc"]; ci=np.searchsorted(a,ca); assert np.all(a[ci]==ca)
sel=np.flatnonzero(m_pre[ci]&ready[ci]&lab_ok[ci])
def corr_union(k,f):
    nz=(np.abs(k)>1e-12)|(np.abs(f)>1e-12)
    if nz.sum()<20 or k[nz].std()==0 or f[nz].std()==0: return None
    return float(np.corrcoef(k[nz],f[nz])[0,1])
def corr_inter(k,f):
    nz=(np.abs(k)>1e-12)&(np.abs(f)>1e-12)
    if nz.sum()<20 or k[nz].std()==0 or f[nz].std()==0: return None
    return float(np.corrcoef(k[nz],f[nz])[0,1])
schemes={}
# A: shuffle only the NONZERO values of f among their own positions (support preserved)
# B: full-vector shuffle (what the prereg device did), union support
# C: full-vector shuffle, intersection support
for name in ("A_support_preserved_union","B_full_shuffle_union","C_full_shuffle_intersection"):
    draws=[]
    for b in range(20):
        rng=np.random.default_rng([20260924,1,b]); vals=[]
        for j in sel:
            k=kc[j]; f=fc[j].copy()
            if name.startswith("A"):
                p=np.flatnonzero(np.abs(f)>1e-12)
                if len(p)>1: f[p]=rng.permutation(f[p])
                v=corr_union(k,f)
            elif name.startswith("B"):
                rng.shuffle(f); v=corr_union(k,f)
            else:
                rng.shuffle(f); v=corr_inter(k,f)
            if v is not None: vals.append(v)
        draws.append(float(np.mean(vals)))
    d=np.array(draws); se=d.std(ddof=1)/np.sqrt(len(d))
    schemes[name]={"mean":float(d.mean()),"sd":float(d.std(ddof=1)),"se":float(se),
                   "abs_mean_over_se":float(abs(d.mean())/se),"pass_3se":bool(abs(d.mean())<=3*se)}
    print("%-34s mean=%+.6f se=%.6f |m|/se=%5.2f pass3se=%s" % (name,d.mean(),se,abs(d.mean())/se,schemes[name]["pass_3se"]))
# the unpermuted truth under both supports, for scale
tu=[corr_union(kc[j],fc[j]) for j in sel]; ti=[corr_inter(kc[j],fc[j]) for j in sel]
tu=[x for x in tu if x is not None]; ti=[x for x in ti if x is not None]
print("TRUTH union=%+.4f (n=%d)  intersection=%+.4f (n=%d)"%(np.mean(tu),len(tu),np.mean(ti),len(ti)))
schemes["TRUTH"]={"union":float(np.mean(tu)),"intersection":float(np.mean(ti))}
json.dump(schemes,open("/workspace/dlarch_2026-09-24/out/S1_NULL_DIAGNOSTIC.json","w"),indent=1)
