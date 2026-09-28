"""Fixed120 action mechanism, frozen positive affine probes, no optimizer/PnL."""
import argparse, ast, hashlib, importlib.util, json, pathlib, resource, sys, time
OUTPUT=pathlib.Path('/workspace/codex_research/QNT-2026-0907/acting_lead_20260927/funding/rank_action_scopefixed_20260928')
HERE=pathlib.Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def write(p,v):
    import os
    with open(p,'x') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())

def load_prefix(out):
    """Reuse verified input loader through model setup, never its FD/evaluation loop."""
    cmd=json.loads((out/'COMMAND.json').read_text());p=HERE/'funding_first120_forward.py'
    if sha(p)!=cmd['source_sha256'][p.name]:raise ValueError('loader drift')
    spec=importlib.util.spec_from_file_location('pinned_original_input_loader',p)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    tree=ast.parse(p.read_bytes());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run')
    stops=[i for i,n in enumerate(node.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='hard_receipt' for t in n.targets)]
    if len(stops)!=1:raise ValueError('loader prefix boundary drift')
    node.body=node.body[:stops[0]]+[ast.Return(value=ast.Call(func=ast.Name(id='locals',ctx=ast.Load()),args=[],keywords=[]))]
    namespace=dict(vars(mod));exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(p),'exec'),namespace)
    return namespace['run'](out)

