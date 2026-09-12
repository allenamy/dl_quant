"""Isolated review probes; only frozen common module and AST-extracted judge function execute.
Monthly driver is called with a fail-closed fake interpreter. No business code executes.
All writes remain beneath this file's output directory.
"""
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
sys.dont_write_bytecode = True
O = Path(__file__).resolve().parent
C = Path('/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09')   # W7: pointed at the LIVE device dir (post-fix)
F = O / 'fixtures'
F.mkdir(exist_ok=True)
RESULT = {'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'scope': 'Synthetic fixture validation only; no real gate PASS or candidate claimed', 'cases': {}}
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def record(name, actual, expected, detail):
    RESULT['cases'][name] = {'actual': actual, 'expected': expected, 'as_expected': actual == expected, 'detail': detail}

# Import only the audited stdlib-only helper. AST extract one judge function, never its module body.
spec = importlib.util.spec_from_file_location('frozen_common', C/'v4_gate_common.py')
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)
contract, err = common.load_contract()
assert err is None
jf = ast.parse((C/'judge_v4.py').read_text())
fn = next(n for n in jf.body if isinstance(n, ast.FunctionDef) and n.name == '_eligibility')
hc = F/'judge_hc'
books = hc/'dev_v4/probe_artifacts'
books.mkdir(parents=True, exist_ok=True)
inputs = {}
for k in common.REQUIRED_INPUTS['BUNDLE_export']:
    if k == 'eligibility_contract': p = C/'ELIGIBILITY_CONTRACT.json'
    elif k.startswith('book_'):
        seat, seed = k.removeprefix('book_').split('_s')
        p = books/f'w10_ablation_series_V4_A1_{seat}_s{seed}.npz'
        p.write_bytes(('synthetic identity only '+k).encode())
    else:
        p = F/'judge_inputs'/k
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(('synthetic identity only '+k).encode())
    inputs[k] = str(p)
ns = {'json': json, '_contract': contract, '_contract_err': None, '_CONTRACT_PATH': str(C/'ELIGIBILITY_CONTRACT.json'), '_require': common.require, 'HC': str(hc), 'ARMS': {('A1',seat,seed): object() for seat in ('dyn','fix') for seed in ('42','2027')}}
exec(compile(ast.Module(body=[fn],type_ignores=[]), str(C/'judge_v4.py'), 'exec'), ns)
receipt = {'gate': 'BUNDLE_export', 'PASS': True, 'arm': 'A1', 'self_sha256': contract['gates']['BUNDLE_export']['approved_source_sha256'][0], 'inputs_sha256': {k:sha(p) for k,p in inputs.items()}, 'inputs_path': inputs, 'utc': RESULT['utc'], 'fixture': True}
rp = F/'synthetic_receipt.json'
caller = {k:p for k,p in inputs.items() if not k.startswith('book_') and k != 'eligibility_contract'}
def eligibility(name, expected, r=None, inp=None):
    rp.write_text(json.dumps(receipt if r is None else r))
    ans = ns['_eligibility']('A1', {'receipt':str(rp), 'inputs': caller if inp is None else inp})
    record(name, ans['ok'], expected, ans)
eligibility('F9_missing_caller_contract_self_bound_positive', True)
r = copy.deepcopy(receipt); r['inputs_sha256'].pop('eligibility_contract')
eligibility('F9_receipt_omits_contract_negative', False, r)
foreign = F/'different_contract.json'; foreign.write_text('{}')
r = copy.deepcopy(receipt); r['inputs_sha256']['eligibility_contract'] = sha(foreign)
eligibility('F9_receipt_foreign_contract_negative', False, r, dict(caller, eligibility_contract=str(foreign)))
eligibility('F9_caller_wrong_path_correct_own_contract_positive', True, inp=dict(caller, eligibility_contract=str(foreign)))
cp = F/'bytecopy_contract.json'; cp.write_bytes((C/'ELIGIBILITY_CONTRACT.json').read_bytes())
eligibility('F9_caller_bytecopy_contract_positive', True, inp=dict(caller, eligibility_contract=str(cp)))
ci = dict(caller); ci.pop('bundle/slow_pred_pinned.npy')
eligibility('W4_omitted_static_bundle_input_negative', False, inp=ci)
pred = Path(inputs['bundle/slow_pred_pinned.npy']); old = pred.read_bytes(); pred.write_bytes(old+b'CHANGED')
eligibility('W4_changed_static_bundle_input_negative', False)
pred.write_bytes(old)
# Dynamic receipt closure is meaningful to a FEMAT-injected book, though not in static 28 floor.
extra = F/'judge_inputs/femat.npy'; extra.write_bytes(b'original synthetic FEMAT')
r = copy.deepcopy(receipt); r['inputs_sha256']['femat'] = sha(extra); r['inputs_path']['femat'] = str(extra)
extra.write_bytes(b'changed synthetic FEMAT')
eligibility('W4_changed_receipt_extra_omitted_by_caller_ACCEPTED', True, r)
eligibility('W4_changed_receipt_extra_declared_by_caller_rejected', False, r, dict(caller, femat=str(extra)))

