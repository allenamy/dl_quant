#!/usr/bin/env python
"""Stop-loss frequency test: live vs backtest base rate. READ-ONLY."""
import json,glob,os,math,statistics as st
root='/Users/haosiyu/dl_quant_live/state/live/pilot_log'
days=sorted(os.path.basename(d) for d in glob.glob(root+'/2026*') if os.path.isdir(d))

# ---- per-day (watchdog cond2 caliber) ----
dayrows=[]
prev=None
for d in days:
    p=f'{root}/{d}/daily_nav.jsonl'
    rr=[json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []
    if not rr: continue
    last=rr[-1]; nav=float(last['nav'])
    flows=[float(r.get('external_flow_usdt') or 0.0) for r in rr]
    flow=max(flows,key=abs) if flows else 0.0     # cumulative-per-day field
    trunc=any(bool(r.get('realised_truncated')) for r in rr)
    lev=(float(last.get('target_gross') or 0.0)/nav) if nav else 0.0
    wd = None if (abs(flow)>1e-9 or prev in (None,0)) else (nav-prev)/prev*100
    dayrows.append(dict(day=d,nav=nav,flow=flow,trunc=trunc,lev=lev,wd=wd,nrows=len(rr)))
    prev=nav

judge=[r for r in dayrows if r['wd'] is not None]
print("=== LIVE DAILY (watchdog cond2 caliber: last nav of day vs last nav of prev day; flow days UNKNOWN) ===")
print(f"calendar days={len(dayrows)}  judgeable(no flow, has prev)={len(judge)}  blind(flow)={len(dayrows)-len(judge)}")
br4=[r for r in judge if r['wd']<=-4.0]; br268=[r for r in judge if r['wd']<=-2.68]; br2=[r for r in judge if r['wd']<=-2.0]
print(" <=-4.00%:", [(r['day'],round(r['wd'],3)) for r in br4])
print(" <=-2.68%:", [(r['day'],round(r['wd'],3)) for r in br268])
print(" <=-2.00%:", [(r['day'],round(r['wd'],3)) for r in br2])
v=[r['wd'] for r in judge]
print(f" judgeable daily: mean {st.mean(v):+.4f}%  sd {st.stdev(v):.4f}%  min {min(v):.3f}%")
combo=[r for r in judge if r['day']>='20260826']
vc=[r['wd'] for r in combo]
print(f" combo era judgeable n={len(vc)} mean {st.mean(vc):+.4f}% sd {st.stdev(vc):.4f}% min {min(vc):.3f}%")
# 2x-equivalent (leverage rescale)
v2=[r['wd']*2.0/r['lev'] for r in judge if r['lev']>0.2]
b4=[(r['day'],round(r['wd']*2.0/r['lev'],3)) for r in judge if r['lev']>0.2 and r['wd']*2.0/r['lev']<=-4.0]
b268=[(r['day'],round(r['wd']*2.0/r['lev'],3)) for r in judge if r['lev']>0.2 and r['wd']*2.0/r['lev']<=-2.68]
print(f" 2x-equivalent judgeable n={len(v2)} sd {st.stdev(v2):.4f}%  <=-4%: {b4}  <=-2.68%: {b268}")

# ---- per-anchor ----
recs=[]
for d in days:
    p=f'{root}/{d}/daily_nav.jsonl'
    if not os.path.exists(p): continue
    for r in [json.loads(l) for l in open(p) if l.strip()]:
        recs.append(dict(day=d,nav=float(r['nav']),flow=float(r.get('external_flow_usdt') or 0.0),
                         tg=float(r.get('target_gross') or 0.0)))
ser=[]
for i in range(1,len(recs)):
    a,b=recs[i-1],recs[i]
    dflow = (b['flow']-a['flow']) if b['day']==a['day'] else b['flow']
    ser.append(dict(day=b['day'], r=(b['nav']-dflow-a['nav'])/a['nav']*100, dflow=dflow,
                    lev=(b['tg']/b['nav'] if b['nav'] else 0.0)))
clean=[x for x in ser if abs(x['dflow'])<1e-6]
print("\n=== LIVE PER-ANCHOR EQUITY RETURNS ===")
for label,sel in [('all clean',clean),('combo >=0826',[x for x in clean if x['day']>='20260826']),
                  ('post-dep >=0903',[x for x in clean if x['day']>='20260903'])]:
    vv=[x['r'] for x in sel]
    lv=[x['lev'] for x in sel if x['lev']>0.2]
    gb=[x['r']*100/x['lev'] for x in sel if x['lev']>0.2]   # bps of gross per anchor
    print(f"{label}: n={len(vv)} mean={st.mean(vv):+.4f}% sd={st.stdev(vv):.4f}% | bps/gross mean={st.mean(gb):+.3f} sd={st.stdev(gb):.3f} | n(<=-40bps)={sum(1 for g in gb if g<=-40)} ({sum(1 for g in gb if g<=-40)/len(gb):.3%}) n(<=-80)={sum(1 for g in gb if g<=-80)}")

# variance ratio: daily var vs 6 x anchor var (combo era, clean, 2x only)
ca=[x['r'] for x in clean if x['day']>='20260826']
cd=[r['wd'] for r in judge if r['day']>='20260826']
vr=(st.stdev(cd)**2)/(6*st.stdev(ca)**2)
print(f"\nVARIANCE RATIO (combo era): daily var / (6 x anchor var) = {vr:.3f}  [1.0 = anchors serially uncorrelated within day]")
ca_all=[x['r'] for x in clean]; cd_all=[r['wd'] for r in judge]
print(f"VARIANCE RATIO (all clean):  {(st.stdev(cd_all)**2)/(6*st.stdev(ca_all)**2):.3f}")

# ---- backtest base rates (VERIFIED from giveback.json) ----
G=json.load(open('/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/allweather_2026-09-05/giveback_diag/results/giveback.json'))
print("\n=== BACKTEST BASE RATE (live-caliber replay, arm d30_n2_c42, L=2x) ===")
rows=[]
for s in ('s42','s2027'):
    m=G['base'][s]['metrics']
    for w in ('2024','2025','2026->08-30','2024->26'):
        mm=m[w]
        sd_anchor = mm['mean_bps_gross']/mm['sharpe']*math.sqrt(2190)
        rows.append((s,w,mm['n_days'],mm['days_le_200'],mm['days_le_268'],mm['days_le_400'],
                     mm['mean_bps_gross'],mm['sharpe'],sd_anchor, sd_anchor*2/1e4*100, sd_anchor*2/1e4*100*math.sqrt(6)))
print(f"{'seed':6s}{'win':14s}{'days':>6s}{'<=-2%':>7s}{'<=-2.68%':>9s}{'<=-4%':>7s}{'mean_bps':>9s}{'Sharpe':>8s}{'sd_bps/anc':>11s}{'sd%/anc@2x':>11s}{'sqrt6*sd%':>10s}")
for r in rows:
    print(f"{r[0]:6s}{r[1]:14s}{r[2]:6d}{r[3]:7d}{r[4]:9d}{r[5]:7d}{r[6]:9.3f}{r[7]:8.2f}{r[8]:11.2f}{r[9]:11.4f}{r[10]:10.4f}")

# ---- binomial tests ----
def binom_ge(k,n,p):
    # P(X>=k)
    tot=0.0
    for i in range(k,n+1):
        tot+=math.comb(n,i)*p**i*(1-p)**(n-i)
    return tot
n_live=len(judge)
print(f"\n=== BINOMIAL TEST: k breaches in n={n_live} judgeable live days ===")
for thr,k,label in [(-4.0,len(br4),'<=-4.0% (cond2 far-end stop)'),(-2.68,len(br268),'<=-2.68% (cond2 alert)'),(-2.0,len(br2),'<=-2.0%')]:
    print(f"\n-- {label}: observed k={k} --")
    for s in ('s42','s2027'):
        for w in ('2024->26','2026->08-30'):
            mm=G['base'][s]['metrics'][w]
            key={-4.0:'days_le_400',-2.68:'days_le_268',-2.0:'days_le_200'}[thr]
            x=mm[key]; nd=mm['n_days']; p=x/nd
            ex=p*n_live
            pv=binom_ge(k,n_live,p) if k>0 else 1.0
            # Jeffreys upper bound on p when x small
            print(f"   {s} {w:12s}: base {x}/{nd} = {p:.5f} ({p*365:.2f}/yr)  E[k]={ex:.3f}  P(X>={k})={pv:.4f}")
