"""One frozen NC liquidity blend; targets/support only, no cash or live calls."""
import argparse,ast,hashlib,json,os,sys,time
from pathlib import Path
import numpy as np
from scipy.stats import rankdata


def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(4<<20),b''):h.update(b)
    return h.hexdigest()


def dump(p,x):
    b=(json.dumps(x,indent=2,allow_nan=False)+'\n').encode();tmp=Path(str(p)+'.tmp')
    with open(tmp,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
    tmp.replace(p)
    assert Path(p).read_bytes()==b


def amihud_at(r,logq,end):
    if end<287:return np.full(r.shape[1],np.nan)
    r=np.asarray(r[end-287:end+1],float);q=np.asarray(logq[end-287:end+1],float)
    ok=np.isfinite(r)&np.isfinite(q);n=ok.sum(0)
    den=np.where(ok,np.expm1(np.clip(q,0,30)),0).sum(0)
    num=np.abs(np.where(ok,r,0).sum(0));out=np.full(r.shape[1],np.nan)
    good=(n>=274)&(den>0);out[good]=num[good]/den[good]*1e6
    return out


def ranked(x,mask):
    good=np.asarray(mask,bool)&np.isfinite(x);out=np.full(len(x),np.nan)
    if good.sum()>=10:out[good]=rankdata(np.asarray(x)[good])/max(good.sum()-1,1)-.5
    return out


def blend(f,a):return .5*np.asarray(f)+.5*np.asarray(a)


def leg_return(z,y):
    z=np.nan_to_num(np.asarray(z,float));ok=np.isfinite(y)
    zz=np.where(ok,z,0.);zz-=zz[ok].mean() if ok.sum() else 0
    g=np.abs(zz).sum()
    return float((zz/g*np.nan_to_num(y,nan=0.)).sum()*1e4) if g>1e-9 else 0.


def support(t,published,groups):
    w=np.abs(t[published]);g=groups[published]
    sums=[float(w[g==i].sum()) for i in range(4)]+[float(w[g<0].sum())]
    total=float(w.sum())
    if not np.isclose(sum(sums),total,rtol=1e-12,atol=1e-12):raise ValueError('support population not closed')
    return {'published_anchors':int(published.sum()),'gross_sum':total,
            'gross_sum_by_q1_q4_unknown':sums,
            'gross_share_by_q1_q4_unknown':[v/total for v in sums] if total else None}


def exact(x,y,label):
    if x.dtype!=y.dtype or x.shape!=y.shape:raise ValueError(label+' shape/dtype mismatch')
    if not np.array_equal(x,y,equal_nan=True):raise ValueError(label+' numeric identity failure')
    # Arrays are the claimed identity; ZIP timestamps/encoding are not a signal.


def main(out):
    out=Path(out);out.mkdir(exist_ok=False);t0=time.time()
    NS=Path('/dev/shm/news2_2026-09-23');NC=Path('/dev/shm/nc_2026-09-23')
    paths={'features':NS/'work/NEWS_FEATURES.npz','legs':NS/'work/legs.npz',
        'legs_receipt':NS/'receipts/P3_LEGS.json','axes':NC/'work/axes.npz',
        'raw_returns':NC/'work/R_crypto.npy','cache':NC/'work/cache_crypto.npy',
        'config':NS/'inputs/bundle_config.json','shadow':NC/'tree/shadow_loop_v3.py',
        'masks':Path('/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz'),
        'crypto':NS/'receipts/P1_members_2025H2on.npz',
        'combo_source':NS/'vendor_live/fea171/combo_stage.py'}
    identities={str(p):sha(p) for p in paths.values()}
    expected={'features':'3c886a2bc0ff65c10b7e0a621c9468210bbd77ef58c90e625f0a29354d63c4d8',
        'raw_returns':'16458cab70cfa65a24360fe602951cfa04f8f33ed0e9a374c0ca598a1e56f185',
        'shadow':'9403dedd0a578cb64f8c542183cf5c6582dc31c5b35cad1d3d30ee34f46c149c'}
    for k,h in expected.items():assert identities[str(paths[k])]==h,k
    lrrec=json.loads(paths['legs_receipt'].read_text())
    assert lrrec['sha256']==identities[str(paths['legs'])]
    with np.load(paths['features']) as z:F={k:z[k] for k in ('anchors','symbols','off','m','fe_v','base_val','qvm')}
    with np.load(paths['legs']) as z:L={k:z[k] for k in z.files}
    ax=np.load(paths['axes']);ts=ax['ts'];cols=ax['crypto_cols'];a=F['anchors'];syms=F['symbols'];n=len(a);nw=len(syms)
    assert np.array_equal(a,L['E_ts']) and np.array_equal(a,ax['anchors']) and np.array_equal(syms,ax['symbols'])
    assert np.all(np.diff(ts)==300) and np.all(np.diff(a)==14400)
    assert np.array_equal(L['symbols'],syms)
    R=np.load(paths['raw_returns'],mmap_mode='r');C=np.load(paths['cache'],mmap_mode='r')
    assert R.shape==C.shape[:2]==(len(ts),len(cols))
    off=F['off'];members=[F['m'][off[i]:off[i+1]].astype(int) for i in range(n)]
    tree=ast.parse(paths['shadow'].read_bytes());tree.body=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='xz_in_base']
    assert len(tree.body)==1;ns={'np':np};exec(compile(tree,str(paths['shadow']),'exec'),ns)
    fund=np.full((n,nw),np.nan);lagrank=np.full_like(fund,np.nan)
    for i,A in enumerate(a):
        m=members[i];bv=F['base_val'][i];base={str(syms[j]):float(bv[j]) for j in np.flatnonzero(np.isfinite(bv))}
        if L['ready'][i]:fund[i,m]=ns['xz_in_base'](F['fe_v'][off[i]:off[i+1]],list(map(str,syms[m])),base)
        if i:
            j=int(np.searchsorted(ts,int(A)-14400));assert ts[j]==A-14400
            vals=np.full(nw,np.nan);vals[cols]=amihud_at(R,C[:,:,3],j)
            lagrank[i]=ranked(vals,np.isfinite(F['base_val'][i-1]))
        if i%2000==0:print('SIGNAL',i,flush=True)
    exact(fund.astype(np.float32),L['ZFD'],'baseline fund score')
    cand=blend(fund,lagrank);LR=L['LR'].copy();check=L['LR'].copy()
    for i in np.flatnonzero(np.isfinite(LR[:,2])):
        assert i+1<n and L['ready'][i] and len(members[i+1])>=50
        j=int(np.searchsorted(ts,a[i+1]));assert ts[j]==a[i+1]
        seg=np.full((48,nw),np.nan,np.float32);seg[:,cols]=R[j-47:j+1]
        ok=np.isfinite(seg);y=np.where(ok,seg,0).sum(0);y[ok.sum(0)<46]=np.nan;m=members[i]
        check[i,2]=leg_return(fund[i,m],y[m]);LR[i,2]=leg_return(cand[i,m],y[m])
    exact(check,L['LR'],'baseline fund LR')
    import alloc_rules,alloc_combo,combo_target,book_universe
    baseline_seats,_=alloc_rules.seats_for('inservice',L['LR'],L['WL'])
    seats=alloc_rules.msharpe(LR,900).astype(np.float32).astype(float)
    causal={}
    for i in (1000,5000,9000):
        altered=LR.copy();altered[i:]=np.nan_to_num(altered[i:])+99
        causal[str(i)]=bool(np.array_equal(alloc_rules.msharpe(altered,900)[i].astype(np.float32),seats[i].astype(np.float32)))
    assert all(causal.values())
    # Recorded source-pinned producer kernels retain the unchanged chain and reshape.
    combo_target.ROOT=NS
    identities[book_universe.PATH]=sha(book_universe.PATH);assert identities[book_universe.PATH]==book_universe.SHA
    uni=np.load(book_universe.PATH);use=(a>=1672531200)&(a<=uni['ts'][-1]);au=a[use]
    mk=np.load(paths['masks']);assert np.array_equal(mk['ts'].astype(np.int64),a)
    crypto=np.load(paths['crypto'])['crypto'];legal=book_universe.align(au,syms,uni)&(mk['mask']&crypto[None,:])[use]
    mu=[members[i] for i in np.flatnonzero(use)];params=json.loads(paths['config'].read_text())['params']
    assert params['msharpe_look']==900
    groups=np.full((n,nw),-1,np.int8)
    for i,m in enumerate(members):
        q=F['qvm'][off[i]:off[i+1]]
        assert np.isfinite(q).all()
        if len(q):groups[i,m]=np.minimum(3,np.floor(4*(rankdata(q)-.5)/len(q))).astype(np.int8)
    gu=groups[use];years=np.array([time.gmtime(int(t)).tm_year for t in au])
    windows={'full':np.ones(len(au),bool),'cost_0826_0910':(au>=1787702400)&(au<1789084800),
        'cost_0911_0918':(au>=1789084800)&(au<1789776000)}
    windows.update({str(y):years==y for y in np.unique(years)})
    comparison={};nsrc={};baseline_targets={};predictions={}
    for seed in (42,2027):
        root=NS/f'work/f10_s{seed}';pr=root/'F10_OOF.npz';tr=root/'TRAIN_RECEIPT.json';rec=json.loads(tr.read_text())
        assert rec['status']=='ALL_DECLARED_FOLDS_SCORED_NOT_COMBO_CERTIFIED' and rec['pred_sha256']==sha(pr)
        assert set(rec['folds'])==set(rec['expected_folds']);alloc_combo.verify_training(root,rec,seed,sha)
        for bucket in ('sources','inputs'):
            for p,h in rec[bucket].items():assert sha(p)==h,p
        identities[str(pr)]=sha(pr);identities[str(tr)]=sha(tr)
        P=np.load(pr);assert np.array_equal(P['E_ts'],a) and np.array_equal(P['symbols'],syms)
        predictions[seed]=P['P'][use].astype(float)
        for policy in ('literal','scaled_diagnostic'):
            refp=NS/f'work/combo_s{seed}/{policy}.npz';identities[str(refp)]=sha(refp)
            ref=np.load(refp);args=(au,L['KZ'][use].astype(float),predictions[seed])
            tail=(L['RN8'][use].astype(float),mu,L['QV'][use].astype(float),legal,L['ready'][use],params,policy,'shared')
            base=alloc_combo.alloc_evolve(*args,L['ZFD'][use].astype(float),baseline_seats[use],*tail)
            assert set(ref.files)==set(base)|{'E_ts','symbols'}
            for k,v in base.items():
                if v.dtype.kind in 'US':assert np.array_equal(v,ref[k]),k
                else:exact(v,ref[k],f'combo control {seed} {policy} {k}')
            baseline_targets[seed,policy]=base
            print('BASELINE_EXACT',seed,policy,flush=True)
    dump(out/'BASELINE_IDENTITY.json',{'all_four_array_sets_exact':True,'fund_score_LR_WL_exact':True,'sources':identities})
    for seed in (42,2027):
        for policy in ('literal','scaled_diagnostic'):
            base=baseline_targets[seed,policy]
            args=(au,L['KZ'][use].astype(float),predictions[seed])
            tail=(L['RN8'][use].astype(float),mu,L['QV'][use].astype(float),legal,L['ready'][use],params,policy,'shared')
            candidate=alloc_combo.alloc_evolve(*args,cand[use].astype(np.float32).astype(float),seats[use],*tail)
            dest=out/f'candidate_s{seed}_{policy}.npz';np.savez_compressed(dest,E_ts=au,symbols=syms,**candidate)
            nsrc[str(dest)]=sha(dest);br=np.zeros_like(base['weights']);cr=br.copy();kern=combo_target.source_kernels()['exec_reshape']
            for k in range(len(au)):
                if base['trade_mask'][k]:br[k]=kern(base['weights'][k])
                if candidate['trade_mask'][k]:cr[k]=kern(candidate['weights'][k])
            tab={}
            for label,w in windows.items():
                bp=base['trade_mask']&w;cp=candidate['trade_mask']&w;both=bp&cp
                tab[label]={'baseline':support(br,bp,gu),'candidate':support(cr,cp,gu),
                    'common_publish':int(both.sum()),'baseline_only':int((bp&~cp).sum()),'candidate_only':int((cp&~bp).sum()),
                    'mean_same_anchor_L1_on_common_publish':float(np.abs(cr[both]-br[both]).sum(1).mean()) if both.any() else None,
                    'mean_fund_seat_baseline':float(alloc_rules.masked_fund(baseline_seats[use][w]).mean()),
                    'mean_fund_seat_candidate':float(alloc_rules.masked_fund(seats[use][w]).mean())}
            comparison[f's{seed}_{policy}']=tab;print('TARGET_DONE',seed,policy,flush=True)
    np.savez_compressed(out/'CANDIDATE_LEGS.npz',E_ts=a,symbols=syms,ZFD=cand.astype(np.float32),LR=LR,WL=seats.astype(np.float32))
    nsrc[str(out/'CANDIDATE_LEGS.npz')]=sha(out/'CANDIDATE_LEGS.npz')
    for p,h in identities.items():assert sha(p)==h,('input changed',p)
    sources={str(p):sha(p) for p in Path(__file__).parent.glob('*.py')}
    result={'status':'TARGET_IDENTITY_AND_SUPPORT_COMPLETE_NOT_ECONOMIC_VALIDATION','inputs':identities,'sources':sources,'outputs':nsrc,
        'baseline_fund_score_LR_seat_and_all_combo_arrays_exact':True,'seat_future_mutations':causal,
        'candidate_missing_member_scores_on_ready':int(sum(np.isnan(cand[i,m]).sum() for i,m in enumerate(members) if L['ready'][i])),
        'baseline_missing_member_scores_on_ready':int(sum(np.isnan(fund[i,m]).sum() for i,m in enumerate(members) if L['ready'][i])),
        'comparisons':comparison,'seconds':time.time()-t0,
        'limits':['No cash/fee/funding/return/Sharpe measurement; not deployable.','Static reshaped intended weight, not executed holding or turnover.',
        'Two fixed F10 models trained under baseline seats; no full-pipeline retraining.','NC transfer of old selected candidate, not independent holdout or exact old XIB reproduction.',
        'Cost groups are NC qvm quartiles; existing fills support does not certify changed size/name/impact.']}
    dump(out/'RESULT.json',result);print(result['status'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out');args=p.parse_args()
    try:main(args.out)
    except Exception as e:
        if Path(args.out).is_dir():dump(Path(args.out)/'FAILURE.json',{'exception':repr(e)})
        raise
