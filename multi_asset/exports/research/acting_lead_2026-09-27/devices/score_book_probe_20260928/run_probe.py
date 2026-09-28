"""Trace sealed score-to-book transformations. No candidates, trades or training."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import argparse,calendar,hashlib,json,sys,time,resource,signal
from pathlib import Path
import numpy as np
from scipy.stats import rankdata
from trace_chain import compile_trace,price_metric

R=Path('/workspace/codex_research/QNT-2026-0907/acting_lead_20260927/residual_book_20260928_attempt2')
S=Path(str(R)+'_sources')
STAGES=['rank_only','mixed_centered','ftrim_centered','demean','normalize','cap_normalize','ema','band','eligible','combo']
WINDOWS={'2023H2':('2023-07-01','2024-01-01'),'2024':('2024-01-01','2025-01-01'),'2025':('2025-01-01','2026-01-01'),'2026JanAug':('2026-01-01','2026-09-01'),'September':('2026-09-01','2026-09-19')}

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(4<<20),b''):h.update(b)
 return h.hexdigest()

def corr(x,y):
 if not np.isfinite(x).all() or not np.isfinite(y).all():return np.nan
 x=x-x.mean();y=y-y.mean();g=np.linalg.norm(x)*np.linalg.norm(y)
 return float(x@y/g) if g>0 else np.nan

def mean(a):
 a=np.asarray(a);return float(a.mean()) if len(a) and np.isfinite(a).all() else None

def run(out):
 limit=int(Path('/sys/fs/cgroup/memory.max').read_text());used=int(Path('/sys/fs/cgroup/memory.current').read_text())
 if limit-used<8*(1<<30):raise RuntimeError('RESOURCE_REFUSED: less than 8GiB headroom')
 if out.exists():raise FileExistsError(out)
 out.mkdir(); started=time.monotonic()
 signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('600s diagnostic budget')));signal.alarm(600)
 (out/'LAUNCH.json').write_text(json.dumps({'pid':os.getpid(),'pgid':os.getpgrp(),'ticks':Path('/proc/self/stat').read_text().split()[21],'utc':time.strftime('%FT%TZ',time.gmtime()),'resource_headroom_bytes':limit-used,'deadline_seconds':600,'source_sha256':sha(__file__)},indent=2))
 rc=1;result={}
 try:
  contract=json.loads((S/'CONTRACT.json').read_text());pins={str(S/f):h for f,h in contract['copied_sources'].items()}
  manifest=json.loads((R/'receipts/REVIEW_MANIFEST.json').read_text());large={x['path']:x['sha256'] for x in manifest['large_artifacts']}
  pm=json.loads((R/'receipts/PREDICTION_METRICS.json').read_text()) if (R/'receipts/PREDICTION_METRICS.json').exists() else json.loads((Path('/workspace/codex_research/QNT-2026-0907/acting_lead_20260927/residual_diagnostics_20260928')/'PREDICTION_METRICS.json').read_text())
  pins.update(pm['input_pins']);sys.path.insert(0,str(S))
  import alloc_combo as AC
  from residual_model import aligned_labels
  from book_universe import align,PATH,SHA
  cell=R/'cells/raw';rec=json.loads((cell/'work/combo_s42/TARGET_RECEIPT.json').read_text());pins.update(rec['inputs']);pins.update(rec['sources'])
  source=cell/'vendor_live/fea171/combo_stage.py';ns,traces=compile_trace(source.read_text());AC.source_kernels=lambda:ns
  for p,h in pins.items():
   if sha(p)!=h:raise ValueError('source/input drift '+p)
  F=np.load(cell/'work/NEWS_FEATURES.npz');a=F['anchors'];symbols=F['symbols'];nw=len(symbols);off=F['off'];mflat=F['m'];leg=np.load(cell/'work/legs.npz');
  if not np.array_equal(leg['E_ts'],a) or not np.array_equal(leg['symbols'],symbols):raise ValueError('leg axes')
  label_path=next(p for p in pm['input_pins'] if p.endswith('dlw_targets.npz'))
  with np.load(label_path,allow_pickle=True) as T:y=aligned_labels(a,symbols,T['E_ts'],T['symbols'],T['y4s'])
  universe=np.load(PATH);assert sha(PATH)==SHA;pins[PATH]=SHA
  use=(a>=1672531200)&(a<=universe['ts'][-1]);ix=np.flatnonzero(use);au=a[use];n=len(ix)
  mkpath=Path('/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz');mk=np.load(mkpath)
  if not np.array_equal(mk['ts'],a):raise ValueError('mask axes')
  crypto=np.load(cell/'receipts/P1_members_2025H2on.npz')['crypto'];legal=align(au,symbols,universe)&mk['mask'][use]&crypto[None,:]
  params=json.loads((cell/'inputs/bundle_config.json').read_text())['params']
  arrays={k:leg[k].astype(float) for k in ['KZ','ZFD','RN8','QV','WL']};ready=leg['ready'];summary={};all_metrics={};models={}
  for name in ['raw','resid','NC42','NC2027']:
   pred_path=Path(pm['models'][name]['path']);pins[str(pred_path)]=pm['models'][name]['sha256'];assert sha(pred_path)==pins[str(pred_path)]
   with np.load(pred_path) as P:
    if not np.array_equal(P['E_ts'],a) or not np.array_equal(P['symbols'],symbols):raise ValueError('pred axes')
    pred=P['P'].astype(float)
   if name in ('raw','resid'):
    target=R/f'cells/{name}/work/combo_s42/scaled_diagnostic.npz';expected=large[str(target)]
   else:
    seed=int(name[2:]);parent=Path(contract['parent_root']);cr=parent/f'receipts/ALLOC_CHAIN_inservice_shared_s{seed}.json'
    assert sha(cr)==contract['parent_receipts'][str(cr.relative_to(parent))]
    c=json.loads(cr.read_text());tr=Path(c['root'])/f'work/combo_s{seed}/TARGET_RECEIPT.json';assert sha(tr)==c['steps']['combo']['outputs']['TARGET_RECEIPT.json']
    old=json.loads(tr.read_text());target=Path(old['policies']['scaled_diagnostic']['path']);expected=old['policies']['scaled_diagnostic']['sha']
    old_pred=[v for k,v in old['inputs'].items() if k.endswith('F10_OOF.npz')];assert old_pred==[pins[str(pred_path)]]
   pins[str(target)]=expected;assert sha(target)==expected
   with np.load(target) as z:
    assert np.array_equal(z['E_ts'],au) and np.array_equal(z['symbols'],symbols)
    saved={k:z[k] for k in ['kc','fc','raw','trade_mask','weights','reason']}
   metrics=np.full((n,len(STAGES)),np.nan);loads=metrics.copy();stage_gross=metrics.copy();correlations=np.full((n,4),np.nan);gross_parts=np.full((n,4),np.nan);checks=0
   for j,i in enumerate(ix):
    if not ready[i]:continue
    m=mflat[off[i]:off[i+1]].astype(int);f=pred[i,m];k=arrays['KZ'][i,m];fund=arrays['ZFD'][i,m];rn=arrays['RN8'][i,m]
    prevk=saved['kc'][j-1] if j else np.zeros(nw);prevf=saved['fc'][j-1] if j else np.zeros(nw);traces.clear()
    v=AC.alloc_step(k,f,fund,arrays['WL'][i],rn,m,arrays['QV'][i,m],legal[j],params,prevk,prevf,'scaled_diagnostic','shared')
    for field in ['kc','fc']:
     val=np.where(np.abs(v[field])>1e-9,v[field],0.)
     if not np.array_equal(val,saved[field][j]):raise ValueError(f'parity {name}/{j}/{field}')
    if v['raw'] is None or not np.array_equal(v['raw'],saved['raw'][j]) or v['accepted']!=saved['trade_mask'][j] or v['reason']!=saved['reason'][j]:raise ValueError(f'parity {name}/{j}/raw_gate')
    expected_w=np.where(np.abs(v['raw'])>1e-9,v['raw'],0.) if v['accepted'] else np.zeros(nw)
    if not np.array_equal(expected_w,saved['weights'][j]):raise ValueError('weights mismatch')
    if len(traces)!=12:raise ValueError('observation count')
    checks+=1;zf=np.full(len(m),np.nan);fin=np.isfinite(f);zf[fin]=rankdata(f[fin])/max(fin.sum()-1,1)-.5
    w=v['seat_masked'];mix=w[0]*np.nan_to_num(zf)+w[2]*np.nan_to_num(fund);trim=np.where((mix<0)&np.isfinite(rn)&(rn<=-.001),0.,mix)
    def full(x):
     b=np.zeros(nw);b[m]=x;return b
    stages=[full(zf-zf.mean()),full(mix-mix.mean()),full(trim-trim.mean())]
    for label,x in traces[6:]:stages.append(full(x) if label in ('demean','normalize','cap_normalize') else x)
    stages.append(v['raw']);assert len(stages)==len(STAGES)
    for q,x in enumerate(stages):
     value=price_metric(x,y[i]);metrics[j,q]=np.nan if value is None else value
     load=price_metric(x,arrays['ZFD'][i]);loads[j,q]=np.nan if load is None else load/1e4
     stage_gross[j,q]=np.abs(x).sum()
    correlations[j]=[corr(f,k),corr(f,fund),corr(zf,k),corr(zf,fund)]
    kg=.55*np.abs(v['kc']).sum();fg=.45*np.abs(v['fc']).sum();g=np.abs(v['raw']).sum();cancel=kg+fg-g
    if cancel < -1e-12:raise ValueError('triangle identity')
    gross_parts[j]=[kg,fg,cancel,g]
   all_metrics[name]=metrics;models[name]=dict(price_label_bps=metrics,fund_rank_loading=loads,stage_gross=stage_gross,score_correlations=correlations,gross_parts=gross_parts,publish=saved['trade_mask'])
   summary[name]={'identity_verified_anchors':checks,'anchors':n};print(name,'identity',checks,flush=True)
  for wname,(lo,hi) in WINDOWS.items():
   mask=(au>=calendar.timegm(time.strptime(lo,'%Y-%m-%d')))&(au<calendar.timegm(time.strptime(hi,'%Y-%m-%d')))
   common=mask.copy()
   for data in models.values():common&=np.isfinite(data['price_label_bps']).all(axis=1)
   group={'window_anchors':int(mask.sum()),'common_all_models_all_stages_price_anchors':int(common.sum()),'models':{}}
   for name,data in models.items():
    gp=data['gross_parts'];cs=data['score_correlations'];okg=mask&np.isfinite(gp).all(1)
    group['models'][name]={'publish':int(data['publish'][mask].sum()),'stage_price_bps_common':{s:mean(data['price_label_bps'][common,j]) for j,s in enumerate(STAGES)},'stage_price_measurable':{s:int((mask&np.isfinite(data['price_label_bps'][:,j])).sum()) for j,s in enumerate(STAGES)},'gross_parts':dict(zip(['weighted_king_chain','weighted_f10_chain','cancellation','combined'],[mean(gp[okg,j]) for j in range(4)])),'score_correlations':{s:mean(cs[mask&np.isfinite(cs[:,j]),j]) for j,s in enumerate(['score_king','score_fund','rank_king','rank_fund'])},'fund_rank_loading':{s:mean(data['fund_rank_loading'][mask&np.isfinite(data['fund_rank_loading'][:,j]),j]) for j,s in enumerate(STAGES)}}
   summary[wname]=group
  for p,h in pins.items():
   if sha(p)!=h:raise ValueError('postflight drift '+p)
  file=out/'STAGES.npz';np.savez_compressed(file,E_ts=au,stages=np.array(STAGES),**{name+'__'+k:v for name,d in models.items() for k,v in d.items()})
  result=dict(status='DESCRIPTIVE_STAGE_PROBE_NOT_CASH_OR_NEW_CANDIDATE',source_sha256=sha(__file__),helper_sha256=sha(Path(__file__).with_name('trace_chain.py')),pins=pins,windows=WINDOWS,results=summary,artifact_sha256=sha(file),limits=['price=next raw4h label of ideal current weights, not execution PnL; excludes funding/fees','common all-stage finite anchors reported; not hidden zero for absent labels','HOLD target never counted as cash; combo is intended prepublication vector','shared previous state per original model; not a fixed-state causal ablation','historical NC membership/publication policy only; not current production certification'],python=sys.executable,numpy=np.__version__);rc=0
 except BaseException as e:result=dict(status='FAILED',error=repr(e));raise
 finally:
  result.update(rc=rc,utc=time.strftime('%FT%TZ',time.gmtime()),seconds=time.monotonic()-started,max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
  with open(out/'TERMINAL.json','x') as f:json.dump(result,f,indent=2,allow_nan=False)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);run(p.parse_args().out)
