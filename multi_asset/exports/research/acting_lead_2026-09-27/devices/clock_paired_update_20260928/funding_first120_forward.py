"""Fixed120 paired one-update implementation probe. Not a candidate model."""
import argparse,hashlib,json,math,os,pathlib,resource,signal,sys,time
ROOT=pathlib.Path('/workspace/codex_research/QNT-2026-0907/acting_lead_20260927/funding')
PACK=ROOT/'first120_input_pack_20260927'
OUTPUT=ROOT/'clock_paired_update_20260928'
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
    import price_units
    import paired_update_contract as pc
    if cmd['optimizer_updates_allowed']!=4:raise ValueError('explicit four-update contract required')
    imported={}
    for module,name in [(acceptance,'funding_pack_acceptance.py'),(core,'funding_first120_clock_core.py'),(price_units,'price_units.py'),(pc,'paired_update_contract.py')]:
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
    price_meta=cfg['inherited_pins']['price_full_meta'];check(price_meta['path'],price_meta['sha256'])
    price_ts=np.load(PACK/'PRICE_TS.npy',mmap_mode='r')
    panel_path='/dev/shm/news2_2026-09-23/engine/bt_hist_sim31.py'
    panel_sha='8ae6e2a441d700824372784b1bc0bd9e0ee2f686a3c22f522b6bb962911022a1'
    price,price_receipt=price_units.decode_log_prices(np,np.load(PACK/'PRICE_RAW.npy',mmap_mode='r'),price_ts,axes['symbols'],nz(price_meta['path']),price_units.panel_class(np,panel_path,panel_sha))
    price_receipt.update({'meta':price_meta,'canonical_panel':{'path':panel_path,'sha256':panel_sha},'adapter_sha256':sha(price_units.__file__)})
    dump(out/'PRICE_INTERPRETATION.json',price_receipt)
    data={**axes,'members':members,'legs':legs,'legal':np.load(PACK/'LEGAL.npy',mmap_mode='r'),'params':params,'events':nz(PACK/'EVENTS.npz'),'price':price,'price_ts':price_ts}
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
    def evaluate(hard=False,active_C=None):
        sc=model.f(XT).squeeze(-1)
        book=core.evolve(T,sc,data,hard=hard)
        parts=core.cash_path(T,book,C if active_C is None else active_C,atoms)
        ob,tail=core.objectives(T,parts)
        return sc,book,parts,ob,tail
    def hard_diagnostic():
        with T.no_grad():sc,bk,pt,ob,tail=evaluate(hard=True)
        ref=reference_run(dense_scores(sc.cpu().numpy()),'scaled_diagnostic')
        err=max(float(np.max(np.abs(ref[k]-bk[k].cpu().numpy()))) for k in ('kc','fc','raw','weights'))
        mask=np.array_equal(ref['trade_mask'],bk['trade_mask']);reason=list(ref['reason'])==bk['reason']
        if err>1e-12 or not mask or not reason:raise ValueError('post-update hard mapping parity')
        desc={'published':sum(bk['trade_mask']),'objectives':{k:float(v) for k,v in ob.items()},'hard_max_error':err,'hard_masks_equal':bool(mask),'hard_reasons_equal':bool(reason)}
        arrays={k:bk[k].cpu().numpy() for k in ('weights','kc','fc','raw')}
        arrays.update({k:pt[k].cpu().numpy() for k in ('price','fee','carry')})
        arrays.update(scores=sc.cpu().numpy(),trade_mask=np.array(bk['trade_mask']))
        return desc,arrays
    initial_digest=pc.tree_digest(T,model.state_dict())
    pre_hard,pre_arrays=hard_diagnostic()
    dump(out/'BASE_HARD_DIAGNOSTIC.json',pre_hard)
    np.savez_compressed(out/'BASE_HARD_ARRAYS.npz',**pre_arrays)
    updates={};done=0
    for label,key,is_zero in [('F0_A0','A0',True),('F0_A1','A1',True),('A0','A0',False),('A1','A1',False)]:
        model.load_state_dict(ck['state_dict'],strict=True);model.eval()
        opt=T.optim.AdamW(model.parameters(),lr=3e-4,weight_decay=1e-4,foreach=False)
        opt.zero_grad(set_to_none=True)
        start_digest=pc.tree_digest(T,model.state_dict())
        if start_digest!=initial_digest:raise ValueError('initial parameter byte identity')
        cc={k:(T.zeros_like(v) if is_zero and k in ('carry_old','carry_delta') else v) for k,v in C.items()}
        sc,bk,pt,ob,tail=evaluate(active_C=cc)
        loss=ob[key]
        if not bool(T.isfinite(loss)):raise ValueError('loss nonfinite')
        loss_bits=pc.tree_digest(T,loss.detach());values_before={k:float(v.detach()) for k,v in ob.items()}
        soft_mask_before=list(bk['trade_mask']);loss.backward()
        grad={n:None if p.grad is None else p.grad.detach().clone() for n,p in model.named_parameters()}
        if not pc.tree_finite(T,grad):raise ValueError('gradient nonfinite')
        grad_hash=pc.tree_digest(T,grad);unused=[k for k,v in grad.items() if v is None]
        gn=float(T.nn.utils.clip_grad_norm_(model.parameters(),1.0,error_if_nonfinite=True))
        opt.step();done+=1
        model_digest=pc.tree_digest(T,model.state_dict());opt_digest=pc.tree_digest(T,opt.state_dict())
        finite=pc.tree_finite(T,model.state_dict()) and pc.tree_finite(T,opt.state_dict())
        if not finite:raise ValueError('optimizer nonfinite')
        # Release the entire retained graph before evaluation/next independent update.
        del sc,bk,pt,ob,tail,loss,grad
        with T.no_grad():sc,bk,pt,ob,tail=evaluate(active_C=cc)
        values_after={k:float(v) for k,v in ob.items()};soft_mask_after=list(bk['trade_mask'])
        del sc,bk,pt,ob,tail
        hd,arrays=hard_diagnostic()
        r={'parameter_hash_before':start_digest,'parameter_hash_after':model_digest,'optimizer_updates':1,
           'loss_before_bits':loss_bits,'gradient_sha256':grad_hash,'optimizer_sha256':opt_digest,
           'all_finite':finite,'unused_parameter_names':unused,'gradient_norm_before_clip':gn,
           'soft_objectives_before':values_before,'soft_objectives_after':values_after,
           'soft_published_before':sum(soft_mask_before),'soft_published_after':sum(soft_mask_after),
           'soft_publication_changes':sum(a!=b for a,b in zip(soft_mask_before,soft_mask_after)),
           'hard_diagnostic':hd,'hard_max_error':hd['hard_max_error'],'hard_masks_equal':hd['hard_masks_equal'],'hard_reasons_equal':hd['hard_reasons_equal'],
           'hard_publication_changes':int(np.sum(arrays['trade_mask']!=pre_arrays['trade_mask'])),
           'hard_weights_max_absolute_change':float(np.max(np.abs(arrays['weights']-pre_arrays['weights']))),
           'zero_cash_coefficients':is_zero,'objective':key}
        # Engineering checkpoints only; never place them under an export/model release root.
        path=out/(label+'_IMPLEMENTATION_ONLY.pt')
        T.save({'model':model.state_dict(),'optimizer':opt.state_dict(),'purpose':'in-sample one-update implementation probe; NOT OOS, NOT EXPORTABLE'},path)
        r['artifact_sha256']=sha(path)
        np.savez_compressed(out/(label+'_HARD_ARRAYS.npz'),**arrays)
        dump(out/(label+'_UPDATE.json'),r);updates[label]=r
        del opt,cc,arrays
        if label=='F0_A1':
            for field in ('loss_before_bits','gradient_sha256','parameter_hash_after','optimizer_sha256'):
                if updates['F0_A0'][field]!=updates['F0_A1'][field]:raise ValueError('full-window F0 mismatch:'+field)
    status=pc.validate_results({'updates':updates,'optimizer_updates':done})
    model.load_state_dict(ck['state_dict'],strict=True)
    if pc.tree_digest(T,model.state_dict())!=initial_digest:raise ValueError('restoration failed')
    check(model_path,ns['model_sha256'])
    T.cuda.synchronize()
    dump(out/'WORKER_MEMORY.json',{'rss_high_water_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'max_cuda_reserved_bytes':T.cuda.max_memory_reserved()})
    dump(out/'WORKER_RESULT.json',{'status':status,'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'optimizer_updates':done,'updates':updates,
         'scope':'fixed Jan2023/202608 checkpoint, in-sample engineering only; no epoch, OOS, candidate or deployment approval',
         'old_double_eps_gate':'UNRESOLVED_RETAINED','model_source':{'path':model_path,'sha256':ns['model_sha256']},'sources':sources,
         'original_model_restored':True,'parameter_hash_before':initial_digest,'parameter_hash_after':pc.tree_digest(T,model.state_dict()),
         'hard_parity':hard_receipt,'base_hard_diagnostic':pre_hard,'actual_executable':sys.executable,'numpy':np.__version__,'torch':T.__version__,
         'optimizer':{'type':'AdamW','lr':3e-4,'weight_decay':1e-4,'clip':1.,'foreach':False,'steps_per_independent_arm':1,'dropout':'disabled eval'},
         'source_sha256':sha(__file__),'elapsed_seconds':time.monotonic()-t0})

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--worker',type=pathlib.Path);a=ap.parse_args()
    if a.worker is None:print(json.dumps({'status':'RUN_NOT_STARTED','optimizer_updates_allowed':4,'output':str(OUTPUT)}));return
    if a.worker!=OUTPUT or not (OUTPUT/'COMMAND.json').is_file():raise ValueError('guard-managed invocation required')
    run(a.worker)
if __name__=='__main__':main()
