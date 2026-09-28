"""Isolated raw archive panel and exact same-code channel comparison; no venue access."""
from pathlib import Path
import ast,csv,datetime as dt,hashlib,io,json,math,sys,time,zipfile
import numpy as np
import download as D

def sha(p):
 with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def extract_functions(p):
 tree=ast.parse(Path(p).read_text());selected=[]
 for n in tree.body:
  if isinstance(n,ast.FunctionDef) and n.name in ('bars_to_channels','clipch'):selected.append(n)
  if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CHN_CLIPS' for t in n.targets):selected.append(n)
 if len(selected)!=3:raise ValueError('producer source structure')
 scope={'np':np,'math':math};exec(compile(ast.Module(body=selected,type_ignores=[]),str(p),'exec'),scope)
 return scope['bars_to_channels'],scope['clipch']
def validate_axis(a,b,n):
 if len(a)!=n or len(a)!=len(set(a)) or a!=b or any(not isinstance(s,str) for s in a):raise ValueError('axis identity')
def make_rows(rows,bar,clip):
 times=[];prices=[];channels=[];valid=[];pt=None;pc=None
 for r in rows:
  t=(int(r[0])+300000)//1000
  if pt is not None and t<=pt:raise ValueError('duplicate/backwards time')
  c,ch=bar(r);ok=pt is not None and t==pt+300 and math.isfinite(pc) and pc>0
  ch[0]=c/pc-1 if ok else np.nan
  times.append(t);prices.append(c);channels.append(clip(ch));valid.append(ok);pt=t;pc=c
 return np.asarray(times,np.int64),np.asarray(prices,np.float64),np.asarray(channels,np.float16),np.asarray(valid,bool)
def compare(a,b,mask):
 if a.shape!=b.shape or a.shape!=mask.shape or mask.dtype!=bool:raise ValueError('comparison shape/type')
 af=np.isfinite(a);bf=np.isfinite(b);both=mask&af&bf;dv=both&(a!=b)
 return {'population':int(mask.sum()),'both_finite':int(both.sum()),'both_missing':int((mask&~af&~bf).sum()),'left_missing_right_finite':int((mask&~af&bf).sum()),'left_finite_right_missing':int((mask&af&~bf).sum()),'value_differences':int(dv.sum()),'max_abs_difference':float(np.max(np.abs(a[dv].astype(float)-b[dv].astype(float)))) if dv.any() else 0.0}
