"""B: 回放(canonpred s42, d30 臂)按(方向×费率桶)分年拆 价格盈亏/carry/名义占比; 急跌锚中多头 sleeve 脆弱性。 D: 2026 分月 regime 仪表盘(B 面板至 08-15)。"""
import numpy as np, time, collections
PD="/mnt/storage/private/work_hsy/probe_artifacts"; B="/mnt/storage/private/work_hsy/pod_backup_2026-08-21"
PW=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True); pts=PW["ts"].astype(np.int64); prow={int(t):j for j,t in enumerate(pts)}
FN=PW["f_fund_now"]; IV=PW["f_fund_iv"]; syms=[str(s) for s in PW["symbols"]]
MT=np.load(f"{B}/wide_fea_hist_meta.npz",allow_pickle=True); mts=MT["E_ts"].astype(np.int64); y4=MT["y4"]; mrow={int(t):i for i,t in enumerate(mts)}
z=np.load(f"{PD}/w10_canonpred_s42.npz",allow_pickle=True); cols=[str(c) for c in z["cols"]]; rec=z["d30_n2_c42_rec"]; W=z["d30_n2_c42_W"]
ts=rec[:,cols.index("ts")].astype(np.int64); yrs=np.array([time.gmtime(int(t)).tm_year for t in ts])
def bucket(r):
    return "S<-10bp" if r<-0.0010 else ("S-10..0" if r<0 else ("P0..10" if r<0.0010 else "P>10bp"))
agg=collections.defaultdict(lambda:collections.defaultdict(lambda:[0.0,0.0,0.0]))  # yr -> (side,b) -> [price bps sum, carry bps sum, gross share sum]
drop=collections.defaultdict(lambda:[0.0,0.0,0])  # yr -> [long price bps in sharp drops, short price bps, n]
for p,t in enumerate(ts):
    y=yrs[p]
    if y<2023: continue
    j=prow.get(int(t)); i=mrow.get(int(t))
    if j is None or i is None: continue
    w=W[p]; g=np.abs(w).sum()
    if g<1e-9: continue
    iv=IV[j]; iv=np.where(np.isfinite(iv)&(iv>0),iv,8.0); fn=np.nan_to_num(FN[j])*(8.0/iv)
    r=np.nan_to_num(y4[i]); 
    mk=np.median(r[np.isfinite(y4[i])]) if np.isfinite(y4[i]).any() else 0
    lp=sp=0.0
    for k in np.where(np.abs(w)>1e-9)[0]:
        side="S" if w[k]<0 else "L"; b=bucket(fn[k])
        price=w[k]*r[k]*1e4/g; car=-abs(w[k])*fn[k]*(0.5)*1e4/g if False else -(w[k]*fn[k]*(4.0/8.0))*1e4/g  # 4h 内 carry ≈ rate*(4/8h-equiv), 符号: 多付正/空付负 ⇒ -w*rate
        a=agg[y][(side,b)]; a[0]+=price; a[1]+=car; a[2]+=abs(w[k])/g
        if side=="L": lp+=price
        else: sp+=price
    if mk< -0.02:
        d=drop[y]; d[0]+=lp; d[1]+=sp; d[2]+=1
print("== B: 回放 sleeve 分年 (bps/锚 of gross, 累计/锚数) | 名义占比")
for y in sorted(agg):
    n=(yrs==y).sum()
    print(f"[{y}]")
    for k in sorted(agg[y]):
        pr,ca,sh=agg[y][k]
        print(f"   {k[0]}|{k[1]:8s} 价格 {pr/n:+.3f} carry {ca/n:+.3f} 合计 {(pr+ca)/n:+.3f} | 名义占比 {sh/n:.2f}")
    d=drop[y]; print(f"   急跌锚(市场中位<-2%): n {d[2]} 多头sleeve {d[0]/max(d[2],1):+.1f} bps/锚  空头 {d[1]/max(d[2],1):+.1f}")
print("== D: 2026 分月 regime(B面板至08-15): fund截面σ(bp) | |fund|>10bp名 | 合格名 | fund IC")
from scipy.stats import spearmanr
Y4p=PW["Y4"]; FE=PW["f_fund_ema_v1"]
mon=collections.defaultdict(list)
for j,t in enumerate(pts):
    tm=time.gmtime(int(t))
    if tm.tm_year!=2026: continue
    v=FE[j]; ok=np.isfinite(v)
    if ok.sum()<60: continue
    iv=IV[j]; iv=np.where(np.isfinite(iv)&(iv>0),iv,8.0); fn=np.nan_to_num(FN[j])*(8.0/iv)
    y4v=Y4p[j]; ok2=ok&np.isfinite(y4v)
    ic=spearmanr(v[ok2],y4v[ok2]).correlation if ok2.sum()>60 else np.nan
    mon[tm.tm_mon].append((np.std(fn[ok])*1e4, int((np.abs(fn[ok])*1e4>10).sum()), int(ok.sum()), ic, float(np.mean(fn[ok]<-0.0010))))
for m in sorted(mon):
    a=np.array(mon[m],dtype=float)
    print(f"  2026-{m:02d}: σ {a[:,0].mean():5.1f} | 极端名 {a[:,1].mean():5.1f} | 合格 {a[:,2].mean():4.0f} | IC {np.nanmean(a[:,3]):+.4f} | 深负名占比 {a[:,4].mean()*100:4.1f}%")
print("SLEEVE_REGIME_DONE")
