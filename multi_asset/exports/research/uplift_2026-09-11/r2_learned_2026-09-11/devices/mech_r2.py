"""Mechanism probe: RESID_SHARPE has book P&L but ~0 full-cross-section forward rank-IC.
Decompose where the return comes from: decile spread, tail-only IC, and the carry/price split per decile.
SIGNAL LAYER on the panel axis; not the book layer."""
import numpy as np, json, sys, calendar, datetime as dt
R2="/workspace/uplift_2026-09-11/r2_learned"
TG=np.load("/workspace/dlw_v4raw/data/dlw_targets.npz",allow_pickle=True)
E_ts=TG["E_ts"].astype(np.int64); y4=TG["y4s"]; nA,NW=y4.shape; yrs=TG["yrs"].astype(int)
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
pts=PW["ts"].astype(np.int64); OFF=int(np.searchsorted(E_ts,pts[0]))
FN=np.asarray(PW["f_fund_now"],float); IV=np.asarray(PW["f_fund_iv"],float)
IVf=np.where(np.isfinite(IV)&(IV>0),IV,8.0); RN4=FN*(4.0/IVf)   # 4h-equivalent funding paid on a long
QV=TG["qvk"]
def xrank(v):
    n=len(v)
    if n<2: return np.zeros(n)
    return np.argsort(np.argsort(v)).astype(np.float64)/max(n-1,1)-0.5
out={}
for name in sys.argv[1:]:
    M=np.load(R2+"/preds/%s.npy"%name)
    rows=[i for i in range(nA) if yrs[i]>=2023 and np.isfinite(M[i]).sum()>=50]
    d_all=[];d_liq=[];ic_all=[];ic_tail=[];car=[];pri=[]
    for i in rows[::2]:
        s=M[i]; t=y4[i]
        qv=np.expm1(np.clip(QV[i],0,30))*48
        ok=np.isfinite(s)&np.isfinite(t)&np.isfinite(qv)&(qv>=2.5e5)
        if ok.sum()<80: continue
        sv=s[ok]; tv=t[ok]
        r=xrank(sv)
        n=len(r); k=max(1,n//10)
        o=np.argsort(sv)
        lo=o[:k]; hi=o[-k:]
        d_all.append(float(tv[hi].mean()-tv[lo].mean())*1e4)
        # funding leg of that same spread (what a long-hi/short-lo book pays)
        j=i-OFF
        if 0<=j<len(pts):
            f=RN4[j][ok]
            car.append(float(np.nan_to_num(f[hi]).mean()-np.nan_to_num(f[lo]).mean())*1e4)
        tr=xrank(tv)
        ic_all.append(float(((r-r.mean())*(tr-tr.mean())).mean()/(r.std()*tr.std()+1e-12)))
        tail=np.concatenate([lo,hi])
        rt=xrank(sv[tail]); tt=xrank(tv[tail])
        ic_tail.append(float(((rt-rt.mean())*(tt-tt.mean())).mean()/(rt.std()*tt.std()+1e-12)))
    out[name]={"n_anchors":len(d_all),
               "decile_spread_bps_4h":round(float(np.mean(d_all)),3),
               "decile_spread_t":round(float(np.mean(d_all)/np.std(d_all,ddof=1)*np.sqrt(len(d_all))),2),
               "funding_spread_bps_4h_paid_by_that_spread":round(float(np.mean(car)),3) if car else None,
               "IC_full_xsec_tradeable":round(float(np.mean(ic_all)),5),
               "IC_within_top_and_bottom_decile":round(float(np.mean(ic_tail)),5)}
    print(name,json.dumps(out[name]),flush=True)
json.dump(out,open(R2+"/MECH_r2.json","w"),indent=1)
