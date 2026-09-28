"""Read-only fixed-population diagnostics; no execution arm fields or venue calls."""
import ast, hashlib, io, json, math, pathlib, sys
import numpy as np

A = 1790524800
WS = pathlib.Path('/Users/haosiyu/wide_shadow')
ROOT = pathlib.Path(__file__).resolve().parents[1]
sources = {}

def raw(p):
    p = pathlib.Path(p); b = p.read_bytes()
    sources[str(p)] = hashlib.sha256(b).hexdigest()
    return b

def js(p): return json.loads(raw(p))

def nz(p):
    with np.load(io.BytesIO(raw(p)), allow_pickle=True) as f:
        return {k: f[k] for k in f.files}

def extracted(p, name, namespace):
    tree = ast.parse(raw(p)); nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name]
    assert len(nodes) == 1, (p, name)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(p), 'exec'), namespace)
    return namespace[name]

def state(branch, anchor, n):
    z = nz(WS/f'fea171/state_H_{branch}_{anchor}.npz')
    assert int(z['anchor']) == anchor
    idx=z['idx'].astype(int); val=z['val'].astype(float)
    assert len(set(idx))==len(idx) and np.all((idx>=0)&(idx<n)) and np.isfinite(val).all()
    r=np.zeros(n);r[idx]=val;return r

def sign(x): return 'unknown' if x is None or not math.isfinite(x) else 'negative' if x<0 else 'positive' if x>0 else 'zero'

def aggregate(rows, key):
    out={}
    for r in rows:
        k=str(r[key]); v=out.setdefault(k,{'n':0,'price_pnl_usdt':0.,'initial_gross_usdt':0.,'negative_pnl_n':0})
        v['n']+=1;v['price_pnl_usdt']+=r['price_pnl_usdt'];v['initial_gross_usdt']+=r['initial_gross'];v['negative_pnl_n']+=int(r['price_pnl_usdt']<0)
    return out

