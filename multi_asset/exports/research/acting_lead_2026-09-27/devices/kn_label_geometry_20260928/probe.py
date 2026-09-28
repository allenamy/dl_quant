"""Diagnostic of frozen KN training labels, not strategy P&L or a new model."""
import hashlib,json,os,sys,time,resource
from pathlib import Path
import numpy as np
from scipy.stats import rankdata

FEATURE=Path('/dev/shm/news2_2026-09-23/work/NEWS_FEATURES.npz')
LABEL=Path('/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz')
NET=Path('/workspace/dlarch_2026-09-24/king_fam_2026-09-27/T_NET.npz')
PINS={str(FEATURE):'3c886a2bc0ff65c10b7e0a621c9468210bbd77ef58c90e625f0a29354d63c4d8',str(LABEL):'ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62',str(NET):'929ff9f6c68280f1994ffb3c34c0c53114d96ad034686183f9dfd9b09b5c7a5c'}

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()

def validate_members(m,n):
    if m.ndim!=1 or m.dtype.kind not in 'iu' or np.any(m<0) or np.any(m>=n) or len(np.unique(m))!=len(m):
        raise ValueError('invalid_members')

def measure(y,net,f):
    if len(y)<2 or y.shape!=net.shape or y.shape!=f.shape or not np.all(np.isfinite([y,net,f])):
        raise ValueError('invalid_values')
    ry=rankdata(y,method='average');rn=rankdata(net,method='average');n=len(y)
    delta=np.abs(rn-ry)/(n-1)
    py=(ry-1)/(n-1);pn=(rn-1)/(n-1)
    top=py>=.9;bottom=py<=.1
    out={'n':n,'spearman':float(np.corrcoef(ry,rn)[0,1]) if ry.std()>0 and rn.std()>0 else None,
         'mean_abs_percentile_change':float(delta.mean()),
         'top_retention':float(np.mean(pn[top]>=.9)) if top.any() else None,
         'bottom_retention':float(np.mean(pn[bottom]<=.1)) if bottom.any() else None,
         'fund_std_over_price_std':float(f.std()/y.std()) if y.std()>0 else None}
    return out,delta

def distribution(a):
    a=np.asarray(a,dtype=float)
    if not len(a):return {'n':0,'mean':None,'p50':None,'p90':None,'p99':None}
    if not np.all(np.isfinite(a)):raise ValueError('nonfinite_statistic')
    return {'n':len(a),'mean':float(a.mean()),**{f'p{q}':float(np.percentile(a,q)) for q in (50,90,99)}}

def main():
    started=time.monotonic();out=Path(sys.argv[1])
    got={p:sha(p) for p in PINS}
    if got!=PINS:raise ValueError('input_sha_drift')
    F=np.load(FEATURE,allow_pickle=False);T=np.load(LABEL,allow_pickle=True);N=np.load(NET,allow_pickle=False)
    a=F['anchors'];sy=F['symbols'];off=F['off'];count=F['count'];members=F['m']
    e=T['E_ts'];y=T['y4s'];net=N['T_net'];fee=N['F'];covered=N['covered']
    if not np.array_equal(sy,T['symbols']) or not np.array_equal(sy,N['symbols']) or not np.array_equal(e,N['E_ts']):raise ValueError('axes_differ')
    if any(v.dtype.kind not in 'iu' or not np.all(np.diff(v)>0) or np.any(v%14400) for v in (a,e)):raise ValueError('anchor_axis_invalid')
    if len(off)!=len(a)+1 or off[0]!=0 or off[-1]!=len(members) or not np.array_equal(np.diff(off),count):raise ValueError('member_offsets')
    if y.shape!=net.shape or y.shape!=fee.shape or y.shape!=(len(e),len(sy)) or covered.shape!=(len(e),):raise ValueError('label_shape')
    rows=[];bins={};unknown={'anchors_without_labels':0,'fewer_than_50':0,'members_missing_net_or_price':0}
    bin_names=('zero','positive_abs_below_10bps','abs_at_least_10bps')
    for i,A in enumerate(a):
        year=time.gmtime(int(A)).tm_year
        if A<1656633600 or A>=1788220800:continue  # 2022-07-01 <= A < 2026-09-01
        ix=int(np.searchsorted(e,A));m=members[off[i]:off[i+1]];validate_members(m,len(sy))
        if ix>=len(e) or e[ix]!=A or not covered[ix]:unknown['anchors_without_labels']+=1;continue
        yy=y[ix,m].astype(np.float64);nn=net[ix,m];ff=fee[ix,m]
        if np.any(np.isinf(yy)) or np.any(np.isinf(nn)) or not np.all(np.isfinite(ff)):raise ValueError('invalid_label_or_fee')
        good=np.isfinite(yy)&np.isfinite(nn);unknown['members_missing_net_or_price']+=int((~good).sum())
        if good.sum()<50:unknown['fewer_than_50']+=1;continue
        yy,nn,ff=yy[good],nn[good],ff[good]
        if not np.array_equal(yy-ff,nn):raise ValueError('price_fee_identity')
        r,delta=measure(yy,nn,ff);r.update(anchor_ts=int(A),year=year);rows.append(r)
        for group in ([str(year),'pre2026'] if 2023<=year<=2025 else [str(year)]):
            b=bins.setdefault(group,{k:[] for k in bin_names})
            absf=np.abs(ff)
            for key,mask in zip(bin_names,(absf==0,(absf>0)&(absf<.001),absf>=.001)):b[key].append(delta[mask])
    summary={}
    for group,b in bins.items():
        rr=[r for r in rows if (2023<=r['year']<=2025 if group=='pre2026' else r['year']==int(group))]
        metrics={k:distribution([r[k] for r in rr if r[k] is not None]) for k in ('spearman','mean_abs_percentile_change','top_retention','bottom_retention','fund_std_over_price_std')}
        stats={}
        for key,arrays in b.items():
            values=np.concatenate(arrays) if arrays else np.array([])
            stats[key]=distribution(values)
            stats[key]['share_rank_change_at_least_10pp']=float(np.mean(values>=.1)) if len(values) else None
        summary[group]={'anchors':len(rr),'member_cells':sum(r['n'] for r in rr),'anchor_weighted':metrics,'cell_weighted_by_realized_fee':stats}
    if {p:sha(p) for p in PINS}!=PINS:raise ValueError('post_input_sha_drift')
    with open(out/'ANCHORS.json','x') as f:json.dump(rows,f,allow_nan=False)
    result={'status':'DIAGNOSTIC_COMPLETE_NOT_STRATEGY_EVIDENCE','inputs_sha256':PINS,'self_sha256':sha(__file__),
            'definition':'KN frozen 4h net labels versus same-population raw price; realized-fee bins are ex post diagnostic',
            'funding_caliber':'original KN seconds-key target; not D10 milliseconds policy',
            'summary':summary,'unknown':unknown,'wall_seconds':time.monotonic()-started,
            'rss_peak_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            'features_body_loaded':False,'gpu_imported':False,'optimizer_updates':0,
            'python':sys.executable,'numpy':np.__version__,'anchor_receipt_sha256':sha(out/'ANCHORS.json')}
    with open(out/'RESULT.json','x') as f:json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps({'status':result['status'],'wall_seconds':result['wall_seconds'],'unknown':unknown}))

if __name__=='__main__':main()
