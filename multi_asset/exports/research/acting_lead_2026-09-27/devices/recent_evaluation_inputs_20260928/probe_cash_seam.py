"""Observe original sampler batch geometry at the old terminal, without mutation."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
from pathlib import Path
import sys,json,math,time
import numpy as np
from funding_overlap import sha
from recent_cash_run import prefix_check,stem
from recent_king_features import materialize
ROOT=Path('/dev/shm/recent_nc_cash_20260928');OUT=Path(sys.argv[1]);OUT.mkdir(exist_ok=False)
cp=ROOT/'s42/CONFIG.json';cfg=json.loads(cp.read_text());sys.path.insert(0,str(ROOT/'engine'));import bt_driver_lib as DL
checks=[]
def check(n,v,d=None):
 checks.append([n,bool(v)])
 if not v:raise ValueError(n)
DL.verify_pins(cfg,check);ES,SL,BH,L2=DL.import_modules(cfg,str(ROOT/'engine'));SL.install_readonly_guard();r=cfg['runs'][0]
c=DL.load_context(cfg,ES,BH,L2,slice(None),[r],check,lambda *a:None);S=DL.make_sim(c,r,20,str(OUT/'tmp'))
oldpath=json.loads((ROOT/'BASELINE_MANIFEST.json').read_text())['42'][20]['npz'];old=materialize(oldpath);seam=int(old['nav5_t0'])+300*(len(old['nav5_sim'])-1);ix=len(old['nav5_sim'])-1
flush=S._flush_nav;records=[]
def observe(t):
 hi=min(S.nav_n,int(math.ceil((float(t)-S.nav_grid0)/300)))
 if S._nb<=ix<hi:
  J,Q=S._arrays();r0=S.P.row(S.nav_grid0+S._nb*300);row=S.P.row(seam);r1=r0+hi-S._nb
  short=S.K+S._values(r0,row+1,J,Q);long=S.K+S._values(r0,r1,J,Q)
  a=float(short[-1]);b=float(long[ix-S._nb]);records.append({'rows_short':row+1-r0,'rows_long':r1-r0,'held_names':len(J),'old_sample':float(old['nav5_sim'][-1]),'same_state_short':a,'same_state_long':b,'short_bitwise_old':np.float64(a).tobytes()==old['nav5_sim'][-1].tobytes(),'difference':b-a,'ulp':float(np.spacing(a))})
 return flush(t)
S._flush_nav=observe;W=S.run();arr=DL.path_arrays(c,S,W);ref=materialize(str(stem(cp.parent,r['tag'],20))+'.npz');unchanged=prefix_check(ref,arr)
if len(records)!=1 or not records[0]['short_bitwise_old'] or records[0]['same_state_long']!=ref['nav5_sim'][ix]:raise ValueError('batch geometry explanation not reproduced')
rec={'status':'SAME_STATE_SAMPLER_BATCH_SHAPE_REPRODUCED','source_sha256':sha(__file__),'old_path_sha256':sha(oldpath),'new_path_sha256':sha(str(stem(cp.parent,r['tag'],20))+'.npz'),'observer_path_unchanged':unchanged,'seam':seam,'records':records,'checks':checks,'scope':'one originally failing seed20 only; no tolerance change and no economic readout'}
(OUT/'RESULT.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec))
