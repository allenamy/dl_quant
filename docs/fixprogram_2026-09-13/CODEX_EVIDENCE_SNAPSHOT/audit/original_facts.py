"""Read fixed raw price/funding facts; no cash or execution Engine imports."""
from batch_contract import *
import csv,io,zipfile,datetime as dt

def source_files(original_pins, watched):
    """Direct consumed inputs only. Native parent manifest binds full ancestry."""
    need(all(watched.get(p)==h for p,h in original_pins.items()),'original INPUT_PINS subset of native watched files')
    out={}
    def take(path):
        need(path in original_pins,'original consumed source absent from exact native closure '+path)
        pin(path,out,original_pins[path]);return read(path) if path.endswith('.json') else Path(path)
    binding=read(BATCH/'INPUT_BINDING.json');cfg=binding['cfg']
    roles={k:cfg[k] for k in ('cash_market','calendar_path','cash_registry_path','assumptions_path','public_funding_descriptor')}
    roles.update(planning=str(R/'book/planning_market_20260915_actual1/planning_market.npz'),observations=str(R/'book/execution_observations_20260915_actual1/execution_observations.npz'))
    for path in roles.values():take(path)
    need(out[roles['cash_market']]=='37f990113aa7378256ad5dde635f1cb2a97c0a52cd5582a46610f0ea291407e7','fixed original raw cash market')
    d=read(roles['public_funding_descriptor'])
    for path in list(d['roles'].values())+list(d['origin_path_map'].values())+[d['query_script']]:take(path)
    return roles,out

def public_marks(descriptor,pins,symbols):
    d=read(descriptor)
    need(d['schema']=='PUBLIC_FUNDING_ADAPTER_CFG_1' and d['symbol']=='AERGOUSDT' and d['month']=='2026-07' and d['expected_records']==185,'fixed original public mark scope')
    def doc(path):need(sha(path)==pins[path],'public original proof SHA');return read(path)
    roles=d['roles'];actual=doc(roles['actual_exit']);result=doc(roles['result']);launch=doc(roles['launch']);freeze=doc(roles['freeze'])
    need(type(actual['actual_child_exit'])is int and actual['actual_child_exit']==0 and actual['argv']==d['expected_query_argv'],'original public actual query identity')
    need(sha(d['query_script'])==actual['script_sha256'],'original public query source')
    need(sha(roles['stdout'])==actual['stdout_sha256'] and sha(roles['stderr'])==actual['stderr_sha256'],'original public actual logs')
    need(result['complete_endpoint_snapshot']is True and result['status']=='COMPLETE_AVAILABLE_ENDPOINT_SNAPSHOT','complete original public snapshot')
    need(freeze['pins']==launch['source_pins']==result['source_pins_before']==result['source_pins_after'],'public unchanged original source map')
    for origin,h in freeze['pins'].items():need(sha(d['origin_path_map'][origin])==h,'public source relocation SHA')
    rows=[]
    for page in result['pages']:
        p=d['origin_path_map'][page['body_path']];need(sha(p)==page['body_sha256'] and Path(p).stat().st_size==page['bytes'] and page['http_status']==200 and page['url']==page['response_url'],'original public body/status/redirect identity')
        body=doc(p);need(len(body)==page['rows'],'public page complete population');rows.extend(body)
    need(rows==result['records'] and len(rows)==185,'all185 original official records')
    j=symbols.index('AERGOUSDT');out={}
    for r in rows:
        t=r['fundingTime'];need(type(t)is int and r['symbol']=='AERGOUSDT' and isinstance(r['fundingRate'],str) and isinstance(r['markPrice'],str),'original public decimal facts')
        need(1782864000000<=t<1785542400000 and (j,t) not in out,'exact unique July2026 source time')
        rate,mark=float(r['fundingRate']),float(r['markPrice']);need(np.isfinite(rate) and np.isfinite(mark) and mark>0,'finite original official mark/rate');out[j,t]=(rate,mark)
    return out

