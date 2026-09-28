"""Freeze historical executor bytes from an offline clone plus checked-in release receipts."""
import ast,collections,datetime,hashlib,json,subprocess,sys
from pathlib import Path
root=Path(sys.argv[1]);repo=Path.cwd();clone=Path('/Users/haosiyu/cc_tmp/gapfix4_exec_20260926T1911Z')
out=root/'EXECUTOR_SOURCES';out.mkdir(exist_ok=False)
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(clone),*args])
base=repo/'multi_asset/exports/research/nc_2026-09-23/receipts'
spec=[('2026-09-24T08:00:00Z','5d3029c0411bf08d7d3e1457f6b46c3ac1ff043b', ['deploy_2026-09-24T0500Z/VP_after_a4.txt','deploy_2026-09-24T0500Z/VP_first_anchor_1790236800.txt']),
 ('2026-09-25T13:18:35Z','96acfddec11e51984a63358155165ab8ee4ba14b',['deploy_v2c_2026-09-25T1300Z/W3_switch.log']),
 ('2026-09-26T01:19:22Z','d01e35db56b4d7ed6abf0befd9f18452cd06c329',['deploy_fixpkg_d_2026-09-26T0100Z/W3_switch.log','deploy_fixpkg_d_2026-09-26T0100Z/W6_verify.log'])]
epochs=[]
for stamp,commit,refs in spec:
 assert git('rev-parse',commit).decode().strip()==commit
 rec={'since_utc':stamp,'since_ts':datetime.datetime.fromisoformat(stamp.replace('Z','+00:00')).timestamp(),'commit':commit,'receipts':{},'sources':{}}
 dest=out/commit[:10];dest.mkdir()
 assert any(commit.encode() in (base/path).read_bytes() for path in refs)
 for path in refs:
  raw=(base/path).read_bytes()
  (dest/Path(path).name).write_bytes(raw);rec['receipts'][str(base/path)]={'sha256':sha(raw),'archived':str((dest/Path(path).name).relative_to(root))}
 for path in ('scheduler/anchor_loop.py','signal/legs.py','live/external_book.py','live/binance_executor.py','config/book.json'):
  raw=git('show',commit+':'+path);name=path.replace('/','__');(dest/name).write_bytes(raw)
  rec['sources'][path]={'sha256':sha(raw),'archived':str((dest/name).relative_to(root))}
  if path=='scheduler/anchor_loop.py':
   txt=raw.decode();nodes=[n for n in ast.parse(txt).body if isinstance(n,ast.FunctionDef) and n.name in ('apply_withhold_and_reshape','withhold_pop','clamp_held_untradable')]
   assert len(nodes)==3;pure='\n\n'.join(ast.get_source_segment(txt,n) for n in nodes)+'\n';(dest/'anchor_pure.py.txt').write_text(pure)
   rec['pure_functions']={'names':[n.name for n in nodes],'sha256':sha(pure.encode()),'archived':str((dest/'anchor_pure.py.txt').relative_to(root))}
 epochs.append(rec)
r=json.loads((root/'RESULT.json').read_bytes());assign=[]
for x in r['rows']:
 applicable=[e for e in epochs if e['since_ts']<=x['execution_anchor']];assert applicable
 assign.append({'anchor':x['anchor'],'execution_anchor':x['execution_anchor'],'commit':applicable[-1]['commit']})
res={'status':'BOUND_FROM_RELEASE_RECEIPTS_NOT_PER_ANCHOR_RUNTIME_ATTESTATION','epochs':epochs,'assignment':assign,'counts':dict(collections.Counter(x['commit'] for x in assign)),
 'limits':['does not rule out undocumented working-tree edits between release checks','W3 fixpkg_d had pair-check invocation errors; later W6 independently verifies code refs/clean/drift','current venue filters remain unavailable as historical evidence'],
 'input_result_sha256':sha((root/'RESULT.json').read_bytes()),'device_sha256':sha(Path(__file__).read_bytes())}
(root/'SOURCE_BINDING.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps({'counts':res['counts'],'status':res['status']}))
