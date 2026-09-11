"""Cross-regime Sharpe CEILING with the present arsenal.
(a) ORACLE: per regime cell pick, with full hindsight, the arsenal form with the highest mean g.
    This is an unreachable UPPER BOUND on what any regime-conditional switch can buy.
(b) WALK-FORWARD switch: at each anchor pick the form with the best mean g over PAST anchors in the
    same cell (min 200 in-cell past anchors, else A0). Implementable, honest.
Both ignore the transition cost of switching books (so (b) is also optimistic)."""
import numpy as np, time, json
from judgeF import gseries, T, FROZEN, boot
A=np.load('arms.npz'); B=np.load('tf.npz'); D=np.load('tf2.npz'); L=np.load('labels.npz')
lmap={int(t):int(l) for t,l in zip(L['ts'],L['lab'])}
FORMS={"A0":A['PARITY_A0_dyn_s42__rec'],"KFnoDL":A['AR_KF_p0__rec'],"FUND":A['AR_FUND__rec'],
       "REV":A['AR_REV__rec'],"ALL3DL":A['AR_ALL3_p45__rec'],"ALL3":A['AR_ALL3_p0__rec'],
       "DLslot":A['AR_F10__rec'],"noFTRIM":A['AR_KF_noftrim__rec'],
       "R1":B['TF_R1__rec'],"R3":B['TF_R3__rec'],"F1":B['TF_F1__rec'],"F1R":B['TF_F1R__rec'],
       "R5":D['TF_R5__rec'],"R6":D['TF_R6__rec']}
G={}; TS=None
for k,r in FORMS.items():
    ts,g=gseries(r)
    if TS is None: TS=set(ts.tolist())
    else: TS&=set(ts.tolist())
TS=np.array(sorted(TS))
for k,r in FORMS.items():
    ts,g=gseries(r); ix={int(t):i for i,t in enumerate(ts)}; G[k]=np.array([g[ix[int(t)]] for t in TS])
lb=np.array([lmap.get(int(t),-1) for t in TS]); yr=np.array([time.gmtime(int(t)).tm_year for t in TS])
mfull=TS<=T(2026,8,10,20)
def sh(v): return v.mean()/v.std(ddof=1)*np.sqrt(2190)
NAMES={-1:'WARM',0:'LL',1:'LH',2:'HL',3:'HH'}
print("common axis over ALL 14 forms:", len(TS), time.strftime('%F',time.gmtime(TS[0])),'->',time.strftime('%F',time.gmtime(TS[-1])))
print("\n(a) ORACLE per-cell pick (IN-SAMPLE UPPER BOUND, not attainable):")
pick={}
for l in (-1,0,1,2,3):
    m=(lb==l)&mfull
    if m.sum()<30: continue
    best=max(FORMS, key=lambda k: G[k][m].mean()); pick[l]=best
    print(f"  {NAMES[l]:5s} n={int(m.sum()):5d} best={best:8s} mean {G[best][m].mean():7.3f} (A0 {G['A0'][m].mean():7.3f})")
orc=np.array([G[pick.get(int(l),'A0')][i] for i,l in enumerate(lb)])
for nm,v in (("ORACLE",orc),("A0",G['A0']),("F1",G['F1'])):
    m=mfull; print(f"  {nm:7s} FULL mean {v[m].mean():7.3f}  Sharpe {sh(v[m]):5.2f} +-{np.sqrt(2190/m.sum()):4.2f}")
print("\n(b) WALK-FORWARD per-cell switch (min 200 in-cell past anchors, else A0):")
MIN=200
sel=[]
hist={l:[] for l in (-1,0,1,2,3)}
run={k:{l:[0.0,0] for l in (-1,0,1,2,3)} for k in FORMS}
for i in range(len(TS)):
    l=int(lb[i])
    n=run['A0'][l][1]
    if n>=MIN:
        best=max(FORMS, key=lambda k: run[k][l][0]/run[k][l][1])
    else: best='A0'
    sel.append(best)
    for k in FORMS: run[k][l][0]+=G[k][i]; run[k][l][1]+=1
sel=np.array(sel); wf=np.array([G[sel[i]][i] for i in range(len(TS))])
m=mfull
print(f"  WF mean {wf[m].mean():7.3f}  Sharpe {sh(wf[m]):5.2f} +-{np.sqrt(2190/m.sum()):4.2f}   switches {int((sel[1:]!=sel[:-1]).sum())}")
print("  form usage:", {k:int((sel[m]==k).sum()) for k in FORMS if (sel[m]==k).any()})
mm=m&(TS>=FROZEN[0])&(TS<FROZEN[1])
print(f"  WF on frozen window: mean {wf[mm].mean():7.3f} Sharpe {sh(wf[mm]):5.2f}   (A0 {G['A0'][mm].mean():7.3f} / {sh(G['A0'][mm]):5.2f})")
mh=m&(TS>=T(2025,1,1))
print(f"  WF on holdout 2025+ : mean {wf[mh].mean():7.3f} Sharpe {sh(wf[mh]):5.2f}   (A0 {G['A0'][mh].mean():7.3f} / {sh(G['A0'][mh]):5.2f})")
print("\n(c) best SINGLE form on FULL history (14-fold selection, uncorrected):")
for k in sorted(FORMS, key=lambda k:-sh(G[k][mfull]))[:6]:
    print(f"   {k:8s} mean {G[k][mfull].mean():7.3f} Sharpe {sh(G[k][mfull]):5.2f}")
print("\n(d) per-year Sharpe of A0 / F1 / ORACLE / WF:")
print(f"{'form':8s}"+"".join(f"{y:>9d}" for y in range(2022,2027)))
for nm,v in (("A0",G['A0']),("F1",G['F1']),("ORACLE",orc),("WF",wf)):
    line=f"{nm:8s}"
    for y in range(2022,2027):
        mm2=(yr==y)&mfull
        line+=f"{sh(v[mm2]):9.2f}" if mm2.sum()>10 else f"{'--':>9s}"
    print(line)
