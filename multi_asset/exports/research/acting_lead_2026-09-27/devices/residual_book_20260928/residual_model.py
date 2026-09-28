"""Small deterministic model contract; no market/network or production writes."""
import hashlib
import json
from pathlib import Path
import numpy as np

SCHEMA='residual_ridge_book/1'


def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(4<<20),b''):h.update(b)
    return h.hexdigest()


def aligned_labels(anchors,symbols,label_anchors,label_symbols,labels):
    a,b=np.asarray(anchors),np.asarray(label_anchors)
    for v in (a,b):
        if v.ndim!=1 or not len(v) or not np.isfinite(v).all() or np.any(v!=np.floor(v)) or np.any(v%14400) or np.any(np.diff(v)<=0):
            raise ValueError('noninteger/unordered 4h axis')
    if not np.array_equal(symbols,label_symbols) or len(set(symbols))!=len(symbols):raise ValueError('symbol axis')
    if np.asarray(labels).shape!=(len(b),len(symbols)):raise ValueError('label shape')
    out=np.full((len(a),len(symbols)),np.nan,dtype=np.float64)
    ii=np.searchsorted(b,a);ok=(ii<len(b))&(b[np.minimum(ii,len(b)-1)]==a)
    out[ok]=labels[ii[ok]]
    return out


def residual_targets(y,k,f,minimum=50):
    y,k,f=(np.asarray(v,dtype=np.float64) for v in (y,k,f))
    if y.ndim!=1 or y.shape!=k.shape or y.shape!=f.shape:raise ValueError('target shape')
    ok=np.isfinite(y)&np.isfinite(k)&np.isfinite(f)
    if ok.sum()<minimum:raise ValueError('insufficient target population')
    b=np.column_stack([np.ones(ok.sum()),k[ok],f[ok]])
    coef=np.linalg.lstsq(b,y[ok],rcond=None)[0]
    out=np.full(len(y),np.nan);out[ok]=y[ok]-b@coef
    return out,ok,coef


def fit_predict(x,y,tr,te):
    from sklearn.linear_model import Ridge
    from scipy.linalg import LinAlgWarning
    import warnings
    x,y=np.asarray(x),np.asarray(y);tr,te=np.asarray(tr),np.asarray(te)
    if x.ndim!=2 or y.shape!=(len(x),) or not len(tr) or not len(te):raise ValueError('fit shape')
    if np.intersect1d(tr,te).size or len(np.unique(tr))!=len(tr) or len(np.unique(te))!=len(te):raise ValueError('overlap/duplicate')
    if not np.isfinite(x[tr]).all() or not np.isfinite(x[te]).all() or not np.isfinite(y[tr]).all():raise ValueError('unknown fit inputs')
    mu=x[tr].mean(0,dtype=np.float64);sd=x[tr].std(0,dtype=np.float64)+1e-9
    with warnings.catch_warnings():
        warnings.simplefilter("error", LinAlgWarning)
        model=Ridge(alpha=1.0).fit(((x[tr]-mu)/sd),y[tr])
    pred=model.predict(((x[te]-mu)/sd))
    if not np.isfinite(pred).all():raise ValueError('nonfinite prediction')
    return pred,dict(mu=mu,sd=sd,coef=np.asarray(model.coef_),intercept=np.asarray(model.intercept_))


def verify_training(out,rec,seed,hashfn=sha):
    out=Path(out)
    if rec.get('schema')!=SCHEMA or rec.get('model_kind')!='deterministic_ridge' or rec.get('seed')!=seed:
        raise ValueError('linear identity')
    if rec.get('expected_folds')!=['2023','2024','2025','2026'] or rec.get('folds')!=rec['expected_folds']:
        raise ValueError('linear fold set')
    if rec.get('target') not in ('raw','resid'):raise ValueError('target identity')
    expected={str((out/t/n).resolve()) for t in rec['folds'] for n in ('FOLD_RECEIPT.json','model.npz','scores.npz')}
    if expected!={str(Path(p).resolve()) for p in rec['fold_artifacts']}:raise ValueError('fold artifacts')
    for p,h in rec['fold_artifacts'].items():
        if hashfn(p)!=h:raise ValueError('fold changed '+p)
    for tag in rec['folds']:
        r=json.loads((out/tag/'FOLD_RECEIPT.json').read_text())
        if any(r[k]!=rec[k] for k in ('inputs','sources','target','schema')) or r['fold']!=tag:raise ValueError('fold provenance')
        if r['train_label_end']>r['test_start']-60*14400:raise ValueError('fold embargo')
    if hashfn(out/'F10_OOF.npz')!=rec['pred_sha256']:raise ValueError('OOF drift')
    for p,h in {**rec['inputs'],**rec['sources']}.items():
        if hashfn(p)!=h:raise ValueError('linear dependency changed '+p)
