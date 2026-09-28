"""alloc_combo.py — combination-layer arm combos for docs/DESIGN_combination_layer_2026-09-26.md.

DERIVED from dlarch's chain device news2_combo.py (sha256 81e2d274..., itself news2 P4 combo + a realpath verify_training and a wider
seed list; copy kept at upstream/news2_combo_dlarch_81e2d274.py). Inputs, identity assertions, universe, members, publication policies,
output layout and receipt are UNCHANGED. Three named substitutions, nothing else:
  S1  seats: legs.npz WL  ->  alloc_rules.seats_for(--rule, LR, WL). The in-service rule RECOMPUTES the seat and asserts it is WL bit for bit.
  S2  evolve/step: continuous_combo.evolve (1501c9f6) / combo_target.step (d7577e82)  ->  alloc_evolve / alloc_step below, which are those
      two functions verbatim except that the two z lines and the 0.55/0.45 blend take their scalars from alloc_rules.mix_weights(--mix, w).
      For --mix shared those scalars are the very objects step uses (w[0], w[2], .55, .45, fund*1.0), so the in-service arm must be bitwise.
      chain / exec_reshape are still compiled from combo_stage.py fb5a9407 by combo_target.source_kernels (imported, not copied).
  S3  receipt: + arm {rule, mix, seat receipt}, + the two substituted sources' sha.
usage (cwd = <root>/devices, env PNOISE_W=<root>): python alloc_combo.py --seed 42 --rule inservice --mix shared
"""
import os, sys, json, argparse, collections, datetime, pathlib, hashlib
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from scipy.stats import rankdata
import combo_target
from combo_target import source_kernels
from book_universe import align as align_universe, PATH as UNIVERSE_PATH, SHA as UNIVERSE_SHA
import alloc_rules

W = pathlib.Path(os.environ.get('PNOISE_W', '/dev/shm/pnoise_2026-09-24'))
combo_target.ROOT = W  # isolated output root contains the source-pinned producer copy


def verify_training(out, rec, seed, sha):
    """dlarch substitution 2 (verbatim from news2_combo.py 81e2d274): continuous_combo.verify_training with the fold-artifact path set
    compared by REALPATH. Nothing relaxed."""
    if rec.get("schema") == "holding_horizon_ridge_book/1":
        from residual_model import verify_training as verify_linear
        return verify_linear(out, rec, seed, sha)
    import pathlib as _pl
    if rec.get("seed") != seed: raise ValueError("wrong training seed")
    exp = {os.path.realpath(str(_pl.Path(out) / tag / name)) for tag in rec["folds"]
           for name in ("FOLD_RECEIPT.json", "model.pt", "scores.npz")}
    got = {os.path.realpath(p) for p in rec.get("fold_artifacts", {})}
    if got != exp:
        raise ValueError("fold artifact set (realpath-normalised): %d recorded vs %d expected" % (len(got), len(exp)))
    for p, h in rec["fold_artifacts"].items():
        if sha(p) != h: raise ValueError("fold artifact drift:" + p)
    for tag in rec["folds"]:
        rr = json.loads((_pl.Path(out) / tag / "FOLD_RECEIPT.json").read_text())
        if rr["seed"] != seed or rr["fold"] != tag or rr["inputs"] != rec["inputs"] or rr["sources"] != rec["sources"]:
            raise ValueError("fold identity")


