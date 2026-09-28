"""Read existing label-window selection only. No training or economic outcome."""
from pathlib import Path
import sys,json,hashlib,datetime as dt,time
import numpy as np
S=Path('/dev/shm/f10_recent_adapt_20260928_attempt2_sources');sys.path.insert(0,str(S))
from adapt_contract import causal_windows,align_indices
sys.path.insert(0,'/dev/shm/news2_2026-09-23/devices')
from f10_observability import span_admissible
from news2_train_f10 import fold_specs

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(4<<20),b''):h.update(b)
 return h.hexdigest()
def iso(t):return dt.datetime.fromtimestamp(int(t),dt.timezone.utc).isoformat()
def main(out):
 started=time.monotonic();NS=Path('/dev/shm/news2_2026-09-23');M=Path('/dev/shm/f10_recent_adapt_20260928_attempt2/models/R180_s42');train=json.loads((M/'TRAIN_RECEIPT.json').read_text());pins={**train['inputs'],**train['sources']}
 for p,h in pins.items():assert sha(p)==h,p
 F=np.load(NS/'work/NEWS_FEATURES.npz');T=np.load('/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz',allow_pickle=True);L=np.load(NS/'work/legs.npz');a=F['anchors'];sy=F['symbols'];off=F['off'];flat_m=F['m'];members=[flat_m[off[i]:off[i+1]].astype(int) for i in range(len(a))]
 ix=np.asarray(align_indices(T['E_ts'].tolist(),a.tolist()));good=ix>=0;y=np.full((len(a),len(sy)),np.nan,np.float32);y[good]=T['y4s'][ix[good]];ready=L['ready'];counts=np.diff(off);rows=[]
 for tag,start,end in fold_specs(a):
  if tag not in ('202607','202608','202609'):continue
  test=a[np.flatnonzero((a>=start)&(a<end))[0]];cut=int(test)-60*14400;wins=causal_windows(a.tolist(),ready.tolist(),counts.tolist(),cut);kept=[];rej=[]
  for win in wins:
   ok,why=span_admissible(members,y,win,ready)
   if ok:kept.append(win);continue
   i=why['anchor'];possible=set().union(*(set(members[j]) for j in win if j<=i));bad=sorted(s for s in possible if not np.isfinite(y[i,s]));assert bad and bad[0]==why['symbol']
   rej.append({'start':iso(a[win[0]]),'last_label_end':iso(a[win[-1]]+14400),'first_bad_anchor':iso(a[i]),'bad_symbols':[str(sy[s]) for s in bad],
       'current_member_bad':[str(sy[s]) for s in bad if s in members[i]],'held_only_bad':[str(sy[s]) for s in bad if s not in members[i]],
       'last_member_anchor':{str(sy[s]):iso(a[max(j for j in win if j<=i and s in members[j])]) for s in bad}})
  rr=json.loads((M/tag/'FOLD_RECEIPT.json').read_text())['admission'];assert len(wins)==rr['raw_windows'] and len(kept)==rr['accepted_windows'] and max(a[w[-1]]+14400 for w in kept)==rr['max_train_label_end']
  rows.append({'fold':tag,'test_start':iso(test),'allowed_cutoff':iso(cut),'latest_constructed_label_end':iso(max(a[w[-1]]+14400 for w in wins)),
    'latest_admitted_label_end':iso(rr['max_train_label_end']),'n_windows':len(wins),'n_admitted':len(kept),'rejected':rej})
 for p,h in pins.items():assert sha(p)==h,p
 x={'status':'ADMISSION_MECHANISM_ONLY_NOT_STRATEGY_EFFECT','source_sha256':sha(__file__),'input_pins':pins,'rows':rows,'wall_seconds':time.monotonic()-started,'utc':dt.datetime.now(dt.timezone.utc).isoformat()}
 with open(out,'x') as f:json.dump(x,f,indent=2,allow_nan=False)
 print(json.dumps(rows,ensure_ascii=False))
if __name__=='__main__':main(sys.argv[1])
