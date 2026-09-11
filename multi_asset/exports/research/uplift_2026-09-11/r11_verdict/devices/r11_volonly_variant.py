import os,json,datetime as dt
import numpy as np
_A=set()
class G(dict):
    def get(s,k,d=None):
        raise RuntimeError("env")
    def __getitem__(s,k):
        raise RuntimeError("env")
os.environ=G(dict(os.environ))
ROOT="/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"
z=np.load(ROOT+"/r10_screen/CMUM_CARRY/pin/A0_PWR230k_s42.npz",allow_pickle=True)
cols=[str(c) for c in z['cols']];rec=z['rec'];C={c:i for i,c in enumerate(cols)}
B=dt.datetime(2026,8,30,20,0,tzinfo=dt.UTC).timestamp()
r=rec[900:]; r=r[r[:,C['ts']]<=B]
g=r[:,C['net_ex']]/r[:,C['gross_total']]
tpg=r[:,C['turnover']]/r[:,C['gross_total']]
cpg=r[:,C['cost_ex']]/r[:,C['gross_total']]
ARM={'A':g,'C':0.5*((g-6.547452*tpg)+(g-cpg*(3.216695-1.0)))}
days=np.array([dt.datetime.fromtimestamp(float(t),dt.UTC).strftime('%Y-%m-%d') for t in r[:,C['ts']]])
ud,inv=np.unique(days,return_inverse=True)
def daily(gs,L):
    rr=gs/1e4*L; out=np.ones(len(ud))
    for i in range(len(gs)): out[inv[i]]*=(1.0+rr[i])
    return out-1.0
def boot(dr,B_=2000,H=365):
    mdd=[];halts=[];frm=[]
    for k in range(B_):
        rng=np.random.default_rng([20260905,k]); p=dr[rng.integers(0,len(dr),H)]
        eq=np.cumprod(1+p); eqp=np.concatenate([[1.0],eq]); pk=np.maximum.accumulate(eqp)
        mdd.append(-(eqp/pk-1).min()); frm.append(eqp.min()-1); halts.append(int((p<=-0.04).sum()))
    mdd=np.array(mdd);halts=np.array(halts);frm=np.array(frm)
    return dict(medDD=float(np.median(mdd)*100),PDD25=float((mdd>=.25).mean()*100),
                Ehalt=float(halts.mean()),P1=float((halts>=1).mean()),P3=float((halts>=3).mean()),
                Pfrm25=float((frm<=-.25).mean()*100))
RATIO=1.4042
print("VOL-ONLY INFLATION: same expected daily return, daily sigma x%.4f (live/replay)"%RATIO)
print("%-4s %-7s %9s %9s %8s %8s %8s %8s"%('arm','gross','NAV%/yr','E[halt]','P>=1','P>=3','medDD','P(DD>=25)'))
res={}
for arm in ['A','C']:
    for L in [1.00,1.10,1.20,1.25,1.30,1.40,1.50,1.75,2.00]:
        dr=daily(ARM[arm],L)
        m=dr.mean(); drv=m+RATIO*(dr-m)
        b=boot(drv)
        nav=ARM[arm].mean()*2190*L/100
        res[(arm,L)]=dict(nav=nav,**b)
        print("%-4s %-7.2f %9.2f %9.3f %8.3f %8.3f %8.2f %8.2f"%(arm,L,nav,b['Ehalt'],b['P1'],b['P3'],b['medDD'],b['PDD25']))
json.dump({f"{a}_{l}":v for (a,l),v in res.items()},open('/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/volonly.json','w'),indent=1)
