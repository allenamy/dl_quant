"""实盘 纸面 vs 真钱 逐锚对账(只读). 纸面 = target_live 权重 × 缓存 5 分钟真简单收益 Π(1+r)−1 (A, A+4h]; 孪生 = 交易所持仓(position_readback) × 标记价变动(anchors.jsonl mid 向量); 资金费 = funding.jsonl 实收; 日 NAV = daily_nav.jsonl(扣外部流入)."""
import json, os, glob, time, numpy as np
WS=os.path.expanduser('~/wide_shadow'); PL=os.path.expanduser('~/dl_quant_live/state/live/pilot_log')
cfg=json.load(open(f'{WS}/shadow_bundle/config.json')); syms=cfg['symbols_panel']; idx={s:j for j,s in enumerate(syms)}
z=np.load(f'{WS}/state/rolling.npz'); cts=z['ts'].astype(np.int64); cd=z['data']; row={int(t):i for i,t in enumerate(cts)}
def rets(A, shift_bars=0):
    i0=row.get(A); i1=row.get(A+14400)
    if i0 is None or i1 is None: return None
    seg=cd[i0+1+shift_bars:i1+1+shift_bars,:,0].astype(np.float64); fin=np.isfinite(seg); n=fin.sum(0); r=np.where(fin,seg,0)
    true=np.expm1(np.log1p(r).sum(0)); ssum=r.sum(0); bad=n<40; true[bad]=np.nan; ssum[bad]=np.nan
    return true, ssum
# pilot_log rows
anch={}; posr={}; fund={}
for d in sorted(os.listdir(PL)):
    if d<'20260825': continue
    p=f'{PL}/{d}/anchors.jsonl'
    if os.path.exists(p):
        for ln in open(p):
            try: r=json.loads(ln)
            except Exception: continue
            A=int(float(r['anchor_ts'])//14400*14400); anch[A]=r
    p=f'{PL}/{d}/position_readback.jsonl'
    if os.path.exists(p):
        for ln in open(p):
            try: r=json.loads(ln)
            except Exception: continue
            A=int(float(r['anchor_ts'])//14400*14400); posr.setdefault(A,{})[r['symbol']]=(float(r['venue_position_qty']), float(r['venue_position_notional']))
    p=f'{PL}/{d}/funding.jsonl'
    if os.path.exists(p):
        for ln in open(p):
            try: r=json.loads(ln)
            except Exception: continue
            ts=float(r['settlement_ts']); A=int((ts-1)//14400*14400)   # 结算 (A, A+4h] 归入 A
            fund[A]=fund.get(A,0.0)+float(r['funding_paid'])
rows=[]
for A in sorted(anch):
    if A<1787713600: continue   # 2026-08-26 04Z combo 起
    wp=f'{WS}/state/target_live/{A}.json'
    if not os.path.exists(wp) or (A+14400) not in anch: continue
    w=json.load(open(wp))['weights']; wv=np.zeros(len(syms))
    for s,x in w.items():
        if s in idx: wv[idx[s]]=x
    g=np.abs(wv).sum(); rr=rets(A); rs=rets(A,5)
    if rr is None or g<1e-9: continue
    true,ssum=rr; okm=np.isfinite(true)
    paper_true=float((wv[okm]*true[okm]).sum()/g*1e4); paper_sum=float((wv[okm]*ssum[okm]).sum()/g*1e4); paper_expm1=float((wv[okm]*np.expm1(ssum[okm])).sum()/g*1e4)
    paper_shift=float((wv[okm]*rs[0][okm]).sum()/g*1e4) if rs is not None else np.nan
    # 孪生: 交易所持仓 × mid 变动
    m0=json.loads(anch[A]['mid_at_anchor_vector']); m1=json.loads(anch[A+14400]['mid_at_anchor_vector']); pos=posr.get(A,{})
    twin=0.0; gross_v=0.0; nmiss=0
    for s,(q,notional) in pos.items():
        if s in m0 and s in m1 and m0[s]>0: twin+=q*(m1[s]-m0[s]); gross_v+=abs(q*m0[s])
        else: nmiss+=1
    rg=float(anch[A].get('realized_gross') or gross_v or np.nan)
    twin_bps=twin/rg*1e4 if rg>0 else np.nan; fund_bps=fund.get(A,0.0)/rg*1e4 if rg>0 else np.nan
    rows.append((A, paper_true, paper_sum, paper_expm1, paper_shift, twin_bps, fund_bps, rg, nmiss, len(pos)))
R=np.array(rows,dtype=float)
print(f"锚数 {len(R)}  {time.strftime('%m-%d %HZ',time.gmtime(R[0,0]))} → {time.strftime('%m-%d %HZ',time.gmtime(R[-1,0]))}  (持仓名缺 mid 均 {R[:,8].mean():.1f}/{R[:,9].mean():.0f})")
def s(x): x=x[np.isfinite(x)]; return f"均 {x.mean():+.2f} 中位 {np.median(x):+.2f} std {x.std():.1f} 合计 {x.sum():+.0f}"
print("纸面 真简单(A,A+4h]     bps/gross:", s(R[:,1]))
print("纸面 Σ简单              bps/gross:", s(R[:,2]))
print("纸面 expm1(Σ简单)(装置法) bps/gross:", s(R[:,3]))
print("纸面 真简单 平移25min    bps/gross:", s(R[:,4]))
print("孪生 持仓×Δmid(价格)     bps/gross:", s(R[:,5]))
print("实收资金费              bps/gross:", s(R[:,6]))
print("孪生+资金费             bps/gross:", s(R[:,5]+R[:,6]))
ok=np.isfinite(R[:,1])&np.isfinite(R[:,5])
print(f"纸面(真简单) vs 孪生: corr {np.corrcoef(R[ok,1],R[ok,5])[0,1]:.3f} | 均差(孪生−纸面) {np.mean(R[ok,5]-R[ok,1]):+.2f} bps/锚 | 平移纸面 vs 孪生 corr {np.corrcoef(R[ok,4],R[ok,5])[0,1]:.3f}")
# 逐日: 孪生+资金费 (USDT) vs daily_nav Δ(扣流入)
byday={}
for r in R:
    d=time.strftime('%Y%m%d',time.gmtime(r[0]+14400+3600*0.05))   # 锚 A 的收益落在 A+4h 所属日(与 daily_nav 00:03Z 快照口径对齐)
    byday.setdefault(d,[]).append((r[5]+r[6])*r[7]/1e4)
navs={}
for d in sorted(os.listdir(PL)):
    p=f'{PL}/{d}/daily_nav.jsonl'
    if os.path.exists(p):
        r=json.loads(open(p).readlines()[-1]); navs[d]=(r.get('equity_delta_since_prev'), r.get('external_flow_usdt') or 0.0, r.get('nav'), r.get('target_gross'))
print("日期     孪生+资金费(USDT)  真实ΔNAV−流入(USDT)  差   [NAV, 目标gross]")
tot_t=tot_r=0.0
for d in sorted(byday):
    if d not in navs or navs[d][0] is None: continue
    t=sum(byday[d]); rl=navs[d][0]-navs[d][1]; tot_t+=t; tot_r+=rl
    print(f"{d}  {t:+9.0f}          {rl:+9.0f}        {rl-t:+7.0f}   [{navs[d][2]:.0f}, {navs[d][3]:.0f}]")
print(f"合计     {tot_t:+9.0f}          {tot_r:+9.0f}        {tot_r-tot_t:+7.0f}")
np.save(f"{os.path.dirname(os.path.abspath(__file__))}/live_paper_vs_real_rows.npy", R)
print("PVR_DONE")
