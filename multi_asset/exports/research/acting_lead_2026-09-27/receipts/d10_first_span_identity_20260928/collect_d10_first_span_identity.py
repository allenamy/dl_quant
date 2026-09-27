import ast,datetime,hashlib,json,os,resource,struct,time,zipfile
from pathlib import Path
os.nice(19);resource.setrlimit(resource.RLIMIT_AS,(512<<20,512<<20));resource.setrlimit(resource.RLIMIT_CPU,(60,60))
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for x in iter(lambda:f.read(1<<20),b''):h.update(x)
 return h.hexdigest()
def pin(p):
 p=Path(p);return {'path':str(p),'resolved':str(p.resolve()),'exists':p.is_file(),'bytes':p.stat().st_size if p.is_file() else None,'sha256':sha(p) if p.is_file() else None}
root=Path('/workspace/dlarch_2026-09-24/chain/d10rr_s42'); eng=Path('/dev/shm/news2_2026-09-23/engine')
cp=root/'configs/RUN_CONFIG_DLARCH_D10RR_s42.json';cfg=json.loads(cp.read_text())
sp=root/'configs/ADAPTER_SPEC_DLARCH_D10RR_s42.json';spec=json.loads(sp.read_text())
lp=root/'receipts/BT_LAUNCH_full_DLARCH_D10RR_s42.json';lr=json.loads(lp.read_text())
tp=root/'work/combo_s42/TARGET_RECEIPT.json';tr=json.loads(tp.read_text())
assets={'actual_config':cp,'actual_launch_receipt':lp,'adapter_spec':sp,'target_receipt':root/'targets/TARGETS_DLARCH_D10RR_s42.json','combo_receipt':tp,'share':Path('/workspace/dlarch_2026-09-24/f10d10_2026-09-27/share_d10rr.json'),'features':root/'work/NEWS_FEATURES.npz','legs':root/'work/legs.npz','legs_receipt':root/'receipts/P3_LEGS.json','king_oof':root/'work/king/KING_OOF.npz','f10_oof':root/'work/f10_s42/F10_OOF.npz','f10_receipt':root/'work/f10_s42/TRAIN_RECEIPT.json','fund_state':Path('/workspace/d10_reread_2026-09-27/r4_fund_state/fund_state_d10ext.npz'),'ms_ledger':Path('/workspace/d10_reread_2026-09-27/r2b_20260927T113701Z/r2/ledger_full_ms_ext_20260927T08.npz'),'targets':Path(cfg['runs'][0]['targets']['sources'][0]['npz'])}
for k in ['price_full_raw','price_full_meta','ledger_full','tradability','g0_labels','calibration','exec_sim','simlib','input_manifest']:
 assets[k]=Path(cfg['pins'][k]['path'])
for k in ['universe']:assets['target_'+k]=Path(spec[k]['path'])
for n in ['bt_launch.py','bt_driver_lib.py','bt_hist_sim31.py','ovn_adapter.py','bt_objb_targets.py']:assets['engine_'+n]=eng/n
for p in tr['inputs']:
 if not any(str(v)==p for v in assets.values()):assets['combo_input_'+Path(p).name]=Path(p)
for p in tr['sources']:assets['combo_source_'+Path(p).name]=Path(p)
for n in ['d10_build_fund_state.py','d10_rebuild_funding_features.py','d10_stage2_assemble.py']:assets['feature_source_'+n]=Path('/workspace/d10_reread_2026-09-27/devices')/n
start=time.monotonic();out={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'INPUT_CODE_IDENTITY_ONLY_NO_EXECUTION_OR_CANDIDATE_RETURNS','assets':{k:pin(p) for k,p in assets.items()},'config':{'nav0_usdt':cfg['nav0_usdt'],'paths_R':cfg['paths_R'],'runs':[{k:r[k] for k in ['arm','events','price','policy','ua_set','tag','book','targets']} for r in cfg['runs']],'current_production_config':cfg['current_production_config'],'funding_pin':cfg['pins']['ledger_full'],'window':cfg['window']},'launch_identity':{k:lr[k] for k in ['device','self_sha256','config']},'launch_selected_checks':[v for v in lr['checks'] if v['check'] in ['pin.ledger_full','pin.calibration','calibration.decision_offset_N+24','axis.tradability_symbols','pin.executor_tree_409ea16_vs_manifest']],'relationships':{'combo_inputs':tr['inputs'],'combo_sources':tr['sources'],'legs_inputs':json.loads((root/'receipts/P3_LEGS.json').read_text())['inputs'],'f10_input_identity':{k:v for k,v in json.loads((root/'work/f10_s42/TRAIN_RECEIPT.json').read_text()).items() if k in ['mode','inputs','sources','frozen_dir','frozen_receipt_sha256']}}}
def head(f):
 assert f.read(6)==b'\x93NUMPY';v=tuple(f.read(2));n=struct.unpack('<H' if v==(1,0) else '<I',f.read(2 if v==(1,0) else 4))[0];d=ast.literal_eval(f.read(n).decode('latin1'));return {'shape':list(d['shape']),'descr':d['descr'],'fortran_order':d['fortran_order']}
out['npz_headers']={}
for name in ['ms_ledger','ledger_full','features','legs','target_universe','price_full_meta','fund_state']:
 with zipfile.ZipFile(assets[name]) as z:out['npz_headers'][name]={n:head(z.open(n)) for n in z.namelist()}
out['cost']={'wall_s':round(time.monotonic()-start,3),'maxrss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'pid':os.getpid(),'pgid':os.getpgid(0),'CPU_limit_s':60,'AS_limit_bytes':512<<20,'nice':19}
print(json.dumps(out,indent=2))
