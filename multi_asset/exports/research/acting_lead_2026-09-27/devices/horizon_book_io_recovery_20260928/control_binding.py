"""Bind reused controls to their actual current configuration before running."""
import json
from pathlib import Path
from residual_model import sha

BASE_CFG=Path('/dev/shm/news2_2026-09-23/configs/RUN_CONFIG_NEWS2_s42X_2026-09-23.json')
ENGINE=Path('/dev/shm/news2_2026-09-23/engine')

def check_config_and_spec(control,config,old_spec,current_spec):
 r=control['steps']['run_config']
 if str(config)!=r['base_config'] or sha(config)!=r['base_config_sha256']:
  raise ValueError('base execution config differs from successful control')
 for key in ('price_meta','universe','window_first_anchor'):
  if old_spec[key]!=current_spec[key]:raise ValueError('adapter base differs from control: '+key)

def verify_controls(parent):
 parent=Path(parent);seen={}
 for seed in (42,2027):
  chain=json.loads((parent/f'receipts/ALLOC_CHAIN_inservice_shared_s{seed}.json').read_text())
  cp=Path(chain['steps']['run_config']['path'])
  if sha(cp)!=chain['steps']['run_config']['sha256']:raise ValueError('control config changed')
  sp=Path(chain['root'])/f'configs/ADAPTER_SPEC_ALLOC_inservice_shared_s{seed}X.json'
  if sha(sp)!=chain['steps']['adapter_spec']['spec_sha256']:raise ValueError('control spec changed')
  base=Path(f'/workspace/old_vs_new_2026-09-23/devices/ADAPTER_SPEC_NEW_s{seed}.json')
  check_config_and_spec(chain,BASE_CFG,json.loads(sp.read_text()),json.loads(base.read_text()))
  ident=next(x for x in json.loads((parent/'ENGINE_IDENTITIES.json').read_text()) if x['seed']==seed)
  md=Path(ident['new']).with_suffix('.json');m=json.loads(md.read_text())
  if m['npz_sha256']!=ident['new_sha256'] or m['config_sha256']!=sha(cp):raise ValueError('control engine receipt identity')
  for name,h in m['device_sha256'].items():
   p=Path(json.loads(cp.read_text())["pins"]["exec_sim"]["path"]) if name=="exec_sim.py" else ENGINE/name
   if sha(p)!=h:raise ValueError('control engine drift '+name)
   seen[str(p)]=h
  seen[str(base)]=sha(base);seen[str(cp)]=sha(cp);seen[str(md)]=sha(md)
 # Adapter source is unchanged from original control derivation 17555e56,
 # unlike our new per-arm specification generator.
 ap=ENGINE/'ovn_adapter.py';ah='17555e56362c53ce4e961e0d8cb050be65cddae31088b275f190eecacd5794ea'
 if sha(ap)!=ah:raise ValueError('control adapter source drift')
 seen[str(ap)]=ah;seen[str(BASE_CFG)]=sha(BASE_CFG)
 return seen