# ───── S2: combo_target.step (d7577e82) verbatim except the marked lines ─────
def alloc_step(king_rank,f10_score,fund_rank,seats,rn8,members,qv,legal,params,kc_prev,fc_prev,publication,mix,mom=None):
    m=np.asarray(members,int);nw=len(kc_prev);n=len(m)
    if len(fc_prev)!=nw or np.asarray(legal).shape!=(nw,) or len(np.unique(m))!=n or np.any(m<0) or np.any(m>=nw):raise ValueError('combo identity')
    if any(np.asarray(v).shape!=(n,) for v in (king_rank,f10_score,fund_rank,rn8,qv)):raise ValueError('member field axes')
    if np.asarray(seats).shape!=(3,) or not np.isfinite(seats).all() or np.any(np.asarray(seats)<0):raise ValueError('seats')
    if not np.isfinite(kc_prev).all() or not np.isfinite(fc_prev).all():raise ValueError('state unknown')
    if not np.isfinite(king_rank).all():return {'accepted':False,'reason':'King scores incomplete','kc':kc_prev.copy(),'fc':fc_prev.copy(),'raw':None,'executor_reshaped':None}
    if publication not in ('literal','scaled_diagnostic'):raise ValueError('publication policy')
    okf=np.isfinite(f10_score);zf=np.full(n,np.nan)
    zf[okf]=rankdata(np.asarray(f10_score)[okf])/max(okf.sum()-1,1)-.5
    w=np.array([seats[0],0.,seats[2]],float);w=w/w.sum() if w.sum()>1e-12 else np.array([.5,0.,.5])
    ak,bk,af,bf,mk,mf,sg=alloc_rules.mix_weights(mix,w)                                   # ALLOC S2
    fr=sg*np.nan_to_num(fund_rank,nan=0.)                                                    # ALLOC S2 (sg=1.0 for shared: bitwise no-op)
    zkc=ak*np.nan_to_num(king_rank,nan=0.)+bk*fr                                             # ALLOC S2 (step: w[0]*king + w[2]*fund)
    zfc=af*np.nan_to_num(zf,nan=0.)+bf*fr                                                    # ALLOC S2 (step: w[0]*zf + w[2]*fund)
    if mix=='momneutral':zkc=alloc_rules.mom_residualise(zkc,mom);zfc=alloc_rules.mom_residualise(zfc,mom)   # ALLOC M (rule §8/§9, M-a: before the rn8 clamp and the chain)
    zkc=np.where((zkc<0)&np.isfinite(rn8)&(rn8<=-.001),0.,zkc)
    zfc=np.where((zfc<0)&np.isfinite(rn8)&(rn8<=-.001),0.,zfc)
    ns=source_kernels();ns.update(P=params,NW=nw,pm=m,sel=np.isfinite(qv)&(np.asarray(qv)>=params['qv4h_min']),LIVE_MASK=np.asarray(legal,bool))
    ns['H']=kc_prev;kc=ns['chain'](zkc);ns['H']=fc_prev;fc=ns['chain'](zfc)
    if kc is None or fc is None:return {'accepted':False,'reason':'degenerate signal','kc':kc_prev.copy(),'fc':fc_prev.copy(),'raw':None,'executor_reshaped':None}
    raw=mk*kc+mf*fc;gross=float(np.abs(raw).sum());names=int((np.abs(raw)>1e-9).sum())         # ALLOC S2 (step: .55*kc+.45*fc)
    if mix=='conc20':raw=alloc_rules.concentrate(raw,0.20)   # ALLOC R_M (rule §9): gross unchanged by construction; the publication gates (gross, names) are evaluated on the combo BEFORE this red-control transform, else the 0.375*n names gate would hold every anchor and R_M would never trade
    coverage_gate=380 if publication=='literal' else int(np.ceil(.95*n));names_gate=150 if publication=='literal' else int(np.ceil(.375*n))
    reasons=[]
    if okf.sum()<coverage_gate:reasons.append('F10 coverage')
    if not .4<=gross<=1.2:reasons.append('gross')
    if names<names_gate:reasons.append('names')
    return {'accepted':not reasons,'reason':','.join(reasons) if reasons else 'publish','kc':kc,'fc':fc,'raw':raw,'executor_reshaped':ns['exec_reshape'](raw),'gross':gross,'names':names,'f10_count':int(okf.sum()),'publication':publication,'seat_masked':w}


