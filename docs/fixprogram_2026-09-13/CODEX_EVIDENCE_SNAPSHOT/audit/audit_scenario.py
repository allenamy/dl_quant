"""Actual independent accounting of current King0/F10 and economic-risk modes."""
import argparse,datetime as dt,importlib.util,sys,time
from batch_contract import *
import original_facts as facts_io
import current_dispatch as dispatch
import endpoint_coverage as endpoint
import mark_facts

def require_pins(pins):
    for p,h in pins.items():need(sha(p)==h,'actual input/source changed '+p)

def run(config_path,config_sha):
    need(HERE==REMOTE,'formal independent accounting fixed Pod namespace')
    cfgp=Path(config_path);need(sha(cfgp)==config_sha,'frozen independent audit config');cfg=read(cfgp)
    sid=cfg['scenario'];require_scenario(sid);need(cfgp==HERE/'formal1'/sid/'CONFIG.json','fixed audit config path')
    out=Path(cfg['output']);need(out==cfgp.parent/'audit1' and not out.exists(),'fresh independent output')
    resource=resources();out.mkdir();start=time.monotonic();pins=dict(cfg['pins']);pin(cfgp,pins,config_sha);require_pins(pins)
    wanted_book,mode=dispatch.scenario_identity(sid);accountant,audit_class=dispatch.load_accountant(mode)
    original_inputs=read(FACT_PARENT/'INPUT_PINS.json');path=BATCH/sid;result=read(path/'RESULT.json')
    need(sha(path/'RESULT.json')==cfg['path_result_sha256'],'closed source path RESULT identity')
    for name,h in result['artifacts'].items():
        p=path/name;need(p.resolve().is_relative_to(path) and sha(p)==h and p.stat().st_size==result['artifact_bytes'][name],'complete source path artifact '+name)
    state=read(path/'STATE.json');rows=state.pop('journal');days=state.pop('days')
    def verify_jsonl(name,expected):
        count=0
        with (path/name).open('rb') as f:
            for b in f:
                need(b.endswith(b'\n') and count<len(expected) and json.loads(b)==expected[count],'standalone/STATE exact row '+name);count+=1
        need(count==len(expected),'standalone/STATE complete population '+name)
    verify_jsonl('JOURNAL.jsonl',rows);verify_jsonl('DAYS.jsonl',days)
    daily=[json.loads(b) for b in (path/'DAILY_TOTALS.jsonl').read_bytes().splitlines()]
    applied,blocked=select_applied(rows,result['status'])
    need(applied and state['clock_ms']==applied[-1]['ts_ms'],'final economic clock equals last accepted event')
    need(len(days)==len(daily)==result['actual_days'] and [r['day_record'] for r in applied if r['type']=='DAY']==days,'complete original DAY rows')
    day_times=[d['ts_ms'] for d in days]
    need(day_times==list(range(FIRST,day_times[-1]+1,86400000))==[d['ts_ms'] for d in daily],'consecutive T-minus DAY nodes')
    if result['status']=='COMPLETE_CONDITIONAL_PATH':need(len(days)==609 and day_times[-1]==TERMINAL and applied[-1]['type']=='DAY','complete609 DAY window')
    cut=applied[-1]['ts_ms']
    roles=cfg['original_roles'];market=arrays(roles['cash_market'],['symbols','decision_ts','event_ms','event_asset','event_rate','event_interval_h','event_close_mark','price_1500','decision_price'])
    planning=arrays(roles['planning'],['symbols','anchor_ts','nav_mark_close_ts','planning_price'])
    observations=arrays(roles['observations'],['symbols','anchor_ts','observation_ts_1500','quote_volume_1500','trade_count_1500'])
    risk_arrays=arrays(roles['risk_observations'])
    f=arrays(BATCH/'FUNDING_FACTS.npz');life=read(BATCH/'LIFECYCLE.json');cal=read(roles['calendar_path']);reg=read(roles['cash_registry_path']);refs=read(roles['assumptions_path'])
    sy=market['symbols'].tolist();need(len(sy)==len(set(sy))==829,'full829 original axis')
    for z in (planning,observations,f):need(np.array_equal(z['symbols'],market['symbols']),'exact original symbol axes')
    anchors=market['decision_ts'];need(np.array_equal(anchors,np.arange(FIRST//1000,TERMINAL//1000+1,14400,dtype=np.int64)),'fixed full raw anchor axis')
    need(np.array_equal(planning['anchor_ts'],anchors[:-1]) and np.array_equal(observations['anchor_ts'],anchors[:-1]),'full planning/observation anchor axes')
    risk_facts=dispatch.OriginalRiskFacts(risk_arrays,anchors[:-1],market['symbols'],cal)
    for off in (1200,1440,1500,3300):
        need(not np.intersect1d(f['event_ms'],(anchors[:-1]+off)*1000).size,'retained ordinary funding-clock applicability')
    public=facts_io.public_marks(roles['public_funding_descriptor'],pins,sy)
    differences=funding_alignment(market,f,FIRST,TERMINAL,public)
    annotation_sources={};annotation_months=facts_io.annotation_archives(market,f,differences,original_inputs,annotation_sources)
    need(all(pins.get(p)==h for p,h in annotation_sources.items()),'annotation evidence included in actual independent manifest')
    initial=facts_io.lifecycle(cal,reg,refs,life,sy);facts_io.funding_generations(f,life,sy)
    econ_cfg=read(BATCH/('CONFIG_'+sid+'.json'));need(econ_cfg==state['config'] and econ_cfg['instruments']==initial,'source config/initial state identity')
    need(econ_cfg['initial_capital']==100000 and econ_cfg['origin_ms']==FIRST and econ_cfg['attempt_offset_ms']==1500000 and econ_cfg['ordinary_fee_bps']==econ_cfg['settlement_fee_bps']==3.52 and econ_cfg['settlement_factor']==1. and econ_cfg['use_pns']is True and econ_cfg['ladder_multiplier']==1.,'fixed central research assumptions')
    descriptor=read(BATCH/'DESCRIPTOR.json');rows_plan=descriptor['plan']['scenarios']
    need([r['id'] for r in rows_plan]==list(SCENARIOS),'fixed single current-main role')
    selected=next(r for r in rows_plan if r['id']==sid)
    need(selected['book']==wanted_book and selected['mode']==mode and selected['settlement_factor']==1. and selected['ordinary_fee_bps']==3.52,'fixed current book/mode assumptions')
    mode_record=read(BATCH/('MODE_'+sid+'.json'))
    need(mode_record['mode']==mode and mode_record['book']==wanted_book and mode_record['pns_readback_offset_ms']==3300000 and mode_record['ordinary_attempt_offset_ms']==1500000 and mode_record['risk_attempt_offset_ms']==(3600000 if mode=='ECONOMIC_HALT' else None) and mode_record['manual_resume_events']==[] and mode_record['sigma_external_events']==[] and mode_record['sigma_multiplier']==1.,'original exact mode record')
    need(mode_record['risk_market_binding_sha256']==sha(BATCH/'RISK_MARKET_BINDING.json'),'mode original risk facts identity')
    need(('economic_risk' in econ_cfg)==(mode=='ECONOMIC_HALT'),'no implicit or omitted economic policy')
    if mode=='ECONOMIC_HALT':
        need(econ_cfg['economic_risk'].get('funding_boundary')==endpoint.BOUNDARY and econ_cfg['economic_risk']['engine_sha256']==endpoint.RISK_ENGINE_SHA,'fixed endpoint-aware source contract')
    valuation=mark_facts.admit(read(BATCH/'INPUT_PINS.json'),pins)
    valuation.validate_stream(read(BATCH/'MARK_VALUATION_BINDING.json'),read(BATCH/'MARK_STREAM_DIFFERENCE.json'),result)
    audit=audit_class(econ_cfg,initial,quantity_schema=state['quantity_schema'])
    boundary=endpoint.EndpointFacts(f,sy,life['segments'],cfg['endpoint_months'],pins,public)
    life_by_id={e['id']:e for e in life['events']};life_seen=[];fund_cursor=0;fund_digest=__import__('hashlib').sha256();fund_count=0
    expected=dispatch.expected_clocks(anchors,f['event_ms'],life['events'],mode)
    projected=[(r['type'],r['ts_ms'],r['id'] if r['type'] in ('CLOSE','OPEN') else None) for r in applied]
    need(projected==expected[:len(applied)],'independent complete event clocks/population through accepted prefix')
    if blocked is None:need(len(applied)==len(expected),'entire original event stream accounted')
    else:need(len(applied)<len(expected) and (blocked['type'],blocked['ts_ms'],blocked['id'] if blocked['type'] in ('CLOSE','OPEN') else None)==expected[len(applied)],'unknown is the immediate next original event, no skipped source rows')
    # All original funding facts are independently checked, including those after
    # a blocked prefix. Only complete applied same-ms batches alter the oracle.
    original_digest=__import__('hashlib').sha256()
    for k in range(len(f['event_ms'])):original_digest.update(json.dumps(facts_io.funding_event(f,k,sy),sort_keys=True,separators=(',',':'),allow_nan=False).encode()+b'\n')
    fact_desc=read(BATCH/'FUNDING_FACTS.json')
    need(original_digest.hexdigest()==fact_desc['original_event_jsonl_sha256'] and len(f['event_ms'])==fact_desc['count'] and fact_desc['source_pins_sha256']==digest(original_inputs),'original full funding fact serialization/input SHA')
    def prices(a):return {s:float(v) if np.isfinite(v) and v>0 else None for s,v in zip(sy,a)}
    day_records=[];mark_records=[];day_index=0;started=time.monotonic()
    for n,r in enumerate(applied):
        typ,t=r['type'],r['ts_ms']
        if typ=='FUNDING':
            need(fund_cursor<len(f['event_ms']) and int(f['event_ms'][fund_cursor])==t,'no omitted source funding batch')
            stop=int(np.searchsorted(f['event_ms'],t,side='right'));events=[facts_io.funding_event(f,k,sy) for k in range(fund_cursor,stop)]
            audit.funding(r,events);fund_count+=len(events);fund_cursor=stop
        elif typ in ('CLOSE','OPEN'):
            e=life_by_id[r['id']];getattr(audit,typ.lower())(r,e);life_seen.append((typ,r['id'],t))
        elif typ=='ATTEMPT':
            anchor=(t-econ_cfg['attempt_offset_ms'])//1000;i=locate(anchors,anchor)
            need(t==anchor*1000+1500000==int(observations['observation_ts_1500'][i])*1000,'original N25 clock')
            px=market['price_1500'][i];qv=observations['quote_volume_1500'][i];ct=observations['trade_count_1500'][i];obs={}
            for j,s in enumerate(sy):
                broad=any(t>=z['announced_at_ms'] and z['effective_ms']<=t<z['end_ms'] for z in cal['symbols'].get(s,{}).get('new_order_restrictions',[]))
                active=np.isfinite(px[j]) and px[j]>0 and np.isfinite(qv[j]) and qv[j]>0 and np.isfinite(ct[j]) and ct[j]>0
                obs[s]=dict(price=float(px[j]) if np.isfinite(px[j]) else None,status='ACTIVE' if active else 'UNOBSERVABLE',submission_allowed=not broad)
            audit.attempt(r,obs)
        elif typ=='READBACK':
            derived=dispatch.dispatch_readback(audit,r,valuation.prices(typ,t,risk_facts.prices(t),audit.positions),mode)
            mark_records.append(dict(ts_ms=t,type=typ,nav=derived,recorded_nav_present=mode=='ECONOMIC_HALT'))
        elif typ=='RISK_ATTEMPT':
            need(mode=='ECONOMIC_HALT','no-halt stream cannot include E60')
            boundary.check(audit,t,fund_cursor)
            audit.risk_exit(r,risk_facts.observations(t))
        elif typ in ('DAY','NAV_SNAPSHOT'):
            if typ=='DAY':
                need(t%86400000==0,'UTC DAY clock');px=prices(market['decision_price'][locate(anchors,t//1000)])
            else:
                i=locate(anchors,(t-1200000)//1000);need(int(planning['nav_mark_close_ts'][i])*1000==t,'original N20 valuation clock');px=prices(planning['planning_price'][i])
            px=valuation.prices(typ,t,px,audit.positions)
            nav=audit.mark(r,px);mark_records.append(dict(ts_ms=t,type=typ,nav=nav))
            if typ=='DAY':
                d=daily[day_index];held={s:audit._q(s)*accountant.number(px[s]) for s in sy if audit._q(s)}
                need(d['held_count']==len(held)==days[day_index]['held_count'],'exact daily held population')
                audit._money(d['cash'],audit.book.cash,'daily_totals_cash');audit._money(d['nav'],nav,'daily_totals_nav')
                gross=sum(abs(v) for v in held.values());net=sum(held.values())
                audit._money(d['gross_notional'],gross,'daily_totals_gross');audit._money(d['net_notional'],net,'daily_totals_net')
                for k,v in audit.totals.items():audit._money(d['totals'][k],v,'daily_total_'+k)
                day_records.append(dict(ts_ms=t,independent_nav=nav,recorded_nav=d['nav'],independent_cash=float(audit.book.cash),held_count=len(held),independent_gross_notional=float(gross),independent_net_notional=float(net),independent_totals={k:float(v) for k,v in audit.totals.items()}));day_index+=1
                if dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).day==1:print(json.dumps(dict(stage='INDEPENDENT_DAY',scenario=sid,ts_ms=t,rows=n+1,elapsed_seconds=time.monotonic()-started)),flush=True)
        else:audit.cash_only(r)
    need(life_seen==[(e['type'],e['id'],e['ts_ms']) for e in life['events'][:len(life_seen)]],'all lifecycle events through accepted prefix')
    valuation.finish(cut)
    prefix_comparison=mark_facts.compare_prefix(day_records,mark_facts.PREFIX.read_bytes())
    audit.check_final(state)
    report=audit.report();q={s:report['canonical_quantities'][s] for s in sy};report.pop('exact_quantities');report.pop('canonical_quantities')
    report.update(mark_valuation=valuation.summary(),original_prefix_comparison=prefix_comparison,endpoint_held_checks=boundary.checks,endpoint_same_ms_held_funding_events=boundary.same_ms_held_events,endpoint_months_verified=len(boundary.month_cache),funding_boundary_contract=endpoint.BOUNDARY,canonical_quantities_sha256=digest(q),source_fact_count=len(f['event_ms']),applied_original_funding_events=fund_count,exact_public_mark_events=len(public),annotation_differences=len(differences),annotation_archive_months=annotation_months)
    save(out/'DAILY_AGGREGATES.json',day_records);save(out/'MARK_AGGREGATES.json',mark_records)
    require_pins(pins)
    final=dict(schema='ACTUAL_INDEPENDENT_CURRENT_CASH_PATH_ACCOUNTING_1',status='ACCOUNTING_PASS_AWAIT_NATIVE_BATCH',scenario=sid,book=wanted_book,mode=mode,scope='CURRENT_KING0_F10_15BEST32_RESEARCH_REPLAY_WITH_EXPLICIT_ECONOMIC_MODE',path_status=result['status'],complete_window=result['status']=='COMPLETE_CONDITIONAL_PATH',blocked=blocked,last_accepted_ms=cut,daily_nodes=len(day_records),daily_return_intervals=max(0,len(day_records)-1),applied_journal_rows=len(applied),independent_accounting=report,resource=resource,wall_seconds=time.monotonic()-start,source_result=dict(path=str(path/'RESULT.json'),sha256=cfg['path_result_sha256']),config=dict(path=str(cfgp),sha256=config_sha),input_source_pins=pins,artifacts={n:sha(out/n) for n in ('DAILY_AGGREGATES.json','MARK_AGGREGATES.json')},statistics_computed=False,pricing_and_halt_assumptions='FROZEN_SCENARIO; NO HISTORICAL_OPERATING_OR_EXACT_SETTLEMENT_CERTIFICATION')
    save(out/'RESULT.json',final);print(json.dumps(dict(status=final['status'],scenario=sid,result=str(out/'RESULT.json'),sha256=sha(out/'RESULT.json'))),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--config-sha256',required=True);a=p.parse_args();run(a.config,a.config_sha256)
