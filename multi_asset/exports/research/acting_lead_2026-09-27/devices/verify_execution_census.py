"""Independent census recomputation from archived whitelist records; no live/API reads."""
import collections,hashlib,json,math,sys,zipfile
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def verify(root):
 root=Path(root);r=json.loads((root/'RESULT.json').read_bytes());checks=[]
 def ck(name,ok):
  checks.append(name)
  if not ok:raise ValueError(name)
 for f,h in r['outputs'].items():ck('output:'+f,sha(root/f)==h)
 archive=next(k for k in r['source_files'] if k.endswith('/PRODUCTION_INPUTS.zip'))
 ck('original_producer_archive',sha(archive)==r['source_files'][archive]['sha256'])
 target_zip=zipfile.ZipFile(archive)
 arrays={k:[row for p in sorted(root.glob('*_'+k+'.json')) for row in json.loads(p.read_bytes())] for k in ('anchors','orders','readback')}
 phases=json.loads((root/'PHASES.json').read_bytes());rows=r['rows'];ck('population',len(rows)==20 and len({x['anchor'] for x in rows})==20)
 totals=collections.Counter();seen=[];nulls=0;requests_without_owner_side=0;none_reduce=0
 for x in rows:
  a=x['anchor'];an=[y for y in arrays['anchors'] if (y.get('external_book') or {}).get('nominal_ts')==a and a<=y['anchor_ts']<a+14400]
  ck(str(a)+':unique_anchor',len(an)==1);an=an[0];rid=an['rebalance_id']
  original=target_zip.read(f'state/target_live/{a}.json')
  ck(str(a)+':consumed_original_bytes',hashlib.sha256(original).hexdigest()==an['external_book']['json_sha']==x['target_sha256'])
  ck(str(a)+':canonical_copy_semantics',json.loads(original)==json.loads((root/f'TARGET_{a}.json').read_bytes()))
  pp=[y for y in phases if y['phase']=='A' and y['data'].get('rebalance_id')==rid]
  ck(str(a)+':phaseA',len(pp)==1 and pp[0]['data']['anchor_ts']==an['anchor_ts'])
  od=[y for y in arrays['orders'] if y.get('rebalance_id')==rid];rb=[y for y in arrays['readback'] if y.get('anchor_ts')==an['anchor_ts']]
  ck(str(a)+':row_count',len(od)==x['coverage']['rows']);ck(str(a)+':readback',len(rb)==x['readback_rows'])
  for k in ('prev_w','target_w','mid_at_anchor'):
   bad=sum(type(y.get(k)) not in (int,float) or not math.isfinite(y[k]) or (k=='mid_at_anchor' and y[k]<=0) for y in od)
   ck(str(a)+':finite:'+k,bad==x['coverage']['missing_plan_fields'][k]==0)
  for y in od:
   entries=y.get('request_ledger');nulls+=entries is None;none_reduce+=type(y.get('reduce_only')) is not bool
   if entries is None:continue
   for z in entries:
    ck(str(a)+':request_quantity',type(z['qty']) in (int,float) and math.isfinite(z['qty']))
    ck(str(a)+':request_identity',isinstance(z['client_id'],str) and bool(z['client_id']))
    seen.append((a,z['client_id']));requests_without_owner_side+=str(y.get('side','')).lower() not in ('buy','sell')
  totals.update(rows=len(od),readback=len(rb),request_entries=sum(len(y.get('request_ledger') or []) for y in od),opening_halted=an['opening_halted'] is True)
 ck('nulls',nulls==sum(x['coverage']['request_ledger_null'] for x in rows))
 ck('request_count',totals['request_entries']==sum(x['coverage']['request_entries'] for x in rows))
 return {'checks':len(checks),'status':'CENSUS_RECOMPUTED_NOT_EXECUTION_PARITY','totals':dict(totals),'request_unique_anchor_client_ids':len(set(seen)),'duplicate_entries':len(seen)-len(set(seen)),
  'null_ledger_rows':nulls,'rows_reduce_only_unavailable':none_reduce,'request_entries_owner_side_unavailable':requests_without_owner_side,
  'limits':['post_anchor positions are not decision-time quantity','null ledger does not establish missing requests','release timeline not per-anchor runtime attestation','current filters cannot certify historical rules'],
  'input_result_sha256':sha(root/'RESULT.json'),'device_sha256':sha(__file__)}
if __name__=='__main__':
 out=verify(sys.argv[1]);p=Path(sys.argv[1])/'VERIFY.json'
 with p.open('x') as f:json.dump(out,f,indent=2,allow_nan=False);f.write('\n')
 print(json.dumps(out))