def annotation_archives(m,f,differences,original_pins,consumed):
    """Only mismatched interval annotations need an independent ZIP override."""
    groups={}
    for k in differences:
        s=str(m['symbols'][int(f['asset'][k])]);mo=dt.datetime.fromtimestamp(int(f['event_ms'][k])/1000,dt.timezone.utc).strftime('%Y-%m')
        groups.setdefault((s,mo),[]).append(k)
    for (s,mo),indices in groups.items():
        name=s+'-fundingRate-'+mo+'.zip';p=R/'book/cash_known59_integer1/official_months/archives'/name
        for path in (p,Path(str(p)+'.CHECKSUM')):need(str(path) in original_pins,'original annotation archive absent');pin(path,consumed,original_pins[str(path)])
        need(Path(str(p)+'.CHECKSUM').read_text().split()[0]==sha(p),'original annotation archive checksum')
        with zipfile.ZipFile(p) as z:
            names=z.namelist();need(len(names)==1,'single source funding CSV')
            rows=list(csv.DictReader(io.StringIO(z.read(names[0]).decode())))
        source={}
        for row in rows:
            t=int(row['calc_time']);need(t not in source,'duplicate source annotation');source[t]=(float(row['funding_interval_hours']),float(row['last_funding_rate']))
        for k in indices:
            t=int(f['event_ms'][k]);need(source.get(t)==(float(f['interval_hours'][k]),float(f['rate'][k])),'independent original funding annotation override')
    return len(groups)

def lifecycle(cal,registry,assumptions,life,symbols):
    initial={};expected=[];close_rows={x['event_id']:x for x in registry['events']}
    for s in symbols:
        c=cal['symbols'].get(s,{});p=dict(active=True,instrument_id=c.get('initial_generation',{}).get('instrument_id',s+'#legacy-unaudited'))
        for t in sorted(c.get('transitions',[]),key=lambda x:x['effective_ms']):
            when=t['effective_ms'];kind=t['kind']
            if when<FIRST:
                if kind=='CLOSE':p['active']=False
                else:p.update(active=True,instrument_id=t['instrument_id'])
            elif when<TERMINAL:expected.append((when,0 if kind=='CLOSE' else 1,s,kind,t))
        initial[s]=p
    need(initial==life['initial'] and life['assumptions']==assumptions,'all original initial generations and conditional assumptions')
    events=life['events'];bykey={(e['symbol'],e['type'],e['ts_ms'],e['instrument_id']):e for e in events}
    need(len(bykey)==len(events)==len(expected),'full original lifecycle population')
    for when,_,s,kind,t in expected:
        e=bykey[s,kind,when,t['instrument_id']]
        if kind=='CLOSE':
            need(e['source_event']==close_rows[e['id']],'original registry CLOSE identity')
            ref=assumptions['assumptions'].get(e['id'])
            need(e['reference_price']==(ref['price'] if ref is not None else None),'original conditional reference price')
            if ref is not None:need(ref['event_ms']==when and ref['instrument_id']==e['instrument_id'],'original conditional reference generation/clock')
        else:need(e['source_event']==t,'original calendar OPEN identity')
    return initial

def funding_generations(f,life,symbols):
    n=len(f['event_ms']);need(f['instrument_index'].shape==(n,) and f['generation_active'].shape==(n,),'funding generation fields')
    for j,s in enumerate(symbols):
        ix=np.flatnonzero(f['asset']==j);events=[e for e in life['events'] if e['symbol']==s]
        events.sort(key=lambda e:(e['ts_ms'],0 if e['type']=='CLOSE' else 1))
        cuts=np.array([e['ts_ms'] for e in events],dtype=np.int64);states=[life['initial'][s].copy()]
        for e in events:
            p=states[-1].copy()
            if e['type']=='CLOSE':p['active']=False
            else:p.update(active=True,instrument_id=e['instrument_id'])
            states.append(p)
        # Funding occurs BEFORE same-ms CLOSE/OPEN, so searchsorted is left.
        at=np.searchsorted(cuts,f['event_ms'][ix],side='left')
        for z,k in enumerate(ix):
            ii=int(f['instrument_index'][k]);need(-1<=ii<len(f['instruments']),'funding generation index bound')
            iid=None if ii<0 else str(f['instruments'][ii]);p=states[int(at[z])]
            need(iid==p['instrument_id'] and bool(f['generation_active'][k])==p['active'],'independent source funding generation/active')

def funding_event(f,k,symbols):
    ii=int(f['instrument_index'][k]);j=int(f['asset'][k]);source=int(f['source_row'][k])
    e=dict(type='FUNDING',ts_ms=int(f['event_ms'][k]),id='funding:'+str(source),symbol=symbols[j],
           source_asset=j,source_row=source,source_kind='Regular',mark_kind=str(f['mark_kind_names'][f['mark_kind_index'][k]]),
           instrument_id=str(f['instruments'][ii]) if ii>=0 else None,source_generation_active=bool(f['generation_active'][k]))
    for name in ('rate','mark','interval_hours'):e[name]=float(f[name][k]) if f[name+'_known'][k] else None
    return e
