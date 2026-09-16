"""Close real native receipts after the four current independent arithmetic runs."""
import argparse
from batch_contract import *

def own_execution(base,pins):
    m=read(pin(base/'MANIFEST.json',pins));l=read(pin(base/'execution1/LAUNCH.json',pins));x=read(pin(base/'execution1/EXIT.json',pins));verify_final_exit(x)
    expected=['/workspace/venv/bin/python',str(HERE/'audit_scenario.py'),'--config',str(base/'CONFIG.json'),'--config-sha256',sha(base/'CONFIG.json')]
    need(m['argv']==l['argv']==x['argv']==expected and l['pins']==m['pins'] and l['manifest_sha256']==x['manifest_sha256']==sha(base/'MANIFEST.json') and x['launch_sha256']==sha(base/'execution1/LAUNCH.json') and l['launcher_sha256']==EXECUTOR_SHA,'actual independent execution/source identity')
    for n in ('STDOUT','STDERR'):pin(base/'execution1'/(n+'.log'),pins,x[n.lower()+'_sha256'])
    cfg=read(pin(base/'CONFIG.json',pins));need(all(m['pins'].get(p)==h for p,h in cfg['pins'].items()),'all actual independent direct inputs monitored')
    result=read(pin(base/'audit1/RESULT.json',pins));need(result['config']==dict(path=str(base/'CONFIG.json'),sha256=sha(base/'CONFIG.json')),'independent actual result/config identity')
    need(result['status']=='ACCOUNTING_PASS_AWAIT_NATIVE_BATCH' and result['input_source_pins']=={**cfg['pins'],str(base/'CONFIG.json'):sha(base/'CONFIG.json')},'independent complete source closure')
    need(json.loads((base/'execution1/STDOUT.log').read_text().splitlines()[-1])==dict(status=result['status'],scenario=result['scenario'],result=str(base/'audit1/RESULT.json'),sha256=sha(base/'audit1/RESULT.json')),'actual independent stdout/result identity')
    for n,h in result['artifacts'].items():pin(base/'audit1'/n,pins,h)
    return result

def close(output):
    need(HERE==REMOTE,'fixed native completion namespace');pins={};native_completion(pins)
    outer=read(pin(BATCH/'RESULT.json',pins));original=read(pin(BATCH/'INPUT_PINS.json',pins));m=read(MANIFEST)
    need(outer['schema']=='CURRENT_RULE_MARK_MAIN_RESULT_1' and outer['source_unchanged']is True and outer['source_pins_before']==outer['source_pins_after']==original and all(m['pins'].get(p)==h for p,h in original.items()),'original complete batch source closure')
    results={}
    for sid in SCENARIOS:
        r=own_execution(HERE/'formal1'/sid,pins);source=outer['path_results'][sid]
        need(r['scenario']==sid and r['source_result']==source['result'] and r['path_status']==source['status'],'original batch/result/independent path identity')
        p=BATCH/sid/'RESULT.json';pin(p,pins,source['result']['sha256'])
        need(outer['artifacts'][sid+'/RESULT.json']['sha256']==sha(p),'batch path artifact identity')
        results[sid]=dict(status='NATIVE_ACCOUNTING_ACCEPTED',path_status=r['path_status'],complete_window=r['complete_window'],daily_nodes=r['daily_nodes'],last_accepted_ms=r['last_accepted_ms'],independent_result=dict(path=str(HERE/'formal1'/sid/'audit1/RESULT.json'),sha256=sha(HERE/'formal1'/sid/'audit1/RESULT.json')))
    out=Path(output);need(out==HERE/'formal1/completion1' and not out.exists(),'fresh batch completion directory');out.mkdir()
    result=dict(schema='ACTUAL_INDEPENDENT_CURRENT_CASH_BATCH_CLOSURE_1',status='NATIVE_ACCOUNTING_ACCEPTED',scope='CURRENT_KING0_F10_15BEST32_WITH_EXPLICIT_ECONOMIC_MODE',paths=results,original_batch=dict(path=str(BATCH/'RESULT.json'),sha256=sha(BATCH/'RESULT.json')),input_source_pins=pins,repeated_arithmetic=False,statistics_computed=False)
    save(out/'RESULT.json',result);print(json.dumps(dict(status=result['status'],result=str(out/'RESULT.json'),sha256=sha(out/'RESULT.json'))))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();close(a.output)
