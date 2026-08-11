import json, glob, zipfile, os, collections, math, statistics, datetime as dt
def secs(t):
    t=float(t); return t/1000.0 if t>1e12 else t
def utc(t): return dt.datetime.fromtimestamp(secs(t),dt.timezone.utc).strftime('%Y-%m-%d')
# prices: both open and close per hour
OP,CL={},{}
for z in glob.glob('klines/*.zip')+glob.glob('k8/*.zip'):
    sym=os.path.basename(z).split('-1h-')[0]
    try:
        with zipfile.ZipFile(z) as zf:
            for line in zf.read(zf.namelist()[0]).decode().splitlines():
                p=line.split(',')
                if p and p[0] and p[0][0].isdigit():
                    OP.setdefault(sym,{})[int(p[0])//1000]=float(p[1])
                    CL.setdefault(sym,{})[int(p[0])//1000]=float(p[4])
    except Exception: pass
R=[]
for f in sorted(glob.glob('shadow/202607*/position_readback.jsonl')): R+=[json.loads(l) for l in open(f) if l.strip()]
pos=collections.defaultdict(dict)
for r in R: pos[int(secs(r['anchor_ts']))][r['symbol']]=float(r.get('venue_position_notional') or 0)
nav={}
for f in sorted(glob.glob('shadow/202607*/daily_nav.jsonl')):
    for l in open(f):
        if l.strip():
            r=json.loads(l); d=str(r['day']); nav['%s-%s-%s'%(d[:4],d[4:6],d[6:])]=r['realised_pnl']
ts=sorted(pos)
def book(mode):
    day=collections.defaultdict(float)
    for t in ts:
        s=0.0
        for sym,v in pos[t].items():
            if not v: continue
            if mode=='OPEN_t_to_t4':   a,b=OP.get(sym,{}).get(t),      OP.get(sym,{}).get(t+4*3600)
            elif mode=='CLOSE_t_to_t4':a,b=CL.get(sym,{}).get(t),      CL.get(sym,{}).get(t+4*3600)
            if a and b: s+=v*(b/a-1.0)
        day[utc(t)]+=s
    return day
print('%-22s %12s %12s %10s'%('口径','我的合计','系统合计','逐日corr'))
for mode in ('OPEN_t_to_t4','CLOSE_t_to_t4'):
    d=book(mode); ks=sorted(set(d)&set(nav))
    md=statistics.mean(d[k] for k in ks); mn=statistics.mean(nav[k] for k in ks)
    num=sum((d[k]-md)*(nav[k]-mn) for k in ks)
    den=(sum((d[k]-md)**2 for k in ks)*sum((nav[k]-mn)**2 for k in ks))**0.5
    print('%-22s %12.2f %12.2f %10.4f'%(mode,sum(d.values()),sum(nav.values()),num/den if den else float('nan')))
print()
d=book('CLOSE_t_to_t4'); ks=sorted(set(d)&set(nav))
print('逐日对照 (CLOSE 口径):')
print('  %-12s %10s %10s %8s'%('day','mine','system','diff'))
for k in ks: print('  %-12s %10.2f %10.2f %8.2f'%(k,d[k],nav[k],d[k]-nav[k]))
