#!/usr/bin/env python3
"""sigma_ladder — σ_fund 条件化 gross 阶梯的状态作业(PREREG_deploy_sigma_ladder_2026-09-04 §1/§2)。只读仪表盘历史与面板种子; 原子写状态文件供执行器只读。
规则(与回放 jp_allweather.py H1 逐字同): 30 锚滚动均 σ_fund 在滚动 2 年(4380 锚)分布中的分位 p; g=1.0 且 p<0.33 连续 ≥84 锚 ⇒ 0.5; g=0.5 且 p>0.50 连续 ≥84 锚 ⇒ 1.0。故障安全: 任何异常 ⇒ 不写新状态(执行器按陈旧/缺失 → g=1.0)。"""
import json, os, glob, time, hashlib, sys
HERE=os.path.dirname(os.path.abspath(__file__)); RD=os.path.expanduser('~/regime_dash'); SEED=f'{HERE}/sigma_seed.json'
OUT=os.environ.get('SIGMA_LADDER_OUT', os.path.expanduser('~/dl_quant_live/state/live/sigma_ladder.json')); STATE=f'{RD}/sigma_ladder_state.json'
P_LOW, P_HIGH, STREAK, WIN, ROLL = 0.33, 0.50, 84, 4380, 30
def series():
    seed=json.load(open(SEED)); s={int(t):float(v) for t,v in seed['series']}
    for f in sorted(glob.glob(f'{RD}/*.jsonl')):
        if 'beta_alpha' in f: continue
        for ln in open(f):
            try: r=json.loads(ln)
            except Exception: continue
            if r.get('sig_fund_bp') is not None and int(r['anchor_ts'])>max(s): s[int(r['anchor_ts'])]=float(r['sig_fund_bp'])
    ts=sorted(s); return ts,[s[t] for t in ts]
def main():
    ts,v=series(); n=len(v)
    roll=[sum(v[max(0,i-ROLL+1):i+1])/len(v[max(0,i-ROLL+1):i+1]) for i in range(n)]
    st=json.load(open(STATE)) if os.path.exists(STATE) else {'g':1.0,'cl':0,'ch':0,'last_ts':0,'history':[]}
    g,cl,ch=st['g'],st['cl'],st['ch']; start=next((i for i,t in enumerate(ts) if t>st['last_ts']),n)
    for i in range(start,n):
        lo=max(0,i-WIN); hist=roll[lo:i+1]
        if len(hist)<1000: continue
        p=sum(1 for h in hist if h<=roll[i])/len(hist)
        cl=cl+1 if p<P_LOW else 0; ch=ch+1 if p>P_HIGH else 0
        prev=g
        if g==1.0 and cl>=STREAK: g=0.5
        if g<1.0 and ch>=STREAK: g=1.0
        if g!=prev: st['history'].append({'anchor_ts':ts[i],'g':g,'p':round(p,3)})
    st.update({'g':g,'cl':cl,'ch':ch,'last_ts':ts[-1],'p_last':round(p,4),'sigma_last':v[-1],'roll_last':round(roll[-1],3),'n':n,'updated_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
    json.dump(st, open(STATE+'.tmp','w'), indent=1); os.replace(STATE+'.tmp', STATE)
    doc={'schema':'sigma_ladder_v1','g':g,'p':round(p,4),'streak_low':cl,'streak_high':ch,'anchor_ts':ts[-1],'written_utc':st['updated_utc'],'rule':f'p<{P_LOW}x{STREAK}->0.5; p>{P_HIGH}x{STREAK}->1.0; roll{ROLL} win{WIN}','seed_sha':hashlib.sha256(open(SEED,'rb').read()).hexdigest()[:12]}
    doc['sha']=hashlib.sha256(json.dumps({k:doc[k] for k in ('schema','g','p','anchor_ts','written_utc')},sort_keys=True).encode()).hexdigest()[:16]
    os.makedirs(os.path.dirname(OUT),exist_ok=True); json.dump(doc, open(OUT+'.tmp','w'), indent=1); os.replace(OUT+'.tmp', OUT)
    print(f"sigma_ladder: g={g} p={p:.3f} streak_low={cl} streak_high={ch} σ={v[-1]:.2f}bp roll30={roll[-1]:.2f} n={n} last={time.strftime('%m-%d %HZ',time.gmtime(ts[-1]))} -> {OUT}")
if __name__=='__main__': main()
