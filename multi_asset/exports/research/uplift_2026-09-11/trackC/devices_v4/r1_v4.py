import sys; sys.path.insert(0,"/workspace/uplift_2026-09-11/trackC")
from lib import *
import numpy as np, json, time
z=np.load("/workspace/uplift_2026-09-11/trackC/cand_v4.npz")
I=np.load("/root/tc/ic_v4.npz")
ts=z["ts"]; u=z["u"]; n=len(u)
lk=z["LEG_leg_king"]; lf=z["LEG_leg_fund"]; lr=z["LEG_leg_rev24"]
print("== R1 PROXY on full history: 'both engines negative over trailing 30 anchors' ==")
print("   (dashboard R1 is on live long/short sleeve USDT; replay proxy = trailing-30 mean of the king and fund legs)")
k30=trail_mean(lk,30); f30=trail_mean(lf,30)
fire=(k30<0)&(f30<0)
s=np.isfinite(k30)&np.isfinite(f30)&np.isfinite(u)
for lab,sel in (("R1 firing",s&fire),("R1 quiet",s&~fire)):
    y=u[sel]; print("   %-12s n=%5d (%.1f%%)  fwd bps/anchor %+0.4f (SE %.4f)  Sharpe %+0.2f"%(lab,len(y),100*len(y)/s.sum(),y.mean(),y.std(ddof=1)/np.sqrt(len(y)),sharpe(y)))
d=u[s&fire].mean()-u[s&~fire].mean()
se=np.sqrt(u[s&fire].var(ddof=1)/max((s&fire).sum(),1)+u[s&~fire].var(ddof=1)/max((s&~fire).sum(),1))
print("   difference %+0.4f bps/anchor, SE %.4f, t = %+0.2f"%(d,se,d/se))
print()
print("== SUMMARY TABLE: every monitor's trigger applied to FULL HISTORY, forward book return ==")
print("%-34s %7s %7s %11s %9s %9s"%("rule (fires when...)","n_fire","%hist","fwd bps/a","SE","Sharpe"))
r48=trail_mean(I["ric"],48)
RULES=[
 ("ic_monitor DECIDE  r48<-0.01656", r48<-0.01656),
 ("ic_monitor ALERT   r24<-0.02277", trail_mean(I["ric"],24)<-0.02277),
 ("regime_dash R1 (both legs<0/30a)", fire),
 ("sigma_ladder p30_ref2y<0.33", np.load("/workspace/uplift_2026-09-11/trackC/pct_v4.npz")["sigfund_2y"]<0.33),
 ("book DD>500bps from peak", None),
]
cum=np.cumsum(np.nan_to_num(u)); pk=np.maximum.accumulate(cum)
dd=pk-cum
RULES[-1]=("book DD>500bps from peak (lagged)", np.concatenate([[False],dd[:-1]>500]))
for lab,f in RULES:
    sel=np.isfinite(u)&np.isfinite(f.astype(float)) if f.dtype!=bool else np.isfinite(u)
    sel=sel&f
    base=np.isfinite(u)&~f
    y=u[sel]
    if len(y)<30: print("%-34s (too few)"%lab); continue
    print("%-34s %7d %6.1f%% %+11.4f %9.4f %+9.2f"%(lab,len(y),100*len(y)/np.isfinite(u).sum(),y.mean(),y.std(ddof=1)/np.sqrt(len(y)),sharpe(y)))
print("%-34s %7d %6.1f%% %+11.4f %9.4f %+9.2f"%("(baseline: all anchors)",np.isfinite(u).sum(),100.0,np.nanmean(u),np.nanstd(u)/np.sqrt(np.isfinite(u).sum()),sharpe(u)))
