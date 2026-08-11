import json,glob,zipfile,os,math,statistics,collections,datetime as dt,numpy as np
def secs(t):
    t=float(t); return t/1000.0 if t>1e12 else t
CL={}
for z in glob.glob('klines/*.zip')+glob.glob('k8/*.zip')+glob.glob('k8all/*.zip'):
    sym=os.path.basename(z).split('-1h-')[0]
    try:
        with zipfile.ZipFile(z) as zf:
            for line in zf.read(zf.namelist()[0]).decode().splitlines():
                p=line.split(',')
                if p and p[0] and p[0][0].isdigit(): CL.setdefault(sym,{})[int(p[0])//1000]=float(p[4])
    except Exception: pass
# 等权市场逐时收益(与面板同定义: 全名字横截面均值)
hours=sorted(set().union(*[set(v) for v in CL.values()]))
mkt={}
for i in range(1,len(hours)):
    t0,t1=hours[i-1],hours[i]
    if t1-t0!=3600: continue
    rs=[math.log(CL[s][t1]/CL[s][t0]) for s in CL if t0 in CL[s] and t1 in CL[s] and CL[s][t0]>0 and CL[s][t1]>0]
    if len(rs)>=40: mkt[t1]=sum(rs)/len(rs)     # ret1[t] 覆盖 [t, t+1h]
def leak(t):   # 面板行 t 的泄漏部分 = market[t+1 .. t+11]
    v=[mkt.get(t+k*3600) for k in range(1,12)]
    return None if any(x is None for x in v) else sum(v)
def causalpart(t):
    v=[mkt.get(t-k*3600) for k in range(0,13)]
    return None if any(x is None for x in v) else sum(v)
# betas (June only, 与探针 1b 同口径)
JUL1=1782950400
def hret(sym,t0,t1):
    c=CL.get(sym,{}); ks=sorted(c); out={}; prev=None
    for t in ks:
        if prev is not None and t0<=t<t1 and c[prev]>0 and c[t]>0: out[t]=math.log(c[t]/c[prev])
        prev=t
    return out
rb=hret('BTCUSDT',0,JUL1); B={}
for s in CL:
    r=hret(s,0,JUL1); ks=[t for t in r if t in rb]
    if len(ks)<200: continue
    n=len(ks); mx=sum(rb[t] for t in ks)/n; my=sum(r[t] for t in ks)/n
    sxx=sum((rb[t]-mx)**2 for t in ks)
    if sxx: B[s]=sum((rb[t]-mx)*(r[t]-my) for t in ks)/sxx
R=[]
for f in sorted(glob.glob('shadow/202607*/position_readback.jsonl')): R+=[json.loads(l) for l in open(f) if l.strip()]
pos=collections.defaultdict(dict)
for r in R: pos[int(secs(r['anchor_ts']))][r['symbol']]=float(r.get('venue_position_notional') or 0)
rows=[]
for t in sorted(pos):
    vals=[(s,v) for s,v in pos[t].items() if v and s in B]
    g=sum(abs(v) for _,v in vals)
    if g<=100: continue
    bbar=sum(abs(v)*B[s] for s,v in vals)/g
    disp=sum(v*(B[s]-bbar) for s,v in vals)
    lk=leak(t); cp=causalpart(t)
    if lk is None or cp is None: continue
    rows.append((t,disp,lk,cp,g))
print('影子期可用锚: %d'%len(rows))
def corr(x,y):
    n=len(x); mx=sum(x)/n; my=sum(y)/n
    num=sum((x[i]-mx)*(y[i]-my) for i in range(n))
    den=(sum((v-mx)**2 for v in x)*sum((v-my)**2 for v in y))**0.5
    return num/den if den else float('nan')
d=[r[1] for r in rows]; lk=[r[2] for r in rows]; cp=[r[3] for r in rows]
print()
print('=== 判别检验: 倾斜是否与【被泄漏的那个标量】共变? ===')
c1=corr(d,lk); c2=corr(d,cp)
n=len(rows)
t1=c1*math.sqrt((n-2)/max(1e-12,1-c1*c1)); t2=c2*math.sqrt((n-2)/max(1e-12,1-c2*c2))
print('  corr(disp_tilt, 泄漏项 sum market[t+1..t+11]) = %+.4f   t=%+.2f'%(c1,t1))
print('  corr(disp_tilt, 因果项 sum market[t-12..t])   = %+.4f   t=%+.2f'%(c2,t2))
print()
print('=== 持续性(静态暴露假说的证据) ===')
neg=sum(1 for x in d if x<0)
print('  倾斜为负的锚: %d/%d = %.1f%%   均值 %+.1f   sd %.1f'%(neg,n,100*neg/n,statistics.mean(d),statistics.stdev(d)))
print('  |均值|/sd = %.3f   (静态暴露 => 该比值大; 择时 => 接近 0)'%(abs(statistics.mean(d))/statistics.stdev(d)))

print()
print('=== 把探针 1b 的 +$699 拆成【静态暴露】与【时机】两部分 ===')
# r_btc 用收盘价对齐, 锚到下一锚(与 probe1b_v3 同口径)
ts_sorted=[r[0] for r in rows]
pnl_tot=0.0; pnl_static=0.0; pnl_timing=0.0; used=0
mbar=statistics.mean(d)
allt=sorted(pos)
nxt={allt[i]:allt[i+1] for i in range(len(allt)-1)}
for (t,disp,lk,cp,g) in rows:
    b=nxt.get(t)
    if b is None: continue
    a0=CL.get('BTCUSDT',{}).get(t); a1=CL.get('BTCUSDT',{}).get(b)
    if not a0 or not a1: continue
    r=a1/a0-1.0
    pnl_tot+=disp*r; pnl_static+=mbar*r; pnl_timing+=(disp-mbar)*r; used+=1
print('  可算区间 %d'%used)
print('  总离散倾斜盈亏        $%+9.2f'%pnl_tot)
print('    其中【静态暴露】部分 $%+9.2f  (= 平均倾斜 x 累计市场收益)'%pnl_static)
print('    其中【时机】部分     $%+9.2f  (= 逐锚偏离 x 该锚市场收益)'%pnl_timing)
print('  时机占比 %.0f%%'%(100*pnl_timing/pnl_tot if pnl_tot else float('nan')))
# 时机部分的显著性: 逐锚项的 bootstrap
import random
terms=[]
for (t,disp,lk,cp,g) in rows:
    b=nxt.get(t)
    if b is None: continue
    a0=CL.get('BTCUSDT',{}).get(t); a1=CL.get('BTCUSDT',{}).get(b)
    if a0 and a1: terms.append((disp-mbar)*(a1/a0-1.0))
random.seed(0)
bs=sorted(sum(terms[random.randrange(len(terms))] for _ in range(len(terms))) for _ in range(20000))
print('  时机部分 bootstrap 95%%CI [$%+.2f, $%+.2f]  排除 0? %s'%(bs[500],bs[19500],'是' if (bs[500]>0 or bs[19500]<0) else '否'))
