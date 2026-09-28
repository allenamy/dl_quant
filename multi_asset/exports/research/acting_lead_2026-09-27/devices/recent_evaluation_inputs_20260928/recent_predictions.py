"""Extend fixed September NC predictions after completed same-code feature controls; no retraining."""
import os
os.environ.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',NPY_DISABLE_CPU_FEATURES='X86_V4 AVX512_ICL AVX512_SPR')
from pathlib import Path
import json,sys,time,subprocess
import numpy as np
from funding_overlap import sha

NS=Path('/dev/shm/news2_2026-09-23')
PINS={
 str(NS/'devices/news2_train_f10.py'):'66bc7c3e69af7aab7062b562674fb3bbe272fd9a28fc3ea9639143f4549420db',
 str(NS/'devices/f10_observability.py'):'c6399d7ae49482503209ce21916e38f1ad36fb7702c980eb5d0b67c5b9349dd1',
 str(NS/'work/king/king_2026.txt'):'700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d',
 str(NS/'work/king/KING_OOF.npz'):'a10b872506ca60afcd0f69b0e43d17a548cdd7c6956075000aac954b21e3df9a',
 str(NS/'work/f10_s42/202609/FOLD_RECEIPT.json'):'46fbb0d800a5dd571a435725e1b55faf4d9678a033af4ca40035e3ef7add2be1',
 str(NS/'work/f10_s2027/202609/FOLD_RECEIPT.json'):'37bfa28b45d4c304ea7175e2328056f1ce07a63d8ab968fa79c7b2bd55d88643',
 '/dev/shm/recent_king_features_20260928/KING_FEATURES_AND_MEMBERS.npz':'0a8f4bb1f9a01d5c6ecd7047e4f63a72fe627809186dbb176b9d202ff36b6855'}

