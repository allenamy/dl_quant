"""Freeze one closed path audit; never start or modify the original cash runner."""
import argparse
from batch_contract import *
import original_facts
import fact_parent
import endpoint_coverage
import mark_facts

def source_gate(expected):
    p=HERE/'SOURCE_LOCK.json';need(sha(p)==expected,'external independent batch source lock');lock=read(p)
    need(lock['schema']=='INDEPENDENT_CURRENT_CASH_BATCH_SOURCE_1','exact batch source schema')
    need(set(lock['own_sources'])=={'batch_contract.py','original_facts.py','audit_scenario.py','prepare_audit.py','close_batch.py','current_dispatch.py','fact_parent.py','test_current_dispatch.py','endpoint_coverage.py','test_endpoint_coverage.py','mark_facts.py','test_mark_facts.py','RUNNER_CONTRACT.json'},'exact bounded current audit source registry')
    pins={str(p):expected}
    for n,h in lock['own_sources'].items():pin(HERE/n,pins,h)
    for relative,h in lock['parent_sources'].items():pin(R/relative,pins,h)
    need(pins[str(HERE.parent/'dynamic_cash_reconciliation_exact_quantity_20260915/exact_reconciliation.py')]==READER_SHA and pins[str(HERE.parent/'dynamic_cash_reconciliation_exact_quantity_20260915/SOURCE_LOCK.json')]==READER_LOCK_SHA,'fixed approved exact reader/lock')
    return pins

def prepare(scenario,source_sha):
    require_scenario(scenario);need(HERE==REMOTE,'fixed native audit namespace');resource=resources();pins=source_gate(source_sha)
    path=BATCH/scenario;rp=path/'RESULT.json'
    required=[rp,BATCH/'INPUT_PINS.json',NATIVE/'LAUNCH.json']
    missing=[str(p) for p in required if not p.is_file()]
    if missing:return dict(status='WAIT_CLOSED_ORIGINAL_PATH',missing=missing,runnable_written=False,exit_code=2)
    m=native_launch(pins);result=read(pin(rp,pins));need(result['status'] in ('COMPLETE_CONDITIONAL_PATH','UNMEASURABLE'),'closed original result')
    for name,h in result['artifacts'].items():
        p=path/name;need(p.resolve().is_relative_to(path),'original artifact cannot escape');pin(p,pins,h);need(p.stat().st_size==result['artifact_bytes'][name],'original artifact size')
    for name in ['INPUT_PINS.json','INPUT_BINDING.json','RISK_MARKET_BINDING.json','DESCRIPTOR.json','FUNDING_FACTS.npz','FUNDING_FACTS.json','LIFECYCLE.json','MODE_'+scenario+'.json','CONFIG_'+scenario+'.json','MARK_VALUATION_BINDING.json','MARK_STREAM_DIFFERENCE.json']:pin(BATCH/name,pins)
    current=read(BATCH/'INPUT_PINS.json')
    valuation=mark_facts.admit(current,pins)
    valuation.validate_stream(read(BATCH/'MARK_VALUATION_BINDING.json'),read(BATCH/'MARK_STREAM_DIFFERENCE.json'),result)
    pin(mark_facts.PREFIX,pins,mark_facts.PREFIX_SHA)
    need(all(m['pins'].get(p)==h for p,h in current.items()),'all current original inputs monitored by actual batch')
    original,original_watch=fact_parent.original(pins,current)
    roles,source_pins=original_facts.source_files(original,original_watch)
    need(all(current.get(p)==h for p,h in source_pins.items()),'current actual uses the same raw market facts')
    merge(pins,source_pins);roles['risk_observations']=fact_parent.risk_market(pins,current)
    # Pre-read only to freeze the exact small archive subset needed for any
    # original interval annotation difference, not all25596 ancestors again.
    market=arrays(roles['cash_market'],['symbols','event_ms','event_asset','event_rate','event_interval_h','event_close_mark'])
    facts=arrays(BATCH/'FUNDING_FACTS.npz');public=original_facts.public_marks(roles['public_funding_descriptor'],pins,market['symbols'].tolist())
    differences=funding_alignment(market,facts,FIRST,TERMINAL,public)
    original_facts.annotation_archives(market,facts,differences,original,pins)
    endpoint_months=endpoint_coverage.prepare_months(path/'JOURNAL.jsonl',original,pins)
    out=HERE/'formal1'/scenario;need(not out.exists(),'new audit config namespace');out.mkdir(parents=True)
    cfg=dict(schema='INDEPENDENT_CURRENT_CASH_SCENARIO_CONFIG_1',scenario=scenario,output=str(out/'audit1'),path_result_sha256=pins[str(rp)],original_roles=roles,endpoint_months=endpoint_months,pins=pins,scope='CURRENT_KING0_F10_15BEST32_EXPLICIT_ECONOMIC_MODE',source_lock_sha256=source_sha)
    save(out/'CONFIG.json',cfg);pin(out/'CONFIG.json',pins)
    argv=['/workspace/venv/bin/python',str(HERE/'audit_scenario.py'),'--config',str(out/'CONFIG.json'),'--config-sha256',sha(out/'CONFIG.json')]
    save(out/'MANIFEST.json',dict(argv=argv,pins=pins,threads=1,cuda_visible_devices=''))
    value=dict(status='PREPARED_INDEPENDENT_ACCOUNTING_NOT_EXECUTED',config=dict(path=str(out/'CONFIG.json'),sha256=sha(out/'CONFIG.json')),manifest=dict(path=str(out/'MANIFEST.json'),sha256=sha(out/'MANIFEST.json')),execution_directory=str(out/'execution1'),expected_argv=argv,resource=resource,source_pins_count=len(pins),exit_code=0)
    save(out/'PREPARED.json',value);return value

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--scenario',required=True);p.add_argument('--source-lock-sha256',required=True);a=p.parse_args();r=prepare(a.scenario,a.source_lock_sha256);print(json.dumps(r));raise SystemExit(r['exit_code'])
