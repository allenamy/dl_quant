# ADDENDUM 5 §A5.3 self-checks. Runs BEFORE any number is read. JSON CONFIG parse; legs_ts is the anchor axis.
import numpy as np, json, sys
D="dev_alt/probe_artifacts/w10_ablation_series_%s.npz"; L="dev_alt/logs/%s.log"
ok=True
def cfg(tag):
    for l in open(L%tag,errors="replace"):
        if l.startswith("CONFIG "): return json.loads(l[7:])
    raise SystemExit("no CONFIG in "+tag)
for pref in ["M1","MEM","FIX"]:
    for s in ["42","2027"]:
        a="%s_UPIT_prod_s%s_ccal"%(pref,s); b="%s_UCRYPTO_prod_s%s_ccal"%(pref,s)
        ka,kb=cfg(a),cfg(b)
        diff=sorted(k for k in set(ka)|set(kb) if json.dumps(ka.get(k),sort_keys=True)!=json.dumps(kb.get(k),sort_keys=True))
        c1=(diff==["UMASK_NPZ"]); ok&=c1
        print("SC1 %-28s diff_keys=%s -> %s"%(b,diff,"OK" if c1 else "FAIL"))
        A=np.load(D%a,allow_pickle=True); B=np.load(D%b,allow_pickle=True)
        ta,tb=A["legs_ts"],B["legs_ts"]
        c3=(ta.shape==tb.shape) and bool((ta==tb).all()); ok&=c3
        print("SC3 %-28s n=%d vs %d axis_equal=%s -> %s"%(b,len(ta),len(tb),c3,"OK" if c3 else "FAIL"))
        t=ta.astype("datetime64[s]"); early=t<np.datetime64("2026-01-01T00:00:00")
        worst=0.0; fl=[]; nb=0
        assert set(A.files)==set(B.files), "field sets differ"
        for f in A.files:
            x,y=A[f],B[f]
            if x.dtype.kind not in "fiu" or x.shape!=y.shape or x.shape[0]!=len(ta): continue
            d=np.abs(np.nan_to_num(x[early].astype(float))-np.nan_to_num(y[early].astype(float)))
            worst=max(worst,float(d.max())); fl.append(f); nb+=int(d.size)
        c2=(worst==0.0); ok&=c2
        print("SC2 %-28s 2022-2025 maxabs=%.3e over %d fields / %d cells (%s) -> %s"%(b,worst,len(fl),nb,",".join(fl),"OK" if c2 else "FAIL"))
        # 2026 must actually differ, else the switch is not wired (zero_delta family)
        late=~early; w=0.0
        for f in ["S0_rec","S0_W"]:
            d=np.abs(np.nan_to_num(A[f][late].astype(float))-np.nan_to_num(B[f][late].astype(float))); w=max(w,float(d.max()))
        print("SC4 %-28s 2026 maxabs=%.6g (must be >0)"%(b,w)); ok &= (w>0)
print("ALL_SELFCHECKS","PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
