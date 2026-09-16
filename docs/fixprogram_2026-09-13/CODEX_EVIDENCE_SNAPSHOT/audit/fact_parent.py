"""Admit fixed already-executed factual parents without importing Engines."""
from batch_contract import *
from current_dispatch import RISK_MARKET_SHA

OLD_FORMAL=FACT_PARENT.parent
KNOWN={'MANIFEST.json':'5884c406c4d83a51ae29689fd72f7b758a1ad1086de41bcb26556215aac728da','execution1/LAUNCH.json':'1129b90757190a33eac2a5e6220a44c6adbf9bcbe9af12038afa2491e22e23e1','execution1/EXIT.json':'c8fe7c3a15fed1ad51c69ed5f6d0183e57b0fa0a00bd530c7a0887b7fe3257f9','execution1/STDOUT.log':'99feae805ac030bfc72283e249a1af124e152c3984b94c0a8a97b81fcaac3ddb','execution1/STDERR.log':'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855','central3/RESULT.json':'6138d234c699b0de04d52bef206466c04403b16b1a358caea2fe32553eedca53','central3/INPUT_PINS.json':FACT_PARENT_INPUT_SHA}
RISK_DIR=R/'integration/current_economic_risk_20260915/market_actual1'
RISK_FILES={'RESULT.json': 'dda5b7e8a17a5da32eb66bd4f61a3272e1e13e07b1253f9a2811934468bd759e', 'ACTUAL_EXIT.json': '7d34184a7a5e0d6d0cdcec96925683f8762da25117a7d43aa2acff8d0193a805', 'PREVIEW.json': 'f4ba3b60c206b43d4af3c44859e525dc55486d1c4eeed3ae5a79aa6967cbd617', 'RAW_MONTHLY_SHA.json': '4195e41e987cad41d67c67312a8d3cf1f3a137d30a51301231c661db87c61fec', 'BUNDLE.json': 'ad400b63a59a2a89fdbd5004140c1e81ccce5a462e9aaae46b5848e252030f30', 'LOADER.py': 'f93a60020e41014c0bed1e93330ec9fe205dfb1a79a44f2f0c094b6a77d27894', 'OUTPUT.zip': 'be99d8e0fbcf5ef42d6fcd64de4053eeaa981500904f90e89ab956c76790e157', 'STDERR.log': '3e2d6c50da0c5c7e0f581da9df7a0da27f40d9fc440e91fc5e86dc8d41ee3a03', 'risk_observations.npz': '1b45e1e8e5e711379eade0c6ff709a05d3a9296948decc54e4f530dfa0d9ac48'}

def original(pins,current_inputs):
    for relative,h in KNOWN.items():
        p=OLD_FORMAL/relative;need(current_inputs.get(str(p))==h,'actual current source consumes original factual receipt '+relative);pin(p,pins,h)
    m,l,x=[read(OLD_FORMAL/p) for p in ('MANIFEST.json','execution1/LAUNCH.json','execution1/EXIT.json')]
    verify_final_exit(x)
    need(m['argv']==l['argv']==x['argv'] and m['pins']==l['pins'] and x['manifest_sha256']==l['manifest_sha256']==KNOWN['MANIFEST.json'] and x['launch_sha256']==KNOWN['execution1/LAUNCH.json'],'complete original factual native execution')
    need(l['launcher_sha256']==EXECUTOR_SHA,'original actual root executor')
    inputs=read(FACT_PARENT/'INPUT_PINS.json');result=read(FACT_PARENT/'RESULT.json')
    need(result['source_unchanged'] is True and result['source_pins_before']==result['source_pins_after']==inputs and all(m['pins'].get(p)==h for p,h in inputs.items()),'original factual native source population')
    binding=read(BATCH/'INPUT_BINDING.json')
    need(binding['schema']=='CURRENT_RULE_SHARED_FACTS_AND_NEW_PUBLICATIONS_1' and binding['model_schema']=='CURRENT_RULE_KING0_F10_15BEST32_PREDICTIONS_1' and binding['old_cash_or_quantity_reused'] is False,'current model, new book and original facts identities')
    parent=binding['shared_fact_parent']
    need(parent['result_path']==str(FACT_PARENT/'RESULT.json') and parent['sha256']==KNOWN['central3/RESULT.json'] and parent['native_exit_sha256']==KNOWN['execution1/EXIT.json'] and parent['original_input_pins']==dict(path=str(FACT_PARENT/'INPUT_PINS.json'),sha256=FACT_PARENT_INPUT_SHA) and parent['old_cash_amounts_reused'] is False and parent['old_model_or_publication_reused'] is False,'exact shared factual parent')
    for name in ('FUNDING_FACTS.json','FUNDING_FACTS.npz','LIFECYCLE.json'):
        h=result['artifacts'][name]['sha256'];p=FACT_PARENT/name
        need(current_inputs.get(str(p))==h and sha(BATCH/name)==h and (BATCH/name).stat().st_size==result['artifacts'][name]['bytes'],'unchanged complete original fact copy '+name)
    return inputs,m['pins']

def risk_market(pins,current_inputs):
    binding=read(BATCH/'RISK_MARKET_BINDING.json')
    need(binding==dict(directory=str(RISK_DIR),files=RISK_FILES,source_scope='RAW_CLOSE_PROXY_NOT_HISTORICAL_FILL_OR_MARK_PRICE'),'fixed actual raw risk market binding')
    for name,h in RISK_FILES.items():
        p=RISK_DIR/name;need(current_inputs.get(str(p))==h,'original risk fact actual source monitored '+name);pin(p,pins,h)
    x=read(RISK_DIR/'ACTUAL_EXIT.json');r=read(RISK_DIR/'RESULT.json')
    need(type(x['actual_ssh_exit']) is int and x['actual_ssh_exit']==0 and x['source_unchanged'] is True and r['source_unchanged'] is True and r['PASS'] is True,'original raw risk actual SSH0')
    need(x['bundle_sha256']==RISK_FILES['BUNDLE.json']==r['source_record']['bundle_sha256'] and x['output_sha256']==RISK_FILES['OUTPUT.zip'] and x['stderr_sha256']==RISK_FILES['STDERR.log'],'original raw risk actual output linkage')
    need(r['E55_byte_parity'] is True and r['anchors']==3648 and r['symbols']==829 and RISK_FILES['risk_observations.npz']==RISK_MARKET_SHA,'full original raw risk population')
    return str(RISK_DIR/'risk_observations.npz')
