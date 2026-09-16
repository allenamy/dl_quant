"""Four independent current-role engines from one immutable admitted input set."""
import copy,hashlib,json,shutil,sys
from pathlib import Path
import numpy as np
import current_plan as plan
import current_modes as modes
import current_admission as a
import current_frames as frames
import shared_inputs as shared
D=Path(__file__).resolve().parent;need=plan.need;sha=shared.sha

def write(path,value):
 with Path(path).open('x') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')
def loaded_gate(pins):
 for mod in tuple(sys.modules.values()):
  f=getattr(mod,'__file__',None)
  if f and str(f).startswith(str(a.R)+'/') and str(f).endswith('.py'):
   p=str(Path(f).resolve());need(p in pins and sha(p)==pins[p],'executed research source outside current closure '+p)

def engine_for(mode,cfg,coverage,base,risk):
 modes.identity(mode);c=copy.deepcopy(cfg);need('economic_risk' not in c,'base config contains no implicit risk policy')
 if mode=='ECONOMIC_HALT':c['economic_risk']=risk.contract();return risk.RiskEngine(c,funding_coverage=coverage),c
 return base.Engine(c,funding_coverage=coverage),c

def run(token,descriptor,manifest):
 need(D==a.REMOTE and isinstance(token,a.CurrentInputs),'actual current input token and own formal namespace')
 need(set(descriptor)=={'schema','source_sha256','pf_execution','plan','output'} and descriptor['schema']=='CURRENT_RULE_FOUR_CASH_DESCRIPTOR_1','exact current descriptor')
 need(token.source_sha256==descriptor['source_sha256'],'current source identity');plan.validate_plan(descriptor['plan'],token.market['symbols'])
 out=Path(descriptor['output']);need(out==D/'formal1/batch' and not out.exists(),'fresh unique current formal batch')
 need(all(manifest['pins'].get(p)==h for p,h in token.pins.items()),'every consumed actual input in current native manifest')
 loaded_gate(token.pins);out.mkdir();p=descriptor['plan'];sy=token.market['symbols'];anchors=token.market['decision_ts'][:-1]
 write(out/'INPUT_PINS.json',token.pins);write(out/'DESCRIPTOR.json',descriptor)
 shared_cfg={k:token.cfg[k] for k in ['cash_market','calendar_path','calendar_sha256','cash_registry_path','cash_registry_sha256','assumptions_path','public_funding_descriptor','supports']}
 parent=dict(token.shared_fact_parent,original_input_pins=dict(path=str(shared.C/'INPUT_PINS.json'),sha256=shared.KNOWN['inputs']))
 write(out/'INPUT_BINDING.json',dict(schema='CURRENT_RULE_SHARED_FACTS_AND_NEW_PUBLICATIONS_1',cfg=shared_cfg,shared_fact_parent=parent,current_publications=token.publications['result'],pf_execution=descriptor['pf_execution'],model_schema=p['model_schema'],books=list(plan.BOOKS),historical_universe_certified=False,historical_feed_certified=False,historical_filter_certified=False,old_cash_or_quantity_reused=False))
 write(out/'RISK_MARKET_BINDING.json',token.risk_market_binding);write(out/'COVERAGE_UPGRADE.json',token.coverage_report)
 # Preserve original descriptor and original INPUT_PINS linkage exactly. The
 # local NPZ copy is byte-identical convenience; it is not a new funding source.
 for name in ('FUNDING_FACTS.json','FUNDING_FACTS.npz','LIFECYCLE.json'):
  source=shared.C/name;need(str(source) in token.pins and sha(source)==token.pins[str(source)],'original shared fact source before copy');shutil.copyfile(source,out/name);need(sha(out/name)==token.pins[str(source)],'unchanged complete factual copy')
 sys.path.insert(0,str(a.RISK));base=shared.load(a.R/'integration/dynamic_executor_quantity_exact_20260915/dynamic_cash.py','current_four_exact_base',token.pins)
 risk=shared.load(a.RISK/'risk_engine.py','current_four_risk_engine',token.pins);runner=shared.load(a.RISK/'risk_path_runner.py','current_four_path_runner',token.pins)
 domain=runner.funding_clock_domain(token.economic_events,anchors*1000);write(out/'FUNDING_CLOCK_DOMAIN.json',domain)
 funding_id='SHARED_CURRENT_FUNDING_'+shared.digest(plan.canonical(dict(event_hash=token.funding_descriptor['original_event_jsonl_sha256'],old=sorted((s,m,r['status']) for (s,m),r in token.old_records.items()),upgrades=[(s,m,r) for (s,m),r in sorted(token.upgrades.items())],segments=token.segments)))
 results={}
 for row in p['scenarios']:
  cfg=plan.engine_config(p,row,sy,token.initial,funding_id)
  coverage=token.economic.HeldFundingCoverage(sy.tolist(),token.segments,token.economic_events,token.original_coverage,token.old_records,token.upgrades,token.months_in,token.month_bounds,funding_id)
  engine,cfg=engine_for(row['mode'],cfg,coverage,base,risk)
  need(all(token.pins.get(path)==h for path,h in engine.policy.pins.items()),'engine exact transitive policy source closure')
  write(out/('CONFIG_'+row['id']+'.json'),cfg);write(out/('MODE_'+row['id']+'.json'),dict(modes.identity(row['mode']),book=row['book'],publication=token.publications['books'][row['book']]['artifact'],risk_market_binding_sha256=sha(out/'RISK_MARKET_BINDING.json')))
  loaded_gate(token.pins);pub=token.publications['books'][row['book']];saved=set()
  def audit_anchor(e,reason,state):
   when=e.get('anchor_ms',e['ts_ms']-e['ts_ms']%14400000);ix=int(np.searchsorted(anchors*1000,when))
   if ix>=len(anchors) or int(anchors[ix])*1000!=when or reason!='BLOCKED' and ix!=0 or (ix,reason) in saved:return
   saved.add((ix,reason));name=row['id']+'_PUBLICATION_'+str(ix)+'_'+reason
   np.savez_compressed(out/(name+'.npz'),symbols=sy,publication_raw=pub['arrays']['publication_raw'][ix],universe=pub['universe'][ix])
   write(out/(name+'.json'),dict(anchor_index=ix,anchor_ms=when,chosen=str(pub['arrays']['chosen'][ix]),known=bool(pub['arrays']['publication_known'][ix]),cn_config=pub['cn_config'],source=pub['artifact'],event=e,blocked=state.get('blocked'),npz_sha256=sha(out/(name+'.npz'))))
  print(json.dumps(dict(stage='CURRENT_PATH_START',scenario=row['id'],book=row['book'],mode=row['mode'])),flush=True)
  result=runner.run_path(engine,frames.iter_frames(token,p,row),out/row['id'],expected_days=[int(x)*1000 for x in token.market['decision_ts'][::6]],on_anchor=audit_anchor)
  counts=result['input_event_types'];need(all(counts[k]==3648 for k in ('PLAN','NAV_SNAPSHOT','ATTEMPT','READBACK')) and counts['FUNDING']==token.funding_descriptor['count'],'all current original anchor/fund events retained')
  need(counts.get('RISK_ATTEMPT',0)==(3648 if row['mode']=='ECONOMIC_HALT' else 0),'only mode-specific E60 domain')
  ref=dict(path=str(out/row['id']/'RESULT.json'),sha256=sha(out/row['id']/'RESULT.json'));results[row['id']]=dict(row=row,status=result['status'],result=ref)
  print(json.dumps(dict(stage='CURRENT_PATH_COMPLETE',scenario=row['id'],status=result['status'],result=ref)),flush=True)
 token.verify_unchanged();loaded_gate(token.pins)
 final=dict(schema='CURRENT_RULE_FOUR_CASH_RESULT_1',status='COMPLETE_CONDITIONAL_BATCH' if all(x['status']=='COMPLETE_CONDITIONAL_PATH' for x in results.values()) else 'CONTAINS_UNMEASURABLE_PATH',path_results=results,source_pins_before=token.pins,source_pins_after=token.pins,source_unchanged=True,shared_fact_parent=parent,statistics_computed=False,other_scenarios_started=False,artifacts={str(x.relative_to(out)):dict(sha256=sha(x),bytes=x.stat().st_size) for x in sorted(out.rglob('*')) if x.is_file()})
 final['artifact_total_bytes_excluding_result']=sum(x['bytes'] for x in final['artifacts'].values());write(out/'RESULT.json',final)
 print(json.dumps(dict(stage='CURRENT_FOUR_CASH_COMPLETE',status=final['status'],result=dict(path=str(out/'RESULT.json'),sha256=sha(out/'RESULT.json')))),flush=True);return final
