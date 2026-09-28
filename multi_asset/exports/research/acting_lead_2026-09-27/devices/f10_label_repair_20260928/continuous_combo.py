"""Continuous corrected-candidate combo targets, not an execution simulator.

States start from zero at the declared first anchor, then use their OWN previous
states, including on publication failure. A false trade_mask means HOLD CONTRACTS.
The weights array is deliberately zero on HOLD; consuming it without the mask
would wrongly flatten the account. Producer sparse-state serialization is kept.
"""
import pathlib,json,argparse,collections
import numpy as np
from combo_target import step,ROOT as LOCAL_ROOT
from book_universe import align as align_universe,PATH as UNIVERSE_PATH,SHA as UNIVERSE_SHA

def verify_training(out,rec,seed,sha):
    if rec.get('seed')!=seed:raise ValueError('wrong training seed')
    expected={str(out/tag/name) for tag in rec['folds'] for name in ('FOLD_RECEIPT.json','model.pt','scores.npz')}
    if set(rec.get('fold_artifacts',{}))!=expected:raise ValueError('fold artifact set')
    for p,h in rec['fold_artifacts'].items():
        if sha(p)!=h:raise ValueError('fold artifact drift:'+p)
    for tag in rec['folds']:
        rr=json.loads((out/tag/'FOLD_RECEIPT.json').read_text())
        if rr['seed']!=seed or rr['fold']!=tag or rr['inputs']!=rec['inputs'] or rr['sources']!=rec['sources']:raise ValueError('fold identity')
        if rr['model_sha256']!=rec['fold_artifacts'][str(out/tag/'model.pt')] or rr['score_sha256']!=rec['fold_artifacts'][str(out/tag/'scores.npz')]:raise ValueError('fold content identity')

def evolve(anchors,king,f10,fund,seats,rn8,members,qv,legal,ready,params,publication):
    a=np.asarray(anchors);k=np.asarray(king);n,w=k.shape
    if len(a)!=n or not np.isfinite(a).all() or np.any(a!=np.floor(a)) or np.any(a%14400) or np.any(np.diff(a)!=14400):raise ValueError('continuous 4h anchor axis required')
    if any(np.asarray(v).shape!=(n,w) for v in (f10,fund,rn8,qv,legal)) or np.asarray(seats).shape!=(n,3) or len(members)!=n or np.asarray(ready).shape!=(n,):raise ValueError('combo field axes')
    if publication not in ('literal','scaled_diagnostic'):raise ValueError('publication policy')
    kc=np.zeros(w);fc=np.zeros(w);out={s:np.zeros((n,w)) for s in ('kc','fc','raw','weights')};out['trade_mask']=np.zeros(n,bool);reasons=[]
    for i in range(n):
        if not ready[i]:
            reasons.append('unready causal legs');out['kc'][i]=kc;out['fc'][i]=fc;continue
        m=np.asarray(members[i],int)
        result=step(k[i,m],f10[i,m],fund[i,m],seats[i],rn8[i,m],m,qv[i,m],legal[i],params,kc,fc,publication)
        # State files contain only abs(state)>1e-9. Reloaded state is NOT rounded.
        kc=np.where(np.abs(result['kc'])>1e-9,result['kc'],0.);fc=np.where(np.abs(result['fc'])>1e-9,result['fc'],0.)
        out['kc'][i]=kc;out['fc'][i]=fc;reasons.append(result['reason'])
        if result['raw'] is not None:out['raw'][i]=result['raw']
        if result['accepted']:
            out['trade_mask'][i]=True
            # Actual target_live serializes float64 and excludes <=1e-9 entries.
            out['weights'][i]=np.where(np.abs(result['raw'])>1e-9,result['raw'],0.)
    out['reason']=np.asarray(reasons);return out

