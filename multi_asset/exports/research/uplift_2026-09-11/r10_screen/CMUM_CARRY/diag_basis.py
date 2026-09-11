import os,json,datetime as dt,numpy as np
W=os.path.dirname(os.path.abspath(__file__))
Z=np.load(W+"/book_inputs.npz",allow_pickle=True);K=np.load(W+"/klines_grid.npz",allow_pickle=True)
TS=Z["TS"];D=Z["D"];H=Z["H"];names=[str(x) for x in Z["names"]]
CMP=K["CMP"];UMP=K["UMP"]
def ret(P):
    r=np.full_like(P,np.nan); r[1:]=P[1:]/P[:-1]-1.0; return r
rCM=ret(CMP);rUM=ret(UMP)
ok=np.isfinite(rCM)&np.isfinite(rUM)&(np.abs(rCM)<0.5)&(np.abs(rUM)<0.5)
dr=rCM-rUM
print(f"{'name':16s}{'nbar':>7s}{'mean_dr_bps':>13s}{'sd_dr_bps':>11s}{'cum_dr_pct':>12s}{'basis_bps_mean':>16s}{'basis_bps_sd':>14s}{'mean_d_hr_bps':>15s}")
rows=[]
for k,nm in enumerate(names):
    m=ok[:,k]
    if m.sum()<100: continue
    b=(CMP[:,k]/UMP[:,k]-1.0)
    bb=b[np.isfinite(b)]
    r=dr[m,k]
    rows.append((nm,int(m.sum()),r.mean()*1e4,r.std()*1e4,100*(np.exp(np.log1p(r).sum())-1),bb.mean()*1e4,bb.std()*1e4,np.nanmean(np.where(H[:,k],D[:,k],np.nan))*1e4))
for r in sorted(rows,key=lambda z:z[4]):
    print(f"{r[0]:16s}{r[1]:7d}{r[2]:13.4f}{r[3]:11.2f}{r[4]:12.2f}{r[5]:16.2f}{r[6]:14.2f}{r[7]:15.4f}")
