"""probe 1b v3 — shadow dispersion PnL recomputed with CLOSE-aligned returns (Y4 convention)."""
import os, math, statistics, random, json, glob, zipfile, collections, datetime as dt
def secs(t):
    t=float(t); return t/1000.0 if t>1e12 else t
def utc(t): return dt.datetime.fromtimestamp(secs(t),dt.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')
CL={}
for z in glob.glob('klines/*.zip')+glob.glob('k8/*.zip'):
    sym=os.path.basename(z).split('-1h-')[0]
    try:
        with zipfile.ZipFile(z) as zf:
            for line in zf.read(zf.namelist()[0]).decode().splitlines():
                p=line.split(',')
                if p and p[0] and p[0][0].isdigit(): CL.setdefault(sym,{})[int(p[0])//1000]=float(p[4])
    except Exception: pass
JUL1=1782950400
def hret(sym,t0,t1):
    c=CL.get(sym,{}); ks=sorted(c); out={}; prev=None
    for t in ks:
        if prev is not None and (t0 is None or t>=t0) and (t1 is None or t<t1) and c[prev]>0 and c[t]>0:
            out[t]=math.log(c[t]/c[prev])
        prev=t
    return out
def betas(t0,t1):
    rb=hret('BTCUSDT',t0,t1); out={}
    for s in CL:
        r=hret(s,t0,t1); ks=[t for t in r if t in rb]
        if len(ks)<200: continue
        n=len(ks); mx=sum(rb[t] for t in ks)/n; my=sum(r[t] for t in ks)/n
        sxx=sum((rb[t]-mx)**2 for t in ks)
        if sxx: out[s]=sum((rb[t]-mx)*(r[t]-my) for t in ks)/sxx
    return out
B=betas(None,JUL1)
R=[]
for f in sorted(glob.glob('shadow/202607*/position_readback.jsonl')): R+=[json.loads(l) for l in open(f) if l.strip()]
pos=collections.defaultdict(dict)
for r in R: pos[int(secs(r['anchor_ts']))][r['symbol']]=float(r.get('venue_position_notional') or 0)
ts=sorted(pos)
def series(BETA):
    out=[]
    for t in ts:
        a,b=CL.get('BTCUSDT',{}).get(t), CL.get('BTCUSDT',{}).get(t+4*3600)
        if not a or not b: continue
        rbtc=b/a-1.0
        vals=[(s,v) for s,v in pos[t].items() if v and s in BETA]
        g=sum(abs(v) for _,v in vals)
        if g<=100: continue
        bbar=sum(abs(v)*BETA[s] for s,v in vals)/g
        out.append((sum(v*(BETA[s]-bbar) for s,v in vals)*rbtc, g, sum(v*(BETA[s]-bbar) for s,v in vals)))
    return out
S=series(B)
pn=[x for x,_,_ in S]; g=statistics.median(gg for _,gg,_ in S)
print('CLOSE-aligned (Y4 convention), shadow: intervals %d  median beta-covered gross $%.0f'%(len(pn),g))
print('  CUMULATIVE dispersion PnL $%+.2f  (%+.2f bps of gross)'%(sum(pn),1e4*sum(pn)/g))
random.seed(0)
bs=sorted(sum(pn[random.randrange(len(pn))] for _ in range(len(pn))) for _ in range(20000))
print('  bootstrap 95%%CI [$%+.2f, $%+.2f] -> excludes 0? %s'%(bs[500],bs[19500],'YES' if (bs[500]>0 or bs[19500]<0) else 'NO'))
print('  disp tilt negative at %d/%d'%(sum(1 for _,_,d in S if d<0),len(S)))
# placebo
syms=sorted(B); vals=[B[s] for s in syms]; real=sum(pn)
random.seed(0); null=[]
for _ in range(2000):
    sh=vals[:]; random.shuffle(sh)
    null.append(sum(x for x,_,_ in series(dict(zip(syms,sh)))))
null.sort(); ge=sum(1 for x in null if abs(x)>=abs(real))
print('  placebo: null sd $%.2f  p(|null|>=|real|)=%.4f'%(statistics.stdev(null),ge/len(null)))
print()
print('对照 v2(OPEN 对齐, 差 1 小时): 累计 +$567.23, CI [+221.75, +931.63]')
