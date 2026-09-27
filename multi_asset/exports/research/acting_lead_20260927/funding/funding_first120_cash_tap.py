"""One fixed D10 whole-book path, original HistSim31 and exact-ms funding tap."""
import os
for n in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[n]='1'
import argparse,collections,hashlib,importlib.util,json,math,pathlib,resource,subprocess,sys,time
G=2**30;os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
resource.setrlimit(resource.RLIMIT_AS,(2*G,2*G));resource.setrlimit(resource.RLIMIT_CPU,(240,250))
ROOT=pathlib.Path(__file__).resolve().parent;T0=time.monotonic()


def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def dump(p,v):p.write_text(json.dumps(v,indent=1,allow_nan=False,default=lambda x:x.item() if hasattr(x,'item') else str(x))+'\n')


class RetainedAudit:
    def __init__(self,audit):self.audit=audit;self.rows=[]
    def append(self,x):self.audit.append(x);self.rows.append(tuple(x))
    def __getattr__(self,k):return getattr(self.audit,k)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--build',required=True);args=ap.parse_args()
    build=pathlib.Path(args.build);out=build/'cash';out.mkdir(exist_ok=False)
    free=int(pathlib.Path('/sys/fs/cgroup/memory.max').read_text())-int(pathlib.Path('/sys/fs/cgroup/memory.current').read_text())
    urss=sum(int(x) for x in subprocess.check_output(['ps','-u',str(os.getuid()),'-o','rss='],text=True).split())*1024
    gate={'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'free_bytes':free,'same_uid_rss_bytes':urss,'pass':free>=10*G and urss+2*G<=30*G,'cpu':1,'rss_budget_bytes':2*G,'spare_bytes':8*G}
    dump(out/'RESOURCE_GATE.json',gate)
    if not gate['pass']:raise SystemExit('RESOURCE_REFUSED_NO_SIMULATION')
    import numpy as np
    ip=ROOT/'IDENTITY_MANIFEST.json';assert sha(ip)=='9a7de4e6cb0a02b9b8fff94c232635bce6aec8ba15ba06cb2baca3522c920b78'
    assets=json.loads(ip.read_text())['assets'];cfg=json.loads((build/'RUN_CONFIG.json').read_text())
    assert sha(build/'RUN_CONFIG.json')==json.loads((build/'BUILD_RESULT.json').read_text())['config_sha256']
    pins={}
    def pin(k):
        e=assets[k];p=pathlib.Path(e['path']);assert sha(p)==e['sha256'],k;pins[k]={'path':str(p),'sha256':e['sha256']};return p
    for k in ('exec_sim','simlib','engine_bt_hist_sim31.py','engine_bt_objb_targets.py','calibration','target_universe','tradability','input_manifest','price_full_meta','price_full_raw'):pin(k)
    sys.path.insert(0,str(pathlib.Path(assets['exec_sim']['path']).parent));sys.path.insert(0,str(pathlib.Path(assets['engine_bt_hist_sim31.py']['path']).parent))
    import exec_sim as ES,simlib as SL,bt_hist_sim31 as BH,bt_objb_targets as OT
    assert sha(ES.__file__)==assets['exec_sim']['sha256'] and sha(BH.__file__)==assets['engine_bt_hist_sim31.py']['sha256']
    SL.install_readonly_guard()
    cp=ROOT/'d10_first_span_identity.py';assert sha(cp)==cfg['checker_sha256']=='5f1ba04e22ac45ae4b7c632a9df1ae11f8f55b164c59ba33e7bc0fc62800c104'
    sp=importlib.util.spec_from_file_location('cash_identity',cp);IC=importlib.util.module_from_spec(sp);sp.loader.exec_module(IC)
    assert sha(cfg['cash_contract']['path'])==cfg['cash_contract']['sha256']
    contract=json.loads(pathlib.Path(cfg['cash_contract']['path']).read_text())
    events,irec=IC.check_and_load(contract,ip,sha(ip));dump(out/'INPUT_RECEIPT.json',irec)
    from funding_exact_ms_consumer import ExactMsFunding,ExactMsFundingMixin
    anchors=np.asarray(cfg['anchors'],np.int64);A0=int(anchors[0]);B=int(cfg['terminal_B'])
    assert A0==1672531200 and B==1674259200 and cfg['seed_execution']==0
    with np.load(assets['price_full_meta']['path'],allow_pickle=False) as z:PM={k:z[k] for k in ('grid','symbols','first_fin','cref_raw','ref_px','unavail_grid_row','unavail_col')}
    syms=[str(s) for s in PM['symbols']];assert syms==[str(s) for s in events['symbols']]
    # Read a contiguous small NPY row block, never mmap/materialize the 2.9GB table.
    p=pathlib.Path(assets['price_full_raw']['path'])
    with p.open('rb') as f:
        before=os.fstat(f.fileno());ver=np.lib.format.read_magic(f)
        shape,order,dtype=(np.lib.format.read_array_header_1_0(f) if ver==(1,0) else np.lib.format.read_array_header_2_0(f))
        assert not order and shape[1]==len(syms)
        base=f.tell();g0=int(PM['grid'][0]);lo=(A0-g0)//300-1;hi=(B-g0)//300+1
        assert 0<=lo<hi<=shape[0]
        f.seek(base+lo*shape[1]*dtype.itemsize);LP=np.fromfile(f,dtype=dtype,count=(hi-lo)*shape[1]).reshape(hi-lo,shape[1])
        IC.stable_fd(p,f,before)
    panel=BH.FullPanel(LP,g0+lo*300,syms,PM['first_fin'],PM['cref_raw'],PM['ref_px'])
    ua=BH.UAIndex(g0,len(PM['grid']),PM['unavail_grid_row'],PM['unavail_col'],len(syms));assert len(ua.cells)==3084
    held_cells=panel.ua_hold(ua,dry=True);panel.ua_hold(ua,dry=False)
    with np.load(assets['tradability']['path'],allow_pickle=False) as z:
        assert [str(s) for s in z['symbols']]==syms;trstate=z['state_W24H'];trrow={int(t):i for i,t in enumerate(z['anchor_ts'])}
    U=np.load(assets['target_universe']['path'],allow_pickle=False);assert [str(s) for s in U['symbols']]==syms
    ui=np.searchsorted(U['ts'],anchors);assert np.array_equal(U['ts'][ui],anchors);pit=U['pit'][ui]
    tg=cfg['targets'];T=OT.load_targets([tg],reading='scaled',arm=cfg['arm'],n_sym=len(syms));W,fresh,kind,cnt=OT.book_for_window(T,anchors,len(syms))
    cal=json.loads(pathlib.Path(assets['calibration']['path']).read_text());prod=cfg['current_production_config']
    assert cfg['nav0_usdt']==100000 and prod['gross_mult']==2 and cal['params']['decision_offset_default_s']==1440
    ES.E4_FROM_ANCHOR=int(prod['E4_from_anchor']);ES.RQ_FIRST_ANCHOR=int(prod['requote_assignment_from_anchor'])
    cmap=BH.CfgMap31(trstate,trrow,syms,2.,prod['chase_weights'],1440)
    M=BH.HistMirror(cfg['paths']['exec_mirror'],str(out/'target_live'))
    manifest=json.loads(pathlib.Path(assets['input_manifest']['path']).read_text())
    for rel,want in manifest['executor_tree']['files_sha256'].items():assert sha(pathlib.Path(M.root)/rel)==want,rel
    rel='state/exchange_info_cache.json';assert sha(pathlib.Path(M.root)/rel)==manifest['files'][rel]['sha256']
    X=ES.ExecutorCode(M);assert X.pns_conf['_profile']=='wide' and X.ext_cfg['gross_mult']==2
    fbook=ExactMsFunding(events,A0*1000,B*1000)
    Hist=BH.make_sim_class(ES)
    class CashSim(ExactMsFundingMixin,Hist):pass
    sim=CashSim(M,cal,'rule',{},X,panel,fbook,anchors,cmap,W,fresh,pit,syms,cfg['arm'],100000.,0,'UA-FREEZE-EXCLUDE',ua,stop_at=float(B))
    sim.trade_log=RetainedAudit(sim.trade_log);sim.fund_log=RetainedAudit(sim.fund_log)
    windows=sim.run();sim._flush_nav(B+1)  # finish sampler only; no events beyond frozen B
    trades=sim.trade_log.rows;logged=sim.fund_log.rows
    assert len(windows)==120
    assert all(A0<t[0]<=B for t in trades)
    # Independent inventory from the actual executed quantities, including the
    # published near-zero inventory normalization in canonical book().
    def add(q,s,dq):
        old=q.get(s,0.);new=old+dq
        if abs(new)<1e-9*max(1.,abs(old)):new=0.
        if new:q[s]=new
        else:q.pop(s,None)
    q={};j=0;expected=[];logged_map={(round(t*1000),s):(qv,pv,rv,cv) for t,s,qv,pv,rv,cv in logged}
    assert len(logged_map)==len(logged)
    worst_q=0.;worst_cash=0.;fund_by_window=np.zeros(120);reachable=0;prevfill={}
    for ms,col,rate in zip(events['ft_ms'],events['symbol_index'],events['rate']):
        t=int(ms)/1000;s=syms[int(col)]
        while j<len(trades) and trades[j][0]<t:
            v=trades[j];add(q,v[1],v[2]);prevfill[v[1]]=v[0];j+=1
        qty=q.get(s,0.);px=panel.px(s,int(t)//300*300)
        if qty:assert px is not None and np.isfinite(px) and px>0,(s,t,'unpriced held settlement')
        cash=0. if qty==0 else -qty*px*float(rate)
        ref=logged_map.pop((int(ms),s),None)
        if ref is None:assert cash==0.,(s,t,'missing nonzero charge')
        else:
            worst_q=max(worst_q,abs(qty-ref[0]));worst_cash=max(worst_cash,abs(cash-ref[3]));assert ref[2]==float(rate)
        k=int(np.searchsorted(anchors*1000,int(ms),side='left')-1);assert 0<=k<120
        fund_by_window[k]+=cash
        reachable+=int(s in prevfill and float(rate)!=0 and qty!=0)
        expected.append((int(ms),s,qty,px,float(rate),cash))
    assert not logged_map and worst_cash<=1e-8
    # Reconstruct price and fee using the same independent inventory at boundaries.
    q={};j=0;price_errors=[];fee_errors=[];identity_errors=[];cash_errors=[]
    def mv(t):
        total=0.
        for s,v in q.items():
            px=panel.px(s,t);assert px is not None and np.isfinite(px),(s,t,'unpriced boundary inventory');total+=v*px
        return total
    for k,A in enumerate(anchors):
        t0=int(A);t1=t0+14400;m0=mv(t0);tc=fee=0.
        while j<len(trades) and trades[j][0]<=t1:
            v=trades[j];assert v[0]>t0;add(q,v[1],v[2]);tc+=v[4];fee+=v[6];j+=1
        price=mv(t1)-m0-tc;w=windows[k]
        price_errors.append(price-w['price_trade']);fee_errors.append(fee-w['fee']);cash_errors.append(float(fund_by_window[k])-w['funding'])
        identity_errors.append((w['nav1']-w['nav0'])-(price-fee+fund_by_window[k]))
    assert max(map(abs,price_errors+fee_errors+identity_errors))<=1e-6
    assert max(map(abs,cash_errors))<=1e-8
    assert abs(cash_errors[0]+.01)>1e-8  # actual amount negative control
    # Every event, including zero baseline q, is retained for the reachable derivative.
    example=None
    for v in trades:
        t,s,dq,fillpx,*_=v;anchor=int(v[8]);past=[e for e in expected if e[1]==s and anchor*1000<=e[0]<=round(t*1000) and e[4]!=0 and e[2]!=0]
        future=[e for e in expected if e[1]==s and e[0]>round(t*1000) and e[3] is not None and e[4]!=0]
        if past and future:
            derivative=-math.fsum(e[3]*e[4] for e in future);eps=1e-4
            fd=math.fsum((-(e[2]+eps)*e[3]*e[4])-(-(e[2]-eps)*e[3]*e[4]) for e in future)/(2*eps)
            assert abs(fd-derivative)<=max(1e-8,abs(derivative)*1e-6)
            wrong=-past[-1][3]*past[-1][4];assert wrong!=0.
            example={'actual_fill':v,'pre_fill_held_event':past[-1],'pre_fill_new_quantity_derivative':0.,'wrong_backdated_derivative':wrong,'future_event_count':len(future),
                     'future_zero_baseline_qty_events':sum(e[2]==0 for e in future),'cash_derivative_per_qty':derivative,'independent_finite_difference':fd}
            break
    nontrivial=bool(trades and reachable and example)
    status='FIRST120_D10_CANONICAL_EXACT_MS_CASH_PASS' if nontrivial else 'UNAVAILABLE_NO_NONTRIVIAL_REACHABLE_CONTROL'
    result={'status':status,'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'source_sha256':sha(__file__),'config_sha256':sha(build/'RUN_CONFIG.json'),
            'canonical_inputs':pins,'consumer_sha256':sha(ROOT/'funding_exact_ms_consumer.py'),'identity_checker_sha256':sha(cp),
            'initial_state':sim.sealed,'initial_state_sha256':sim.sealed_sha,'first_A':A0,'terminal_B':B,'windows':120,'fills':len(trades),'logged_funding':len(logged),'all_ms_events':len(expected),'reachable_nonzero_inventory_events':reachable,
            'max_quantity_difference':worst_q,'max_event_cash_error_usd':worst_cash,'max_window_cash_error_usd':max(map(abs,cash_errors)),
            'max_window_price_error_usd':max(map(abs,price_errors)),'max_window_fee_error_usd':max(map(abs,fee_errors)),
            'max_window_equity_identity_error_usd':max(map(abs,identity_errors)),'plus_one_cent_control_red':True,'causal_example':example,
            'original_audits':{'fee_max_error':sim.trade_log.max_fee_err,'funding_max_error':sim.fund_log.max_err,'funding_duplicates':sim.fund_log.dup},
            'ua_counters':dict(sim.ua),'ua_held_price_cells':held_cells,'price_row_block':{'row_start':lo,'row_end_exclusive':hi,'bytes':LP.nbytes},
            'elapsed_seconds':time.monotonic()-T0,'rss_peak_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            'limits':['one fixed window and execution seed, no OOS/candidate/Sharpe conclusion','canonical simulated fills, not external venue fills','price oracle shared with canonical','quantity reconstruction applies published near-zero cleanup','local fixed-tape derivative excludes strategy replanning, no training performed']}
    dump(out/'RESULT.json',result)
    dump(out/'TAPE.json',{'initial_state':sim.sealed,'trade_log':trades,'fund_log':logged,'independent_ms_cash_rows':expected,'window_cash_errors':cash_errors,'window_price_errors':price_errors,'window_fee_errors':fee_errors,'window_identity_errors':identity_errors})
    assert sum(p.stat().st_size for p in out.iterdir() if p.is_file())<64<<20
    print(json.dumps({k:result[k] for k in ('status','fills','logged_funding','all_ms_events','reachable_nonzero_inventory_events','max_event_cash_error_usd','max_window_cash_error_usd','max_window_equity_identity_error_usd','elapsed_seconds','rss_peak_bytes')},indent=2))


if __name__=='__main__':main()
