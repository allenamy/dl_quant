# Controlled carry contrast: SAME rate model + SAME members mask, king weights vs deployed weights.
import json,os,numpy as np,datetime,bisect
WS='/Users/haosiyu/wide_shadow'
cfg=json.load(open(f'{WS}/shadow_bundle/config.json'))
syms=cfg['symbols_panel']; NW=len(syms); sidx={s:j for j,s in enumerate(syms)}
aux=json.load(open(f'{WS}/state/aux.json')); LT=aux['ledger_tail']
LTj={}
for s,rows in LT.items():
    j=sidx.get(s)
    if j is None: continue
    LTj[j]=(np.array([r[0] for r in rows]), np.array([r[1] for r in rows],float), np.array([r[2] for r in rows],float))
def fund_at(A):
    fn=np.zeros(NW); iv=np.full(NW,8.0); fresh=np.zeros(NW,bool)
    for j,(ts,rt,ivv) in LTj.items():
        i=bisect.bisect_right(ts,A)-1
        if i<0: continue
        if A-ts[i]>12*3600: continue
        fn[j]=rt[i]; iv[j]=ivv[i] if ivv[i]>0 else 8.0; fresh[j]=True
    return fn,iv,fresh
CE=1787716800
rows=[]
for f in sorted(os.listdir(f'{WS}/state/weights')):
    A=int(f.split('.')[0])
    if A<CE: continue
    tl=f'{WS}/state/target_live/{A}.json'
    if not os.path.exists(tl): continue
    w=np.load(f'{WS}/state/weights/{A}.npz')
    kv=np.zeros(NW); kv[w['idx'].astype(int)]=w['val'].astype(np.float64)
    mem=np.zeros(NW,bool); mem[w['members'].astype(int)]=True
    t=json.load(open(tl)); dv=np.zeros(NW)
    for s,x in t['weights'].items():
        j=sidx.get(s)
        if j is not None: dv[j]=float(x)
    fn,iv,fresh=fund_at(A)
    c=fn*(4.0/iv)
    ck=float((kv*mem*c).sum()*1e4); cd=float((dv*mem*c).sum()*1e4)
    gk=float(np.abs(kv).sum()); gd=float(np.abs(dv).sum())
    rows.append(dict(A=A,utc=datetime.datetime.utcfromtimestamp(A).strftime('%Y-%m-%dT%H:%MZ'),
        carry_king=ck,carry_dep=cd,gk=gk,gd=gd,
        pu_king=ck/gk,pu_dep=cd/gd,producer=t.get('producer','')[:20],
        kout=float(np.abs(kv*(~mem)).sum()),dout=float(np.abs(dv*(~mem)).sum())))
json.dump(rows,open(os.path.dirname(os.path.abspath(__file__))+'/r6_carry.json','w'),indent=1)
def m(x): return sum(x)/len(x)
def sd(x):
    mu=m(x); return (sum((a-mu)**2 for a in x)/(len(x)-1))**.5
print('n',len(rows))
print('raw carry king',round(m([r['carry_king'] for r in rows]),4),' dep',round(m([r['carry_dep'] for r in rows]),4))
print('PER-UNIT carry king',round(m([r['pu_king'] for r in rows]),4),' dep',round(m([r['pu_dep'] for r in rows]),4))
dd=[r['pu_king']-r['pu_dep'] for r in rows]
print('per-unit carry diff (king-dep) mean',round(m(dd),4),'sd',round(sd(dd),4),'t',round(m(dd)/(sd(dd)/len(dd)**.5),2))
print('gross_norm king',round(m([r['gk'] for r in rows]),4),'dep',round(m([r['gd'] for r in rows]),4))
print('weight outside members: king',round(m([r['kout'] for r in rows]),5),'dep',round(m([r['dout'] for r in rows]),5))
# compare recomputed king carry to LOGGED carry
log={}
for ln in open(f'{WS}/shadow_log.jsonl'):
    try: d=json.loads(ln)
    except: continue
    if d.get('e')=='score': log[int(d['anchor_ts'])]=d
pairs=[(r['carry_king'],log[r['A']]['carry_bps']) for r in rows if r['A'] in log]
print('king carry recomp vs logged: n',len(pairs),'mean recomp',round(m([a for a,b in pairs]),4),'mean logged',round(m([b for a,b in pairs]),4),
      'max|d|',round(max(abs(a-b) for a,b in pairs),4))
