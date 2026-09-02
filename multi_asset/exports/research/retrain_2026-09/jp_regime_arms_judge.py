"""跨regime战役统一判官 @jpline: 各臂(seat_*/band_*) vs 基线 canonpred_s42(msharpe, 无trim): 2023+ ΔNet 块自举CI / 分年净&夏普 / ES5 / 最坏五分位 / 急跌锚净 / 换手变化。判据(冻结见 PREREG_xregime_2026-09-02): ΔNet CI下界>0 且 逐年无 <-0.3 且 ES5 不劣化>10% 且 换手≤+25%。"""
import numpy as np, time, sys, glob, os
PD="/mnt/storage/private/work_hsy/probe_artifacts"; B="/mnt/storage/private/work_hsy/pod_backup_2026-08-21"
rng=np.random.default_rng(0)
MT=np.load(f"{B}/wide_fea_hist_meta.npz",allow_pickle=True); mts=MT["E_ts"].astype(np.int64); y4=MT["y4"]; mrow={int(t):i for i,t in enumerate(mts)}
def load(run):
    z=np.load(f"{PD}/{run}.npz",allow_pickle=True); cols=[str(c) for c in z["cols"]]; rec=z["d30_n2_c42_rec"]
    g=lambda k: rec[:,cols.index(k)].astype(np.float64)
    return rec[:,cols.index("ts")].astype(np.int64), g("net_ex"), g("turnover"), g("w3_king"), g("w3_fund")
BASE=os.environ.get("BASE","w10_canonpred_s42"); SEEDTAG=os.environ.get("SEEDTAG","s42"); print(f"[judge] BASE={BASE} SEEDTAG={SEEDTAG}")
tb,nb,tob,wkb,wfb=load(BASE); yrs=np.array([time.gmtime(int(t)).tm_year for t in tb]); sel=yrs>=2023
mk=np.full(len(tb),np.nan)
for p,t in enumerate(tb):
    i=mrow.get(int(t))
    if i is not None:
        v=y4[i]; v=v[np.isfinite(v)]
        if len(v)>50: mk[p]=np.median(v)
drop=sel&(mk<-0.02)
def stats(n):
    r=n[sel]; return r.mean(), r.mean()/(r.std()+1e-12)*np.sqrt(2190), np.sort(r)[:max(1,int(len(r)*0.05))].mean(), np.sort(r)[:max(1,int(len(r)*0.2))].mean()
bm,bs,bes,bwq=stats(nb)
print(f"基线 msharpe: 净 {bm:+.3f} 夏普 {bs:.2f} ES5 {bes:+.1f} 最坏五分位 {bwq:+.2f} 急跌锚净 {nb[drop].mean():+.2f}(n{drop.sum()}) 换手 {tob[sel].mean():.4f} w3_king均 {wkb[sel].mean():.2f} w3_fund均 {wfb[sel].mean():.2f}")
for y in (2023,2024,2025,2026):
    s=yrs==y; print(f"   {y}: 净 {nb[s].mean():+.3f} 夏普 {nb[s].mean()/(nb[s].std()+1e-12)*np.sqrt(2190):.2f}")
runs=sorted(os.path.basename(p)[:-4] for p in glob.glob(f"{PD}/w10_seat_*.npz")+glob.glob(f"{PD}/w10_band_*.npz"))
runs=[r for r in runs if r.endswith("_s2027")==(SEEDTAG=="s2027")]  # 种子配对: s2027 臂只与 s2027 基线比
for run in runs:
    ta,na,toa,wka,wfa=load(run)
    if not np.array_equal(ta,tb):   # 锚集对齐(臂内 sel<80 跳锚等): ts 交集成对
        mb={int(t):i for i,t in enumerate(tb)}; pr=[(mb[int(t)],k) for k,t in enumerate(ta) if int(t) in mb]
        ib=np.array([x[0] for x in pr]); ia=np.array([x[1] for x in pr])
        na_=np.full(len(tb),np.nan); toa_=np.full(len(tb),np.nan); wka_=np.full(len(tb),np.nan)
        na_[ib]=na[ia]; toa_[ib]=toa[ia]; wka_[ib]=wka[ia]; na,toa,wka=na_,toa_,wka_
        print(f"  ({run}: 锚集不同, 交集 {len(ib)}/{len(tb)}, 缺锚按基线值填)"); na=np.where(np.isnan(na),nb,na); toa=np.where(np.isnan(toa),tob,toa); wka=np.where(np.isnan(wka),wkb,wka)
    d=(na-nb)[sel]; nb6=len(d)//6; blocks=d[:nb6*6].reshape(nb6,6).sum(1)
    boots=np.array([blocks[rng.integers(0,nb6,nb6)].mean() for _ in range(4000)])/6
    lo,hi=np.quantile(boots,[0.025,0.975])
    am,as_,aes,awq=stats(na)
    yl={y:round((na-nb)[yrs==y].mean(),3) for y in (2023,2024,2025,2026)}
    es_ok = aes >= bes*1.10 if bes<0 else aes>=bes*0.9
    to=toa[sel].mean()/max(tob[sel].mean(),1e-9)-1
    ok = lo>0 and all(v>=-0.3 for v in yl.values()) and es_ok and to<=0.25
    print(f"[{run}] Δ {d.mean():+.3f} CI[{lo:+.3f},{hi:+.3f}] 夏普 {as_:.2f}(基{bs:.2f}) ES5 {aes:+.1f}({'OK' if es_ok else 'FAIL'}) 最坏五分位 {awq:+.2f} 急跌净 {na[drop].mean():+.2f} 换手{to*100:+.1f}% w3_king {wka[sel].mean():.2f} 逐年Δ {yl} -> {'ADMIT候选' if ok else '不过'}")
print("JUDGE_DONE")
