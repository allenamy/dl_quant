import numpy as np, calendar, time
B="/workspace/review_scratch/health_check/dev_v4/pod_backup_2026-08-21"
import os
print(os.listdir(B)[:20])
PW=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True)
print(PW.files)
FN=PW["f_fund_now"]; IV=PW["f_fund_iv"]; ts=PW["ts"].astype(np.int64)
IVf=np.where(np.isfinite(IV)&(IV>0),IV,8.0); RN8=np.nan_to_num(FN,nan=0.0)*(8.0/IVf)
fin=np.isfinite(FN)
print("panel rows",FN.shape, "span", time.strftime("%Y-%m-%d",time.gmtime(ts[0])), time.strftime("%Y-%m-%d",time.gmtime(ts[-1])))
# frozen window rows
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
m=(ts>=T(2025,3,1))&(ts<=T(2026,8,10,20))
print("frozen rows",m.sum())
print()
print("=== CARRY-MODEL EXPLOITABILITY: does the LAST SETTLED rate (what the device charges AND selects on)")
print("    predict the rate settled over the NEXT 8h (what you actually pay if you stay)? ===")
for lead in (1,2,3,6):
    a=RN8[:-lead][m[:-lead]]; b=RN8[lead:][m[:-lead]]
    f=fin[:-lead][m[:-lead]]&fin[lead:][m[:-lead]]
    a=a[f]; b=b[f]
    neg=a<0
    print(f"  lead={lead} rows ({lead*4}h ahead): n={len(a)}  corr={np.corrcoef(a,b)[0,1]:.3f}  "
          f"P(next<0 | now<0)={ (b[neg]<0).mean():.3f}  mean(next | now<0)={b[neg].mean()*1e4:+.2f}bp/8h  mean(now|now<0)={a[neg].mean()*1e4:+.2f}bp/8h")
print()
print("  => the fraction of the modelled carry saving that is real = mean(next|now<0)/mean(now|now<0) at lead=2 (8h)")
print()
print("=== SHALLOW-NEGATIVE band (-10bp..0), which is the band FT00 / FT00S newly trims ===")
a=RN8[:-2][m[:-2]]; b=RN8[2:][m[:-2]]; f=fin[:-2][m[:-2]]&fin[2:][m[:-2]]
a=a[f]; b=b[f]
sh=(a>-0.0010)&(a<0.0)
print(f"  n={sh.sum()}  mean(now)={a[sh].mean()*1e4:+.3f}bp/8h  mean(8h ahead)={b[sh].mean()*1e4:+.3f}bp/8h  P(next<0)={ (b[sh]<0).mean():.3f}")
dp=(a<-0.0010)
print(f"  deep(<-10bp) n={dp.sum()} mean(now)={a[dp].mean()*1e4:+.3f} mean(8h ahead)={b[dp].mean()*1e4:+.3f} P(next<0)={(b[dp]<0).mean():.3f}")
