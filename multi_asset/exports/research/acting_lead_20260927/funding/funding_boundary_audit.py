#!/usr/bin/env python3
# Follow-up predicate frozen 2026-09-27 16:02:35 UTC: exact decomposition only, no strategy outcomes.
import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
import numpy as np,json,hashlib,time,resource
START=time.time()
def sha(p):return hashlib.sha256(open(p,'rb').read()).hexdigest()
paths={
 'old':('/workspace/uplift_r2_2026-09-13/P2/work/ledger_full.npz','bea6f5752772d54e659a4da5571ca41945a27d1b2316ec0ae52f387074f795ad'),
 'new':('/workspace/d10_reread_2026-09-27/r2b_20260927T113701Z/r2/ledger_full_ms_ext_20260927T08.npz','76b777bf07d5b3630e9d4818b562cd798f1ca495af8af190c8f24421c9b538db'),
 'label':('/workspace/dlarch_2026-09-24/king_fam_2026-09-27/T_NET.npz','929ff9f6c68280f1994ffb3c34c0c53114d96ad034686183f9dfd9b09b5c7a5c')}
for p,h in paths.values():assert sha(p)==h
z={k:np.load(p,allow_pickle=False) for k,(p,h) in paths.items()};A=z['label']['E_ts'];S=z['label']['symbols'];Fc=z['label']['F'];cov=z['label']['covered'];A=A[cov];Fc=Fc[cov]
for k in ['old','new']:assert np.array_equal(z[k]['symbols'],S)
N=z['new'];O=z['old'];nf=N['ft_ms'];nr=N['rate'];no=N['off'];of=O['ft'];orr=O['rate'];oo=O['off']
counts={k:0 for k in ['changed_total','changed_ms_boundary','changed_extra_event_or_rate','old_label_not_exact_rate_sum','left_nonzero','right_nonzero','both_nonzero','extra_only','boundary_only','both_sources']};maxima={k:0. for k in ['decomposition_error','old_label_error','prefix_collapsed_error','left_rate_max','right_rate_max']};examples=[];extracount=0
for j,s in enumerate(S):
 ft=nf[no[j]:no[j+1]];rt=nr[no[j]:no[j+1]];oldft=of[oo[j]:oo[j+1]];oldrt=orr[oo[j]:oo[j+1]]
 def sumat(t,r,left,right):
  cc=np.r_[0.,np.cumsum(r)];return cc[np.searchsorted(t,right,'right')]-cc[np.searchsorted(t,left,'right')]
 old=sumat(oldft,oldrt,A,A+14400);ms=sumat(ft,rt,A*1000,(A+14400)*1000);floor=sumat(ft//1000,rt,A,A+14400)
 # These are literal boundary event-rate sums, not a subtraction of aggregate F arrays.
 left=np.zeros(len(A));right=np.zeros(len(A))
 for k,t in enumerate(A):
  left[k]=rt[(ft>t*1000)&(ft<(t+1)*1000)].sum();right[k]=rt[(ft>(t+14400)*1000)&(ft<(t+14401)*1000)].sum()
 boundary=left-right;extra=floor-old;delta=ms-Fc[:,j]
 maxima['decomposition_error']=max(maxima['decomposition_error'],float(np.max(np.abs(delta-boundary-extra))))
 maxima['old_label_error']=max(maxima['old_label_error'],float(np.max(np.abs(old-Fc[:,j]))))
 maxima['left_rate_max']=max(maxima['left_rate_max'],float(np.max(np.abs(left))));maxima['right_rate_max']=max(maxima['right_rate_max'],float(np.max(np.abs(right))))
 mc=np.abs(delta)>1e-12;mb=np.abs(boundary)>1e-12;me=np.abs(extra)>1e-12
 for name,m in [('changed_total',mc),('changed_ms_boundary',mb),('changed_extra_event_or_rate',me),('old_label_not_exact_rate_sum',np.abs(old-Fc[:,j])>1e-12),('left_nonzero',np.abs(left)>1e-12),('right_nonzero',np.abs(right)>1e-12),('both_nonzero',(np.abs(left)>1e-12)&(np.abs(right)>1e-12)),('extra_only',me&~mb),('boundary_only',mb&~me),('both_sources',mb&me)]:counts[name]+=int(m.sum())
 # Deterministic examples: first changed cell for each first five crypto names, alphabetic axis inherited.
 if len(examples)<5 and s in ['BTCUSDT','ETHUSDT','SOLUSDT','DOGEUSDT','ADAUSDT'] and mc.any():
  k=int(np.flatnonzero(mc)[0]);a=int(A[k]);sel=(ft>=a*1000)&(ft<=(a+14401)*1000)
  examples.append({'symbol':str(s),'anchor':a,'anchor_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(a)),'F_old':float(old[k]),'F_ms':float(ms[k]),'left_plus':float(left[k]),'right_minus':float(right[k]),'extra_event':float(extra[k]),'events':[{'ft_ms':int(t),'utc':time.strftime('%Y-%m-%dT%H:%M:%S',time.gmtime(t//1000))+f'.{t%1000:03d}Z','rate':float(r),'included_ms':bool(a*1000<t<=(a+14400)*1000),'included_old_second':bool(a<t//1000<=a+14400)} for t,r in zip(ft[sel],rt[sel])]})
assert maxima['old_label_error']<=2e-12 and maxima['decomposition_error']<=2e-12,maxima
print(json.dumps({'utc_start':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(START)),'utc_end':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'inputs':paths,'same_symbol_axis':True,'covered_anchors':len(A),'symbols':len(S),'counts':counts,'maxima':maxima,'examples':examples,'formula':'F_ms - F_old = rates at A+(0,1s) minus rates at A+4h+(0,1s) plus difference after flooring ALL new events vs old seconds ledger','wall_seconds':time.time()-START,'rss_max_kb':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},indent=2))
