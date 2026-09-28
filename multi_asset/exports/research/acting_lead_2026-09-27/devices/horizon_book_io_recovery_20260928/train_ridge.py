"""FAST vs SLOW, same sparse training population, full dense OOF inference."""
import os
os.environ['OMP_NUM_THREADS']='2';os.environ['OPENBLAS_NUM_THREADS']='2'
import calendar,gc,json,sys,time,hashlib
from pathlib import Path
import numpy as np
import sklearn
from residual_model import aligned_labels,fit_predict,verify_training,sha,SCHEMA
from horizon import targets,training_rows,HORIZON,EMBARGO,DECAY

HERE=Path(__file__).resolve().parent
C=json.loads((HERE/'CONTRACT.json').read_text());ROOT=Path(C['root'])
W=Path('/dev/shm/news2_2026-09-23')
FEAT=W/'work/NEWS_FEATURES.npz';LEGS=W/'work/legs.npz'
LAB=Path('/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz')
PINS={str(FEAT):'3c886a2bc0ff65c10b7e0a621c9468210bbd77ef58c90e625f0a29354d63c4d8',str(LEGS):'9ee5886f37d1727c306d0fb692d2cad1e6400ae13f19d5cd4e280dc59f208f65',str(LAB):'ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62'}

def write(p,d):
    with open(p,'x') as f:json.dump(d,f,indent=2,allow_nan=False);f.flush();os.fsync(f.fileno())

def save(p,**a):
    with open(p,'xb') as f:np.savez_compressed(f,**a);f.flush();os.fsync(f.fileno())

def main():
    sources={str(HERE/n):h for n,h in C['copied_sources'].items()}
    for p,h in {**PINS,**sources}.items():
        if sha(p)!=h:raise ValueError('input/source changed '+p)
    with np.load(FEAT) as F,np.load(LEGS) as L,np.load(LAB,allow_pickle=True) as T:
        a=F['anchors'];symbols=F['symbols'];off=F['off'];ps=F['m'].astype(np.int64)
        if not np.array_equal(L['E_ts'],a) or not np.array_equal(L['symbols'],symbols):raise ValueError('leg axes')
        if off[0]!=0 or off[-1]!=len(ps) or not np.array_equal(np.diff(off),F['count']):raise ValueError('member axes')
        y=aligned_labels(a,symbols,T['E_ts'],T['symbols'],T['y4s']);slow=targets(y)
        pa=np.repeat(np.arange(len(a)),np.diff(off));yl=y[pa,ps];sl=slow[pa,ps]
        x=np.concatenate([F['X82'],F['X89']],1).astype(np.float32)
    if not np.isfinite(x).all():raise ValueError('features unknown')
    common=np.isfinite(yl)&np.isfinite(sl)
    for i in range(len(a)):
        if len(np.unique(ps[off[i]:off[i+1]]))!=off[i+1]-off[i]:raise ValueError('duplicate member')
    roots={kind:ROOT/'models'/kind for kind in ('fast','slow')};preds={k:np.full((len(a),len(symbols)),np.nan,np.float32) for k in roots}
    for p in roots.values():p.mkdir(parents=True,exist_ok=False)
    folds=[];admission=[]
    for year in (2023,2024,2025,2026):
        tag=str(year);folds.append(tag);s0,s1=[calendar.timegm((v,1,1,0,0,0)) for v in (year,year+1)]
        tr=training_rows(a,pa,common,s0);te_a=np.flatnonzero((a>=s0)&(a<s1));te=np.flatnonzero(np.isin(pa,te_a))
        if not len(te_a) or not len(tr):raise ValueError('empty fold')
        atr=np.unique(pa[tr]);trainend=int(a[atr[-1]]+HORIZON*14400);teststart=int(a[te_a[0]])
        if trainend>teststart-EMBARGO*14400 or np.any(np.diff(a[atr])<HORIZON*14400):raise ValueError('embargo/overlap')
        potential=training_rows(a,pa,np.ones(len(pa),bool),s0)
        admission.append({'fold':tag,'eligible_before_label':len(potential),'common_pairs':len(tr),'unknown48h_pairs':len(potential)-len(tr),'train_anchor_count':len(atr),'first_anchor':int(a[atr[0]]),'last_label_end':trainend,'rows_sha256':hashlib.sha256(tr.tobytes()).hexdigest()})
        # Mutate ALL test/future labels before rebuilding horizon labels; no training dependence.
        ym=y.copy();ym[a>=s0]=.9;sm=targets(ym)[pa,ps]
        rmut=training_rows(a,pa,np.isfinite(ym[pa,ps])&np.isfinite(sm),s0)
        if not np.array_equal(tr,rmut) or not np.array_equal(sl[tr],sm[tr]) or not np.array_equal(yl[tr],ym[pa,ps][tr]):raise ValueError('future-label dependence')
        del ym,sm,rmut
        for kind,target in [('fast',yl),('slow',sl)]:
            started=time.monotonic();prediction,model=fit_predict(x,target,tr,te)
            d=roots[kind]/tag;d.mkdir();save(d/'model.npz',**model)
            p=np.full((len(te_a),len(symbols)),np.nan,np.float32);where=np.searchsorted(te_a,pa[te]);p[where,ps[te]]=prediction;preds[kind][te_a]=p
            save(d/'scores.npz',P=p,rows=te_a,E_ts=a[te_a],symbols=symbols)
            rec=dict(schema=SCHEMA,fold=tag,target=kind,inputs=PINS,sources=sources,train_label_end=trainend,test_start=teststart,train_pairs=len(tr),test_pairs=len(te),training_rows_sha256=hashlib.sha256(tr.tobytes()).hexdigest(),label='next4h' if kind=='fast' else 'fixed_initial_quantity_12x4h_decay0.9_normalized_price_only',training_stride_anchors=HORIZON,embargo_after_label_anchors=EMBARGO,algorithm='Ridge(alpha=1.0), train-only normalization, float64 solve',python=sys.executable,numpy=np.__version__,sklearn=sklearn.__version__,model_sha256=sha(d/'model.npz'),score_sha256=sha(d/'scores.npz'),seconds=time.monotonic()-started)
            write(d/'FOLD_RECEIPT.json',rec);print('FOLD',kind,tag,'train',len(tr),'seconds',rec['seconds'],flush=True)
            del prediction,model,p;gc.collect()
    for kind,d in roots.items():
        save(d/'F10_OOF.npz',P=preds[kind],E_ts=a,symbols=symbols)
        rec=dict(schema=SCHEMA,status='HORIZON_LINEAR_FOLDS_COMPLETE_NOT_COMBO_CERTIFIED',model_kind='deterministic_ridge',seed=42,seed_note='interface only, deterministic model',target=kind,folds=folds,expected_folds=folds,inputs=PINS,sources=sources,fold_artifacts={str(d/t/n):sha(d/t/n) for t in folds for n in ('FOLD_RECEIPT.json','model.npz','scores.npz')},pred_sha256=sha(d/'F10_OOF.npz'))
        write(d/'TRAIN_RECEIPT.json',rec);verify_training(d,rec,42)
    write(ROOT/'MODEL_DONE.json',dict(status='PAIRED_HORIZON_MODELS_COMPLETE',admission=admission,future_label_training_values_and_rows_invariant=True,retained_kernel_mass=1-DECAY**HORIZON,input_shas=PINS,utc=time.strftime('%FT%TZ',time.gmtime())))

if __name__=='__main__':main()
