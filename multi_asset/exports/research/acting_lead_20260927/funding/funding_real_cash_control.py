#!/usr/bin/env python3
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
import sys,pathlib,json,hashlib,time,resource,collections,bisect
T0=time.time();ROOT=pathlib.Path('/Users/haosiyu/.codex/worktrees/acting-lead-20260927/quant_research');SRC=ROOT/'multi_asset/exports/research/replay_exec_2026-09-19';MIR='/Users/haosiyu/quant_mirrors/replay_exec_mirror_59875e5a'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
assert sha(SRC/'exec_sim.py')=='29679672e68d4842a62616e40c5fc57143f724b9ebfa6bbde927670624247c24'
assert sha(SRC/'INPUT_MANIFEST.json')=='59875e5a69db415f5ce20b35b888f2d49a31427fdde8b7b847a9645ee135a5ae'
calpath=SRC/'CALIBRATION_v3_POOLED_20260826_20260910.json';assert sha(calpath)=='fda342431d39703e8a2cc49d566f0cdd89155248c1f7bd46a6e46b3ffbc937e6'
refpath=SRC/'SIM_v31_live_CAL_continuous_20260826_20260918_PATHS/seed_02.json';REF=json.loads(refpath.read_text());ref=REF['windows'][:6]
sys.path.insert(0,str(SRC));import exec_sim as ES
L=ES.L;M=ES.WideMirror(MIR);M.manifest=json.loads((SRC/'INPUT_MANIFEST.json').read_text());bad=M.verify_manifest();assert not bad,bad[:5]
treebad=[p for p,h in M.manifest['executor_tree']['files_sha256'].items() if sha(pathlib.Path(MIR)/p)!=h];assert not treebad,treebad[:5]
# The same inherited safety guard blocks subprocess/network/production tree opens during simulation.
L.install_readonly_guard()
cal=json.loads(calpath.read_text());Wall=ES.live_windows_from(L.LIVE_G);xf=ES.transfers_from(L.INCOME_TRANSFER)
S=ES.Sim(M,cal,'live',{k:False for k in ES.KNOBS},seed=2,run_start_anchor=REF['run_start_anchor'],last_anchor=L.nominal(ref[-1]['t0']),windows=Wall,transfers=xf)
assert S.sealed_sha==REF['initial_state_sha256'],('initial state',S.sealed_sha,REF['initial_state_sha256'])
W=S.run();assert len(W)==6
maxwin=0.
for a,b in zip(W,ref):
 assert a.keys()==b.keys()
 for k in a:
  if isinstance(a[k],(int,float)):
   maxwin=max(maxwin,abs(a[k]-b[k]));assert abs(a[k]-b[k])<=1e-8,(k,a[k],b[k])
  else:assert a[k]==b[k],(k,a[k],b[k])
# Independently reconstruct quantities from initial state and the executed fill tape.
tr=sorted(S.trade_log,key=lambda x:x[0]);fu=sorted(S.fund_log,key=lambda x:x[0]);q=collections.defaultdict(float,S.sealed['positions_qty']);ti=0;records=[];dqerr=0.;casherr=0.;priceerr=0.
for t,s,logged_q,logged_P,logged_r,logged_f in fu:
 while ti<len(tr) and tr[ti][0]<t:
  x=tr[ti];q[x[1]]+=x[2];ti+=1
 rate=S.F.rate[(s,int(t))];px=S.P.px(s,L.floor_b(t));assert px is not None
 calc=-q[s]*px*rate
 dqerr=max(dqerr,abs(q[s]-logged_q));casherr=max(casherr,abs(calc-logged_f));priceerr=max(priceerr,abs(px-logged_P))
 assert abs(q[s]-logged_q)<=1e-8 and abs(calc-logged_f)<=1e-8,(s,t,q[s],logged_q,calc,logged_f)
 records.append({'t':t,'s':s,'q':q[s],'price':px,'rate':rate,'cash':calc})
windowcash=[]
for w in W:
 got=sum(x['cash'] for x in records if w['t0']<x['t']<=w['t1']);assert abs(got-w['funding'])<1e-8,(got,w['funding']);windowcash.append({'t0':w['t0'],'t1':w['t1'],'independent_cash':got,'canonical_cash':w['funding']})
# Fixed executed path: perturb one dq, leave all later fills unchanged; no counterfactual replanning implied.
chosen=None
for fill in tr:
 future=[x for x in records if x['s']==fill[1] and x['t']>fill[0]]
 if future:
  chosen=fill;break
assert chosen is not None
cf=sum(x['cash'] for x in records);eps=1e-4
later=[x for x in records if x['s']==chosen[1] and x['t']>chosen[0]];deriv=-sum(x['price']*x['rate'] for x in later)
plus=sum(-(x['q']+(eps if x['s']==chosen[1] and x['t']>chosen[0] else 0))*x['price']*x['rate'] for x in records)
minus=sum(-(x['q']-(eps if x['s']==chosen[1] and x['t']>chosen[0] else 0))*x['price']*x['rate'] for x in records)
fd=(plus-minus)/(2*eps);assert abs(fd-deriv)<1e-8,(fd,deriv)
# Entry cash and end mark share the same actual fill; carry is evaluated only after the fill.
endpx=S.P.px(chosen[1],L.floor_b(W[-1]['t1']));assert endpx is not None
out={'utc_start':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(T0)),'utc_end':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'verdict':'FIXED_CANONICAL_PATH_CASH_PASS','mirror':MIR,'manifest_sha':sha(SRC/'INPUT_MANIFEST.json'),'manifest_files_verified':len(M.manifest['files']),'tree_files_verified':len(M.manifest['executor_tree']['files_sha256']),'reference_path':str(refpath),'reference_sha':sha(refpath),'source_sha':sha(SRC/'exec_sim.py'),'calibration_sha':sha(calpath),'initial_state_sha':S.sealed_sha,'max_window_difference':maxwin,'max_quantity_difference':dqerr,'max_cash_difference':casherr,'max_price_difference':priceerr,'windows':windowcash,'linear_carry':{'chosen_actual_fill':chosen,'future_settlements':len(later),'cash_derivative_per_qty':deriv,'finite_difference_per_qty':fd,'price_derivative_per_qty_same_fill_to_end':endpx-chosen[3],'fill_price':chosen[3],'end_price':endpx,'pre_fill_carry_derivative':0.,'interpretation':'fixed later trade tape, no policy/stop replanning derivative'},'initial_state':S.sealed,'trade_log':S.trade_log,'fund_log':S.fund_log,'independent_funding':records,'funding_source_crosscheck':S.F.xcheck,'wall_seconds':time.time()-T0,'rss_max_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'limitations':['Mac ru_maxrss bytes; this fixed historical execution prefix is not September NC/D10 strategy efficacy','Seconds source contract unchanged; no D10 milliseconds injected','Independent quantity reconstruction and canonical price source, not independent price oracle','No GPU training; previous authorization expired']}
print(json.dumps(out,indent=1,allow_nan=False,default=lambda x:x.item() if hasattr(x,'item') else str(x)))
