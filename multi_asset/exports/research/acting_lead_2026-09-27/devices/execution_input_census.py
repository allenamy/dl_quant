"""Read-only whitelist capture of decision evidence. No fills, fees, PnL or arm outcomes."""
import argparse,hashlib,json,math,re,sys,time,zipfile
from pathlib import Path

ORDER_KEYS=('anchor_ts','rebalance_id','symbol','prev_w','target_w','mid_at_anchor','intended_notional','intended_full','intended_residual','attempt_idx','order_type','side','reduce_only','submit_ts','request_ledger')
REQUEST_KEYS=('client_id','qty','state','order_id','confirmed_qty','terminal','intent','phase','request_ts')
ANCHOR_KEYS=('anchor_ts','rebalance_id','book_source','external_book','opening_halted','target_gross','weights','reshape','rows_persisted','target_vector_hash','m3_beta_overlay','mid_at_anchor_vector')
PHASE_KEYS=('action','anchor_ts','anchor_wall_ts','rebalance_id','book_source','sizing','external_book','external_filters','external_wait','n_planned','n_targets','untradable_disposition','untradable_held','untradable_names','untradable_reason','venue_cap_clamp','universe','live_reduce_only_syms','per_name_stop')
READBACK_KEYS=('anchor_ts','rebalance_id','symbol','source','read_ts','readback_ts','venue_position_qty','venue_position_notional','mid','mark_price')

def finite(v):return type(v) in (int,float) and math.isfinite(v)
def select(r,keys):return {k:r[k] for k in keys if k in r}
def order_record(r):
    out=select(r,ORDER_KEYS)
    if 'request_ledger' in out and out['request_ledger'] is not None:
        if not isinstance(out['request_ledger'],list) or any(not isinstance(x,dict) for x in out['request_ledger']):raise ValueError('request_ledger_schema')
        out['request_ledger']=[select(x,REQUEST_KEYS) for x in out['request_ledger']]
    return out
def order_coverage(rows):
    missing={k:sum(not finite(r.get(k)) or (k=='mid_at_anchor' and r[k]<=0) for r in rows) for k in ('prev_w','target_w','mid_at_anchor')}
    requests=[x for r in rows for x in (r.get('request_ledger') or [])]
    return {'rows':len(rows),'names':len({r.get('symbol') for r in rows}),'complete_plan_fields':bool(rows) and not any(missing.values()),'missing_plan_fields':missing,
      'row_reduce_only_missing':sum(type(r.get('reduce_only')) is not bool for r in rows),'row_side_missing':sum(str(r.get('side','')).lower() not in ('buy','sell') for r in rows),
      'request_ledger_null':sum('request_ledger' in r and r['request_ledger'] is None for r in rows),'request_ledger_missing':sum('request_ledger' not in r for r in rows),'request_entries':len(requests),'request_quantity_missing':sum(not finite(x.get('qty')) for x in requests),
      'request_client_id_missing':sum(not isinstance(x.get('client_id'),str) or not x['client_id'] for x in requests)}
def anchor_candidates(rows,a):return [r for r in rows if (r.get('external_book') or {}).get('nominal_ts')==a and finite(r.get('anchor_ts')) and a<=r['anchor_ts']<a+14400]
def population_context(rows):
    return [r for r in rows if finite(r.get('anchor_ts')) and 1790222400<=r['anchor_ts']<1790568000]
def readback_candidates(rows,anchor):
    return [r for r in rows if finite(r.get('anchor_ts')) and r['anchor_ts']==anchor['anchor_ts']]
