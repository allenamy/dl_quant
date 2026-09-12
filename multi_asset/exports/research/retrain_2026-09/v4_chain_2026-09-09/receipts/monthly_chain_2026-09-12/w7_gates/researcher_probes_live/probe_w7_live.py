"""Bounded CPU-only gates on synthetic fixtures. No production data or business module imported."""
import ast
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import numpy as np
sys.dont_write_bytecode = True
O=Path(__file__).resolve().parent
C=Path('/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09')   # W7: LIVE device dir (post-fix)
F=O/'fixtures/w7'; F.mkdir(parents=True,exist_ok=True)
# Reuse only reviewed synthetic fixture functions/constant assignments from the lead's test, not its test runner.
tree=ast.parse((C/'tests_pipeline_gates.py').read_text())
WANT={'_members','_base','_write_month','_env1','_env2','_T0','_NWm','_KP','_NA_REF','_NA_NEW','_N82','_N89','_SYM'}
nodes=[n for n in tree.body if (isinstance(n,ast.FunctionDef) and n.name in WANT) or (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in WANT for t in n.targets))]
ns={'np':np,'os':os,'_shu':shutil}
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(C/'tests_pipeline_gates.py'),'exec'),ns)
b=ns['_base'](1,230)
ns['_write_month'](str(F/'new'),b,230,'new')
ns['_write_month'](str(F/'ref'),b,200,'ref')
res={'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'scope':'synthetic small CPU fixtures only; no actual monthly production gate or candidacy claimed','cases':{}}
def gate(name, script, env, expected):
 p=subprocess.run([sys.executable,str(C/script)],env=dict(env,PATH='/usr/bin:/bin',PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,timeout=20)
 r=json.loads(Path(env.get('STEP1_OUT') or env['STEP2_OUT']).read_text())
 res['cases'][name]={'returncode':p.returncode,'PASS':r['PASS'],'expected':expected,'as_expected':r['PASS']==expected and p.returncode==(0 if expected else 3),'receipt':env.get('STEP1_OUT') or env['STEP2_OUT'],'receipt_sha256':hashlib.sha256(Path(env.get('STEP1_OUT') or env['STEP2_OUT']).read_bytes()).hexdigest(),'clamp_checks':r.get('clamp_checks'),'inputs':sorted(r['inputs_sha256']),'tail_exempt':r.get('anchors_only_v4_tail_exempt'),'refused':r.get('REFUSED')}
 return r
e1=ns['_env1'](str(F/'new'),str(F/'ref'),str(F/'step1_positive.json'))
r1=gate('W7_STEP1_extension_positive','v4_gate_step1_m.py',e1,True)
e2=ns['_env2'](str(F/'new'),str(F/'ref'),str(F/'step2_positive.json'))
r2=gate('W7_STEP2_extension_positive','v4_gate_step2_m.py',e2,True)
e3=ns['_env2'](str(F/'new'),str(F/'ref'),str(F/'step2_none.json'),PREV_KING_FEA_UNCLAMPED='NONE')
r3=gate('W7_NONE_positive_without_any_builder_or_preflight_identity','v4_gate_step2_m.py',e3,True)
# An out-of-neighbourhood mutation of one actual common candidate cell must fail.
p=F/'new/king_fea.npy'; original=np.load(p).copy(); a=original.copy(); a[199,0,2]+=1;np.save(p,a)
e4=ns['_env2'](str(F/'new'),str(F/'ref'),str(F/'step2_common_negative.json'),PREV_KING_FEA_UNCLAMPED='NONE')
gate('W7_NONE_changed_common_cell_negative','v4_gate_step2_m.py',e4,False)
# Tail comparison is expressly exempt. Determine its finite-data assurance boundary, not an undisclosed policy change.
a=original.copy();a[200:]=np.nan;np.save(p,a)
e5=ns['_env2'](str(F/'new'),str(F/'ref'),str(F/'step2_tail_nan.json'),PREV_KING_FEA_UNCLAMPED='NONE')
gate('W7_entire_new_tail_NaN_still_PASS_boundary','v4_gate_step2_m.py',e5,True)
np.save(p,original)
e6=ns['_env2'](str(F/'new'),str(F/'ref'),str(F/'step2_selfref.json'),PREV_KING_FEA=str(F/'new/king_fea.npy'))
gate('W7_candidate_as_reference_negative','v4_gate_step2_m.py',e6,False)
# Authentic contract should reject either new gate source; no contract edit or simulation approval here.
sp=importlib.util.spec_from_file_location('w7_frozen_common',C/'v4_gate_common.py');cm=importlib.util.module_from_spec(sp);sp.loader.exec_module(cm)
for gate_name,r,source,profile in [('STEP1',r1,'v4_gate_step1_m.py','v4'),('STEP2',r2,'v4_gate_step2_m.py',None)]:
 path=e1['STEP1_OUT'] if gate_name=='STEP1' else e2['STEP2_OUT']
 inp={k:r['inputs_path'][k] for k in cm.required_inputs(gate_name,profile)[0]}
 ok,why=cm.require(path,inp,expected_gate=gate_name,expected_self_sha=hashlib.sha256((C/source).read_bytes()).hexdigest(),profile=profile)
 res['cases'][f'W7_real_contract_refuses_{gate_name}_unapproved']={'ok':ok,'expected':False,'as_expected':ok is False and 'not an APPROVED source' in why,'why':why}
res['source_sha256']={n:hashlib.sha256((C/n).read_bytes()).hexdigest() for n in ['v4_gate_step1_m.py','v4_gate_step2_m.py','tests_pipeline_gates.py','ELIGIBILITY_CONTRACT.json']}
res['all_probe_expectations_met']=all(x['as_expected'] for x in res['cases'].values())
(O/'PROBE_W7_RESULTS_live.json').write_text(json.dumps(res,indent=2)+'\n')
print(json.dumps(res,indent=2))