def main(root):
    start=time.monotonic();root=Path(root);root.mkdir(exist_ok=False);fr=Path('/dev/shm/recent_f10_features_20260928');term=json.loads((fr/'TERMINAL.json').read_text());r=json.loads((fr/'RESULT.json').read_text())
    if term['rc']!=0 or term['result_sha256']!=sha(fr/'RESULT.json') or r['source_sha256']!='b11fd03447fb86ac91a942ac180fd37a8da874484ef7a010b2dac2fc63cb68f4' or r['anchors']!=55 or not all(r['boundary_controls'].values()):raise ValueError('feature task not certified')
    pins={**PINS,str(fr/'RESULT.json'):sha(fr/'RESULT.json'),str(Path(__file__).resolve()):sha(__file__)}
    for p,h in pins.items():
        if sha(p)!=h:raise ValueError('fixed input changed '+p)
    with np.load('/dev/shm/recent_king_features_20260928/KING_FEATURES_AND_MEMBERS.npz') as z:k={key:z[key] for key in z.files}
    if len(k['anchors'])!=55 or k['anchors'][0]!=1789776000 or k['anchors'][-1]!=1790553600 or np.any(np.diff(k['anchors'])!=14400):raise ValueError('fixed prediction axis')
    xx=[]
    for i,A in enumerate(k['anchors']):
        p=fr/f'ROW_{A}.npz'
        if sha(p)!=r['outputs'][p.name]['sha256']:raise ValueError('feature row identity')
        pins[str(p)]=sha(p)
        with np.load(p) as z:
            m=k['m'][k['off'][i]:k['off'][i+1]]
            if int(z['anchor'])!=A or not np.array_equal(z['members'],m):raise ValueError('member/anchor mismatch')
            x=np.concatenate([z['X82'],z['X89']],axis=1).astype(np.float32)
            if x.shape!=(len(m),171) or not np.isfinite(x).all():raise ValueError('unmeasured feature')
            xx.append(x)
    import lightgbm as lgb
    king=lgb.Booster(model_file=str(NS/'work/king/king_2026.txt'));KP=np.full((len(xx),len(k['symbols'])),np.nan,np.float32)
    for i in range(len(xx)):
        sl=slice(k['off'][i],k['off'][i+1]);m=k['m'][sl];KP[i,m]=king.predict(k['king_X78'][sl],num_threads=2).astype(np.float32)
    with np.load(NS/'work/king/KING_OOF.npz') as z:
        if not np.array_equal(z['symbols'],k['symbols']):raise ValueError('old King symbol axis')
        idx=np.flatnonzero(z['E_ts']==k['anchors'][0]);assert len(idx)==1
        control=z['P'][int(idx[0])]
    if not np.array_equal(KP[0],control,equal_nan=True):raise ValueError('King old-boundary scores differ')
    sys.path.insert(0,str(NS/'devices'));import news2_train_f10 as N
    import torch
    torch.set_num_threads(2);device='cpu';peer_query='unavailable'
    try:
        q=subprocess.run(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],capture_output=True,text=True,timeout=5)
        peer_query=q.stdout.strip() if q.returncode==0 else 'query_failed'
        if q.returncode==0 and not peer_query and torch.cuda.is_available():device='cuda'
    except (OSError,subprocess.TimeoutExpired):pass
    outs={};controls={'king_exact':True}
    for seed in (42,2027):
        base=NS/f'work/f10_s{seed}/202609';br=json.loads((base/'FOLD_RECEIPT.json').read_text())
        for name,key in [('model.pt','model_sha256'),('scores.npz','score_sha256')]:
            p=base/name;pins[str(p)]=br[key]
            if sha(p)!=br[key]:raise ValueError('model/score identity')
        ck=torch.load(base/'model.pt',map_location=device,weights_only=False);model=N.Net().to(device);model.load_state_dict(ck['state_dict']);model.eval();mu,sd=ck['mu'].to(device),ck['sd'].to(device)
        if not torch.isfinite(mu).all() or not torch.isfinite(sd).all() or not (sd>0).all():raise ValueError('normalization invalid')
        P=np.full_like(KP,np.nan)
        with torch.no_grad():
            for i,x in enumerate(xx):
                if time.monotonic()-start>170:raise TimeoutError('180s inference budget')
                m=k['m'][k['off'][i]:k['off'][i+1]];xt=torch.from_numpy(x).to(device);P[i,m]=model.f(torch.clamp((xt-mu)/sd,-5,5)).squeeze(-1).cpu().numpy()
        with np.load(base/'scores.npz') as z:
            idx=np.flatnonzero(z['E_ts']==k['anchors'][0]);assert len(idx)==1 and np.array_equal(z['symbols'],k['symbols']);ref=z['P'][int(idx[0])]
        if not np.array_equal(np.isfinite(ref),np.isfinite(P[0])):raise ValueError('F10 finite population')
        delta=float(np.max(np.abs(ref[np.isfinite(ref)]-P[0,np.isfinite(ref)])))
        if delta>1e-6:raise ValueError('F10 original inference control '+str(delta))
        controls[f'f10_{seed}_max_abs_diff']=delta
        p=root/f'NC_F10_s{seed}_PREDICTIONS.npz';np.savez_compressed(p,E_ts=k['anchors'],symbols=k['symbols'],P=P);outs[p.name]=sha(p)
        del model,ck
        if device=='cuda':torch.cuda.empty_cache()
    p=root/'KING_PREDICTIONS.npz';np.savez_compressed(p,E_ts=k['anchors'],symbols=k['symbols'],P=KP);outs[p.name]=sha(p)
    for p,h in pins.items():
        if sha(p)!=h:raise ValueError('input drift '+p)
    result={'status':'FIXED_NC_PREDICTIONS_COMPLETE_NOT_COMBO_OR_CASH','utc':time.strftime('%FT%TZ',time.gmtime()),'inputs':pins,'outputs':outs,'controls':controls,'seconds':time.monotonic()-start,'python':sys.executable,'numpy':np.__version__,'torch':torch.__version__,'lightgbm':lgb.__version__,'inference_device':device,'pre_cuda_peer_query':peer_query,'new_training':False,'limits':['Original September NC fold models, no refit or candidate selection','55 feature anchors; last future-return window not available','Continuous sleeve/book and executable cash path still required']}
    (root/'RESULT.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');(root/'TERMINAL.json').write_text(json.dumps({'rc':0,'result_sha256':sha(root/'RESULT.json')},indent=2)+'\n');print({k:result[k] for k in ('status','controls','seconds','inference_device')})

if __name__=='__main__':
    try:main(sys.argv[1])
    except BaseException as e:
        root=Path(sys.argv[1]);root.mkdir(exist_ok=True);(root/'TERMINAL.json').write_text(json.dumps({'rc':1,'error':repr(e)},indent=2)+'\n');raise
