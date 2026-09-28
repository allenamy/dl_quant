"""Two paired, deterministic annual walk-forward models; private artifacts only."""
import os
os.environ['OMP_NUM_THREADS']='2';os.environ['OPENBLAS_NUM_THREADS']='2'
import calendar,gc,json,sys,time
from pathlib import Path
import numpy as np
import sklearn
from residual_model import aligned_labels,residual_targets,fit_predict,verify_training,sha,SCHEMA

HERE=Path(__file__).resolve().parent
C=json.loads((HERE/'CONTRACT.json').read_text());ROOT=Path(C['root'])
W=Path('/dev/shm/news2_2026-09-23')
FEAT=W/'work/NEWS_FEATURES.npz';LEGS=W/'work/legs.npz'
LAB=Path('/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz')
PINS={str(FEAT):'3c886a2bc0ff65c10b7e0a621c9468210bbd77ef58c90e625f0a29354d63c4d8',
      str(LEGS):'9ee5886f37d1727c306d0fb692d2cad1e6400ae13f19d5cd4e280dc59f208f65',
      str(LAB):'ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62',
      str(W/'devices/king_folds.py'):'4886c278c12b0f5126bb1e8ad6b4789db95e604180a77d0cd02f1e7c612df640'}


def write(p,d):
    with open(p,'x') as f:json.dump(d,f,indent=2,allow_nan=False);f.flush();os.fsync(f.fileno())


def save(p,**a):
    with open(p,'xb') as f:np.savez_compressed(f,**a);f.flush();os.fsync(f.fileno())


def main():
    for p,h in PINS.items():
        if sha(p)!=h:raise ValueError('input changed '+p)
    sources={str(HERE/n):h for n,h in C['copied_sources'].items()}
    for p,h in sources.items():
        if sha(p)!=h:raise ValueError('source changed '+p)
    sys.path.insert(0,str(W/'devices'));from king_folds import fold_rows
    with np.load(FEAT) as F,np.load(LEGS) as L,np.load(LAB,allow_pickle=True) as T:
        a=F['anchors'].astype(np.int64);symbols=F['symbols'];off=F['off'];ps=F['m'].astype(np.int64)
        if not np.array_equal(L['E_ts'],a) or not np.array_equal(L['symbols'],symbols):raise ValueError('leg axes')
        if np.any(np.diff(a)!=14400) or off[0]!=0 or off[-1]!=len(ps) or not np.array_equal(np.diff(off),F['count']):raise ValueError('member axes')
        y=aligned_labels(a,symbols,T['E_ts'],T['symbols'],T['y4s'])
        pa=np.repeat(np.arange(len(a)),np.diff(off));yl=y[pa,ps];k=L['KZ'][pa,ps];fund=L['ZFD'][pa,ps]
        x=np.concatenate([F['X82'],F['X89']],1).astype(np.float32)
    if not np.isfinite(x).all():raise ValueError('features unknown')
    residual=np.full(len(pa),np.nan);coeff=np.full((len(a),3),np.nan);maxcorr=0.
    for i in range(len(a)):
        sl=slice(off[i],off[i+1])
        if len(np.unique(ps[sl]))!=off[i+1]-off[i]:raise ValueError('duplicate member')
        if (np.isfinite(yl[sl])&np.isfinite(k[sl])&np.isfinite(fund[sl])).sum()<50:continue
        residual[sl],ok,coeff[i]=residual_targets(yl[sl],k[sl],fund[sl])
        for z in (k[sl][ok],fund[sl][ok]):
            if np.std(z)>0 and np.std(residual[sl][ok])>0:maxcorr=max(maxcorr,abs(float(np.corrcoef(z,residual[sl][ok])[0,1])))
    if maxcorr>1e-10:raise ValueError('orthogonality')
    common=np.isfinite(residual)&np.isfinite(yl)
    roots={kind:ROOT/'models'/kind for kind in ('raw','resid')}
    preds={kind:np.full((len(a),len(symbols)),np.nan,np.float32) for kind in roots}
    for p in roots.values():p.mkdir(parents=True,exist_ok=False)
    folds=[];future_checks=[]
    for year in (2023,2024,2025,2026):
        tag=str(year);folds.append(tag)
        s0,s1=[calendar.timegm((v,1,1,0,0,0)) for v in (year,year+1)]
        tr_a,te_a=fold_rows(a,s0,s1,60)
        tr=np.flatnonzero(np.isin(pa,tr_a)&common);te=np.flatnonzero(np.isin(pa,te_a))
        trainend=int(a[pa[tr]].max()+14400);teststart=int(a[te_a[0]])
        if trainend>teststart-60*14400:raise ValueError('embargo')
        for kind,target in [('raw',yl),('resid',residual)]:
            started=time.monotonic();prediction,model=fit_predict(x,target,tr,te)
            # Factual same training selection/labels under an arbitrary test-label mutation.
            future=target.copy();future[te]=np.nan
            same=np.array_equal(target[tr],future[tr])
            if not same:raise ValueError('test-label dependency')
            future_checks.append(dict(fold=tag,target=kind,training_values_unaffected=same))
            d=roots[kind]/tag;d.mkdir()
            save(d/'model.npz',**model)
            p=np.full((len(te_a),len(symbols)),np.nan,np.float32)
            where=np.searchsorted(te_a,pa[te]);p[where,ps[te]]=prediction
            preds[kind][te_a]=p
            save(d/'scores.npz',P=p,rows=te_a,E_ts=a[te_a],symbols=symbols)
            rec=dict(schema=SCHEMA,fold=tag,target=kind,inputs=PINS,sources=sources,
                train_label_end=trainend,test_start=teststart,train_pairs=len(tr),test_pairs=len(te),
                training_rows_sha256=__import__('hashlib').sha256(tr.tobytes()).hexdigest(),
                algorithm='Ridge(alpha=1.0), training-only mean/std, float32 standardized features',
                python=sys.executable,numpy=np.__version__,sklearn=sklearn.__version__,
                model_sha256=sha(d/'model.npz'),score_sha256=sha(d/'scores.npz'),seconds=time.monotonic()-started)
            write(d/'FOLD_RECEIPT.json',rec)
            print('FOLD',kind,tag,'train',len(tr),'test',len(te),'seconds',rec['seconds'],flush=True)
            del prediction,model,p,future;gc.collect()
    for kind,d in roots.items():
        save(d/'F10_OOF.npz',P=preds[kind],E_ts=a,symbols=symbols)
        rec=dict(schema=SCHEMA,status='LINEAR_ALL_DECLARED_FOLDS_SCORED_NOT_COMBO_CERTIFIED',
          model_kind='deterministic_ridge',seed=42,seed_note='interface label only; deterministic model, not an F10 random seed',
          target=kind,folds=folds,expected_folds=folds,inputs=PINS,sources=sources,
          fold_artifacts={str(d/t/n):sha(d/t/n) for t in folds for n in ('FOLD_RECEIPT.json','model.npz','scores.npz')},
          pred_sha256=sha(d/'F10_OOF.npz'))
        write(d/'TRAIN_RECEIPT.json',rec);verify_training(d,rec,42)
    write(ROOT/'MODEL_DONE.json',dict(status='PAIRED_LINEAR_MODELS_COMPLETE',max_projection_corr=maxcorr,
        future_label_train_input_checks=future_checks,finite_training_population=int(common.sum()),
        input_shas=PINS,utc=time.strftime('%FT%TZ',time.gmtime())))


if __name__=='__main__':main()