# ───── S2: continuous_combo.evolve (1501c9f6) verbatim except step -> alloc_step(..., mix) ─────
def alloc_evolve(anchors,king,f10,fund,seats,rn8,members,qv,legal,ready,params,publication,mix,mom=None):
    a=np.asarray(anchors);k=np.asarray(king);n,w=k.shape
    if len(a)!=n or not np.isfinite(a).all() or np.any(a!=np.floor(a)) or np.any(a%14400) or np.any(np.diff(a)!=14400):raise ValueError('continuous 4h anchor axis required')
    if any(np.asarray(v).shape!=(n,w) for v in (f10,fund,rn8,qv,legal)) or np.asarray(seats).shape!=(n,3) or len(members)!=n or np.asarray(ready).shape!=(n,):raise ValueError('combo field axes')
    if publication not in ('literal','scaled_diagnostic'):raise ValueError('publication policy')
    kc=np.zeros(w);fc=np.zeros(w);out={s:np.zeros((n,w)) for s in ('kc','fc','raw','weights')};out['trade_mask']=np.zeros(n,bool);reasons=[]
    for i in range(n):
        if not ready[i]:
            reasons.append('unready causal legs');out['kc'][i]=kc;out['fc'][i]=fc;continue
        m=np.asarray(members[i],int)
        result=alloc_step(k[i,m],f10[i,m],fund[i,m],seats[i],rn8[i,m],m,qv[i,m],legal[i],params,kc,fc,publication,mix,None if mom is None else mom[i][m])   # ALLOC S2
        kc=np.where(np.abs(result['kc'])>1e-9,result['kc'],0.);fc=np.where(np.abs(result['fc'])>1e-9,result['fc'],0.)
        out['kc'][i]=kc;out['fc'][i]=fc;reasons.append(result['reason'])
        if result['raw'] is not None:out['raw'][i]=result['raw']
        if result['accepted']:
            out['trade_mask'][i]=True
            out['weights'][i]=np.where(np.abs(result['raw'])>1e-9,result['raw'],0.)
    out['reason']=np.asarray(reasons);return out


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(16 << 20), b''): h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--seed', type=int, choices=(42, 2027, 7, 11, 23, 101, 3, 5), required=True)
    ap.add_argument('--rule', required=True); ap.add_argument('--mix', required=True, choices=('shared', 'orth', 'fundflip', 'negbook', 'momneutral', 'conc20')); args = ap.parse_args()
    froot = W / f'work/f10_s{args.seed}'
    paths = [W / 'work/NEWS_FEATURES.npz', W / 'work/legs.npz', W / 'receipts/P3_LEGS.json', froot / 'F10_OOF.npz', froot / 'TRAIN_RECEIPT.json', W / 'inputs/bundle_config.json',
             W / 'receipts/P1_members_2025H2on.npz', pathlib.Path('/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz')]
    ident = {str(p): sha(p) for p in paths}
    rec = json.loads(paths[4].read_text()); lr = json.loads(paths[2].read_text())
    assert rec['status'] in ('ALL_DECLARED_FOLDS_SCORED_NOT_COMBO_CERTIFIED', 'LINEAR_ALL_DECLARED_FOLDS_SCORED_NOT_COMBO_CERTIFIED', 'HORIZON_LINEAR_FOLDS_COMPLETE_NOT_COMBO_CERTIFIED') and rec['pred_sha256'] == ident[str(paths[3])]
    verify_training(froot, rec, args.seed, sha)
    assert set(rec['folds']) == set(rec['expected_folds'])
    for p, h in rec['inputs'].items(): assert sha(p) == h, ('training input drift', p)
    for p, h in rec['sources'].items(): assert sha(p) == h, ('training source drift', p)
    assert ident[str(paths[1])] == lr['sha256']
    F = np.load(paths[0]); leg = np.load(paths[1]); score = np.load(paths[3]); a = F['anchors'].astype(np.int64); syms = F['symbols']
    for z in (leg, score): assert np.array_equal(z['E_ts'], a) and np.array_equal(z['symbols'], syms)
    mk = np.load(paths[7]); assert np.array_equal(mk['ts'].astype(np.int64), a)
    crypto = np.load(paths[6])['crypto']; cand = mk['mask'] & crypto[None, :]
    off = F['off']; members = [F['m'][off[i]:off[i + 1]].astype(np.int64) for i in range(len(a))]
    assert sha(UNIVERSE_PATH) == UNIVERSE_SHA, 'universe content identity'
    universe = np.load(UNIVERSE_PATH)
    use = (a >= 1672531200) & (a <= universe['ts'][-1]); au = a[use]
    book_legal = align_universe(au, syms, universe) & cand[use]
    ident[UNIVERSE_PATH] = UNIVERSE_SHA
    config = json.loads(paths[5].read_text())
    seats_all, seat_rec = alloc_rules.seats_for(args.rule, leg['LR'], leg['WL'])                      # ALLOC S1
    mom_u = None
    if args.mix == 'momneutral':                                                                          # ALLOC M: past 1/3/7-day log returns, causal
        MP = pathlib.Path('/workspace/alloc_2026-09-26/work/mom_features.npz'); ident[str(MP)] = sha(MP)
        MZ = np.load(MP); assert np.array_equal(MZ['E_ts'].astype(np.int64), a) and np.array_equal(MZ['symbols'], syms)
        mom_u = MZ['mom'][use]
    seats_u = seats_all[use]
    wl_u = leg['WL'][use].astype(np.float64)
    seat_rec['anchors_seat_differs_from_WL_on_ready'] = int(((seats_u != wl_u).any(1) & leg['ready'][use]).sum())
    sources = {str(p): sha(p) for p in [pathlib.Path(__file__), pathlib.Path(HERE) / 'alloc_rules.py', pathlib.Path(HERE) / 'combo_target.py', pathlib.Path(HERE) / 'book_universe.py',
                                          W / 'vendor_live/fea171/combo_stage.py']}
    out = W / f'work/combo_s{args.seed}'; out.mkdir(exist_ok=False)
    mem_u = [members[i] for i in np.flatnonzero(use)]
    outside = int(sum(int((~book_legal[k][m]).sum()) for k, m in enumerate(mem_u)))
    summary = {}
    for policy in ('literal', 'scaled_diagnostic'):
        result = alloc_evolve(au, leg['KZ'][use].astype(np.float64), score['P'][use].astype(np.float64), leg['ZFD'][use].astype(np.float64), seats_u,
                              leg['RN8'][use].astype(np.float64), mem_u, leg['QV'][use].astype(np.float64), book_legal, leg['ready'][use], config['params'], policy, args.mix, mom_u)
        p = out / (policy + '.npz'); tmp = out / (policy + '.tmp.npz'); np.savez_compressed(tmp, E_ts=au, symbols=syms, **result); tmp.replace(p)
        counts = dict(collections.Counter(result['reason'])); years = {}
        yr = np.array([datetime.datetime.fromtimestamp(int(x), datetime.timezone.utc).year for x in au])
        for y in np.unique(yr):
            m = yr == y; years[str(y)] = {'anchors': int(m.sum()), 'publish': int(result['trade_mask'][m].sum()), 'mean_producer_gross': float(np.abs(result['raw'][m]).sum(1).mean())}
        summary[policy] = {'path': str(p), 'sha': sha(p), 'reasons': counts, 'years': years}
    for p, h in ident.items(): assert sha(p) == h
    for p, h in sources.items(): assert sha(p) == h
    receipt = {'status': 'ALLOC_ARM_TARGETS_NOT_EXECUTION_PNL', 'seed': args.seed, 'arm': {'rule': args.rule, 'mix': args.mix, 'seat': seat_rec},
               'inputs': ident, 'sources': sources, 'policies': summary,
               'model_kind': rec.get('model_kind','F10'), 'model_target':rec.get('target'),
               'seed_note':rec.get('seed_note','F10 model seed'),
               'member_cells_outside_book_universe': outside,
               'state_init': 'zero at 2023-01-01; hypothetical common start, not live archived state',
               'hold_contract': 'trade_mask False = maintain quantities, never King substitution',
               'limits': ['production-caliber legs replayed on history; seat history starts with King OOF (2022H2)', 'no execution/cash or policy-stop result',
                          'scaled_diagnostic changes historical publication gate; never current-live literal',
                          'F10 score slot is replaced by the model_kind/model_target named above; seed may be interface-only. King/funding/seat stay NC; this is not a new F10 training run']}
    (out / 'TARGET_RECEIPT.json').write_text(json.dumps(receipt, indent=2, allow_nan=False))
    print(json.dumps({k: receipt[k] for k in ('seed', 'member_cells_outside_book_universe')}), json.dumps(receipt['arm']), json.dumps({k: v['reasons'] for k, v in summary.items()}), flush=True)


if __name__ == '__main__':
    main()
