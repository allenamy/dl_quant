import numpy as np, time
C6="/workspace/review_scratch/refute_C6_2/altrun"; G6="/workspace/review_scratch/gap_6/altrun"
def load(p):
    z=np.load(p,allow_pickle=True); cols=[str(c) for c in z["cols"]]; c={n:k for k,n in enumerate(cols)}; return z["d30_n2_c42_rec"],c
def yr(ts): return np.array([time.gmtime(int(t)).tm_year for t in ts])
for form in ("w3fix","dyn"):
    for cal in ("sum","prod"):
        Ru,cu=load(f"{C6}/new{cal}/probe_artifacts/w10_ablation_series_alt_new{cal}_{form}.npz"); Rs,cs=load(f"{G6}/shift{cal}/probe_artifacts/w10_ablation_series_alt_shift{cal}_{form}.npz")
        tu=Ru[:,cu["ts"]].astype(np.int64); ts_=Rs[:,cs["ts"]].astype(np.int64)
        missing=sorted(set(tu.tolist())-set(ts_.tolist())); extra=sorted(set(ts_.tolist())-set(tu.tolist()))
        print(f"{form} {cal}: anchors unshift {len(tu)} shift {len(ts_)} | dropped in shift: {[time.strftime('%F %H:%M',time.gmtime(t)) for t in missing]} | extra: {[time.strftime('%F %H:%M',time.gmtime(t)) for t in extra]}")
        common=np.intersect1d(tu,ts_); iu={t:k for k,t in enumerate(tu)}; is_={t:k for k,t in enumerate(ts_)}
        au=np.array([Ru[iu[t],cu["net_ex"]] for t in common]); as_=np.array([Rs[is_[t],cs["net_ex"]] for t in common]); y=yr(common); d=as_-au
        for lab,m in (("2024",y==2024),("2025",y==2025),("2026",y==2026),("2024on",y>=2024)):
            dd=d[m]; se=dd.std(ddof=1)/np.sqrt(len(dd)); print(f"   {lab:7s} n={m.sum():4d} paired Δ(shift−unshift) mean {dd.mean():+.4f} SE {se:.4f} t {dd.mean()/se:+.2f} | corr(unshift,shift) {np.corrcoef(au[m],as_[m])[0,1]:.4f} | σ_unshift {au[m].std(ddof=1):.2f} σ_shift {as_[m].std(ddof=1):.2f}")
# where did the dropped anchor go? check sel count in base at that ts
Rb,cb=load(f"{G6}/base/probe_artifacts/w10_ablation_series_alt_base_w3fix.npz"); tb=Rb[:,cb["ts"]].astype(np.int64)
Rs,cs=load(f"{G6}/shiftprod/probe_artifacts/w10_ablation_series_alt_shiftprod_w3fix.npz"); ts_=Rs[:,cs["ts"]].astype(np.int64)
for t in sorted(set(tb.tolist())-set(ts_.tolist())):
    k=int(np.where(tb==t)[0][0]); print("dropped anchor", time.strftime('%F %H:%M',time.gmtime(t)), "base row nsel", int(Rb[k,cb["nsel"]]), "nmember", int(Rb[k,cb["nmember"]]), "net_ex", round(float(Rb[k,cb["net_ex"]]),3))
