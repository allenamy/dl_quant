# INDEPENDENT replica of shadow_loop_v3.run_anchor score block (L425-445), READ-ONLY.
import json, glob, os, numpy as np, datetime
WS='/Users/haosiyu/wide_shadow'
cfg=json.load(open(f'{WS}/shadow_bundle/config.json'))
syms=cfg['symbols_panel']; NW=len(syms); sidx={s:j for j,s in enumerate(syms)}
z=np.load(f'{WS}/state/rolling.npz',allow_pickle=True)
cts=z['ts'].astype(np.int64); CD=z['data'].astype(np.float16).astype(np.float32)
row_of={int(t):i for i,t in enumerate(cts)}
print('panel NW',NW,'cache rows',len(cts),'first',datetime.datetime.utcfromtimestamp(int(cts[0])).isoformat(),'last',datetime.datetime.utcfromtimestamp(int(cts[-1])).isoformat())

def y4(prev_a, a):
    pi=row_of.get(int(prev_a)); ai=row_of.get(int(a))
    if pi is None or ai is None: return None
    seg=CD[pi+1:ai+1,:,0]
    fin=np.isfinite(seg)
    v=np.where(fin,seg,0).sum(0)
    v[fin.sum(0)<46]=np.nan
    return v

# logged
log={}
for ln in open(f'{WS}/shadow_log.jsonl'):
    ln=ln.strip()
    if not ln: continue
    try: d=json.loads(ln)
    except: continue
    if d.get('e')=='score': log[int(d['anchor_ts'])]=d

out=[]
for A in sorted(log):
    W=f'{WS}/state/weights/{A}.npz'
    if not os.path.exists(W): continue
    yv=y4(A, A+14400)
    if yv is None: continue
    w=np.load(W); idx=w['idx'].astype(int); val=w['val'].astype(np.float64)
    g=float((val*np.nan_to_num(yv[idx],nan=0.0)).sum()*1e4)
    gn=float(np.abs(val).sum())
    netw=float(val.sum())
    # deployed target_live
    tl=f'{WS}/state/target_live/{A}.json'
    dg=dgn=dnw=None; prod=None; cos=l1=None; nmiss=None
    if os.path.exists(tl):
        t=json.load(open(tl)); prod=t.get('producer','')
        dv=np.zeros(NW); miss=0
        for s,x in t['weights'].items():
            j=sidx.get(s)
            if j is None: miss+=1; continue
            dv[j]=float(x)
        dgn=float(np.abs(dv).sum()); dnw=float(dv.sum())
        dg=float((dv*np.nan_to_num(yv,nan=0.0)).sum()*1e4)
        kv=np.zeros(NW); kv[idx]=val
        cos=float(kv@dv/((np.linalg.norm(kv)*np.linalg.norm(dv))+1e-18))
        l1=float(np.abs(kv-dv).sum()); nmiss=miss
    out.append(dict(A=A,utc=datetime.datetime.utcfromtimestamp(A).strftime('%Y-%m-%dT%H:%MZ'),
        logged_gross=log[A]['gross_bps'],logged_net=log[A]['net_bps'],carry=log[A]['carry_bps'],cost=log[A]['cost_bps'],
        repro=g,king_gn=gn,king_netw=netw,dep_gross=dg,dep_gn=dgn,dep_netw=dnw,producer=prod,cos=cos,l1=l1,miss=nmiss))
json.dump(out,open(os.path.dirname(os.path.abspath(__file__))+'/r6_recon.json','w'),indent=1)
d=[abs(r['repro']-r['logged_gross']) for r in out]
print('replica n',len(out),'max|diff|',max(d),'mean',sum(d)/len(d))
