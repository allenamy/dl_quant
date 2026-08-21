"""薄币执行探针 7 天正式判官(PREREG_exec_probe_thin / P3 判定表): 按臂 成交率 + markout(成交→轮末 mid) + 块自助 CI;
判定表(冻结): fill≥0.75 且 markout≥−2 ⇒ λ 可开 0.3(情景 a); fill 0.5-0.75 ⇒ λ 0.1; fill<0.5 或 markout<−2 ⇒ λ=0(情景 b/c)。"""
import json, collections, statistics, sys, time, numpy as np
ev=[json.loads(l) for l in open('/Users/haosiyu/exec_probe/events.jsonl')]
last={}
for e in ev:
    if e.get('e')=='status' and 'orderId' in e: last[e['orderId']]=e
rem=collections.defaultdict(list)
for e in ev:
    if e.get('e')=='round_end_mid' and e.get('mid'): rem[e.get('symbol')].append((e.get('ts'),float(e['mid'])))
rows=[]
for e in last.values():
    q=float(e.get('executedQty') or 0); px=float(e.get('avgPrice') or 0); arm=e.get('arm') or 'base0'
    mk=None
    if q>0 and px>0:
        c=[m for t,m in rem.get(e.get('symbol'),[]) if t>=e.get('ts',0)]
        if c: mk=(1 if str(e.get('side','')).lower()=='buy' else -1)*(c[0]-px)/px*1e4
    rows.append((arm, 1 if q>0 else 0, mk, e.get('ts',0)))
t0=min(r[3] for r in rows); t1=max(r[3] for r in rows); span_d=(t1-t0)/86400/(1000 if t1>2e10 else 1)
rng=np.random.RandomState(7); out={"span_days":round(span_d,1),"n_orders":len(rows)}
for arm in sorted({r[0] for r in rows}):
    R=[r for r in rows if r[0]==arm]; fills=np.array([r[1] for r in R]); mks=np.array([r[2] for r in R if r[2] is not None])
    fb=[rng.choice(fills,len(fills)).mean() for _ in range(1000)]; mb=[rng.choice(mks,len(mks)).mean() for _ in range(1000)] if len(mks)>5 else [np.nan]
    fr=float(fills.mean()); mk=float(mks.mean()) if len(mks) else float('nan')
    lam = 0.3 if (fr>=0.75 and mk>=-2) else (0.1 if (fr>=0.5 and mk>=-2) else 0.0)
    out[arm]={"n":len(R),"fill":round(fr,3),"fill_CI":[round(float(np.percentile(fb,2.5)),3),round(float(np.percentile(fb,97.5)),3)],
              "markout":round(mk,2),"markout_CI":[round(float(np.nanpercentile(mb,2.5)),2),round(float(np.nanpercentile(mb,97.5)),2)],"n_markout":int(len(mks)),"lambda_by_table":lam}
print(json.dumps(out,ensure_ascii=False,indent=1)); json.dump(out,open('/Users/haosiyu/exec_probe/probe_7day_judge.json','w'),indent=1)
