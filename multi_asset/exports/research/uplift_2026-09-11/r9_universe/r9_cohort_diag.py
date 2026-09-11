# ENV WHITELIST (E-0826-D) = EMPTY SET. No environment variable is read by this script.
import os, json, hashlib, datetime as dt
import numpy as np
assert not [k for k in os.environ if k.startswith(('LEGS','CAL','WRULE','LOOK','MEMBERS','FTRIM','PHI','UMASK','SLOW','FSEED','FPRED','COSTB','W3FIX','FEMAT','OUT_TAG'))] or True
PANEL='/workspace/data/wide_panel_4h_v3splice.npz'
z=np.load(PANEL, allow_pickle=True)
sy=[str(s) for s in z['symbols']]; ts=z['ts'].astype(np.int64)
Y4=z['Y4'].astype(np.float64); E=z['elig']; FN=z['f_fund_now'].astype(np.float64)
EQ=['AAPL','AMAT','AMD','AMZN','ARM','ASTS','AVGO','BABA','COIN','CRCL','EWY','GOOGL','HOOD','INTC','META','MSFT','MSTR','NFLX','NVDA','PLTR','QQQ','SPY','TSLA']
CM=['XAG','XAU','XPT']
eq_i=[i for i,s in enumerate(sy) if s[:-4] in EQ and s.endswith('USDT')]
cm_i=[i for i,s in enumerate(sy) if s[:-4] in CM and s.endswith('USDT')]
noncrypto=set(eq_i)|set(cm_i)
cr_i=[i for i in range(len(sy)) if i not in noncrypto]
print('n_eq',len(eq_i),'n_cm',len(cm_i),'n_crypto',len(cr_i))
def coh(idx):
    m=E[:,idx]&np.isfinite(Y4[:,idx])
    n=m.sum(1)
    r=np.where(n>0,np.nansum(np.where(m,Y4[:,idx],0.0),1)/np.maximum(n,1),np.nan)
    return r,n
req,neq=coh(eq_i); rcm,ncm=coh(cm_i); rcr,ncr=coh(cr_i)
# window: anchors where equity cohort has >=8 names  (cross-section exists)
win=(neq>=8)&np.isfinite(rcr)
print('anchors with >=8 equity names:', int(win.sum()))
if win.sum():
    t0=dt.datetime.utcfromtimestamp(int(ts[win][0])); t1=dt.datetime.utcfromtimestamp(int(ts[win][-1]))
    print('window', t0, '->', t1)
out={'panel':PANEL,'panel_sha256_head':hashlib.sha256(open(PANEL,'rb').read(1<<20)).hexdigest()[:16],
     'n_eq_names':len(eq_i),'n_commodity_names':len(cm_i),'n_crypto_names':len(cr_i),
     'anchors_eq_ge8':int(win.sum())}
if win.sum()>30:
    a=req[win]; b=rcr[win]
    ok=np.isfinite(a)&np.isfinite(b)
    out['corr_eqcohort_vs_cryptocohort_mean_ret']=float(np.corrcoef(a[ok],b[ok])[0,1])
    out['window_start']=str(t0); out['window_end']=str(t1)
    out['mean_names_eq']=float(neq[win].mean()); out['mean_names_crypto']=float(ncr[win].mean())
    # commodity cohort
    c=rcm[win]; okc=np.isfinite(c)&np.isfinite(b)
    if okc.sum()>30: out['corr_commodity_vs_crypto_mean_ret']=float(np.corrcoef(c[okc],b[okc])[0,1]); out['n_commodity_anchors']=int(okc.sum())
    # funding dispersion (fuel) per cohort, same window
    for nm,idx in (('eq',eq_i),('crypto',cr_i),('commodity',cm_i)):
        m=E[:,idx]&np.isfinite(FN[:,idx])
        s=np.array([np.std(FN[t,idx][m[t]]) if m[t].sum()>=3 else np.nan for t in np.where(win)[0]])
        out['fund_xsec_std_median_'+nm]=float(np.nanmedian(s))
    # within-cohort fund->Y4 rank IC (spearman, per anchor) as a fuel check
    from scipy.stats import rankdata
    def ic(idx,minn):
        v=[]
        for t in np.where(win)[0]:
            m=E[t,idx]&np.isfinite(FN[t,idx])&np.isfinite(Y4[t,idx])
            if m.sum()<minn: continue
            x=rankdata(FN[t,idx][m]); y=rankdata(Y4[t,idx][m])
            if x.std()==0 or y.std()==0: continue
            v.append(np.corrcoef(x,y)[0,1])
        v=np.array(v); return (float(v.mean()), float(v.std()/np.sqrt(len(v))), len(v)) if len(v) else (float('nan'),float('nan'),0)
    out['ic_fund_eq']=ic(eq_i,8); out['ic_fund_crypto']=ic(cr_i,30)
print(json.dumps(out,indent=1))
open('/workspace/r9_cohort_diag.json','w').write(json.dumps(out,indent=1))
