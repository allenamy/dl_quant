"""Materialize predefined peer-flow/funding interactions on corrected D10 inputs."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
from pathlib import Path
import json,sys,time,traceback,resource
import numpy as np
from price_panel import sha
from peer_features import fit_graph,transform,loo_market
from flow_funding import window_mean,fund_asof,peer_flows,past_mad,OWN_NAMES,NEW_NAMES

def main(root,contract_path):
 started=time.monotonic();root=Path(root);root.mkdir(exist_ok=False);C=json.loads(Path(contract_path).read_text());pins=C['inputs']
 for p,h in pins.items():
  if sha(p)!=h:raise ValueError('input identity '+p)
 for n,h in C['helpers'].items():
  if sha(Path(__file__).with_name(n))!=h:raise ValueError('helper identity '+n)
 fr=json.loads(Path(C['paths']['fund_receipt']).read_text())
 assert fr['mode']=='d10' and fr['output']['sha256']==pins[C['paths']['fund_state']]
 assert fr['self_sha256']==pins[C['paths']['fund_source']] and fr['rule_module_sha256']==pins[C['paths']['fund_rule']]
 assert fr['nc_contract'][1]==pins[C['paths']['ema_source']] and fr['inputs']['ledger_ms'][1]==pins[C['paths']['ledger_ms']]
 assert fr['rebuild_device_sha256']==pins[C['paths']['fund_rebuild']]
 pz=np.load(C['paths']['price_panel']);A=pz['anchors'];sy=pz['symbols'];r4=pz['r4'];r24=pz['r24'];legal=pz['legal'];PX=pz['X'];scale=pz['scale'];betas=pz['beta']
 n=len(sy);ax=np.load(C['paths']['old_axes']);cols=ax['crypto_cols'];ts=ax['ts'];nx=np.load(C['paths']['new_axes']);nts=nx['ts']
 assert np.array_equal(sy,ax['symbols']) and np.array_equal(sy,nx['symbols']) and np.array_equal(cols,nx['crypto_cols'])
 assert np.all(np.diff(ts)==300) and np.all(np.diff(nts)==300)
 flow=np.full((len(A),n),np.nan);vol=np.full_like(flow,np.nan)
 for key,tt,use in [('old_cache',ts,A<=ts[-1]),('new_cache',nts,A>ts[-1])]:
  cache=np.load(C['paths'][key],mmap_mode='r');aa=A[use];ends=np.searchsorted(tt,aa);assert np.array_equal(tt[ends],aa)
  for b in range(0,len(cols),64):
   g=cols[b:b+64]
   f=np.array(cache[:,b:b+64,6],dtype=float);f[(f<0)|(f>1)]=np.nan
   v=np.array(cache[:,b:b+64,3],dtype=float);v[v<0]=np.nan
   flow[np.ix_(use,g)]=window_mean(f,ends,48)-window_mean(f,ends-48,288)
   vol[np.ix_(use,g)]=window_mean(v,ends,48)-window_mean(v,ends-48,2016)
  del cache
 # D10 state has the full event axis to Sep27 but an old convenience kidx to Sep19.
 # Select from event times ourselves, never extrapolate a stale rate or read future events.
 ff=np.load(C['paths']['fund_state']);F={k:ff[k] for k in ('cols','ev_off','ft','rate','iv','ema')};assert np.array_equal(cols,F['cols'])
 funds=np.full((len(A),n,3),np.nan)
 for ci,j in enumerate(cols):
  b,e=F['ev_off'][ci:ci+2];ft=F['ft'][b:e];assert np.all(np.diff(ft)>=0)
  ix=np.searchsorted(ft,A,side='right')-1;ok=ix>=0;ii=b+ix[ok]
  funds[ok,j]=fund_asof(A[ok],F['ft'][ii],F['rate'][ii],F['iv'][ii],F['ema'][ii])
 # Member-cell as-of values must equal the independently archived D10 feature build.
 dz=np.load(C['paths']['d10_features']);da=dz['anchors'];dm=dz['m'];dc=dz['count'];dr=np.repeat(np.arange(len(da)),dc);take=(da[dr]>=A[0])&(da[dr]<=A[-1]);dd=dr[take];ii=np.searchsorted(A,da[dd]);jj=dm[take]
 for got,want in ((funds[ii,jj,1],dz['fe_v'][take]),(funds[ii,jj,2],dz['fn_v'][take])):
  assert np.array_equal(got,want,equal_nan=True),'D10 feature parity'
 del dz,dm,dr,dd,ii,jj
 own=np.full((len(A),n,8),np.nan,np.float32);out=np.full((len(A),n,3),np.nan,np.float32);graphs=[];days=[];last=None;nan=np.full(n,np.nan);graph_checks=0
 for i,a in enumerate(A):
  if a<C['feature_start']:continue
  if time.monotonic()-started>C['budget_seconds']:raise TimeoutError('flow panel budget')
  day=int(a//86400*86400)
  if day!=last:
   G=fit_graph(A,r4,legal,sy,day,**C['graph']);last=day;days.append(day);graphs.append(G['peers'].astype(np.int16))
   fm,fs=past_mad(A,np.where(legal,flow,np.nan),day);vm,vs=past_mad(A,np.where(legal,vol,np.nan),day)
  v=transform(G,int(a),r4=r4[i],r24=r24[i],flow_delta=nan,qv_anomaly=nan,fund8=nan,ema8=nan,active=legal[i])
  assert np.array_equal(v['X'][:,:4].astype(np.float32),PX[i],equal_nan=True),'price graph changed';graph_checks+=1
  e4=r4[i]-G['beta']*loo_market(r4[i],legal[i]&np.isfinite(r4[i]),G['min_market'])
  e24=r24[i]-G['beta']*loo_market(r24[i],legal[i]&np.isfinite(r24[i]),G['min_market'])
  rn,em,raw=funds[i].T
  fd=(flow[i]-fm)/fs;vd=(vol[i]-vm)/vs
  own[i]=np.c_[raw,em,rn,np.maximum(-rn,0),e4/G['scale'],e24/(G['scale']*np.sqrt(6)),fd,vd]
  out[i,:,:2]=peer_flows(G['peers'],legal[i],fd,vd,G['min_peers'])
  out[i,:,2]=np.maximum(-rn,0)*PX[i,:,0]
  if i%600==0:print('anchor',int(a),'elapsed',round(time.monotonic()-started,2),flush=True)
 output=root/'FLOW_FUND_PEERS.npz';np.savez_compressed(output,anchors=A,symbols=sy,X=out,own=own,price=PX,graph_days=np.array(days),peers=np.array(graphs),y4_raw=pz['y4_raw'],legal=legal)
 for p,h in pins.items():
  if sha(p)!=h:raise ValueError('input drift '+p)
 res={'status':'PANEL_COMPLETE_NOT_SIGNAL_EVIDENCE','utc':time.strftime('%FT%TZ',time.gmtime()),'source_sha256':sha(__file__),'contract_sha256':sha(contract_path),'inputs':pins,'helpers':C['helpers'],'outputs':{output.name:sha(output)},'candidate_columns':list(NEW_NAMES),'own_control_columns':list(OWN_NAMES),'shape':list(out.shape),'price_graph_equal_anchors':graph_checks,'d10_member_funding_parity':int(take.sum()),'feature_cutoff_convention':'D10 uses event seconds <= anchor; original ms within same second included, still before A+24m decision','eval_end':C['eval_end'],'funding_snapshot_final_event':int(F['ft'].max()),'seconds':time.monotonic()-started,'peak_rss_gib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20,'limits':['No trading or candidate returns','D10 interval convention differs from live NC by design, not deployed','Quote flow is f16 production channel, not exact dollar flow','Price-family graph recomputed unchanged to archive reusable identities']}
 (root/'RESULT.json').write_text(json.dumps(res,indent=2,allow_nan=False)+'\n');(root/'TERMINAL.json').write_text(json.dumps({'rc':0,'result_sha256':sha(root/'RESULT.json')})+'\n');print('FLOW PANEL COMPLETE',res['seconds'],flush=True)

if __name__=='__main__':
 try:main(*sys.argv[1:])
 except BaseException as e:
  root=Path(sys.argv[1]);root.mkdir(exist_ok=True);(root/'TERMINAL.json').write_text(json.dumps({'rc':1,'error':repr(e),'traceback':traceback.format_exc()},indent=2)+'\n');raise
