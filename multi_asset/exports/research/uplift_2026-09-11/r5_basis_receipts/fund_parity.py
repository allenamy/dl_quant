"""R5/ND1 CROSS-SOURCE GATE. Rebuild f_fund_now and f_fund_iv from MY downloaded fundingRate archives,
using the SAME rule as pod_panel_ext.py L153 (searchsorted(ft, anchor, side=right)-1 = last settlement at
or before the anchor; NaN when the last settlement is >12h stale), and compare to the panel column.
If my acquisition + alignment path is right for funding, it is right for the premium index: same symbols,
same monthly-zip machinery, same anchor rule."""
import numpy as np, zipfile, glob, json, time
R="/workspace/uplift_2026-09-11/r5_basis"
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
TS=PW["ts"].astype(np.int64); SYM=[str(s) for s in PW["symbols"]]
FN=np.asarray(PW["f_fund_now"],float); IVp=np.asarray(PW["f_fund_iv"],float)
ALLOWED=np.array([1.,2.,4.,6.,8.])
mine=np.full(FN.shape,np.nan); mineiv=np.full(FN.shape,np.nan)
t0=time.time(); nsym=0
for c,s in enumerate(SYM):
    rows={}
    for f in sorted(glob.glob(R+"/raw/fund/%s/*.zip"%s)):
        try: z=zipfile.ZipFile(f)
        except Exception: continue
        for n in z.namelist():
            for ln in z.read(n).decode().splitlines():
                if not ln or ln[0]=="c": continue
                p=ln.split(",")
                try: t=int(p[0])//1000; iv=float(p[1]); r=float(p[2])
                except Exception: continue
                rows[t]=(r,iv)
    if not rows: continue
    nsym+=1
    ft=np.array(sorted(rows),np.int64); fr=np.array([rows[t][0] for t in ft])
    fiv=np.array([rows[t][1] for t in ft])
    dt_h=np.round(np.diff(ft)/3600.0); dv=np.full(len(ft),np.nan); dv[1:]=np.where((dt_h>0)&(dt_h<=24),dt_h,np.nan)
    iv_full=np.where(np.isfinite(fiv)&(fiv>0),fiv,dv); iv_full=np.where(np.isfinite(iv_full),iv_full,8.0)
    iv_full=ALLOWED[np.argmin(np.abs(iv_full[:,None]-ALLOWED[None,:]),axis=1)]
    pos=np.searchsorted(ft,TS,side="right")-1; ok=pos>=0
    v=np.full(len(TS),np.nan); vi=np.full(len(TS),np.nan)
    v[ok]=fr[pos[ok]]; vi[ok]=iv_full[pos[ok]]
    stale=ok&((TS-np.where(ok,ft[np.maximum(pos,0)],0))>12*3600)
    v[stale]=np.nan; vi[stale]=np.nan
    mine[:,c]=v; mineiv[:,c]=vi
    if c%200==0: print("sym",c,"%.0fs"%(time.time()-t0),flush=True)
both=np.isfinite(FN)&np.isfinite(mine)
d=np.abs(FN[both]-mine[both])
OUT={"symbols_with_archive":nsym,"cells_panel_finite":int(np.isfinite(FN).sum()),
 "cells_mine_finite":int(np.isfinite(mine).sum()),"cells_both":int(both.sum()),
 "panel_finite_but_mine_nan":int((np.isfinite(FN)&~np.isfinite(mine)).sum()),
 "mine_finite_but_panel_nan":int((~np.isfinite(FN)&np.isfinite(mine)).sum()),
 "maxabs_diff_rate":float(d.max()),"frac_exact_within_1e-9":float((d<1e-9).mean()),
 "frac_within_1e-6":float((d<1e-6).mean()),
 "iv_agree_frac":float((mineiv[both]==IVp[both]).mean())}
print(json.dumps(OUT,indent=1),flush=True)
json.dump(OUT,open(R+"/FUND_PARITY.json","w"),indent=1)
