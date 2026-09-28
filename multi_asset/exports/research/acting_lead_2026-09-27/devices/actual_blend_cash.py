"""Algebraic contributions of two smoothed mixed sleeves; never pure-model attribution."""
import collections
import hashlib
import io
import json
import math
from pathlib import Path
import sys
import time
import zipfile
import numpy as np

PARTS=('kc','fc','export','clamp')
ZIP_SHA='d6c793dab6174f4d2f81636e655c9cf5f271a426fe09e89c1d408c6c2666e09a'
CENSUS_SHA='013971851550b68371f196ba5f2b604f3b0b66c9a4b4e2b1c8fa01d09779d8dc'
PARENT_SHA='176da1b8183d4f1500e6c4162853341d540fb620fa5c7d1ce2f011d926a28b64'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def finite(x):return type(x) in (float,int) and math.isfinite(x)
def put(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')

def read_state(raw,anchor,symbols):
    with np.load(io.BytesIO(raw),allow_pickle=False) as d:
        a,idx,val=d['anchor'],d['idx'],d['val']
        if a.size!=1 or a.dtype.kind not in 'iu' or int(a.reshape(-1)[0])!=anchor:raise ValueError('state_anchor')
        if idx.ndim!=1 or val.shape!=idx.shape or idx.dtype.kind not in 'iu':raise ValueError('state_shape')
        if len(set(map(int,idx)))!=len(idx) or np.any(idx<0) or np.any(idx>=len(symbols)):raise ValueError('state_index')
        if not np.isfinite(val).all():raise ValueError('state_nonfinite')
        return {symbols[int(i)]:float(v) for i,v in zip(idx,val)}

def allocate(kc,fc,raw,gross,norm,removed,forced,clamped,recorded):
    if not finite(gross) or not finite(norm) or gross<=0 or norm<=0:raise ValueError('scale')
    if not raw or any(not finite(v) for d in (kc,fc,raw,recorded) for v in d.values()):raise ValueError('population_or_finite')
    error=max(abs(raw.get(s,0)-.55*kc.get(s,0)-.45*fc.get(s,0)) for s in set(raw)|set(kc)|set(fc))
    if error>1e-8:raise ValueError('mixed_state_target_mismatch')
    if len(set(removed))!=len(removed) or not set(forced)<=set(removed):raise ValueError('removed_schema')
    active=sorted(set(raw)-set(removed))
    if not active:raise ValueError('no_active_names')
    if set(recorded)-set(active)-set(forced)-set(clamped):raise ValueError('recorded_population')
    if set(active)-set(recorded):raise ValueError('active_target_missing')
    initial={s:{'kc':.55*kc.get(s,0)*gross/norm,'fc':.45*fc.get(s,0)*gross/norm} for s in active}
    for s in active:initial[s]['export']=raw[s]*gross/norm-initial[s]['kc']-initial[s]['fc']
    means={k:math.fsum(initial[s][k] for s in active)/len(active) for k in ('kc','fc','export')}
    combined={s:raw[s]*gross/norm for s in active};mean=math.fsum(combined.values())/len(active)
    denom=math.fsum(abs(v-mean) for v in combined.values())
    if denom<=0:raise ValueError('zero_reshape_gross')
    scale=gross/denom;components={};maxoutside=0
    for s,v in recorded.items():
        p={k:(initial[s][k]-means[k])*scale if s in initial else 0.0 for k in ('kc','fc','export')}
        difference=v-math.fsum(p.values())
        if s not in clamped:
            maxoutside=max(maxoutside,abs(difference))
            if abs(difference)>1e-6:raise ValueError('unlisted_post_reshape_difference:'+s)
            p['clamp']=0.0
        else:p['clamp']=difference
        if abs(math.fsum(p.values())-v)>1e-6:raise ValueError('final_target_identity')
        components[s]=p
    return {'components':components,'raw_max_abs':error,'scale':scale,'active_names':len(active),
            'max_unlisted_difference_usdt':maxoutside,'clamped':clamped}

def value_components(parts,p0,p1):
    if set(parts)!=set(PARTS) or any(not finite(v) for v in parts.values()):raise ValueError('component_schema')
    if not any(v!=0 for v in parts.values()):return {'verdict':'PRICED','values':dict.fromkeys(PARTS,0.0)}
    if not finite(p0) or not finite(p1) or p0<=0 or p1<=0:return {'verdict':'COMPONENT_UNPRICED','values':None}
    return {'verdict':'PRICED','values':{k:v*(p1/p0-1) for k,v in parts.items()}}

def run(zip_path,census,parent_path,out):
    if sha(zip_path)!=ZIP_SHA or sha(census/'RESULT.json')!=CENSUS_SHA or sha(parent_path)!=PARENT_SHA:raise ValueError('input_identity')
    cm=json.loads((census/'RESULT.json').read_bytes());parent=json.loads(parent_path.read_bytes())
    for n,h in cm['outputs'].items():
        if sha(census/n)!=h:raise ValueError('census_member_changed:'+n)
    anchors=[x for p in census.glob('*_anchors.json') for x in json.loads(p.read_bytes())]
    orders=[x for p in census.glob('*_orders.json') for x in json.loads(p.read_bytes())]
    phases=json.loads((census/'PHASES.json').read_bytes());mapped={};members={}
    with zipfile.ZipFile(zip_path) as z:
        symbols=json.loads(z.read('shadow_bundle/config.json'))['symbols_panel']
        if len(set(symbols))!=len(symbols) or not all(isinstance(s,str) and s for s in symbols):raise ValueError('symbol_axis')
        for c in cm['rows']:
            a=c['anchor'];files=[f'fea171/state_H_{leg}_{a}.npz' for leg in ('kc','fc')]
            bs=[z.read(n) for n in files]
            for name,b in zip(files,bs):members[name]=hashlib.sha256(b).hexdigest()
            kc,fc=[read_state(b,a,symbols) for b in bs];doc=json.loads(z.read(f'state/target_live/{a}.json'))
            if hashlib.sha256(z.read(f'state/target_live/{a}.json')).hexdigest()!=c['consumed_target_sha256']:raise ValueError('target_consumed')
            ar=[x for x in anchors if x['rebalance_id']==c['rid']];pa=[x['data'] for x in phases if x['phase']=='A' and x['data'].get('rebalance_id')==c['rid']]
            if len(ar)!=1 or len(pa)!=1:raise ValueError('decision_identity')
            ar=ar[0];rs=ar['reshape'];p=pa[0]
            if rs['redemean_applied'] is not True or rs['rescale_applied'] is not True:raise ValueError('reshape_policy')
            if len(rs['removed_names'])!=rs['n_removed']:raise ValueError('removed_count')
            if any(p['venue_cap_clamp'].get(k) for k in ('capped','error','invalid')):raise ValueError('cap_unmodelled')
            targets={}
            for x in orders:
                if x['rebalance_id']!=c['rid']:continue
                v=x['target_w']*ar['target_gross'];s=x['symbol']
                if s in targets and targets[s]!=v:raise ValueError('target_conflict')
                targets[s]=v
            m=allocate(kc,fc,doc['weights'],p['sizing']['gross'],ar['external_book']['gross_norm'],rs['removed_names'],rs['forced_flat_names'],rs['clamped_after_reshape']['names'],targets)
            m['halted_start']=c['opening_halted'];mapped[a]=m
    windows=[];grouped=collections.defaultdict(list)
    for w in parent['windows']:
        m=mapped[w['anchor_from']];rows=[]
        for old in w['pieces']:
            s=old['symbol'];components=m['components'].get(s,dict.fromkeys(PARTS,0.0))
            if abs(math.fsum(components.values())-old['target_notional'])>1e-6:raise ValueError('parent_target_identity')
            row={'symbol':s,'parent_status':old['verdict'],'parent_benchmark':old['benchmark'],'notional_components':components}
            if old['verdict']!='PRICED':row.update(verdict='PARENT_UNPRICED',values=None)
            elif m['halted_start']:row.update(verdict='POLICY_HOLD',values=dict(dict.fromkeys(PARTS,0.0),policy_hold=old['benchmark']))
            else:
                row.update(value_components(components,old['start_mark'],old['end_mark']))
                if row['values'] is not None and abs(math.fsum(row['values'].values())-old['benchmark'])>1e-7:raise ValueError('priced_identity')
            rows.append(row)
        ready=[r for r in rows if r['values'] is not None]
        total={k:math.fsum(r['values'].get(k,0) for r in ready) for k in PARTS+('policy_hold',)}
        outw={'anchor_from':w['anchor_from'],'anchor_to':w['anchor_to'],'period':w['period'],'halted_start':m['halted_start'],
              'counts':dict(collections.Counter(r['verdict'] for r in rows)),'priced_contribution':total,
              'same_population_parent_benchmark':math.fsum(r['parent_benchmark'] for r in ready),'rows':rows}
        if abs(math.fsum(total.values())-outw['same_population_parent_benchmark'])>1e-7:raise ValueError('window_identity')
        windows.append(outw);grouped[w['period']].append(outw)
    summary={g:{'counts':dict(sum((collections.Counter(w['counts']) for w in ws),collections.Counter())),
         'priced_contribution':{k:math.fsum(w['priced_contribution'][k] for w in ws) for k in PARTS+('policy_hold',)},
         'same_population_parent_benchmark':math.fsum(w['same_population_parent_benchmark'] for w in ws)} for g,ws in grouped.items()}
    result={'utc':time.strftime('%FT%TZ',time.gmtime()),'scope':'actual mixed-sleeve accounting contribution only, not pure King/F10/funding causal attribution',
       'input_sha256':{str(zip_path):ZIP_SHA,str(census/'RESULT.json'):CENSUS_SHA,str(parent_path):PARENT_SHA},
       'source_sha256':sha(__file__),'numpy':np.__version__,'python':sys.executable,'state_member_sha256':members,
       'mapped':mapped,'windows':windows,'summary':summary,'limits':['each half includes funding, nonlinear state and FTRIM',
       'shared reshape scale is frozen to actual full book; not sleeve-removal counterfactual','missing component marks remain unknown even if their total cancels',
       'static post-snapshot mark benchmark excludes fees/carry and intra-window policy changes; not full strategy performance']}
    out.mkdir(exist_ok=False);put(out/'RESULT.json',result);print(json.dumps({'summary':summary,'sha256':sha(out/'RESULT.json')},indent=2))

if __name__=='__main__':run(*map(Path,sys.argv[1:]))
