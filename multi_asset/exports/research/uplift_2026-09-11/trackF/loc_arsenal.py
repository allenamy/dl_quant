import numpy as np, time, json
A = np.load('arms.npz'); Z = np.load('regime_vars.npz', allow_pickle=True)
RC=[str(c) for c in Z['cols']]; V=Z['V']; K={c:i for i,c in enumerate(RC)}; ts_r=V[:,0].astype(np.int64)
BURN=2190
def lab1(x):
    out=np.full(len(x),-1,np.int8)
    for i in range(len(x)):
        if i<BURN or not np.isfinite(x[i]): continue
        p=x[:i]; p=p[np.isfinite(p)]
        if len(p)<BURN//2: continue
        out[i]=1 if x[i]>np.median(p) else 0
    return out
LF=lab1(V[:,K['sig_fund']]); LD=lab1(V[:,K['disp24']])
LAB=np.full(len(ts_r),-1,np.int8); ok=(LF>=0)&(LD>=0); LAB[ok]=LF[ok]*2+LD[ok]
np.savez('labels.npz', ts=ts_r, lab=LAB, lf=LF, ld=LD)
NAMES={-1:'WARM',0:'LL',1:'LH',2:'HL',3:'HH'}
COLSR=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLSR)}
ARMS=["PARITY_A0_dyn_s42","AR_KF_p0","AR_FUND","AR_KING","AR_REV","AR_ALL3_p45","AR_ALL3_p0","AR_F10","AR_KF_noftrim"]
LBL={"PARITY_A0_dyn_s42":"A0 in-service","AR_KF_p0":"king+fund noDL","AR_FUND":"fund only","AR_KING":"king only","AR_REV":"rev24 only","AR_ALL3_p45":"3legs+DL","AR_ALL3_p0":"3legs noDL","AR_F10":"DL-slot book","AR_KF_noftrim":"A0 no-FTRIM"}
D={a:(np.round(A[a+'__rec'][:,0]).astype(np.int64), A[a+'__rec']) for a in ARMS}
for a in ARMS: print(a, D[a][0].shape, time.strftime('%F',time.gmtime(D[a][0][0])))
common=set(D[ARMS[0]][0].tolist())
for a in ARMS[1:]: common&=set(D[a][0].tolist())
common=np.array(sorted(common)); print('COMMON', len(common), time.strftime('%F',time.gmtime(common[0])),'->',time.strftime('%F',time.gmtime(common[-1])))
lmap={int(t):LAB[i] for i,t in enumerate(ts_r)}
lc=np.array([lmap.get(int(t),-1) for t in common]); yc=np.array([time.gmtime(int(t)).tm_year for t in common])
def sh(v): return v.mean()/v.std(ddof=1)*np.sqrt(2190) if len(v)>2 and v.std(ddof=1)>0 else np.nan
print('cells', {NAMES[l]:int((lc==l).sum()) for l in (-1,0,1,2,3)})
print('years', {int(y):int((yc==y).sum()) for y in range(2022,2027)})
print()
print(f"{'form':17s}"+"".join(f"{NAMES[l]+' n'+str(int((lc==l).sum())):>18s}" for l in (0,1,2,3))+f"{'ALL':>18s}")
res={}
for a in ARMS:
    ts,R=D[a]; idx={int(t):i for i,t in enumerate(ts)}; s=np.array([idx[int(t)] for t in common])
    g=R[s,C['net_ex']]/R[s,C['gross_total']]; line=f"{LBL[a]:17s}"; cc={}
    for l in (0,1,2,3):
        v=g[lc==l]; cc[NAMES[l]]={'n':int(len(v)),'mean':float(v.mean()),'sharpe':float(sh(v)),'se':float(v.std(ddof=1)/np.sqrt(len(v)))}
        line+=f"{v.mean():10.3f}({sh(v):5.2f})"
    v=g[lc>=0]; cc['ALL']={'n':int(len(v)),'mean':float(v.mean()),'sharpe':float(sh(v))}
    line+=f"{v.mean():10.3f}({sh(v):5.2f})"; print(line); res[a]={'label':LBL[a],'cells':cc}
print('\n1-D splits (common set), mean g (Sharpe):')
for nm,mask in (("dispLOW",(lc==0)|(lc==2)),("dispHIGH",(lc==1)|(lc==3)),("sigfundLOW",(lc==0)|(lc==1)),("sigfundHIGH",(lc==2)|(lc==3))):
    line=f"{nm:12s} n={int(mask.sum()):5d} "
    for a in ("PARITY_A0_dyn_s42","AR_FUND","AR_KING","AR_F10","AR_REV"):
        ts,R=D[a]; idx={int(t):i for i,t in enumerate(ts)}; s=np.array([idx[int(t)] for t in common])
        g=R[s,C['net_ex']]/R[s,C['gross_total']]; v=g[mask]; line+=f"{LBL[a]}:{v.mean():6.3f}({sh(v):5.2f}) "
    print(line)
ts,R=D['PARITY_A0_dyn_s42']; idx={int(t):i for i,t in enumerate(ts)}; s=np.array([idx[int(t)] for t in common]); S=R[s]; gt=S[:,C['gross_total']]
print('\nA0 decomposition per unit gross (bps/anchor):')
for l in (0,1,2,3):
    m=lc==l
    print(f"{NAMES[l]:4s} n={int(m.sum()):5d} pnl {np.mean(S[m,C['pnl_ex']]/gt[m]):7.3f} carry {np.mean(S[m,C['carry_ex']]/gt[m]):7.3f} cost {np.mean(S[m,C['cost_ex']]/gt[m]):7.3f} net {np.mean(S[m,C['net_ex']]/gt[m]):7.3f} | w3king {np.mean(S[m,C['w3_king']]):5.3f} w3fund {np.mean(S[m,C['w3_fund']]):5.3f} turn {np.mean(S[m,C['turnover']]):6.4f} nsel {np.mean(S[m,C['nsel']]):5.1f}")
g=S[:,C['net_ex']]/gt
print('\nA0 mean g by (year,cell):')
print(f"{'yr':5s}"+"".join(f"{NAMES[l]:>17s}" for l in (0,1,2,3)))
for y in range(2022,2027):
    line=f"{y:<5d}"
    for l in (0,1,2,3):
        m=(yc==y)&(lc==l); line+= f"{g[m].mean():10.3f}[{int(m.sum()):4d}]" if m.sum()>2 else f"{'--':>17s}"
    print(line)
json.dump(res,open('RESULT_arsenal_common.json','w'),indent=1)