def main():
    from build_combo_inputs import ROOT,sha
    ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,choices=(42,2027),required=True);args=ap.parse_args()
    r=ROOT/'corrected_combo_v1d';froot=r/f'f10_s{args.seed}'
    paths=[r/'data/dlw_targets.npz',r/'data/f10v2_legs.npz',r/'data/LEGS_RECEIPT.json',r/'data/funding_state.npz',r/'BUILD_RECEIPT.json',froot/'F10_OOF.npz',froot/'TRAIN_RECEIPT.json',ROOT/'vendor_live/shadow_bundle/config.json']
    ident={str(p):sha(p) for p in paths};rec=json.loads(paths[6].read_text());br=json.loads(paths[4].read_text());lr=json.loads(paths[2].read_text())
    assert rec['status']=='ALL_DECLARED_FOLDS_SCORED_NOT_COMBO_CERTIFIED' and rec['pred_sha256']==ident[str(paths[5])]
    verify_training(froot,rec,args.seed,sha)
    assert set(rec['folds'])==set(rec['expected_folds']) and len(rec['folds'])==len(rec['expected_folds'])
    for p,h in rec['inputs'].items():assert sha(p)==h,('training input drift',p)
    for p,h in rec['sources'].items():assert sha(p)==h,('training source drift',p)
    for p in paths[:5]:
        if str(p) in rec['inputs']:assert ident[str(p)]==rec['inputs'][str(p)]
    assert ident[str(paths[1])]==lr['artifact_sha'];assert sha(ROOT/'devices/combo_legs.py')==lr['source_sha']
    for p,h in lr['input_sha'].items():assert sha(p)==h,('leg upstream drift',p)
    assert ident[str(paths[0])]==br['artifacts'][str(paths[0])] and ident[str(paths[3])]==br['artifacts'][str(paths[3])]
    t=np.load(paths[0],allow_pickle=True);leg=np.load(paths[1]);fund=np.load(paths[3]);score=np.load(paths[5]);a=t['E_ts'];syms=t['symbols']
    for z in (leg,fund,score):assert np.array_equal(z['E_ts'],a) and np.array_equal(z['symbols'],syms)
    # No synthetic F10 predictions for 2022. Start hypothetical strategy in cash.
    assert sha(UNIVERSE_PATH)==UNIVERSE_SHA,'universe content identity'
    universe=np.load(UNIVERSE_PATH)
    # Explicit common extent, never fabricate rows beyond the frozen book axis.
    use=(a>=1672531200)&(a<=universe['ts'][-1]);a=a[use]
    book_legal=align_universe(a,syms,universe)&fund['legal'][use]
    ident[UNIVERSE_PATH]=UNIVERSE_SHA
    config=json.loads(paths[-1].read_text());sources={str(p):sha(p) for p in [pathlib.Path(__file__),ROOT/'devices/combo_target.py',ROOT/'devices/book_universe.py',ROOT/'vendor_live/fea171/combo_stage.py']}
    out=r/f'combo_s{args.seed}'
    if out.is_symlink():
        if out.resolve().parent!=pathlib.Path('/tmp/codex_combo_20260923'):raise ValueError('output link outside isolated ephemeral root')
        out.resolve().mkdir(exist_ok=False)
    else:out.mkdir(exist_ok=False)
    summary={}
    for policy in ('literal','scaled_diagnostic'):
        result=evolve(a,leg['KZ'][use],score['P'][use],leg['ZFD'][use],leg['WL'][use],fund['rn8'][use],list(t['members'][use]),t['qvk'][use],book_legal,leg['ready'][use],config['params'],policy)
        p=out/(policy+'.npz');tmp=p.with_suffix('.tmp.npz');np.savez_compressed(tmp,E_ts=a,symbols=syms,**result);tmp.replace(p)
        counts=dict(collections.Counter(result['reason']));years={}
        import datetime
        yr=np.array([datetime.datetime.fromtimestamp(int(x),datetime.timezone.utc).year for x in a])
        for y in np.unique(yr):
            m=yr==y;years[str(y)]={'anchors':int(m.sum()),'publish':int(result['trade_mask'][m].sum()),'mean_producer_gross':float(np.abs(result['raw'][m]).sum(1).mean())}
        summary[policy]={'path':str(p),'sha':sha(p),'reasons':counts,'years':years}
    for p,h in ident.items():assert sha(p)==h
    for p,h in sources.items():assert sha(p)==h
    receipt={'status':'CORRECTED_CANDIDATE_TARGETS_NOT_EXECUTION_PNL','seed':args.seed,'inputs':ident,'sources':sources,'policies':summary,'state_init':'zero at 2023-01-01; hypothetical common start, not live archived state','hold_contract':'trade_mask False = maintain quantities, never King substitution','limits':['not whole producer parity: causal historical funding base and corrected features explicitly differ','no execution/cash or policy-stop result','scaled_diagnostic changes historical publication gate; never current-live literal']}
    (out/'TARGET_RECEIPT.json').write_text(json.dumps(receipt,indent=2,allow_nan=False));print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