def run(root):
 root=Path(root);cp=root/'CONTRACT.json';C=json.loads(cp.read_text());start=time.monotonic();pins={str(cp):sha(cp)}
 if C['device_sha256']!=sha(__file__) or C['validator_sha256']!=sha(D.__file__):raise ValueError('device identity')
 for name,r in C['copied_sources'].items():
  p=root/name
  if sha(p)!=r['sha256']:raise ValueError('copied source changed')
  pins[str(p)]=sha(p)
 archive=Path(C['archive'])
 if sha(archive)!=C['archive_sha256']:raise ValueError('raw archive identity')
 pins[str(archive)]=C['archive_sha256']
 snap=Path(C['snapshot']);gp=snap/'generation.json'
 if sha(gp)!=C['snapshot_generation_sha256']:raise ValueError('snapshot generation identity')
 generation=json.loads(gp.read_text());pins[str(gp)]=sha(gp)
 for name,r in generation['files'].items():
  p=snap/name
  if sha(p)!=r['sha256']:raise ValueError('snapshot file identity')
  pins[str(p)]=sha(p)
 cfg=json.loads((root/'bundle_config.json').read_text());cr=json.loads((root/'crypto_axis.json').read_text());aux=json.loads((snap/'aux.json').read_text())
 with np.load(snap/'rolling.npz',allow_pickle=False) as z:live_t=z['ts'];live=z['data']
 axis=cfg['symbols_panel'];validate_axis(axis,cr['symbols'],live.shape[1])
 if live.dtype!=np.float16 or live.shape!=(len(live_t),len(axis),7) or live_t.dtype.kind not in 'iu' or np.any(np.diff(live_t)!=300):raise ValueError('rolling schema')
 if int(live_t[-1])!=generation['anchor_ts'] or aux['last_anchor']!=generation['anchor_ts']:raise ValueError('snapshot cutoff')
 bar,clip=extract_functions(root/'producer.py');examples=[]
 with zipfile.ZipFile(archive) as za:
  manifest=json.loads(za.read('ARCHIVE_MANIFEST.json'))
  if len(za.namelist())!=len(set(za.namelist())):raise ValueError('duplicate member')
  def read(name):
   b=za.read(name);m=manifest[name]
   if len(b)!=m['bytes'] or D.digest(b)!=m['sha256']:raise ValueError('inner archive member identity')
   return b
  merged=json.loads(read('RECENT_PUBLIC_PRICES_MERGED_20260928.json'))
  if merged['status']!='REQUEST_POPULATION_CLOSED_WITH_EXPLICIT_ABSENCES':raise ValueError('unfinished collection')
  symbols=axis+sorted({r['symbol'] for r in merged['results']}-set(axis));days=sorted(merged['by_day'])
  if {(r['symbol'],r['day']) for r in merged['results']}!={(s,d) for s in symbols for d in days}:raise ValueError('request population')
  start_ts=int(dt.datetime.fromisoformat(days[0]).replace(tzinfo=dt.timezone.utc).timestamp())+300
  end_ts=int(dt.datetime.fromisoformat(days[-1]).replace(tzinfo=dt.timezone.utc).timestamp())+86400
  ts=np.arange(start_ts,end_ts+1,300,dtype=np.int64)
  raw=np.full((len(ts),len(symbols)),np.nan);data=np.full((*raw.shape,7),np.nan,dtype=np.float16);observed=np.zeros(raw.shape,bool);ret_ok=np.zeros(raw.shape,bool)
  by_symbol={s:[] for s in symbols};absent=[];zero_volume_bars=0
  for r in merged['results']:
   if r['status']=='ARCHIVE_ABSENT':absent.append({'symbol':r['symbol'],'day':r['day']});continue
   if r['status']!='VERIFIED_ARCHIVE':raise ValueError('nonterminal archive record')
   name=r['file'].removeprefix('/dev/shm/');b=read(name);check=read(name+'.CHECKSUM');D.validate(b,check.decode(),r['symbol'],r['day'])
   with zipfile.ZipFile(io.BytesIO(b)) as zz:rows=list(csv.reader(io.StringIO(zz.read(zz.namelist()[0]).decode())))
   if rows and rows[0][0]=='open_time':rows=rows[1:]
   zero_volume_bars+=sum(float(x[7])==0 for x in rows)
   by_symbol[r['symbol']].extend(rows)
  for j,s in enumerate(symbols):
   if time.monotonic()-start>C['budget_seconds']:raise TimeoutError('frozen time budget')
   if not by_symbol[s]:continue
   t,p,ch,v=make_rows(by_symbol[s],bar,clip);ix=np.searchsorted(ts,t)
   if np.any(ix>=len(ts)) or not np.array_equal(ts[ix],t) or observed[ix,j].any():raise ValueError('row alignment')
   raw[ix,j]=p;data[ix,j]=ch;observed[ix,j]=True;ret_ok[ix,j]=v
  overlap=(ts>=live_t[0])&(ts<=live_t[-1]);tt=ts[overlap];ii=np.searchsorted(live_t,tt)
  if not np.array_equal(live_t[ii],tt):raise ValueError('overlap time identity')
  x=data[overlap,:len(axis),:];y=live[ii];obs=observed[overlap,:len(axis)];mask=np.broadcast_to(obs[:,:,None],x.shape).copy();mask[:,:,0]&=ret_ok[overlap,:len(axis)]
  channels=['ret5','range','close_position','log_quote_volume','log_count','log_average_trade','taker_buy_fraction']
  global_stats={c:compare(x[:,:,k],y[:,:,k],mask[:,:,k]) for k,c in enumerate(channels)}
  daily={}
  day_values=np.array([dt.datetime.fromtimestamp(int(t)-1,dt.timezone.utc).date().isoformat() for t in tt])
  for d in days:
   sel=day_values==d;daily[d]={c:compare(x[sel,:,k],y[sel,:,k],mask[sel,:,k]) for k,c in enumerate(channels)}
  mismatch=mask&((np.isfinite(x)!=np.isfinite(y))|(np.isfinite(x)&np.isfinite(y)&(x!=y)))
  for k,c in enumerate(channels):
   ix=np.argwhere(mismatch[:,:,k]);
   for a,j in ix[:10]:examples.append({'channel':c,'symbol':axis[j],'close_ts':int(tt[a]),'official':float(x[a,j,k]) if np.isfinite(x[a,j,k]) else None,'production':float(y[a,j,k]) if np.isfinite(y[a,j,k]) else None})
  counts_by_symbol=[{'symbol':s,'matched_values':int((mask[:,j,:]&np.isfinite(x[:,j,:])&np.isfinite(y[:,j,:])&(x[:,j,:]==y[:,j,:])).sum()),'value_differences':int((mask[:,j,:]&np.isfinite(x[:,j,:])&np.isfinite(y[:,j,:])&(x[:,j,:]!=y[:,j,:])).sum()),'official_finite_production_missing':int((mask[:,j,:]&np.isfinite(x[:,j,:])&~np.isfinite(y[:,j,:])).sum()),'official_missing_production_finite':int((mask[:,j,:]&~np.isfinite(x[:,j,:])&np.isfinite(y[:,j,:])).sum())} for j,s in enumerate(axis)]
  panel=root/'RAW_AND_PRODUCTION_CHANNELS.npz'
  with panel.open('xb') as f:np.savez_compressed(f,ts=ts,symbols=np.asarray(symbols),close=raw,data=data,observed=observed,ret5_eligible=ret_ok)
  result={'utc':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'PARITY' if not mismatch.any() else 'DIFFERS','scope':'raw observed bars only; absent archives explicitly unmeasured; first ret5 without prior raw close excluded','source_sha256':sha(__file__),'validator_sha256':sha(D.__file__),'python':sys.executable,'numpy':np.__version__,'elapsed_seconds':time.monotonic()-start,'input_pins':pins,'output':{'path':str(panel),'sha256':sha(panel),'bytes':panel.stat().st_size},'n_times':len(ts),'n_symbols':len(symbols),'n_production_axis':len(axis),'extra_axis_symbols':symbols[len(axis):],'n_observed_bars':int(observed.sum()),'n_zero_quote_volume_bars':zero_volume_bars,'channels':global_stats,'by_day':daily,'by_symbol':counts_by_symbol,'examples':examples,'absent_archives':absent,'production_finite_without_archive_observation':int((~obs[:,:,None]&np.isfinite(y)).sum()),'limits':C['limits']+['same feature functions, not all production fetch/backfill/arrival semantics','no funding/tradability/continuous-book joining yet; no economic conclusion']}
  D.write(root/'RESULT.json',(json.dumps(result,indent=2,allow_nan=False)+'\n').encode());D.write(root/'TERMINAL.json',(json.dumps({'rc':0,'status':'COMPARISON_COMPLETE','verdict':result['status'],'result_sha256':sha(root/'RESULT.json'),'utc':result['utc']},indent=2)+'\n').encode());print({k:result[k] for k in ('status','elapsed_seconds','n_times','n_symbols','n_observed_bars','channels','production_finite_without_archive_observation')})
if __name__=='__main__':
 try:run(sys.argv[1])
 except BaseException as e:
  root=Path(sys.argv[1]);D.write(root/'TERMINAL.json',(json.dumps({'rc':1,'status':'FAILED','error':repr(e)},indent=2)+'\n').encode());raise