# No original training/gate/producer code executes: this interpreter logs requests and exits 77.
mock = F/'mock_python'
mock.write_text('#!'+sys.executable+'\nimport json,os,sys\nfrom pathlib import Path\np=Path(os.environ["PROBE_LOG"])\nwith p.open("a") as f: f.write(json.dumps({"argv":sys.argv[1:],"env":{k:os.environ.get(k) for k in ["F10_DLW","F10_OUT","BEST_EP_FIX","SEED","DLWT_RAW_PATCH"]}})+"\\n")\nif len(sys.argv)>2 and sys.argv[2]=="sha": print("a"*64+" mock-only");sys.exit(0)\nprint("SAFE_INTERCEPT_NO_BUSINESS_CODE_EXECUTED")\nsys.exit(77)\n')
mock.chmod(0o755)
keys = re.search(r'^V4_MONTH_KEYS="([^"]+)"', (C/'chain_lib.sh').read_text(), re.M).group(1).split()
root = F/'empty_month'; root.mkdir(exist_ok=True)
vals = dict.fromkeys(keys, str(F/'nonexistent_input'))
vals.update(V4_MONTH='2026-10',R=str(root),PY=str(mock),SEEDS='42',MONTHS_ALL='202501,202502,202503,202504',MWF_ROOT=str(F/'mwf'),BUNDLE_GENERATION='v4_2026-10',GATE_STEP1='v4_gate_step1.py',GATE_STEP2='v4_gate_step2.py')
def config(name, omit=()):
    p=F/name; p.write_text(''.join(f'{k}={vals[k]}\n' for k in keys if k not in omit)); return p
cfg=config('month.cfg')
baseenv={'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'PROBE_LOG':str(F/'intercept.jsonl')}
log=Path(baseenv['PROBE_LOG']); log.write_text('')
s = subprocess.run(['/bin/bash', str(C/'chain_v4_monthly.sh'), str(cfg)], env=dict(baseenv,V4_STAGES='refit'), capture_output=True,text=True,timeout=10)
calls = [json.loads(l) for l in log.read_text().splitlines()]
refitcalls=[x for x in calls if any(str(a).endswith('pod_f10_refit_v4.py') for a in x['argv'])]
record('W3_refit_subset_dispatches_without_upstream_receipts', bool(refitcalls), True, {'returncode':s.returncode,'stdout':s.stdout,'stderr':s.stderr,'refit_calls':refitcalls,'preflight_receipt_exists':(root/'v4_gates/preflight.json').exists(),'step1_receipt_exists':(root/'v4_gates/step1.json').exists()})
# Exercise only chain_lib's configuration loader, with an omitted SEEDS key.
missing=config('omitted_seed.cfg', ('SEEDS',))
command='. "$1"; load_month_env "$2"; echo "PROBE_SEEDS=$SEEDS"'
for inherited in (False,True):
    env = dict(baseenv, L='/dev/stderr')
    if inherited: env['SEEDS']='42'
    p=subprocess.run(['/bin/bash','-c',command,'probe',str(C/'chain_lib.sh'),str(missing)],env=env,capture_output=True,text=True,timeout=10)
    record('W3_omitted_SEEDS_'+('inherited_ACCEPTED' if inherited else 'clean_env_rejected'),p.returncode,0 if inherited else 4,{'stdout':p.stdout,'stderr':p.stderr})
# Exact CLIP target command copied from frozen driver; harmless interpreter shows ambient raw-patch propagation.
line=next(l.strip() for l in (C/'chain_v4_monthly.sh').read_text().splitlines() if 'DLWT_OUT=$DLW_CLIP' in l and 'pod_dlw_targets_raw.py' in l)
command=line.split(' >> ')[0]
p=subprocess.run(['/bin/bash','-c',command],env=dict(baseenv,PY=str(mock),D=str(C),CACHE='fixture-cache',PANEL_SPLICE='fixture-panel',DLW_CLIP='fixture-clip',DLWT_RAW_PATCH='stale-inherited-patch'),capture_output=True,text=True,timeout=10)
last=json.loads(log.read_text().splitlines()[-1])
record('W3_CLIP_command_inherits_ambient_RAW_PATCH',last['env']['DLWT_RAW_PATCH'],'stale-inherited-patch',{'source_command':command,'intercept':last,'returncode':p.returncode})
RESULT['source_sha256']={n:sha(C/n) for n in ['chain_v4_monthly.sh','chain_lib.sh','judge_v4.py','v4_gate_common.py','ELIGIBILITY_CONTRACT.json']}
RESULT['all_probe_expectations_met']=all(x['as_expected'] for x in RESULT['cases'].values())
(O/'PROBE_RESULTS_live.json').write_text(json.dumps(RESULT,indent=2)+'\n')
print(json.dumps({'utc':RESULT['utc'],'cases':{k:{'actual':v['actual'],'as_expected':v['as_expected']} for k,v in RESULT['cases'].items()},'all_probe_expectations_met':RESULT['all_probe_expectations_met']},indent=2))
