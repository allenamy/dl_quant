"""Independent Decimal mapping from archived states, original decisions and pinned price parent."""
from decimal import Decimal as D
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile
import numpy as np

def verify(result_path,out):
    result=json.loads(result_path.read_bytes());paths=list(result['input_sha256'])
    for name,h in result['input_sha256'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h
    archive,census_file,parent_file=map(Path,paths);census=census_file.parent;cm=json.loads(census_file.read_bytes());parent=json.loads(parent_file.read_bytes())
    for name,h in cm['outputs'].items():assert hashlib.sha256((census/name).read_bytes()).hexdigest()==h
    aa=[x for p in census.glob('*_anchors.json') for x in json.loads(p.read_bytes())];oo=[x for p in census.glob('*_orders.json') for x in json.loads(p.read_bytes())];ph=json.loads((census/'PHASES.json').read_bytes())
    maps={};checks=0;maximum=0.0
    def check(a,b):
        nonlocal checks,maximum
        err=abs(float(a)-float(b));maximum=max(maximum,err);checks+=1;assert err<1e-7,(a,b,err)
    with zipfile.ZipFile(archive) as z:
        symbols=json.loads(z.read('shadow_bundle/config.json'))['symbols_panel']
        for c in cm['rows']:
            a=c['anchor'];model=result['mapped'][str(a)];states=[]
            for leg in ('kc','fc'):
                name=f'fea171/state_H_{leg}_{a}.npz';raw=z.read(name);assert hashlib.sha256(raw).hexdigest()==result['state_member_sha256'][name]
                with np.load(io.BytesIO(raw),allow_pickle=False) as n:states.append({symbols[int(i)]:D(str(float(v))) for i,v in zip(n['idx'],n['val'])})
            ar=next(x for x in aa if x['rebalance_id']==c['rid']);pa=next(x['data'] for x in ph if x['phase']=='A' and x['data'].get('rebalance_id')==c['rid']);rs=ar['reshape']
            raw=json.loads(z.read(f'state/target_live/{a}.json'))['weights'];active=sorted(set(raw)-set(rs['removed_names']));g=D(str(pa['sizing']['gross']));norm=D(str(ar['external_book']['gross_norm']))
            source={s:{'kc':D('.55')*states[0].get(s,D(0))*g/norm,'fc':D('.45')*states[1].get(s,D(0))*g/norm} for s in active}
            for s in active:source[s]['export']=D(str(raw[s]))*g/norm-source[s]['kc']-source[s]['fc']
            avg={k:sum((v[k] for v in source.values()),D(0))/len(active) for k in ('kc','fc','export')}
            total={s:sum(v.values(),D(0)) for s,v in source.items()};center=sum(total.values(),D(0))/len(active);scale=g/sum((abs(v-center) for v in total.values()),D(0))
            check(scale,model['scale']);recorded={}
            for order in oo:
                if order['rebalance_id']==c['rid']:recorded[order['symbol']]=D(str(order['target_w']))*D(str(ar['target_gross']))
            maps[a]={}
            for s,v in recorded.items():
                pieces={k:(source[s][k]-avg[k])*scale if s in source else D(0) for k in ('kc','fc','export')}
                gap=v-sum(pieces.values(),D(0));pieces['clamp']=gap if s in rs['clamped_after_reshape']['names'] else D(0)
                if s not in rs['clamped_after_reshape']['names']:assert abs(gap)<D('.000001')
                for k,n in pieces.items():check(n,model['components'][s][k])
                check(sum(pieces.values(),D(0)),v);maps[a][s]=pieces
    for w in result['windows']:
        pw=next(x for x in parent['windows'] if x['anchor_from']==w['anchor_from']);prices={p['symbol']:p for p in pw['pieces']};totals={k:D(0) for k in ('kc','fc','export','clamp','policy_hold')}
        for row in w['rows']:
            p=prices[row['symbol']];comp=maps[w['anchor_from']].get(row['symbol'],dict.fromkeys(('kc','fc','export','clamp'),D(0)))
            if p['verdict']!='PRICED':assert row['verdict']=='PARENT_UNPRICED';continue
            if w['halted_start']:assert row['verdict']=='POLICY_HOLD';totals['policy_hold']+=D(str(p['benchmark']));continue
            if any(comp.values()) and (p['start_mark'] is None or p['end_mark'] is None):assert row['verdict']=='COMPONENT_UNPRICED';checks+=1;continue
            ret=D(str(p['end_mark']))/D(str(p['start_mark']))-1 if any(comp.values()) else D(0)
            for k,v in comp.items():check(v*ret,row['values'][k]);totals[k]+=v*ret
        for k,v in totals.items():check(v,w['priced_contribution'][k])
        check(sum(totals.values(),D(0)),w['same_population_parent_benchmark'])
    receipt={'verdict':'PASS','checks':checks,'max_arithmetic_delta':maximum,
      'result_sha256':hashlib.sha256(result_path.read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      'method':'no analyzer imports; raw archive H states and original decision targets; Decimal shared transform; marks from pinned previously-verified parent'}
    out.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))

if __name__=='__main__':verify(*map(Path,sys.argv[1:]))
