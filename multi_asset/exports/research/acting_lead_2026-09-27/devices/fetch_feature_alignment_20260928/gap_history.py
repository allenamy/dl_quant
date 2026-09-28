"""Fixed three observed membership holes, propagated with the original feature code."""
import ast,copy,io,json,sys,time,traceback
from pathlib import Path
import numpy as np
import run as R

FETCH=Path('/dev/shm/fetch_feature_alignment_20260928')
FETCH_SHA='e40122efbc5277cbdf0ec8f48df33401574037948b09e33bbe7d0de21eaf466a'
GAPS=frozenset((1790424000,1790438400,1790481600))

def remove_observed_holes(history,a):
    if a in GAPS or a not in history:raise ValueError('current_anchor_invalid')
    out=R.history_asof(history,a)
    removed=[]
    for g in sorted(GAPS):
        if g<a:
            if g not in out:raise ValueError('control_history_already_missing')
            removed.append(g);del out[g]
    return out,removed

def setup_function():
    """Reuse the pinned initialization and King controls, stopping before any F10 runs."""
    source=Path(R.__file__).read_text();tree=ast.parse(source)
    f=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    boundaries=[i for i,n in enumerate(f.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='mini' for t in n.targets)]
    if len(boundaries)!=1:raise ValueError('setup_AST_boundary')
    f=copy.deepcopy(f);f.name='prepare_gap';f.body=f.body[:boundaries[0]]+[ast.Return(ast.Call(ast.Name('locals',ast.Load()),[],[]))]
    ns=dict(R.__dict__);module=ast.fix_missing_locations(ast.Module(body=[f],type_ignores=[]));exec(compile(module,'pinned_fetch_setup','exec'),ns)
    return ns['prepare_gap'],R.sha(R.__file__)