def phases(text):
    out=[]
    for l in text.splitlines():
        m=re.match(r'^(\S+) phase_([AC]): (.*)$',l)
        if not m:continue
        r=json.loads(m[3]);out.append({'logged_utc':m[1],'phase':m[2],'data':select(r,PHASE_KEYS)})
    return out
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    # UTC wall-clock first: do not even read a live log outside the authorized span.
    if not 3600<=time.time()%14400<13200:raise RuntimeError('outside_quiet_window')
    common=Path(__file__).parents[2]/'common';sys.path.insert(0,str(common))
    from venue_quiet_window import quiet_window_status
    quiet=quiet_window_status()
    if not quiet['open'] or quiet['override'] or quiet.get('stale_start') or quiet.get('anchor_in_progress'):raise RuntimeError('anchor_not_finished_in_quiet_window')
    root=args.out;root.mkdir(exist_ok=False);source={};files={}
    def read(p):
        raw=p.read_bytes();source[str(p)]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)};return raw
    def jl(raw):return [json.loads(l) for l in raw.splitlines() if l.strip()]
    def put(name,value):
        p=root/name;p.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');files[name]=hashlib.sha256(p.read_bytes()).hexdigest()
    parent=Path('/Users/haosiyu/.codex/tmp/live_replay_layers_20260928/result')
    meta=json.loads(read(parent/'RESULT.json'));raw=read(parent/'PRODUCTION_INPUTS.zip')
    if hashlib.sha256(raw).hexdigest()!=meta['archive_sha256']:raise ValueError('producer_archive_identity')
    import io
    z=zipfile.ZipFile(io.BytesIO(raw));anchors=[r['anchor'] for r in meta['rows'] if r['anchor']>=1790236800 and r['model_status']=='SAME_MODEL_FILES']
    if len(anchors)!=20 or anchors[-1]!=1790553600:raise ValueError('fixed_anchor_population')
    live=Path.home()/'dl_quant_live';pilot=live/'state/live/pilot_log';all_an=[];all_od=[];all_rb=[]
    for day in sorted({time.strftime('%Y%m%d',time.gmtime(a)) for a in anchors}):
        ar=population_context([select(r,ANCHOR_KEYS) for r in jl(read(pilot/day/'anchors.jsonl'))])
        od=population_context([order_record(r) for r in jl(read(pilot/day/'orders.jsonl'))])
        rb=population_context([select(r,READBACK_KEYS) for r in jl(read(pilot/day/'position_readback.jsonl'))])
        all_an.extend(ar);all_od.extend(od);all_rb.extend(rb)
        put(day+'_anchors.json',ar);put(day+'_orders.json',od);put(day+'_readback.json',rb)
    pa=phases(read(live/'state/anchor_runs.log').decode())
    pa=[r for r in pa if '2026-09-24'<=r['logged_utc']<'2026-09-28T04:00:00Z'];put('PHASES.json',pa)
    # Current filters are retained ONLY as current evidence, never historical values.
    filterpath=live/'state/live/exchange_info_cache.json';filterraw=read(filterpath);put('CURRENT_FILTERS.json',json.loads(filterraw))
    records=[]
    for a in anchors:
        an=anchor_candidates(all_an,a);status=[];rec={'anchor':a,'anchor_records':len(an)}
        if len(an)!=1:
            rec.update(status='UNAVAILABLE_ANCHOR_IDENTITY');records.append(rec);continue
        row=an[0];rid=row.get('rebalance_id');pp=[r for r in pa if r['phase']=='A' and r['data'].get('rebalance_id')==rid];od=[r for r in all_od if r.get('rebalance_id')==rid]
        tp=f'state/target_live/{a}.json';raw=z.read(tp);target=json.loads(raw);ts=hashlib.sha256(raw).hexdigest();put(f'TARGET_{a}.json',target)
        if row['external_book'].get('json_sha')!=ts:status.append('consumed_target_sha_mismatch')
        if len(pp)!=1:status.append('phase_A_identity_missing_or_ambiguous')
        else:
            p=pp[0]['data']
            if p.get('anchor_ts')!=row.get('anchor_ts'):status.append('capture_clock_mismatch')
            if not finite((p.get('sizing') or {}).get('nav')) or not finite((p.get('sizing') or {}).get('gross')):status.append('sizing_unavailable')
        cov=order_coverage(od)
        if not cov['complete_plan_fields']:status.append('plan_field_population_not_complete')
        if cov['row_reduce_only_missing'] or cov['row_side_missing']:status.append('request_owner_fields_incomplete')
        if cov['request_ledger_null']:status.append('request_ledger_null_rows_not_request_loss_claim')
        if cov['request_ledger_missing'] or cov['request_quantity_missing'] or cov['request_client_id_missing']:status.append('request_evidence_incomplete')
        if row.get('opening_halted') is not False:status.append('opening_halted_or_unknown')
        rbs=readback_candidates(all_rb,row)
        rec.update(rid=rid,execution_anchor=row.get('anchor_ts'),phase_A_records=len(pp),action=pp[0]['data'].get('action') if len(pp)==1 else None,opening_halted=row.get('opening_halted'),coverage=cov,
          readback_rows=len(rbs),readback_sources=sorted({str(r.get('source')) for r in rbs}),readback_identity='exact_execution_anchor_ts_not_rid',readback_timestamp_keys={k:sum(finite(r.get(k)) for r in rbs) for k in ('read_ts','readback_ts')},
          target_sha256=ts,consumed_target_sha256=row['external_book'].get('json_sha'),issues=status,status='FIELD_CENSUS_ONLY_NO_PARITY_CLAIM',
          historical_filters='UNAVAILABLE_CURRENT_FILE_NOT_HISTORICAL',runtime_code='UNAVAILABLE_NO_PER_ANCHOR_CODE_IDENTITY_BOUND')
        records.append(rec)
    result={'utc':time.strftime('%FT%TZ',time.gmtime()),'scope':'fixed_twenty_anchor_input_census_no_execution_parity_or_economic_result','quiet':quiet,'source_files':source,'outputs':files,'rows':records,
      'device_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'filters_mtime_utc':time.strftime('%FT%TZ',time.gmtime(filterpath.stat().st_mtime))}
    put('RESULT.json',result)
    print(json.dumps({'anchors':len(records),'result':str(root/'RESULT.json'),'sha256':files['RESULT.json']}))
if __name__=='__main__':main()
