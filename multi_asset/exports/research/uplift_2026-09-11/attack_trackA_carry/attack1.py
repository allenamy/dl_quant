import numpy as np, json, time, calendar
P="/workspace/uplift_2026-09-11/probe_artifacts/"
def L(nm): return np.load(P+f"w10_ablation_series_{nm}.npz",allow_pickle=True)
COLS=list(L("A0_dyn_s42")["cols"]); C={c:i for i,c in enumerate(COLS)}
print("COLS",COLS)
def ts2(t): return time.strftime("%Y-%m-%d",time.gmtime(int(t)))
def win(ts,a,b):
    a=calendar.timegm(time.strptime(a,"%Y-%m-%d %H:%M")); b=calendar.timegm(time.strptime(b,"%Y-%m-%d %H:%M"))
    return (ts>=a)&(ts<=b)
FRZ=("2025-03-01 00:00","2026-08-10 20:00")

def g(rec,msk,num="net_ex"):
    return rec[msk,C[num]].sum()/rec[msk,C["gross_total"]].sum()

def boot(rec_a,rec_b,msk,seed_k,nb=2000):
    # UTC-day block bootstrap on paired anchors, judge_v4 scheme
    ts=rec_a[msk,C["ts"]].astype(np.int64)
    day=(ts//86400)
    ud=np.unique(day); idx={d:np.where(day==d)[0] for d in ud}
    na=rec_a[msk,C["net_ex"]]; nb_=rec_b[msk,C["net_ex"]]; gr=rec_a[msk,C["gross_total"]]; grb=rec_b[msk,C["gross_total"]]
    rng=np.random.default_rng([20260905,seed_k])
    out=np.empty(nb)
    for i in range(nb):
        pick=rng.integers(0,len(ud),len(ud))
        sel=np.concatenate([idx[ud[p]] for p in pick])
        out[i]=nb_[sel].sum()/grb[sel].sum()-na[sel].sum()/gr[sel].sum()
    return out

for seed in ("s42","s2027"):
    A=L(f"A0_dyn_{seed}")["d30_n2_c42_rec"]; B=L(f"FT00S_dyn_{seed}")["d30_n2_c42_rec"]
    assert np.array_equal(A[:,0],B[:,0])
    m=win(A[:,0],*FRZ); n=m.sum()
    gA=g(A,m); gB=g(B,m); d=gB-gA
    bs=boot(A,B,m,20)
    ci=np.percentile(bs,[2.5,97.5])
    print(f"\n=== {seed} FT00S-A0 dyn frozen n={n} ===")
    print(f"  A0 g={gA:.4f}  FT00S g={gB:.4f}  delta={d:.4f}  CI95=[{ci[0]:.4f},{ci[1]:.4f}]  P>0={(bs>0).mean():.4f}")
    for comp in ("pnl_ex","carry_ex","cost_ex"):
        dA=A[m,C[comp]].sum()/A[m,C["gross_total"]].sum(); dB=B[m,C[comp]].sum()/B[m,C["gross_total"]].sum()
        print(f"  d_{comp} = {dB-dA:+.4f}   (A0 {dA:+.4f} -> {dB:+.4f})")
    # seat weights
    for w in ("w3_king","w3_rev24","w3_fund"):
        print(f"  {w}: A0 {A[m,C[w]].mean():.4f}  FT00S {B[m,C[w]].mean():.4f}  delta {B[m,C[w]].mean()-A[m,C[w]].mean():+.4f}")
    print(f"  turnover: A0 {A[m,C['turnover']].mean():.5f} FT00S {B[m,C['turnover']].mean():.5f}  +{100*(B[m,C['turnover']].mean()/A[m,C['turnover']].mean()-1):.1f}%")
    print(f"  gross_total: A0 {A[m,C['gross_total']].mean():.4f} FT00S {B[m,C['gross_total']].mean():.4f}")
