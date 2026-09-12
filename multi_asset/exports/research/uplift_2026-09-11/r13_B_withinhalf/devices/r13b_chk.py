import os,sys,json,hashlib,time,calendar
WHITE=set(sys.argv[1].split(",")); EXTRA=sorted(k for k in os.environ if k not in WHITE)
assert EXTRA==[],("ENV",EXTRA)
BANNED=('CAL','JUDGE','UPLIFT','PANEL','LOOK','WRULE','LEGS','PHI','FSEED','W3FIX','FTRIM','UMASK','SLOW',
 'FPRED','MEMBERS_TOPN','COSTB','SLEEVE','KMOD','SEAT','RNSM','LTRIM','CDAMP','FUNDSCALE','FEMAT',
 'TRADE_TOPN','REF_SKIP','PYTHON','OMP','MKL')
BAN=sorted(k for k in os.environ if k.startswith(BANNED)); assert BAN==[],("FLAG",BAN)
import numpy as np
sys.path.insert(0,"/workspace/uplift_2026-09-11/r13_B_withinhalf/devices")
src=open("/workspace/uplift_2026-09-11/r13_B_withinhalf/devices/r13b_core.py").read()
cut=src.index("# ------------------------------------------------------------------ S6 statistics")
ns={'__file__':"/workspace/uplift_2026-09-11/r13_B_withinhalf/devices/r13b_core.py",'__name__':'r13b'}
sys.argv=[sys.argv[0],sys.argv[1]]
exec(compile(src[:cut],"r13b_core_head","exec"),ns)
np=ns['np']; BK={t:ns['load_book'](t) for t in ns['BOOKS']}
ROWS=ns['static_rows'](BK['s42'],'s42'); reshape_ex=ns['reshape_ex']; overlay=ns['overlay']; BETA=ns['BETA']
rng=np.random.default_rng([20260905,99])
l1r=[];sm0=[];idem=[];lev=[]
for k in rng.integers(300,len(ROWS),400):
    k=int(k); r=ROWS[k]; sm=BK['s42']['W'][k].astype(np.float64); G=BK['s42']['gt'][k]
    smr=reshape_ex(sm); u=smr/G
    up,_=overlay(u,r['m'],BETA[250][r['i']],1.00)
    v=up*G
    L1s=np.abs(smr).sum()
    l1r.append(abs(np.abs(v).sum()-L1s)/L1s)          # vs the book it actually modifies
    sm0.append(abs(v.sum()-smr.sum()))
    idem.append(float(np.abs(reshape_ex(v)-v).max()))  # executor reshape must be the IDENTITY
    lev.append(abs(np.abs(sm).sum()-G)/G)              # float32 storage error vs archived gross_total
print(json.dumps(dict(
 n=len(l1r),
 L1_rel_err_vs_smr_max=max(l1r),
 sum_abs_err_max=max(sm0),
 executor_reshape_idempotence_maxabs=max(idem),
 float32_storage_gross_rel_err_max=max(lev),
 note="prereg 3.3 quoted |L1(u')-1|<1e-12; the core device compared against the ARCHIVED gross_total, "
      "which carries float32 storage error, so it logged 7.4e-9. Against the book the overlay actually "
      "modifies (smr) the preservation is round-off. Diagnostic-only; the ledger is unaffected."),indent=1))
