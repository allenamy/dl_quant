"""Actual 78-column King recipe; annual causal refits, no OOS selection."""
import os
os.environ['OMP_NUM_THREADS']='8';os.environ['OPENBLAS_NUM_THREADS']='2'
import pathlib,json,time,calendar
import numpy as np
from scipy.stats import rankdata,spearmanr,pearsonr
from build_combo_inputs import sha,ROOT,log
from king_folds import fold_rows

def main():
    root=ROOT/'corrected_combo_v1d';out=root/'king';out.mkdir(exist_ok=False)
    rec=json.load(open(root/'BUILD_RECEIPT.json'));assert rec['status']=='INPUT_BUILD_PASS_NOT_MODEL_OR_BOOK_CERTIFICATION'
    paths=[root/'data/dlw_targets.npz',root/'data/dlw_fea82.npz']
    for p in paths:assert sha(p)==rec['artifacts'][str(p)]
    z=np.load(paths[0],allow_pickle=True);f=np.load(paths[1]);cfg=json.load(open(ROOT/'vendor_live/shadow_bundle/config.json'))
    a=z['E_ts'];syms=z['symbols'];y=z['y4s'];pa=f['pair_a'];ps=f['pair_s'];x=f['X'][:,cfg['keep_idx']].astype(np.float32)
    assert [str(f['names'][i]) for i in cfg['keep_idx']]==cfg['keep_names'] and x.shape[1]==78
    assert np.isfinite(x).all();target=np.full(len(pa),np.nan,np.float32);st=np.searchsorted(pa,np.arange(len(a)+1))
    for i in range(len(a)):
        ix=np.arange(st[i],st[i+1]);vals=y[i,ps[ix]];good=np.isfinite(vals)
        if good.sum()>=50:target[ix[good]]=rankdata(vals[good])/max(good.sum()-1,1)-.5
    import lightgbm as lgb
    params=dict(n_estimators=400,learning_rate=.05,num_leaves=63,subsample=.8,colsample_bytree=.8,n_jobs=8,verbose=-1,random_state=0)
    pred=np.full(y.shape,np.nan,np.float32);model_id=np.full(len(a),'',dtype='U64');folds=[]
    utc=lambda yr,mo=1,day=1:calendar.timegm((yr,mo,day,0,0,0))
    specs=[('2022H2_WARMUP',utc(2022,7),utc(2023))]+[(str(yr),utc(yr),utc(yr+1)) for yr in (2023,2024,2025,2026)]
    for tag,start,end in specs:
        train,test=fold_rows(a,start,end,60);tr=np.isin(pa,train)&np.isfinite(target);te=np.isin(pa,test)
        assert tr.sum()>1000 and te.sum()>0
        t=time.monotonic();log('King start',tag,int(tr.sum()),int(te.sum()))
        model=lgb.LGBMRegressor(**params).fit(x[tr],target[tr]);modelpath=out/('king_'+tag+'.txt');model.booster_.save_model(str(modelpath))
        pred[pa[te],ps[te]]=model.predict(x[te]);mh=sha(modelpath);model_id[test]=mh
        ic=[];pp=[]
        for i in test:
            good=np.isfinite(pred[i])&np.isfinite(y[i])
            if good.sum()>=30:
                ic.append(float(spearmanr(pred[i,good],y[i,good]).correlation));pp.append(float(pearsonr(pred[i,good],y[i,good])[0]))
        per=[]
        for j in range(len(syms)):
            good=np.isfinite(pred[test,j])&np.isfinite(y[test,j])
            if good.sum()>=30 and np.std(pred[test[good],j])>0:per.append(float(pearsonr(pred[test[good],j],y[test[good],j])[0]))
        rr={'fold':tag,'score_start':int(a[test[0]]),'score_end':int(a[test[-1]]),'max_train_label_end':int(a[pa[tr]].max()+14400),'embargo_anchors':60,'train_pairs':int(tr.sum()),'scored_pairs':int(te.sum()),'model_path':str(modelpath),'model_sha256':mh,'seconds':time.monotonic()-t,'mean_cs_spearman':float(np.mean(ic)),'mean_cs_pearson':float(np.mean(pp)),'mean_per_asset_pearson':float(np.mean(per)),'n_cs_anchors':len(ic),'status':'SIGNAL_DIAGNOSTIC_ONLY'}
        assert rr['max_train_label_end']<=rr['score_start']-60*14400
        folds.append(rr);log(json.dumps(rr));(out/'PROGRESS.json').write_text(json.dumps(folds,indent=2,allow_nan=False))
    np.savez(out/'KING_OOF.npz',P=pred,E_ts=a,symbols=syms,model_sha256=model_id)
    for p in paths:assert sha(p)==rec['artifacts'][str(p)]
    receipt={'status':'OOF_KING_NOT_FULL_STRATEGY','recipe':params,'folds':folds,'source_sha':{str(pathlib.Path(__file__)):sha(__file__),str(ROOT/'devices/king_folds.py'):sha(ROOT/'devices/king_folds.py')},'inputs':{str(p):sha(p) for p in paths},'predictions_sha256':sha(out/'KING_OOF.npz'),'prohibitions':['No swap based on signal IC','No fixed-model backcast counted as OOS','No future label used for score population','No first-half-2022 prediction fabricated']}
    (out/'TRAIN_RECEIPT.json').write_text(json.dumps(receipt,indent=2,allow_nan=False));log('KING_DONE')
if __name__=='__main__':main()
