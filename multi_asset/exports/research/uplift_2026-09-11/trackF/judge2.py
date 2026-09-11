import numpy as np, time, json
from judgeF import gseries, levels, contrast, T, FROZEN, C
A=np.load('arms.npz'); B=np.load('tf.npz'); D=np.load('tf2.npz'); L=np.load('labels.npz')
lmap={int(t):int(l) for t,l in zip(L['ts'],L['lab'])}
S42={"A0":A['PARITY_A0_dyn_s42__rec'],"R1":B['TF_R1__rec'],"R3":B['TF_R3__rec'],"F1":B['TF_F1__rec'],
     "F1R":B['TF_F1R__rec'],"R5":D['TF_R5__rec'],"R6":D['TF_R6__rec']}
S27={"A0":D['S27_A0__rec'],"R1":D['S27_R1__rec'],"F1":D['S27_F1__rec'],"R5":D['S27_R5__rec'],"R6":D['S27_R6__rec']}
SPANS={"FULL(2022-01-31..2026-08-10)":(0,T(2026,8,10,20)+1),
       "2023..2026-08-10":(T(2023,1,1),T(2026,8,10,20)+1),
       "2024-01..2026-08-10":(T(2024,1,1),T(2026,8,10,20)+1),
       "HOLDOUT 2025-01..2026-08-10":(T(2025,1,1),T(2026,8,10,20)+1),
       "frozen 2025-03..2026-08-10":FROZEN}
def report(name, SET):
    print(f"\n########## seed {name} ##########")
    print(f"{'form':5s}"+"".join(f"{'|'+s.split('(')[0][:22]:>25s}" for s in SPANS))
    for nm,rec in SET.items():
        ts,g=gseries(rec); line=f"{nm:5s}"
        for s,(lo,hi) in SPANS.items():
            m=(ts>=lo)&(ts<hi); v=g[m]
            line+=f" {v.mean():7.3f} Sh{v.mean()/v.std(ddof=1)*np.sqrt(2190):5.2f}+-{np.sqrt(2190/m.sum()):4.2f}"
        print(line)
    print(f"\n{'form':5s}"+"".join(f"{y:>10d}" for y in range(2022,2027))+"   (mean g per year)")
    for nm,rec in SET.items():
        ts,g=gseries(rec); yr=np.array([time.gmtime(int(t)).tm_year for t in ts]); line=f"{nm:5s}"
        for y in range(2022,2027):
            m=yr==y
            if y==2026: m=m&(ts<=T(2026,8,10,20))
            line+=f"{g[m].mean():10.3f}"
        print(line)
report("s42", S42); report("s2027", S27)
print("\n########## contrasts vs A0, both seeds ##########")
print(f"{'cand':5s}{'seed':6s}{'window':30s}{'n':>6s}{'delta':>9s}{'CI95':>22s}{'P>0':>7s}")
k=0
for nm in ("R1","R3","F1","F1R","R5","R6"):
    for sd,SET in (("s42",S42),("s2027",S27)):
        if nm not in SET: continue
        k+=1
        tsA,gA=gseries(SET["A0"]); ts,g=gseries(SET[nm])
        for wn,(lo,hi) in (("frozen 2025-03..2026-08-10",FROZEN),("FULL 2022..2026-08-10",(0,T(2026,8,10,20)+1)),("HOLDOUT 2025-01..2026-08-10",(T(2025,1,1),T(2026,8,10,20)+1))):
            ia={int(t):i for i,t in enumerate(tsA)}; ib={int(t):i for i,t in enumerate(ts)}
            cm=np.array(sorted(set(ia)&set(ib))); m=(cm>=lo)&(cm<hi); cc=cm[m]
            d=np.array([g[ib[int(t)]]-gA[ia[int(t)]] for t in cc])
            from judgeF import boot
            rng=np.random.default_rng([20260905,k])
            blo,bhi,p=boot(d, cc//86400, rng)
            print(f"{nm:5s}{sd:6s}{wn:30s}{len(cc):6d}{d.mean():9.3f}   [{blo:7.3f},{bhi:7.3f}]{p:7.3f}")
