"""Explicit budget-overrun recovery: finish only the last unchanged cash cell."""
from pathlib import Path
import json,time,sys,traceback
import run_batch as B
import resume_cash as RC

def main():
 old=Path(B.C['cash_parent']);term=old/'TERMINAL.json';t=json.loads(term.read_text())
 if B.sha(term)!=B.C['cash_parent_terminal_sha256'] or t['rc']!=1 or t['error'] not in ("TimeoutError('frozen budget exhausted')","TimeoutError('original total budget exhausted')"):raise ValueError('not a budget-only failure')
 src=old.with_name(old.name+'_sources');c=json.loads((src/'CONTRACT.json').read_text())
 for n,h in c['copied_sources'].items():
  if B.sha(src/n)!=h or B.sha(B.H/n)!=h:raise ValueError('frozen source drift')
 if B.sha(__file__)!=B.C['finalizer_sha256']:raise ValueError('finalizer drift')
 for name in ('resume_U_42','resume_U_2027','R180_42'):
  if json.loads((old/f'steps/{name}.json').read_text())['rc']!=0:raise ValueError('earlier cell unfinished')
 for p in (old/'processes').glob('*.json'):
  x=json.loads(p.read_text());s=Path(f"/proc/{x['pid']}/stat")
  if s.exists() and s.read_text().split()[21]==str(x['start_ticks']):raise ValueError('parent still running')
 RC.check_parent(Path(c['continuation_old_root']),c['failed_terminal_sha256'])
 from control_binding import verify_controls
 control=verify_controls(Path(B.C['parent_root']))
 B.R.mkdir(exist_ok=False)
 for n in ('logs','receipts','processes','steps','cells'):(B.R/n).mkdir()
 (B.R/'models').symlink_to(old/'models',target_is_directory=True)
 existing={}
 for kind in ('U','R180'):
  for seed in (42,2027):
   cell=old/f'cells/{kind}_s{seed}';(B.R/f'cells/{kind}_s{seed}').symlink_to(cell,target_is_directory=True)
   for p in cell.glob('runs/*/PATH_*.npz'):
    m=p.with_suffix('.json')
    if m.exists() and json.loads(m.read_text())['npz_sha256']==B.sha(p):existing[str(p)]=B.sha(p)
 B.write('EXISTING_CERTIFIED_PATHS.json',existing)
 B.write('ENGINE_IDENTITIES.json',json.loads((old/'ENGINE_IDENTITIES.json').read_text()))
 cfg=old/'cells/R180_s2027/configs/RUN_CONFIG_ADAPT_R180_s2027X.json'
 if B.sha(cfg)!=B.C['last_config_sha256']:raise ValueError('configuration drift')
 B.wait([B.launch('finish_last',[B.PY,'-B','/dev/shm/news2_2026-09-23/engine/bt_launch.py','PATH,HOME,LC_CTYPE',str(cfg),'--resume','ADAPT_R180_s2027X'])])
 RC.audit_cells()
 B.write('SIMULATION_TERMINAL.json',{'rc':0,'status':'SIMULATIONS_AUDITED','steps':B.STEPS,'original_budget_passed':False,'parent_failed':str(old)})
 B.wait([B.launch('economic',[B.PY,'-B',str(B.H/'economic_readout.py'),'--root',str(B.R),'--out',str(B.R/'receipts/ECONOMIC_FULL_BOOK.json')])])
 from decision import decide
 B.write('receipts/BOOK_DECISION.json',decide(json.loads((B.R/'receipts/ECONOMIC_FULL_BOOK.json').read_text())))
 if control!=verify_controls(Path(B.C['parent_root'])):raise ValueError('baseline drift')
 for p,h in existing.items():
  if B.sha(p)!=h:raise ValueError('previous certified path overwritten')
 if B.sha(term)!=B.C['cash_parent_terminal_sha256']:raise ValueError('parent failure changed')
 for n,h in c['copied_sources'].items():
  if B.sha(B.H/n)!=h:raise ValueError('source drift after run')

if __name__=='__main__':
 rc=1;error=None
 try:main();rc=0
 except BaseException as e:error=repr(e);traceback.print_exc()
 finally:
  B.stop_own()
  if B.R.exists():B.write('TERMINAL.json',{'rc':rc,'status':'COMPLETE_OVER_ORIGINAL_BUDGET_NOT_RELEASE' if rc==0 else 'FAILED','error':error,'original_budget_passed':False,'training_repeated':False,'utc':time.strftime('%FT%TZ',time.gmtime()),'steps':B.STEPS,'production_changes':0})
 raise SystemExit(rc)