def main(root):
    root=Path(root)
    if R.sha(FETCH/'RESULT.json')!=FETCH_SHA:raise ValueError('fetch_result_changed')
    old=json.loads((FETCH/'RESULT.json').read_text())
    if R.sha(R.__file__)!=old['inputs'].get(str(Path(R.__file__).resolve())):raise ValueError('setup_source_not_original')
    for name,h in old['outputs'].items():
        if R.sha(FETCH/name)!=h:raise ValueError('fetch_output_changed')
    prepare,setup_sha=setup_function();c=prepare(str(root))
    H,I,sy=c['H'],c['I'],c['sy'];N=c['N'];rows=c['rows'];E=c['E'];z=c['z'];frows=c['frows']
    mh=c['variant_mh'];mini=H._mini_block();cf=H._combo_funcs();scratch=root/'scratch';scratch.mkdir()
    pins=c['pins'];pins[str(Path(__file__).resolve())]=R.sha(__file__);pins[str(FETCH/'RESULT.json')]=FETCH_SHA
    for name,h in old['outputs'].items():pins[str(FETCH/name)]=h
    # Start from the passed C4 arrays; do not redo already completed unaffected features.
    controls=[];outputs={};history_checks=[]
    for row in rows:
        a=row['anchor'];stored=R.load(FETCH/f'ROW_{a}.npz')
        for k,v in frows[a].items():
            if not R.same(v,stored[k]):raise ValueError('fetch_King_context_changed:'+k)
        frows[a]['P']=stored['P'].copy()
        if a==1790409600:
            ctl=H.pass2_anchor(I,a,R.history_asof(mh,a),str(scratch),mini,cf)
            if ctl['mh_missing']!=0 or not all(R.same(np.asarray(ctl[k],np.float32),stored[k]) for k in ('X82','X89')):raise ValueError('last_pre_gap_control')
            controls.append(a)
        if a<min(GAPS):continue
        if time.monotonic()-c['start']>860:raise TimeoutError('gap_budget_900s')
        R.resources();hist,removed=remove_observed_holes(mh,a)
        rts=I.window(a)[0];eligible=set(int(t) for i,t in enumerate(rts) if i>=48 and t%14400==0)
        expected=len(set(removed)&eligible)
        got=H.pass2_anchor(I,a,hist,str(scratch),mini,cf)
        xx=np.concatenate((got['X82'],got['X89']),axis=1).astype(np.float32)
        if got['mh_missing']!=expected or not np.isfinite(xx).all():raise ValueError('unexplained_feature_history_hole')
        frows[a]['P']=c['predict'](xx)
        path=root/f'ROW_{a}.npz';np.savez_compressed(path,anchor=np.int64(a),X82=got['X82'],X89=got['X89'],**frows[a]);outputs[path.name]=R.sha(path)
        history_checks.append({'anchor':a,'removed_known_holes':removed,'expected_missing':expected,'actual_missing':got['mh_missing']})
        print(time.strftime('%FT%TZ',time.gmtime()),'GAP_FEATURE_ROW',a,flush=True)
    if len(controls)!=1 or len(history_checks)!=7:raise ValueError('fixed_population')
    step=R.imp(R.NS/'devices/combo_target.py','gap_step').step;seed=R.START-14400
    def state(k,a):
        with np.load(io.BytesIO(z.read(f'fea171/state_H_{k}_{a}.npz')),allow_pickle=False) as h:
            if int(h['anchor'])!=a:raise ValueError('state_anchor')
            out=np.zeros(N);out[h['idx'].astype(int)]=h['val'];return out
    hs={k:state(k,seed) for k in ('kc','fc')};states={};result_rows=[];by={r['anchor']:r for r in rows};reference=R.load(FETCH/'STATES.npz')
    for i,a0 in enumerate(E):
        a=int(a0)
        if a<R.START:continue
        if a not in GAPS:
            f=frows[a];args={k:f[v].astype(float) for k,v in [('king_rank','KZ'),('fund_rank','ZFD'),('rn8','RN8'),('qv','QV'),('f10_score','P')]}
            got=step(**args,seats=np.asarray(by[a]['live_w3']),members=f['m'],legal=c['elig']['legal'][i+1],params=c['params'],kc_prev=hs['kc'],fc_prev=hs['fc'],publication='literal')
            if not got['accepted']:raise ValueError('publication_failed')
            hs={k:got[k].copy() for k in ('kc','fc')}
        raw=.55*hs['kc']+.45*hs['fc'];stack=np.stack((hs['kc'],hs['fc'],raw));states[f'C5_{a}']=stack
        if a<min(GAPS) and not np.array_equal(stack,reference[f'C4_fetch_{a}']):raise ValueError('pre_gap_continuous_control')
        if a not in by:continue
        livej=json.loads(z.read(f'state/target_live/{a}.json'));live=np.array([livej['weights'].get(s,0.) for s in sy]);err=R.error(live,raw)
        result_rows.append({'anchor':a,'utc':by[a]['utc'],'error':err,'component_errors':{k:R.error(state(k,a),hs[k]) for k in ('kc','fc')},'max_error_le_1e8':err['max_abs']<=1e-8})
    path=root/'STATES.npz';np.savez_compressed(path,**states);outputs[path.name]=R.sha(path)
    for p,h in pins.items():
        if R.sha(p)!=h:raise ValueError('input_changed:'+p)
    result={'status':'CONDITIONAL_TARGET_TOLERANCE_PASS' if all(r['max_error_le_1e8'] for r in result_rows) else 'RESIDUAL_NOT_EXPLAINED', 'utc':time.strftime('%FT%TZ',time.gmtime()),'inputs':pins,'outputs':outputs,'history_checks':history_checks,'feature_control':controls,'rows':result_rows,'setup_source_sha256':setup_sha,'seconds':time.monotonic()-c['start'],'limits':['Historical live seats supplied, not reconstructed','Reproduces existing production gap behavior, not a fix or release','No PnL or independent full-history certification']}
    R.save(root/'RESULT.json',result);R.save(root/'TERMINAL.json',{'rc':0,'utc':time.strftime('%FT%TZ',time.gmtime()),'result_sha256':R.sha(root/'RESULT.json')})

if __name__=='__main__':
    try:main(sys.argv[1])
    except BaseException as e:
        p=Path(sys.argv[1]);p.mkdir(exist_ok=True);R.save(p/'TERMINAL.json',{'rc':1,'utc':time.strftime('%FT%TZ',time.gmtime()),'error':repr(e),'traceback':traceback.format_exc()});raise
