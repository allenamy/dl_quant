"""宇宙机制掩码构建 @jpline(PREREG_universe_dyn_2026-09-04): 全部 era-synchronous。
输入: meta(E_ts, members, qvk 全宽 12985×829) + 面板(ts, symbols 829, 首现=首个有限 f_rev_4h/Y4 的锚)。
输出: umask_<rule>.npz(ts=面板 ts, symbols, mask[面板锚×829] bool) — 装置只在 meta 成员上做交集(只缩)。
规则: F_M/F_Q/F_Y(月/季/年首锚刷新: trailing 30d 报价额中位 top-450 ∧ 年龄≥14d, 期内固定) · A14/A30/A60(年龄门) · N300(动态 top-300) · H_300_400(滞回)。"""
import numpy as np, time
B="/mnt/storage/private/work_hsy/pod_backup_2026-08-21"; PD="/mnt/storage/private/work_hsy/probe_artifacts"
M=np.load(f"{B}/wide_fea_hist_meta.npz",allow_pickle=True); E=M["E_ts"].astype(np.int64); qvk=M["qvk"]; mem=M["members"]
P=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True); pts=P["ts"].astype(np.int64); syms=[str(s) for s in P["symbols"]]; NW=len(syms)
R4=P["f_rev_4h"]; fin=np.isfinite(R4)
first=np.where(fin.any(0), pts[np.argmax(fin,axis=0)], 2**62)          # 首现日期(面板)
prow={int(t):j for j,t in enumerate(pts)}
qv=np.expm1(np.clip(np.nan_to_num(qvk,nan=0.0),0,30))*48                 # 4h 报价额(USDT), meta 锚网格
# 逐锚 trailing 30 日(180 锚)报价额中位(era-synchronous: 只用 ≤i)
def trailing_median(i, win=180):
    lo=max(0,i-win+1); return np.median(qv[lo:i+1],axis=0)
# 正典成员 vs qvk 排名重建 的一致性(装置扩展臂的前提)
ov=[]
for i in range(len(E)-2000,len(E),50):
    q=np.nan_to_num(qvk[i],nan=-1.0); top=set(np.argsort(-q)[:len(mem[i])].tolist()); ov.append(len(top&set(mem[i].tolist()))/max(len(mem[i]),1))
print(f"正典 members vs 当锚 qvk 排名 top-|members| 重叠: 均 {np.mean(ov):.3f} 最低 {np.min(ov):.3f}")
def rank_at(i):
    return np.argsort(-trailing_median(i))     # 降序名索引
masks={}
Lm=len(pts)
def new_mask(): return np.zeros((Lm,NW),bool)
# 年龄门(动态): 每锚 age≥d
for d in (14,30,60):
    m=new_mask()
    for j,t in enumerate(pts): m[j]=(t-first)/86400.0>=d
    masks[f"A{d}"]=m
# 刷新节奏: 在刷新锚重算 top-450(trailing 中位 ∧ age≥14), 期内固定
def refresh_mask(period):
    m=new_mask(); cur=None; last_key=None
    for i,t in enumerate(E):
        tm=time.gmtime(int(t)); key={"M":(tm.tm_year,tm.tm_mon),"Q":(tm.tm_year,(tm.tm_mon-1)//3),"Y":(tm.tm_year,)}[period]
        if key!=last_key or cur is None:
            age=(t-first)/86400.0; r=rank_at(i); allowed=[k for k in r if age[k]>=14][:450]; cur=np.zeros(NW,bool); cur[allowed]=True; last_key=key
        j=prow.get(int(t))
        if j is not None: m[j]=cur
    return m
for per in ("M","Q","Y"): masks[f"F_{per}"]=refresh_mask(per)
# N300 动态: 当锚 qvk 排名前 300
m=new_mask()
for i,t in enumerate(E):
    j=prow.get(int(t))
    if j is None: continue
    q=np.nan_to_num(qvk[i],nan=-1.0); top=np.argsort(-q)[:300]; mm=np.zeros(NW,bool); mm[top]=True; m[j]=mm
masks["N300"]=m
# 滞回: 入 rank≤300 出 rank>400(按当锚 qvk 排名)
m=new_mask(); cur=np.zeros(NW,bool)
for i,t in enumerate(E):
    j=prow.get(int(t))
    q=np.nan_to_num(qvk[i],nan=-1.0); order=np.argsort(-q); rank=np.empty(NW,int); rank[order]=np.arange(NW)
    cur=(cur & (rank<=400)) | (rank<300)
    if j is not None: m[j]=cur
masks["H_300_400"]=m
for k,mk in masks.items():
    np.savez_compressed(f"{PD}/umask_{k}.npz", ts=pts, symbols=np.array(syms), mask=mk)
    last=pts>=E[-2000]; print(f"{k}: 末 2000 锚 平均允许名数 {mk[last].sum(1).mean():.0f} | 2023+ 平均 {mk[pts>=1672531200].sum(1).mean():.0f}")
print("UMASK_RULES_DONE")
