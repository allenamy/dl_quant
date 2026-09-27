"""Review-only entrypoint for a fixed120 forward/gradient instrument. No optimizer."""
import argparse,hashlib,json,math,os,pathlib,resource,signal,sys,time
ROOT=pathlib.Path('/workspace/codex_research/QNT-2026-0907/acting_lead_20260927/funding')
PACK=ROOT/'first120_input_pack_20260927'
OUTPUT=ROOT/'first120_network_clock_20260928'
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def dump(p,v):
    with open(p,'x') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def check(p,h):
    if sha(p)!=h:raise ValueError('source/input drift:'+str(p))
def run(out):
    t0=time.monotonic();cmd=json.loads((out/'COMMAND.json').read_text());signal.setitimer(signal.ITIMER_REAL,max(.001,cmd['deadline_monotonic']-t0))
    for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
    os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8';os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    for name,h in cmd['source_sha256'].items():check(pathlib.Path(__file__).parent/name,h)
    import funding_pack_acceptance as acceptance
    import funding_first120_clock_core as core
    imported={}
    for module,name in [(acceptance,'funding_pack_acceptance.py'),(core,'funding_first120_clock_core.py')]:
        actual=pathlib.Path(module.__file__).resolve();expected=(pathlib.Path(__file__).parent/name).resolve()
        if actual!=expected:raise ValueError('unexpected import path:'+name)
        check(actual,cmd['source_sha256'][name]);imported[name]={'actual_file':str(actual),'sha256':sha(actual)}
    dump(out/'ACTUAL_IMPORTS.json',imported)
    accepted=acceptance.accept(ROOT,verify_arrays=True);dump(out/'PACK_ACCEPTANCE.json',accepted)
    import numpy as np
    import torch as T
    T.set_num_threads(1);T.set_num_interop_threads(1);T.use_deterministic_algorithms(True)
    if not T.cuda.is_available():raise ValueError('CUDA required; no CPU fallback')
    T.cuda.set_per_process_memory_fraction(7*2**30/T.cuda.get_device_properties(0).total_memory,0)
    post=json.loads((ROOT/'first120_input_pack_postverify_20260927/POSTVERIFY.json').read_text())
    ns=post['normalization'];model_path=ns['model_path'];check(model_path,ns['model_sha256'])
    cfgpath=ROOT/'first120_canonical_20260927/RUN_CONFIG.json';check(cfgpath,'3a482d58c3adbc3f42ddf92c05539594ab078f6a7f5c589babc9060830b4fb63');cfg=json.loads(cfgpath.read_text())
    pins=cfg['input_pins'];sources={}
    for k,n in [('combo','combo_source_combo_target.py'),('continuous','combo_source_continuous_combo.py'),('stage','combo_source_combo_stage.py')]:sources[k]=(pins[n]['path'],pins[n]['sha256'])
    source=next(v for p,v in ns['training_sources'].items() if p.endswith('/news2_train_f10.py'));sources['net']=(source['path'],source['sha256'])
    c=cfg['inherited_pins']['calibration'];check(c['path'],c['sha256']);cal=json.loads(pathlib.Path(c['path']).read_text())
    bc=pins['combo_input_bundle_config.json'];check(bc['path'],bc['sha256']);params=json.loads(pathlib.Path(bc['path']).read_text())['params']
    def nz(p):
        with np.load(p,allow_pickle=False) as z:return {k:z[k] for k in z.files}
    axes=nz(PACK/'AXES.npz');legs=nz(PACK/'LEGS.npz');norm=nz(PACK/'NORMALIZATION.npz');initial=json.loads((PACK/'INITIAL_STATE.json').read_text())
    sealed=initial['canonical_sealed']
    if sealed['positions_qty']!={} or sealed['n_positions']!=0 or sealed['nav0_usdt']!=100000. or sealed['cash_K0']!=100000.:raise ValueError('initial quantity/numeraire changed')
    if sealed['t0']!=1672531200. or initial['producer_kc_fc']!='zero at original Jan1 origin; prefix0':raise ValueError('producer origin/prefix changed')
    if initial['canonical_sealed_sha256']!='83c32f281cbbd950fb3e4a09ed14493535842e19d6baf76d27deb92509c9b714':raise ValueError('sealed initial state identity')
    if not np.array_equal(axes['anchors'],np.array(cfg['anchors'])):raise ValueError('frozen anchors differ')
    off=axes['off'];members=[axes['m'][off[i]:off[i+1]].astype(np.int64) for i in range(120)]
    data={**axes,'members':members,'legs':legs,'legal':np.load(PACK/'LEGAL.npy',mmap_mode='r'),'params':params,'events':nz(PACK/'EVENTS.npz'),'price':np.load(PACK/'PRICE_RAW.npy',mmap_mode='r'),'price_ts':np.load(PACK/'PRICE_TS.npy',mmap_mode='r')}
    if not np.array_equal(data['events']['symbols'],axes['symbols']):raise ValueError('ledger/member/price symbol order differs')
    if data['legal'].shape!=(120,829) or data['price'].shape!=(5762,829) or not np.all(np.diff(data['price_ts'])==300):raise ValueError('fixed pack axes differ')
    if data['events']['ft_ms'].dtype!=np.dtype('<i8') or len(data['events']['ft_ms'])!=9104:raise ValueError('fixed exact-ms events differ')
    coeff,atoms,event_rows=core.coefficient_pack(np,data,cal)
    dump(out/'COEFFICIENT_EVENT_CONTROL.json',core.coefficient_control(np,data,coeff,atoms,event_rows))
    dump(out/'CLOCK_COEFFICIENT_RECEIPT.json',{'all_events':len(event_rows),'structural_zero_unknown_price':sum(x['structural_zero_unknown_price'] for x in event_rows),'all_event_ids_sha256':hashlib.sha256(json.dumps(event_rows,sort_keys=True,allow_nan=False).encode()).hexdigest(),'atoms':atoms,'formula':'q_old*C_old + delta*C_delta; every event enumerated; funding strictly before same-time fill','price_fee_clock':'cash balances marked at A/B; fill price decision_mid*(1+side*signed_slip); USDT fee; fixed NAV100000 GM2','scope':'fixed expected-fill proxy, excludes canonical lot/min-notional/stops/dynamic NAV','no_new_cash_truth_claim':True})
    np.savez_compressed(out/'CLOCK_COEFFICIENTS.npz',**coeff)
    dump(out/'EVENT_COEFFICIENT_ROWS.json',event_rows)
    reference,Net=core.original_definitions(np,T,sources)
    ck=T.load(model_path,map_location='cpu',weights_only=True);model=Net();model.load_state_dict(ck['state_dict'],strict=True);model=model.to('cuda').eval()
    if sum(p.numel() for p in model.parameters())!=110082:raise ValueError('parameter count')
    for k in ('mu','sd'):
        if not np.array_equal(norm[k],ck[k].cpu().numpy()):raise ValueError('checkpoint normalization drift')
    mu=T.as_tensor(norm['mu'],device='cuda');sd=T.as_tensor(norm['sd'],device='cuda')
    x=np.load(PACK/'X171.npy',mmap_mode='r');assert x.shape==(17520,171) and np.isfinite(x).all()
    XT=T.as_tensor(np.array(x),device='cuda');XT=T.clamp((XT-mu)/sd,-5,5)
    C={k:T.as_tensor(v,device='cuda') for k,v in coeff.items()};par=tuple(model.parameters());names=[k for k,_ in model.named_parameters()]
    def state_hash():return core.fingerprint(T,*[v for _,v in model.state_dict().items()])
    initial_sha=state_hash();base=[p.detach().clone() for p in par]
    def dense_scores(s):
        d=np.full((120,len(axes['symbols'])),np.nan)
        for i in range(120):d[i,members[i]]=s[off[i]:off[i+1]]
        return d
    def reference_run(d,policy):return reference(axes['anchors'],legs['KZ'].astype(np.float64),d.astype(np.float64),legs['ZFD'].astype(np.float64),legs['WL'].astype(np.float64),legs['RN8'].astype(np.float64),members,legs['QV'].astype(np.float64),data['legal'],legs['ready'],params,policy)
    hard_receipt={}
    # Separate old OOF -> old sealed targets from new checkpoint-score equality.
    oof=np.load(PACK/'REFERENCE_F10_OOF.npy');new_score=model.f(XT).squeeze(-1).detach().cpu().numpy()
    for label,dense,flat in [('old_oof',oof,np.concatenate([oof[i,members[i]] for i in range(120)])),('new_checkpoint',dense_scores(new_score),new_score)]:
        for policy in ('literal','scaled_diagnostic'):
            ref=reference_run(dense,policy)
            with T.no_grad():got=core.evolve(T,T.as_tensor(flat,dtype=T.float64),data,policy,hard=True)
            errs={k:float(np.max(np.abs(ref[k]-got[k].cpu().numpy()))) for k in ('kc','fc','raw','weights')}
            if max(errs.values())>1e-12 or not np.array_equal(ref['trade_mask'],got['trade_mask']) or list(ref['reason'])!=got['reason']:raise ValueError('continuous hard parity failed:'+label+'/'+policy)
            if label=='old_oof':
                saved=nz(PACK/(policy+'.npz'))
                for k in ('kc','fc','raw','weights','trade_mask','reason'):
                    if not np.array_equal(ref[k],saved[k]):raise ValueError('old OOF sealed target differs:'+k)
            hard_receipt[label+'/'+policy]={'max_error':errs,'published':int(ref['trade_mask'].sum()),'holds':120-int(ref['trade_mask'].sum()),'continuous_state_and_HOLD_checked':True}
    dump(out/'HARD_CONTINUOUS_PARITY.json',hard_receipt)
    def forward():
        s=model.f(XT).squeeze(-1);book=core.evolve(T,s,data,hard=False);parts=core.cash_path(T,book,C,atoms);objs,tails=core.objectives(T,parts)
        gates={'producer':book['gates'],'publication':book['trade_mask'],'fill_sign':parts['fill_sign_gates'],'ES_tails':tails}
        return objs,gates,parts,s
    objs,gates,parts,scores=forward();grads={};grad_report={}
    for key,obj in objs.items():
        if obj.requires_grad:gs=T.autograd.grad(obj,par,retain_graph=True,allow_unused=True)
        else:gs=[None]*len(par)
        flat=T.cat([(T.zeros_like(p) if g is None else g).reshape(-1) for p,g in zip(par,gs)])
        if not bool(T.isfinite(flat).all()):raise ValueError('nonfinite parameter gradient')
        grads[key]=flat;grad_report[key]={'value':float(obj.detach()),'l2_NAV_bps_per_parameter':float(flat.norm()),'nonzero_parameters':int((flat!=0).sum()),'unused_parameter_names':[n for n,g in zip(names,gs) if g is None]}
    score_grad=T.autograd.grad(objs['carry'],scores,allow_unused=True,retain_graph=True)[0] if objs['carry'].requires_grad else None
    peranchor=[0. if score_grad is None else float(score_grad[off[i]:off[i+1]].norm()) for i in range(120)]
    rng=T.Generator(device='cpu').manual_seed(20260927);direction=(T.randint(0,2,(110082,),generator=rng,dtype=T.int64).float()*2-1).to('cuda')/math.sqrt(110082)
    directional={k:float(T.dot(v,direction)) for k,v in grads.items()};values={k:float(v.detach()) for k,v in objs.items()}
    cash_arrays={k:v.detach().cpu().numpy() for k,v in parts.items() if k in ('price','fee','carry')};np.savez(out/'DESCRIPTIVE_PROXY_PARTS.npz',**cash_arrays)
    cos={}
    for k in ('price','fee','A0','A1'):
        denom=float(grads[k].norm()*grads['carry'].norm());cos[k]=None if denom==0 else float(T.dot(grads[k],grads['carry'])/denom)
    del objs,obj,parts,scores,score_grad,grads # Release the sole backward graph before FD forwards.
    def shift(e):
        at=0
        with T.no_grad():
            for p,b in zip(par,base):p.copy_(b+e*direction[at:at+p.numel()].reshape_as(p));at+=p.numel()
    fd=[]
    for eps in (1e-3,1e-4):
        results=[]
        for sign in (1,-1):
            shift(sign*eps)
            with T.no_grad():v,g,_,_=forward()
            results.append(({k:float(x) for k,x in v.items()},g))
        same=[k for k in gates if results[0][1][k]!=gates[k] or results[1][1][k]!=gates[k]]
        for k,ad in directional.items():
            measured=(results[0][0][k]-results[1][0][k])/(2*eps);err=abs(measured-ad);tol=5e-4+.02*abs(ad)
            fd.append({'part':k,'eps':eps,'autograd':ad,'FD':measured,'absolute_error':err,'absolute_tolerance':5e-4,'tolerance':tol,'AD_to_absolute_tolerance':abs(ad)/5e-4,'below_absolute_resolution':abs(ad)<=5e-4,'nonzero_signal_claim':False,'gate_crossings':same,'verified':not same and err<=tol})
    shift(0.);assert state_hash()==initial_sha,'parameter restoration differs'
    T.cuda.synchronize()
    dump(out/'WORKER_MEMORY.json',{'rss_high_water_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'max_cuda_reserved_bytes':T.cuda.max_memory_reserved()})
    report={'status':'FIRST120_FORWARD_GRADIENT_MEASUREMENT_NO_OPTIMIZER','utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'scope':'Jan2023 input and 202608 checkpoint, implementation only; no OOS/candidate','pack_acceptance':accepted,'sources':sources,'hard_parity':hard_receipt,'soft_published':sum(gates['publication']),'soft_hold':120-sum(gates['publication']),'gradient_components':grad_report,'carry_gradient_cosines':cos,'carry_score_gradient_l2_by_anchor':peranchor,'burn_anchors':24,'burn_detached':False,'directional_FD':fd,'gradient_acceptance':'VERIFIED_AT_BOTH_EPS' if all(x['verified'] for x in fd) else 'UNRESOLVED_FD_OR_GATE_CROSSING','fixed_direction':'Rademacher seed20260927/sqrt110082; no direction search','F0_strict_byte_identity':'UNRESOLVED_PREVIOUS_ATTEMPT_NOT_RERUN','parameter_hash_before':initial_sha,'parameter_hash_after':state_hash(),'optimizer_updates':0,'alpha_parameter_used':False,'max_cuda_allocated_bytes':T.cuda.max_memory_allocated(),'max_cuda_reserved_bytes':T.cuda.max_memory_reserved(),'torch':T.__version__,'executable':sys.executable,'elapsed_seconds':time.monotonic()-t0,'source_sha256':sha(__file__)}
    dump(out/'WORKER_RESULT.json',report)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--worker',type=pathlib.Path);a=ap.parse_args()
    if a.worker is None:print(json.dumps({'status':'RUN_NOT_STARTED','scope':'source review; fixed120 forward/backward only','optimizer_updates':0,'output':str(OUTPUT)}));return
    if a.worker!=OUTPUT or not (OUTPUT/'COMMAND.json').is_file():raise ValueError('guard-managed invocation required')
    run(a.worker)
if __name__=='__main__':main()
