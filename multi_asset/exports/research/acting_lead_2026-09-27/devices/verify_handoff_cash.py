"""Independent saved-path verification; does not import runner or metric helper."""
import hashlib,json,sys
from decimal import Decimal as D
from pathlib import Path
import numpy as np

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(4<<20),b''):h.update(b)
 return h.hexdigest()

def main(root):
 root=Path(root);r=json.loads((root/'RESULT.json').read_bytes());t=json.loads((root/'TERMINAL.json').read_bytes())
 if t!={'rc':0,'result_sha256':sha(root/'RESULT.json')}:raise ValueError('terminal')
 if len(r['paths'])!=256:raise ValueError('path_population')
 for p,h in r['inputs'].items():
  if sha(p)!=h:raise ValueError('input_identity:'+p)
 checks=0;maxerr=0.;independent={}
 def check(x,y,tol=1e-8):
  nonlocal checks,maxerr
  d=abs(float(x)-float(y));checks+=1;maxerr=max(maxerr,d)
  if not np.isfinite(d) or d>tol:raise ValueError('numeric_mismatch:'+str((x,y)))
 def derive(p,start,end):
  axes=list(map(int,p['A']));selected=[i for i,a in enumerate(axes) if start<=a<end]
  if [axes[i] for i in selected]!=list(range(start,end,14400)):raise ValueError('clock_population')
  out={};ident=0.
  for k in ('price_trade','funding','fee','turnover','unk_held','unk_notional','n_stop_events','n_flatten_events'):
   out[k]=float(sum((D(str(float(p[k][i]))) for i in selected),D(0)))
  for i in selected:
   d=D(str(float(p['nav1'][i])))-D(str(float(p['nav0'][i])))
   x=sum((D(str(float(p[k][i])))*sgn for k,sgn in [('price_trade',1),('funding',1),('fee',-1),('transfer',1)]),D(0))
   check(d,x,1e-6);ident=max(ident,abs(float(d-x)))
  j0=(start-int(p['nav5_t0']))//300;j1=(end-int(p['nav5_t0']))//300
  nav=p['nav5_main'][j0:j1+1]
  if len(nav)!=(end-start)//300+1 or not np.isfinite(nav).all() or min(nav)<=0:raise ValueError('NAV_coverage')
  peak=D(str(float(nav[0])));worst=D(0)
  for v in nav:
   x=D(str(float(v)));peak=max(peak,x);worst=min(worst,x/peak-1)
  out['maxdd_5m']=float(worst);out['compound']=float(D(str(float(nav[-1])))/D(str(float(nav[0])))-1)
  product=D(1)
  for i in selected:product*=D(str(float(p['navm1'][i])))/D(str(float(p['navm0'][i])))
  check(product-1,out['compound'],1e-10)
  out['halt_anchors']=sum(int(p['status'][i])==1 for i in selected);out['hold_anchors']=sum(int(p['status'][i])==2 for i in selected)
  out['priced_complete']=out['unk_held']==out['unk_notional']==0
  return out
 for cell in ('base','fee_x1.25','slip_x1.5','fill_x0.9'):
  rows=r['results'][cell]
  if [x['execution_seed'] for x in rows]!=list(range(32)):raise ValueError('seed_population')
  independent[cell]=[]
  for row in rows:
   pair={};read={}
   for arm in ('B','S'):
    label=f'{cell}_{arm}_{row["execution_seed"]:02d}';desc=r['paths'][label]
    p=root/(label+'.npz')
    if sha(p)!=desc['sha256']:raise ValueError('output_identity')
    with np.load(p,allow_pickle=False) as z:a={k:z[k] for k in z.files}
    if not np.array_equal(a['A'],np.arange(1790222400,1790553600,14400)):raise ValueError('full_axis')
    read[arm]=a;pair[arm]=derive(a,1790236800,1790553600)
    first=derive(a,1790236800,1790251200)
    for k,v in pair[arm].items():check(v,row['arms'][arm][k])
    for k,v in first.items():check(v,row['first_switch_window'][arm][k])
   for k in ('nav0','nav1','fee','funding','price_trade','turnover'):
    if read['B'][k][0].tobytes()!=read['S'][k][0].tobytes():raise ValueError('common_window')
   if read['B']['nav5_main'][:49].tobytes()!=read['S']['nav5_main'][:49].tobytes():raise ValueError('common_NAV')
   independent[cell].append(pair)
  for k,stats in r['summary'][cell].items():
   if k=='priced_complete':
    if stats!=all(p[a][k] for p in independent[cell] for a in ('B','S')):raise ValueError('priced_complete')
    continue
   b=[D(str(p['B'][k])) for p in independent[cell]];s=[D(str(p['S'][k])) for p in independent[cell]];d=[y-x for x,y in zip(b,s)]
   expected={'B_mean':sum(b)/32,'S_mean':sum(s)/32,'paired_delta_mean':sum(d)/32,'paired_delta_min':min(d),'paired_delta_max':max(d)}
   for key,v in expected.items():check(v,stats[key])
 out={'status':'INDEPENDENT_SAVED_CASH_DECIMAL_PASS','checks':checks,'max_abs_error':maxerr,'paths':256,'pairs':128,'result_sha256':sha(root/'RESULT.json'),'source_sha256':sha(__file__),'limits':['Verifies saved accounting and aggregation, not an independent execution engine','Hypothetical shared inventory setup, historical research H prefix, exploratory window','Execution seeds are not independent market samples; no release inference']}
 (root/'VERIFY.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main(sys.argv[1])
