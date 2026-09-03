"""宇宙机制掩码 v2 @jpline(PREREG_universe_dyn §1): 修正首现来源 —— 面板 f_rev_4h 在上市前被填充(全 829 名首现 2020-01-31, 伪), 正确来源 = meta qvk>0 / y4 首有限锚(两者逐名同日)。
A14/A30/A60: 上市年龄门(动态); F_M/F_Q/F_Y: 月/季/年首锚刷新 trailing 30d 报价额中位(只对已上市锚取中位)top-450 ∧ 年龄≥14d, 期内固定; X14: 年龄≥14d 掩码(与 MEMBERS_TOPN 扩展臂合用)。"""
import numpy as np, time
B="/mnt/storage/private/work_hsy/pod_backup_2026-08-21"; PD="/mnt/storage/private/work_hsy/probe_artifacts"
M=np.load(f"{B}/wide_fea_hist_meta.npz",allow_pickle=True); E=M["E_ts"].astype(np.int64); qvk=M["qvk"]
P=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True); pts=P["ts"].astype(np.int64); syms=[str(s) for s in P["symbols"]]; NW=len(syms)
qv=np.expm1(np.clip(np.nan_to_num(qvk,nan=0.0),0,30))*48; listed=qv>0
first=np.where(listed.any(0), E[np.argmax(listed,axis=0)], 2**62)
prow={int(t):j for j,t in enumerate(pts)}; Lm=len(pts)
def new_mask(): return np.zeros((Lm,NW),bool)
def age_mask(d):
    m=new_mask()
    for j,t in enumerate(pts): m[j]=(t-first)/86400.0>=d
    return m
masks={f"A{d}":age_mask(d) for d in (14,30,60)}; masks["X14"]=masks["A14"]
qvn=np.where(listed, qv, np.nan)
def trailing_median(i, win=180):
    lo=max(0,i-win+1); return np.nanmedian(qvn[lo:i+1],axis=0)
def refresh_mask(period):
    m=new_mask(); cur=None; last_key=None
    for i,t in enumerate(E):
        tm=time.gmtime(int(t)); key={"M":(tm.tm_year,tm.tm_mon),"Q":(tm.tm_year,(tm.tm_mon-1)//3),"Y":(tm.tm_year,)}[period]
        if key!=last_key or cur is None:
            age=(t-first)/86400.0; tmv=np.nan_to_num(trailing_median(i),nan=-1.0); r=np.argsort(-tmv)
            allowed=[k for k in r if age[k]>=14 and tmv[k]>0][:450]; cur=np.zeros(NW,bool); cur[allowed]=True; last_key=key
        j=prow.get(int(t))
        if j is not None: m[j]=cur
    return m
for per in ("M","Q","Y"): masks[f"F_{per}"]=refresh_mask(per)
for k,mk in masks.items():
    np.savez_compressed(f"{PD}/umask_{k}.npz", ts=pts, symbols=np.array(syms), mask=mk)
    s25=pts>=1735689600; print(f"{k}: 2025+ 平均允许名数 {mk[s25].sum(1).mean():.0f} | 2023+ {mk[pts>=1672531200].sum(1).mean():.0f} | 2025+ 被排除的已上市名均 {((~mk)&(np.isin(pts,E)[:,None]))[s25].sum(1).mean():.0f}")
yrs=np.array([time.gmtime(int(t)).tm_year for t in first]); print("首现年分布", {int(y):int((yrs==y).sum()) for y in np.unique(yrs)})
print("UMASK_RULES_V2_DONE")
