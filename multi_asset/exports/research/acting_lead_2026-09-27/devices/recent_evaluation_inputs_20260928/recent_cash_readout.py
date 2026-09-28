"""Post-terminal cash table and observational per-name ledger, pooled outcomes only."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
from pathlib import Path
import json,sys,time,traceback,shutil,types,calendar
import numpy as np
from funding_overlap import sha
from recent_king_features import materialize
from recent_cash_run import prefix_check,stem

ROOT=Path('/dev/shm/recent_nc_cash_20260928')
START=1789776000
END=1790553600

def complete_days(A,r):
    A=np.asarray(A);r=np.asarray(r)
    if A.ndim!=1 or r.shape!=A.shape or not len(A) or np.any(np.diff(A)!=14400) or np.any(A%14400) or not np.isfinite(r).all() or np.any(r<=-1):raise ValueError('daily axis/returns')
    day=A//86400*86400;ds=np.unique(day);out=[]
    for d in ds:
        m=day==d
        if not np.array_equal(A[m],np.arange(d,d+86400,14400)):raise ValueError('incomplete daily population')
        out.append(np.prod(1+r[m])-1)
    return ds,np.array(out)

def per_name_cash(mv0,mv1,tradecash,fund,fee):
    vs=list(map(np.asarray,(mv0,mv1,tradecash,fund,fee)))
    if len({v.shape for v in vs})!=1 or not all(np.isfinite(v).all() for v in vs):raise ValueError('unknown per-name cash')
    p=vs[1]-vs[0]-vs[2]
    return {'price':p,'funding':vs[3],'fee':vs[4],'net':p+vs[3]-vs[4]}

def iso(t):return time.strftime('%FT%TZ',time.gmtime(int(t)))
def stamp(s):return calendar.timegm(time.strptime(s,'%Y-%m-%d'))

def summarize_path(p,lo,hi):
    ix=(p['A']>=lo)&(p['A']<hi);a=p['A'][ix]
    if len(a)!=(hi-lo)//14400 or a[0]!=lo or a[-1]+14400!=hi:raise ValueError('window not covered')
    rm=p['navm1'][ix]/p['navm0'][ix]-1;ds,d=complete_days(a,rm)
    g0=int(p['nav5_t0']);j0=(lo-g0)//300;j1=(hi-g0)//300
    n=p['nav5_main'][j0:j1+1]
    if len(n)!=(hi-lo)//300+1 or not np.isfinite(n).all() or np.any(n<=0):raise ValueError('5m NAV coverage')
    comp=float(np.prod(1+d)-1);navcomp=float(n[-1]/n[0]-1)
    if not np.isclose(comp,navcomp,rtol=0,atol=1e-10):raise ValueError('daily vs 5m NAV')
    ident=(p['nav1']-p['nav0'])-(p['price_trade']+p['funding']-p['fee']+p['transfer'])
    if np.max(np.abs(ident[ix]))>1e-6:raise ValueError('cash accounting')
    daily_sd=float(d.std(ddof=1));out={'n_days':len(d),'compound':comp,'daily_mean_bps':float(d.mean()*1e4),'sharpe_daily_descriptive':float(d.mean()/daily_sd*np.sqrt(365)) if daily_sd else None,'maxdd_5m':float(np.min(n/np.maximum.accumulate(n)-1)),
        'price_bps_per_day':float(np.sum(p['price_trade'][ix]/p['nav0'][ix])*1e4/len(d)),
        'funding_bps_per_day':float(np.sum(p['funding'][ix]/p['nav0'][ix])*1e4/len(d)),
        'fee_bps_per_day':float(np.sum(p['fee'][ix]/p['nav0'][ix])*1e4/len(d)),
        'turnover_nav_per_day':float(np.sum(p['turnover'][ix]/p['nav0'][ix])/len(d)),
        'unknown_held_sum':float(p['unk_held'][ix].sum()),'unknown_notional_sum':float(p['unk_notional'][ix].sum()),'unknown_excluded_price_fund_sum':float((p['unk_price'][ix]+p['unk_funding'][ix]).sum()),
        'stopped_events':float(p['n_stop_events'][ix].sum()),'flatten_events':float(p['n_flatten_events'][ix].sum()),'halt_anchors':int((p['status'][ix]==1).sum()),'hold_anchors':int((p['status'][ix]==2).sum()),'cash_identity_max_usd':float(np.max(np.abs(ident[ix])))}
    return out,ds,d

def table(root,out):
    result=json.loads((root/'RESULT.json').read_text());t=json.loads((root/'TERMINAL.json').read_text())
    if t.get('rc')!=0 or t['result_sha256']!=sha(root/'RESULT.json') or not result['all64_old_prefixes_bitwise_equal']:raise ValueError('cash terminal/identity')
    windows={'recent9':(START,END),'september27':(stamp('2026-09-01'),END),'last3_descriptive':(stamp('2026-09-25'),END)};R={};pins={str(root/'RESULT.json'):sha(root/'RESULT.json')};daily={}
    for sd in (42,2027):
        c=result['configs'][str(sd)];cp=Path(c['path'])
        if sha(cp)!=c['sha256']:raise ValueError('cash config drift')
        cfg=json.loads(cp.read_text());tag=cfg['runs'][0]['tag'];R[str(sd)]={};values={k:[] for k in windows}
        for s in range(32):
            st=stem(cp.parent,tag,s);p=materialize(str(st)+'.npz');j=json.loads(Path(str(st)+'.json').read_text());hp=sha(str(st)+'.npz')
            if j['npz_sha256']!=hp:raise ValueError('path source drift')
            pins[str(st)+'.npz']=hp;pins[str(st)+'.json']=sha(str(st)+'.json')
            for key,(lo,hi) in windows.items():
                v,ds,d=summarize_path(p,lo,hi);values[key].append(v)
                if key=='september27':daily[f's{sd}_p{s}']=d;daily['dates']=ds
        for key,vals in values.items():
            agg={k:{'mean':float(np.mean([v[k] for v in vals])),'min':float(min(v[k] for v in vals)),'max':float(max(v[k] for v in vals))} for k in vals[0] if vals[0][k] is not None}
            R[str(sd)][key]={'start':iso(windows[key][0]),'end_exclusive':iso(windows[key][1]),'metrics':agg,'paths':vals}
    np.savez_compressed(out/'DAILY_PATHS.npz',**daily)
    rec={'status':'DESCRIPTIVE_RECENT_FIXED_NC_NOT_LIVE','utc':iso(time.time()),'inputs':pins,'results':R,'daily_sha256':sha(out/'DAILY_PATHS.npz'),'limits':result['limitations']+['32 paths are execution randomness, not independent markets','Nine-day Sharpe is descriptive and not an expected strategy level','Actual live reseed and double-executor incident absent'],'source_sha256':sha(__file__)}
    (out/'ECONOMIC.json').write_text(json.dumps(rec,indent=2,allow_nan=False)+'\n');return rec

def trace(sd,out):
    cp=ROOT/f's{sd}/CONFIG.json';cfg=json.loads(cp.read_text());engine=ROOT/'engine';sys.path.insert(0,str(engine));import bt_driver_lib as DL
    checks=[]
    def check(name,ok,detail=None):
        checks.append({'name':name,'ok':bool(ok)})
        if not ok:raise ValueError('trace input check '+name)
    DL.verify_pins(cfg,check);ES,SL,BH,L2=DL.import_modules(cfg,str(engine));SL.install_readonly_guard();r=cfg['runs'][0]
    c=DL.load_context(cfg,ES,BH,L2,slice(None),[r],check,lambda *a:None);tdir=out/f'temp_s{sd}';S=DL.make_sim(c,r,0,str(tdir));index={s:j for j,s in enumerate(c.SY)};n=len(index)
    origtrade=S.trade_log.append;origfund=S.fund_log.append;origboundary=S._boundary;active=[False];rows=[];box={}
    def vector_q():
        q=np.zeros(n)
        for s,v in S.q.items():q[index[s]]=v
        return q
    def mv(t):
        v=np.zeros(n)
        for s,q in S.q.items():
            p=S.px(s,int(t))
            if p is None:raise ValueError('held unpriced '+s)
            v[index[s]]=q*p
        return v
    def tr(x):
        origtrade(x)
        if active[0]:box['cash'][index[x[1]]]+=x[4];box['fee'][index[x[1]]]+=x[6]
    def fu(x):
        origfund(x)
        if active[0]:box['fund'][index[x[1]]]+=x[5]
    def boundary(t,k):
        previous=active[0];v=mv(t) if START<=t<=END else None;q=vector_q() if v is not None else None
        origboundary(t,k)
        if previous:
            d=per_name_cash(box['mv0'],v,box['cash'],box['fund'],box['fee']);a=S.bsnap[k-1];z=S.bsnap[k]
            amounts={'price':(z['mv']-a['mv'])-(z['tradecash']-a['tradecash']),'funding':z['fund']-a['fund'],'fee':z['fee']-a['fee']}
            err={key:abs(float(d[key].sum())-val) for key,val in amounts.items()}
            if max(err.values())>1e-6:raise ValueError('per-name window identity '+str(err))
            rows.append({'A':int(t)-14400,'q0':box['q0'],'q1':q,'mv0':box['mv0'],'mv1':v,'nav0':a['equity'],'cash':box['cash'],'unknown':box['unknown'],**d,'max_error':max(err.values())})
        active[0]=START<=t<END
        if active[0]:box.update(q0=q,mv0=v,cash=np.zeros(n),fund=np.zeros(n),fee=np.zeros(n),unknown=np.array([s in S._uw for s in c.SY]))
    S.trade_log.append=tr;S.fund_log.append=fu;S._boundary=boundary
    began=time.monotonic();W=S.run();arr=DL.path_arrays(c,S,W);ref=materialize(str(stem(cp.parent,r['tag'],0))+'.npz');gate=prefix_check(ref,arr)
    if len(arr['A'])!=len(ref['A']) or len(rows)!=54:raise ValueError('trace complete population')
    if not DL.audits_clean(DL.path_summary(c,S,arr,r,0,time.monotonic()-began)['audits']):raise ValueError('trace audits')
    np.savez_compressed(out/f'PER_NAME_s{sd}_p0.npz',symbols=np.array(c.SY),**{k:np.array([r0[k] for r0 in rows]) for k in rows[0]})
    result={'model_seed':sd,'execution_seed':0,'reference_path_sha256':sha(str(stem(cp.parent,r['tag'],0))+'.npz'),'path_unchanged':gate,'anchors':len(rows),'source_identity_checks':len(checks),'seconds':time.monotonic()-began,'per_name_max_identity_error':max(r0['max_error'] for r0 in rows),'npz_sha256':sha(out/f'PER_NAME_s{sd}_p0.npz')}
    (out/f'TRACE_s{sd}.json').write_text(json.dumps(result,indent=2)+'\n');shutil.rmtree(tdir);return result

def main(out):
    out=Path(out);out.mkdir(exist_ok=False);deadline=1790604000  # 2026-09-28 14:00Z, fixed before reading numbers
    while not (ROOT/'TERMINAL.json').exists():
        if time.time()>deadline:raise TimeoutError('cash readout waiting deadline')
        time.sleep(20)
    rec=table(ROOT,out);traces=[]
    for sd in (42,2027):
        if time.time()>deadline-180:raise TimeoutError('no trace budget remaining')
        traces.append(trace(sd,out))
    outputs={p.name:sha(p) for p in out.iterdir() if p.is_file()}
    (out/'RESULT.json').write_text(json.dumps({'status':'RECENT_CASH_READOUT_AND_PER_NAME_COMPLETE','utc':iso(time.time()),'source_sha256':sha(__file__),'outputs':outputs,'traces':traces},indent=2)+'\n');(out/'TERMINAL.json').write_text(json.dumps({'rc':0,'result_sha256':sha(out/'RESULT.json')})+'\n')
    print('READOUT AND TRACES COMPLETE',flush=True)

if __name__=='__main__':
    try:main(*sys.argv[1:])
    except BaseException as e:
        out=Path(sys.argv[1]);out.mkdir(exist_ok=True);(out/'TERMINAL.json').write_text(json.dumps({'rc':1,'error':repr(e),'traceback':traceback.format_exc()},indent=2));raise
