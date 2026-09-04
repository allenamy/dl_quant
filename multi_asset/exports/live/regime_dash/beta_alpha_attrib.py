#!/usr/bin/env python3
"""beta_alpha_attrib — 书的 β/α 拆分(只读; PREREG_deploy_universe 后续监控项, 2026-09-04)。
每锚: β_book = Σ_j w_j·β_j(target_live 权重 × 7 日 5m 对 BTC 回归 β; 多头 β 低/空头 β 高 ⇒ 美元中性书净 β<0),
      β P&L = β_book(上锚) × BTC 4h 收益 × gross_usdt; α = 实现 sleeve 合计 − β P&L。
输出 ~/regime_dash/beta_alpha.jsonl(逐锚)+ 汇总 30/60 锚; 规则(INFO, 不是动作): R5_β主导 = 30 锚 |β P&L| ≥ 0.5% NAV; R6_映射不付钱 = fund 腿 200 锚 β 调整后 alpha ≤ 0。"""
import json, os, glob, time, numpy as np
WS=os.path.expanduser('~/wide_shadow'); PL=os.path.expanduser('~/dl_quant_live/state/live/pilot_log'); RD=os.path.expanduser('~/regime_dash'); OUT=f'{RD}/beta_alpha.jsonl'
cfg=json.load(open(f'{WS}/shadow_bundle/config.json')); syms=cfg['symbols_panel']; idx={s:j for j,s in enumerate(syms)}
z=np.load(f'{WS}/state/rolling.npz',allow_pickle=True); cts=z['ts'].astype(np.int64); cd=z['data']; row={int(t):i for i,t in enumerate(cts)}; btc=idx['BTCUSDT']
def ret5(j): r=cd[:,j,0].astype(np.float32); return r
def btc_ret(Ta,Tb): r=ret5(btc)[row[Ta]+1:row[Tb]+1]; r=np.where(np.isfinite(r),r,0); return float(np.expm1(np.log1p(r).sum()))
def betas_at(T):
    i=row[T]; seg=cd[i+1-2016:i+1,:,0].astype(np.float32); mb=seg[:,btc]; ok=np.isfinite(mb); vb=np.var(mb[ok]); out={}
    for j in range(len(syms)):
        x=seg[:,j]; m=ok&np.isfinite(x)
        if m.sum()>500: out[j]=float(np.cov(x[m],mb[m])[0,1]/vb)
    return out
def weights(A):
    p=f'{WS}/state/target_live/{A}.json'
    return json.load(open(p))['weights'] if os.path.exists(p) else None
def gross_nav(A):
    day=time.strftime('%Y%m%d',time.gmtime(A)); g=nav=None
    for d in (day, time.strftime('%Y%m%d',time.gmtime(A+86400))):
        for name,key in (('anchors.jsonl','realized_gross'),('daily_nav.jsonl','nav')):
            p=f'{PL}/{d}/{name}'
            if not os.path.exists(p): continue
            for ln in open(p):
                try: r=json.loads(ln)
                except Exception: continue
                ts=int(float(r.get('anchor_ts') or r.get('nav_ts') or 0))
                if A<=ts<A+14400:
                    if key=='realized_gross' and r.get(key): g=float(r[key])
                    if key=='nav' and r.get(key): nav=float(r[key])
    return g, nav
def sleeve_total(A):
    f=sorted(glob.glob(f'{RD}/*.jsonl')); f=[x for x in f if 'beta_alpha' not in x]
    if not f: return None
    for ln in open(f[-1]):
        r=json.loads(ln)
        if int(r['anchor_ts'])==A+14400:
            sl=r.get('sleeve_prev_interval_usdt') or {}; return sum(v['price']+v['carry'] for v in sl.values()) if sl else None
    return None
done=set()
if os.path.exists(OUT):
    for ln in open(OUT): done.add(int(json.loads(ln)['anchor_ts']))
anchors=[int(t) for t in cts if t%14400==0 and int(t)-7*86400 in row and int(t)+14400 in row]
new=0
for A in anchors:
    if A in done: continue
    w=weights(A)
    if not w: continue
    b=betas_at(A); bw=sum(float(v)*b.get(idx.get(s,-1),np.nan) for s,v in w.items() if idx.get(s) in b); g=sum(abs(float(v)) for v in w.values())
    beta_book=bw/g if g>0 else float('nan')   # 每单位 gross 的净 β
    br=btc_ret(A,A+14400); G,NAV=gross_nav(A); st=sleeve_total(A)
    rec={"anchor_ts":A,"anchor_utc":time.strftime('%Y-%m-%dT%H:%MZ',time.gmtime(A)),"beta_book_per_gross":round(beta_book,4),"btc_ret_4h":round(br,5),"gross_usdt":G,"nav_usdt":NAV,
         "beta_pnl_usdt":(round(beta_book*br*G,2) if G else None),"sleeve_total_usdt":(round(st,2) if st is not None else None)}
    rec["alpha_usdt"]=(round(st-rec["beta_pnl_usdt"],2) if (st is not None and rec["beta_pnl_usdt"] is not None) else None)
    open(OUT,'a').write(json.dumps(rec)+"\n"); new+=1
rows=[json.loads(l) for l in open(OUT)] if os.path.exists(OUT) else []
print(f"beta_alpha 行数 {len(rows)} (+{new}); 末行 {rows[-1] if rows else None}")
def summ(n):
    rs=[r for r in rows if r.get('beta_pnl_usdt') is not None][-n:]
    b=sum(r['beta_pnl_usdt'] for r in rs); s=[r['sleeve_total_usdt'] for r in rs if r['sleeve_total_usdt'] is not None]; a=[r['alpha_usdt'] for r in rs if r['alpha_usdt'] is not None]
    nav=next((r['nav_usdt'] for r in reversed(rs) if r.get('nav_usdt')),None); bb=np.mean([r['beta_book_per_gross'] for r in rs])
    print(f"末 {len(rs)} 锚: β_book/gross 均 {bb:+.3f} | BTC {np.prod([1+r['btc_ret_4h'] for r in rs])-1:+.2%} | β P&L {b:+,.0f}U | sleeve 合计 {sum(s):+,.0f}U (n{len(s)}) | α {sum(a):+,.0f}U (n{len(a)}) | NAV {nav}")
for n in (30,60): summ(n)
# R6: fund 腿 200 锚 β 调整 alpha(腿书 β 用 顶/底五分位 β 差 × 0.5 近似 = −0.16 常数改为估计: 用 beta_book/gross 的均值)
LR=json.load(open(f'{WS}/state/leg_returns_live.json')); f=np.array(LR['fund']); n=min(200,len(anchors)-1)
Ta,Tb=anchors[-1-n],anchors[-1]; brn=btc_ret(Ta,Tb); bb=np.mean([r['beta_book_per_gross'] for r in rows[-n:]]) if rows else -0.16
alpha200=f[-n:].sum()-bb*brn*1e4; print(f"R6 检: fund 腿末 {n} 锚 实际 {f[-n:].sum():+.0f} bps, BTC {brn:+.2%}, β_book/gross {bb:+.3f} ⇒ β 调整 alpha {alpha200:+.0f} bps ({alpha200/n:+.2f}/锚) -> {'触发(≤0)' if alpha200<=0 else '未触发'}")