def run(out):
    started=time.monotonic();s=load_prefix(out)
    np,T,core,data=s['np'],s['T'],s['core'],s['data']
    from trace_step import observed_step
    cmd=json.loads((out/'COMMAND.json').read_text())
    if sha(HERE/'trace_step.py')!=cmd['source_sha256']['trace_step.py']:raise ValueError('tracer drift')
    csha=cmd['source_sha256']['funding_first120_clock_core.py']
    model=s['model'];state_hash=s['state_hash'];initial=s['initial_sha']
    with T.no_grad():score=model.f(s['XT']).squeeze(-1).detach().cpu().double()
    np.save(out/'CHECKPOINT_SCORES.npy',score.numpy())
    count=120;nw=len(data['symbols']);off=data['off'];members=data['members']
    def tt(x):return T.as_tensor(np.array(x,copy=True))
    def args(i,values,kh,fh,hard):
        m=members[i]
        return (T,tt(data['legs']['KZ'][i,m]).double(),values[off[i]:off[i+1]],
                tt(data['legs']['ZFD'][i,m]).double(),tt(data['legs']['WL'][i]).double(),
                tt(data['legs']['RN8'][i,m]).double(),tt(m).long(),tt(data['legs']['QV'][i,m]).double(),
                tt(data['legal'][i]).bool(),data['params'],kh,fh,'scaled_diagnostic',hard)
    def evolve(values,hard,trace=False):
        kh=T.zeros(nw,dtype=T.float64);fh=kh.clone();rows={k:[] for k in ('kc','fc','raw','weights','trade_mask','reason')};obs=[]
        previous=[]
        for i in range(count):
            previous.append((kh.clone(),fh.clone()))
            if not bool(data['legs']['ready'][i]):
                raw=None;accepted=False;reason='unready causal legs';o=None
            else:
                aa=args(i,values,kh,fh,hard)
                if trace:
                    got,o=observed_step(core.step,csha,*aa);plain=core.step(*aa)
                    for a,b in zip(got,plain):
                        if isinstance(a,T.Tensor):assert T.equal(a,b),'tracer changes numbers'
                        else:assert a==b,'tracer changes branch'
                else:got=core.step(*aa);o=None
                kc,fc,raw,accepted,reason,_=got
                kh=T.where(kc.abs()>1e-9,kc,0.);fh=T.where(fc.abs()>1e-9,fc,0.)
            for k,v in [('kc',kh),('fc',fh),('raw',kh*0 if raw is None else raw),
                        ('weights',T.where(raw.abs()>1e-9,raw,0.) if accepted else kh*0)]:rows[k].append(v.numpy().copy())
            rows['trade_mask'].append(accepted);rows['reason'].append(reason);obs.append(o)
        rows={k:np.asarray(v) for k,v in rows.items()}
        return rows,obs,previous
    transforms={'identity':(1.,0.),'scale01':(.1,0.),'scale10':(10.,0.),'shift7':(1.,7.)}
    books={};traces={};previous={};checks={};summary={}
    with T.no_grad():
        for name,(scale,shift) in transforms.items():
            values=score*scale+shift
            # Check order and equality sets before claiming a rank-invariant intervention.
            for i in range(count):
                a=score[off[i]:off[i+1]];b=values[off[i]:off[i+1]]
                assert T.equal(a[:,None]>a[None,:],b[:,None]>b[None,:]),'ordering changed'
                assert T.equal(a[:,None]==a[None,:],b[:,None]==b[None,:]),'ties changed'
            for hard in (True,False):
                key=('hard/' if hard else 'soft/')+name
                book,trace,prev=evolve(values,hard,name=='identity');books[key]=book
                if name=='identity':traces[key]=trace;previous[key]=prev
                np.savez_compressed(out/('BOOK_'+key.replace('/','_')+'.npz'),**book)
                summary[key]={'published':int(book['trade_mask'].sum()),'holds':count-int(book['trade_mask'].sum()),
                              'gross_median':float(np.median(np.abs(book['raw']).sum(1))),
                              'gross_min':float(np.abs(book['raw']).sum(1).min()),'gross_max':float(np.abs(book['raw']).sum(1).max())}
        hard=books['hard/identity'];soft=books['soft/identity']
        ref=s['reference_run'](s['dense_scores'](score.numpy()),'scaled_diagnostic')
        parity={k:float(np.max(np.abs(ref[k]-hard[k]))) for k in ('kc','fc','raw','weights')}
        assert max(parity.values())<=1e-12
        assert np.array_equal(ref['trade_mask'],hard['trade_mask']) and np.array_equal(ref['reason'],hard['reason'])
        for name in transforms:
            for k in hard:assert np.array_equal(books['hard/'+name][k],hard[k]),'hard invariance:'+name+'/'+k
        for k in ('kc','fc','raw','weights'):assert np.max(np.abs(books['soft/shift7'][k]-soft[k]))<=1e-12,'soft shift numerical drift'
        for k in ('trade_mask','reason'):assert np.array_equal(books['soft/shift7'][k],soft[k]),'soft shift decisions'
        checks.update(hard_affine='EXACT',soft_shift='WITHIN_1e-12_AND_EXACT_DECISIONS',trace_outputs='EXACT_EVERY_OBSERVED_STEP',original_continuous_parity=parity)
        crosses=[]
        for i in range(count):
            if not bool(data['legs']['ready'][i]):crosses.append({'anchor':int(data['anchors'][i]),'unready':True});continue
            sh=core.step(*args(i,score,*previous['hard/identity'][i],False))
            hs=core.step(*args(i,score,*previous['soft/identity'][i],True))
            if sh[2] is None or hs[2] is None:raise ValueError('crossed degenerate needs explicit population')
            direct=sh[2].numpy()-hard['raw'][i];inherited=soft['raw'][i]-sh[2].numpy();total=soft['raw'][i]-hard['raw'][i]
            error=float(np.max(np.abs(total-direct-inherited)));assert error<=1e-12
            crosses.append({'anchor':int(data['anchors'][i]),'raw_gap_L1':float(np.abs(total).sum()),
                            'map_given_hard_history_L1':float(np.abs(direct).sum()),'history_given_soft_map_L1':float(np.abs(inherited).sum()),
                            'decomposition_linf_error':error,'hard_own_publish':bool(hard['trade_mask'][i]),'soft_own_publish':bool(soft['trade_mask'][i]),
                            'soft_hard_history_publish':bool(sh[3]),'hard_soft_history_publish':bool(hs[3]),
                            'hard_own_gross':float(np.abs(hard['raw'][i]).sum()),'soft_own_gross':float(np.abs(soft['raw'][i]).sum()),
                            'soft_hard_history_gross':float(sh[2].abs().sum()),'hard_soft_history_gross':float(hs[2].abs().sum())})
    def arr(t):return t.numpy()
    layer_rows=[];arrays={}
    for i in range(count):
        h=traces['hard/identity'][i];v=traces['soft/identity'][i]
        if h is None or v is None:continue
        scores=score[off[i]:off[i+1]];row={'anchor':int(data['anchors'][i]),'members':len(members[i]),'score_std':float(scores.std(unbiased=False)),
             'hard_rank_std':float(h['zf'].std(unbiased=False)),'soft_rank_std':float(v['zf'].std(unbiased=False)),
             'w0':float(h['w0']),'w2':float(h['w2']), 'chains':[]}
        arrays[f'{i}_hard_zf']=arr(h['zf']);arrays[f'{i}_soft_zf']=arr(v['zf'])
        for j,leg in enumerate(('king_fund','f10_fund')):
            a,b=h['chains'][j],v['chains'][j];d={'leg':leg}
            for k in ('input_z','z','v','target','previous_state','sm','output'):
                if a.get(k) is None or b.get(k) is None:raise ValueError('incomplete trace layer '+k)
                delta=arr(b[k])-arr(a[k]);d[k]={'L1':float(np.abs(delta).sum()),'Linf':float(np.abs(delta).max())}
            for k in ('blocked','band','leave'):d[k+'_different']=int((a[k]!=b[k]).sum())
            row['chains'].append(d)
            for label,x in [('hard',a),('soft',b)]:
                for k in ('input_z','blocked','z','target','band','leave','sm','previous_state','output'):arrays[f'{i}_{label}_{leg}_{k}']=arr(x[k])
        layer_rows.append(row)
    np.savez_compressed(out/'LAYER_TRACES.npz',**arrays)
    write(out/'LAYER_ROWS.json',layer_rows);write(out/'STATE_CROSSES.json',crosses)
    # Rehash every input after measurement; use the same manifest as the accepted pack.
    accepted=s['acceptance'].accept(OUTPUT.parent,verify_arrays=True);assert accepted==s['accepted'],'input acceptance changed'
    assert state_hash()==initial,'model changed'
    T.cuda.synchronize()
    write(out/'WORKER_MEMORY.json',{'rss_high_water_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'max_cuda_reserved_bytes':T.cuda.max_memory_reserved()})
    write(out/'WORKER_RESULT.json',{'status':'MECHANISM_MEASURED_NOT_CANDIDATE','scope':'Jan2023/202608 checkpoint; engineering only; no new fit or PnL',
          'checks':checks,'transforms':transforms,'summary':summary,'anchors':count,'ready_anchors':len(layer_rows),
          'scale_changes_order':False,'optimizer_updates':0,'parameter_hash_before':initial,'parameter_hash_after':state_hash(),
          'executable':sys.executable,'torch':T.__version__,'numpy':np.__version__,'elapsed_seconds':time.monotonic()-started,
          'source_sha256':{p.name:sha(p) for p in HERE.glob('*.py')}})

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--worker',type=pathlib.Path);a=ap.parse_args()
    if a.worker!=OUTPUT or not (OUTPUT/'COMMAND.json').is_file():raise ValueError('guard managed invocation required')
    run(a.worker)