def main(out):
    loss=js(ROOT/'receipts/LATEST_LOSS_20260928/POOLED_PRICE_BRIDGE.json')
    assert loss['read_ts']==[1790527671.2659872,1790541956.391472]
    assert len(loss['rows'])==309 and not loss['unresolved'] and loss['group']['short']['n']==155
    snap=WS/f'state/snap/{A}'; aux=js(snap/'aux.json'); gen=js(snap/'generation.json')
    assert gen['anchor_ts']==aux['last_anchor']==aux['prev_rec']['anchor_ts']==A
    assert gen['files']['aux.json']['sha256']==sources[str(snap/'aux.json')]
    cfg=js(WS/'shadow_bundle/config.json'); axes=nz(WS/'fea171/xfer_syms.npz'); sy=[str(x) for x in axes['symbols']]
    assert sy==cfg['symbols_panel'] and len(set(sy))==len(sy)
    n=len(sy); col={s:j for j,s in enumerate(sy)};pr=aux['prev_rec'];pm=np.array(pr['members'],int)
    assert len(set(pm))==len(pm) and np.all((pm>=0)&(pm<n))
    pos={sy[int(j)]:i for i,j in enumerate(pm)}
    kc=state('kc',A,n);fc=state('fc',A,n);oldkc=state('kc',A-14400,n);oldfc=state('fc',A-14400,n)
    live=js(WS/f'state/target_live/{A}.json');combo=js(WS/f'state/target_combo/{A}.json')
    assert live['anchor_ts']==combo['anchor_ts']==A and combo['kc_state_source']==combo['fc_state_source']=='own'
    mix=.55*kc+.45*fc; actual=np.zeros(n)
    for s,w in live['weights'].items(): actual[col[s]]=w
    err=float(np.max(np.abs(mix-actual)));assert err<1e-15, ('combo state mismatch',err)
    fundpath=WS/'fea171/nc_contract.py'; ftree=ast.parse(raw(fundpath))
    const={}
    for node in ftree.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='FRESH_S' for t in node.targets):
            const['FRESH_S']=eval(compile(ast.Expression(node.value),str(fundpath),'eval'),{'__builtins__':{}})
    fns={'math':math,**const,'ContractError':ValueError}
    fund=extracted(fundpath,'funding_asof',fns)
    rates={}
    for s in sy:
        ledger=aux['ledger_tail'].get(s,[])
        rates[s]=fund(aux['ema'].get(s),ledger[-1] if ledger else None,A)
    w3=np.array(combo['w3_masked'],float)
    lr=js(snap/'leg_returns_live.json');assert sources[str(snap/'leg_returns_live.json')]==gen['files']['leg_returns_live.json']['sha256']
    look=cfg['params']['msharpe_look'];r=np.stack([np.asarray(lr[k][-look:],float) for k in ['king','rev24','fund']])
    assert r.shape==(3,look) and np.isfinite(r).all()
    sh=np.maximum(r.mean(1)/(r.std(1)+1e-9),0);w=sh/sh.sum() if sh.sum()>0 else np.ones(3)/3
    wm=np.array([w[0],0,w[2]]);wm=wm/wm.sum() if wm.sum()>1e-12 else np.array([.5,0,.5])
    assert np.allclose(wm,w3,atol=5.1e-7,rtol=0), 'seat identity'
    kz=np.array(pr['legz']['king'],float);fz=np.array(pr['legz']['fund'],float)
    assert kz.shape==fz.shape==(len(pm),)
    z=wm[0]*np.nan_to_num(kz)+wm[2]*np.nan_to_num(fz)
    rn8=np.array([rates[sy[j]][3] for j in pm]);trim=(z<0)&np.isfinite(rn8)&(rn8<=-.001)
    sel=np.zeros(len(pm),bool);sel[np.array(pr['sel_idx'],int)]=True
    env={'np':np,'sel':sel,'P':cfg['params'],'NW':n,'pm':pm,'H':oldkc,'LIVE_MASK':np.array([s in set(live['universe']) for s in sy])}
    chain=extracted(WS/'fea171/combo_stage.py','chain',env)
    reconstructed=chain(np.where(trim,0,z));kc_err=float(np.max(np.abs(reconstructed-kc)))
    assert kc_err<1e-15, ('kc source replay mismatch',kc_err)
    # Fresh target is a diagnostic of this SAME snapshot. It is not a proposed strategy.
    pre=np.where(sel,np.where(trim,0,z),0.);pre=np.where(sel,pre-(pre[sel].mean() if sel.any() else 0),pre)
    pre/=abs(pre).sum();pre=np.clip(pre,-cfg['params']['cap_mult']/max(sel.sum(),1),cfg['params']['cap_mult']/max(sel.sum(),1));pre/=abs(pre).sum()
    rows=[]
    for item in loss['rows']:
        row=dict(item);s=row['symbol'];j=col.get(s);i=pos.get(s)
        assert j is not None, ('loss symbol absent from axis',s)
        fe,fn,iv,rr=rates[s]
        row.update(member=i is not None,fund_ema=fe if math.isfinite(fe) else None,latest_rate=fn if math.isfinite(fn) else None,
                   interval_h=iv if math.isfinite(iv) else None,rn8=rr if math.isfinite(rr) else None,
                   king_z=float(kz[i]) if i is not None and math.isfinite(kz[i]) else None,
                   fund_z=float(fz[i]) if i is not None and math.isfinite(fz[i]) else None,
                   kc_previous=float(oldkc[j]),kc_current=float(kc[j]),fc_previous=float(oldfc[j]),fc_current=float(fc[j]),
                   kc_unchanged=bool(kc[j]==oldkc[j]),fc_unchanged=bool(fc[j]==oldfc[j]),
                   kc_fresh_target=float(pre[i]) if i is not None else None,kc_ftrim=bool(trim[i]) if i is not None else None,
                   producer_weight=float(actual[j]),ledger_last_ts=aux['ledger_tail'].get(s,[[None]])[-1][0])
        row.update(signal_sign_pair='king_'+sign(row['king_z'])+'__fund_'+sign(row['fund_z']),
                   latest_rate_sign=sign(row['rn8']),ema_sign=sign(row['fund_ema']),
                   kc_fresh_sign=sign(row['kc_fresh_target']),kc_current_sign=sign(row['kc_current']),fc_current_sign=sign(row['fc_current']))
        rows.append(row)
    by={}
    for population in ['all','short','long']:
        rr=rows if population=='all' else [x for x in rows if x['initial_side']==population]
        by[population]={k:aggregate(rr,k) for k in ['member','signal_sign_pair','latest_rate_sign','ema_sign','kc_unchanged','fc_unchanged','kc_fresh_sign','kc_current_sign','fc_current_sign','kc_ftrim']}
    result={'scope':'post hoc same-population descriptive signal/state bridge; not causal leg PnL','anchor':A,
            'plan_commit':'7ff1d6429','seats':wm.tolist(),'gates':{'combo_state_max_abs':err,'kc_source_replay_max_abs':kc_err},
            'unavailable':['per-name F10 scores: historical mini/parity sandbox not retained; do not infer from fc weights',
                           'raw sign is not independent contribution after centering/capping/state/execution',
                           'latest EMA vs rate compares different filters, not proof of stale data'],
            'source_sha256':sources,'summary':by,'rows':rows}
    for p,h in sources.items():assert hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==h,('source changed',p)
    result['device_sha256']=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
    with pathlib.Path(out).open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({'gates':result['gates'],'seats':result['seats'],'short':by['short']},indent=2))

if __name__=='__main__':main(sys.argv[1])
