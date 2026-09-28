"""96-step LQ population continuation; original U models/control already completed. No checkpoint selection."""
import os
os.environ.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',NPY_DISABLE_CPU_FEATURES='X86_V4 AVX512_ICL AVX512_SPR')
import sys,json,pathlib,hashlib,time,collections,copy
import numpy as np
import torch
from torch import nn
from adapt_contract import probabilities,choose,causal_windows,align_indices
import liquid_utility as Q
H=pathlib.Path(__file__).resolve().parent
C=json.loads((H/'CONTRACT.json').read_text());ROOT=pathlib.Path(C['root']);NS=pathlib.Path('/dev/shm/news2_2026-09-23')
PINS={str(NS/'work/NEWS_FEATURES.npz'):'3c886a2bc0ff65c10b7e0a621c9468210bbd77ef58c90e625f0a29354d63c4d8',str(NS/'work/legs.npz'):'9ee5886f37d1727c306d0fb692d2cad1e6400ae13f19d5cd4e280dc59f208f65','/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz':'ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62'}
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()
def write(p,x):
 p.parent.mkdir(parents=True,exist_ok=True)
 with open(p,'x') as f:json.dump(x,f,indent=2,allow_nan=False);f.flush();os.fsync(f.fileno())
def model_sha(model):
 h=hashlib.sha256()
 for k,v in model.state_dict().items():h.update(k.encode());h.update(v.detach().cpu().contiguous().numpy().tobytes())
 return h.hexdigest()
def main():
 if not __debug__:raise RuntimeError('optimized assertions forbidden')
 for p,h in PINS.items():assert sha(p)==h,('input drift',p)
 source=NS/'devices/news2_train_f10.py';obs=NS/'devices/f10_observability.py'
 assert sha(source)=='66bc7c3e69af7aab7062b562674fb3bbe272fd9a28fc3ea9639143f4549420db'
 assert sha(obs)=='c6399d7ae49482503209ce21916e38f1ad36fb7702c980eb5d0b67c5b9349dd1'
 sys.path.insert(0,str(NS/'devices'));import news2_train_f10 as N
 from f10_observability import span_admissible
 torch.set_num_threads(2);assert torch.cuda.is_available()
 sources={str(p):sha(p) for p in [H/'train_adapt.py',H/'adapt_contract.py',source,obs,H/'liquid_utility.py']}
 for seed in (42,2027):
  recp=NS/f'work/f10_s{seed}/TRAIN_RECEIPT.json';rec=json.loads(recp.read_text())
  assert rec['seed']==seed and set(rec['folds'])==set(rec['expected_folds'])
  for p,h in {**rec['sources'],**rec['inputs'],**rec['fold_artifacts']}.items():assert sha(p)==h,('base provenance',p)
  PINS[str(recp)]=sha(recp)
 inputs=dict(PINS)
 F=np.load(NS/'work/NEWS_FEATURES.npz');T=np.load(list(PINS)[2],allow_pickle=True);L=np.load(NS/'work/legs.npz')
 a=F['anchors'].astype(np.int64);sy=F['symbols'];off=F['off'];m=F['m'].astype(int);n=len(a);w=len(sy)
 assert np.array_equal(T['symbols'],sy) and np.array_equal(L['symbols'],sy) and np.array_equal(L['E_ts'],a)
 ti=np.asarray(align_indices(T['E_ts'].tolist(),a.tolist()));ok=ti>=0
 y=np.full((n,w),np.nan,np.float32);y[ok]=T['y4s'][ti[ok]];ready=L['ready'];counts=np.diff(off)
 write(ROOT/'models/LABEL_ALIGNMENT.json',{'missing_axis_anchors':a[~ok].tolist(),'missing_kept_as':'NaN, original NC contract; no zero fill'})
 x=np.concatenate([F['X82'].astype(np.float32),F['X89']],1).astype(np.float32);assert np.isfinite(x).all()
 XT=torch.from_numpy(x).to('cuda');del x
 YT=torch.from_numpy(np.where(np.isfinite(y),y,0.)).cuda();YVALID=torch.from_numpy(np.isfinite(y)).cuda()
 Z24=torch.from_numpy(np.nan_to_num(L['Z24'],nan=0.)).cuda();ZFD=torch.from_numpy(np.nan_to_num(L['ZFD'],nan=0.)).cuda();WL=torch.from_numpy(L['WL']).cuda()
 members=[m[off[i]:off[i+1]] for i in range(n)];cols=[torch.as_tensor(v,device='cuda') for v in members]
 QV=L['QV'];liq_host=[Q.mask_from_qv(QV[i,members[i]]) if ready[i] and counts[i]>=50 else np.zeros(len(members[i]),bool) for i in range(n)]
 liq=[torch.as_tensor(v,device='cuda') for v in liq_host];n_liq=[int(v.sum()) for v in liq_host]
 env={'python':sys.executable,'numpy':np.__version__,'torch':torch.__version__,'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name(0),'env':{k:os.environ.get(k) for k in ('NPY_DISABLE_CPU_FEATURES','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS')}}
 write(ROOT/'models/ENVIRONMENT.json',env)
 def predict(model,mu,sd,rows):
  model.eval();p=np.full((len(rows),w),np.nan,np.float32)
  with torch.no_grad():
   for j,i in enumerate(rows):
    if counts[i]<50:continue
    xx=torch.clamp((XT[off[i]:off[i+1]]-mu)/sd,-5,5)
    p[j,members[i]]=model.f(xx).squeeze(-1).cpu().numpy()
  return p
 def run_span(model,span,mu,sd):
  held=torch.zeros(w,device='cuda');alpha=model.alpha();nets=[];bad=[]
  for k,i in enumerate(span):
   xx=torch.clamp((XT[off[i]:off[i+1]]-mu)/sd,-5,5);score=model.f(xx).squeeze(-1)
   u=Q.utility(score,Z24[i,cols[i]],ZFD[i,cols[i]],WL[i],.3,liq[i],n_liq[i],False)
   target=torch.zeros(w,device='cuda').scatter(0,cols[i],u);new=(1-alpha)*held+alpha*target
   bad.append(((new!=0)&~YVALID[i]).any())
   net=1e4*(new*YT[i]).sum()-3.52*torch.sqrt((new-held)**2+1e-12).sum()
   if k>=24:nets.append(net)
   held=new
  if bool(torch.stack(bad).any().item()):raise ValueError('unknown held labels')
  return torch.stack(nets)
 # Same fold order for both model seeds; no inference from unfinished folds.
 for seed in (42,2027):
  outs={k:ROOT/f'models/{k}_s{seed}' for k in ('LQ',)};preds={k:np.full((n,w),np.nan,np.float32) for k in outs};arts={k:{} for k in outs};tags=[]
  for tag,start,end in N.fold_specs(a):
   te=np.flatnonzero((a>=start)&(a<end));cutoff=int(a[te[0]])-60*14400
   rawwindows=causal_windows(a.tolist(),ready.tolist(),counts.tolist(),cutoff);windows=[];rejected=collections.Counter()
   for span in rawwindows:
    ok,why=span_admissible(members,y,span,ready)
    if ok:windows.append(span)
    else:rejected[why['reason']]+=1
   assert len(windows)>=5
   base=NS/f'work/f10_s{seed}/{tag}';br=json.loads((base/'FOLD_RECEIPT.json').read_text());assert br['model_sha256']==sha(base/'model.pt') and br['score_sha256']==sha(base/'scores.npz')
   ck=torch.load(base/'model.pt',map_location='cuda',weights_only=False);mu=ck['mu'];sd=ck['sd'];assert torch.isfinite(mu).all() and torch.isfinite(sd).all() and (sd>0).all()
   model=N.Net().cuda();model.load_state_dict(ck['state_dict']);initial=model_sha(model)
   z=np.load(base/'scores.npz');assert np.array_equal(z['rows'],te) and np.array_equal(z['symbols'],sy)
   picks=np.unique(np.linspace(0,len(te)-1,min(6,len(te))).astype(int));p0=predict(model,mu,sd,te[picks]);ref=z['P'][picks]
   assert np.array_equal(np.isfinite(p0),np.isfinite(ref));delta=float(np.max(np.abs(p0[np.isfinite(p0)]-ref[np.isfinite(ref)])));assert delta<=1e-6,('warmstart parity',tag,delta)
   assert model_sha(model)==initial
   ends=[int(a[s[-1]])+14400 for s in windows];us=np.random.default_rng(seed+int(tag)).random(96).tolist()
   for kind,hl in [('LQ',None)]:
    out=outs[kind]/tag;out.mkdir(parents=True,exist_ok=False);torch.manual_seed(seed);np.random.seed(seed)
    model=N.Net().cuda();model.load_state_dict(ck['state_dict']);assert model_sha(model)==initial
    opt=torch.optim.AdamW(model.parameters(),lr=3e-5,weight_decay=1e-4);probs=probabilities(ends,cutoff,hl);chosen=choose(probs,us)
    ur=pathlib.Path(f'/dev/shm/f10_recent_adapt_20260928_attempt2/models/U_s{seed}/{tag}/FOLD_RECEIPT.json');uct=json.loads(ur.read_text())
    assert chosen==uct['admission']['sampled_windows'] and ends==uct['admission']['label_end_times'] and cutoff==uct['admission']['cutoff'],'matched U sampling differs'
    assert initial==uct['initial_state_sha256'] and br['model_sha256']==uct['initial_model_file_sha256'],'U initialization differs'
    start_t=time.monotonic();curve=[];model.train()
    for step,wi in enumerate(chosen):
     if time.time()>C['training_deadline_epoch']:raise TimeoutError('25 minute training budget')
     nets=run_span(model,windows[wi],mu,sd);es=torch.topk(-nets,max(1,int(np.ceil(.05*len(nets))))).values.mean();loss=-nets.mean()+.25*es
     assert torch.isfinite(loss),'nonfinite adaptation loss'
     opt.zero_grad();loss.backward();nn.utils.clip_grad_norm_(model.parameters(),1.);opt.step();curve.append(float(loss.detach()))
    final=model_sha(model);assert final!=initial
    pred=predict(model,mu,sd,te);preds[kind][te]=pred
    torch.save({'state_dict':model.state_dict(),'mu':mu,'sd':sd,'input_dim':171,'fixed_epoch_index':None,'continuation_updates':96},out/'model.pt')
    np.savez_compressed(out/'scores.npz',P=pred,rows=te,E_ts=a[te],symbols=sy)
    admission={'cutoff':cutoff,'test_start':int(a[te[0]]),'max_train_label_end':max(ends),'raw_windows':len(rawwindows),'accepted_windows':len(windows),'rejected':dict(rejected),'half_life_days':hl,'effective_windows':float(1/sum(v*v for v in probs)),'sampled_windows':chosen,'probabilities':probs,'label_end_times':ends}
    rr={'status':'F10_CONTINUATION_SCORES_NOT_BOOK','seed':seed,'fold':tag,'arm':kind,'inputs':inputs,'sources':sources,'initial_model_path':str(base/'model.pt'),'initial_model_file_sha256':br['model_sha256'],'initial_state_sha256':initial,'final_state_sha256':final,'score_sha256':sha(out/'scores.npz'),'model_sha256':sha(out/'model.pt'),'admission':admission,'initial_inference_max_abs_diff':delta,'fixed_updates':96,'matched_U_receipt_path':str(ur),'matched_U_receipt_sha256':sha(ur),'loss_history':curve,'elapsed_seconds':time.monotonic()-start_t,'environment':env}
    write(out/'FOLD_RECEIPT.json',rr)
    for p in (out/'FOLD_RECEIPT.json',out/'scores.npz',out/'model.pt'):arts[kind][str(p)]=sha(p)
    print(time.strftime('%FT%TZ',time.gmtime()),'FOLD_DONE',seed,tag,kind,round(rr['elapsed_seconds'],2),flush=True)
    del model,opt;torch.cuda.empty_cache()
   tags.append(tag)
  for kind,out in outs.items():
   np.savez_compressed(out/'F10_OOF.npz',P=preds[kind],E_ts=a,symbols=sy)
   write(out/'TRAIN_RECEIPT.json',{'status':'ALL_DECLARED_FOLDS_SCORED_NOT_COMBO_CERTIFIED','seed':seed,'folds':tags,'expected_folds':[t[0] for t in N.fold_specs(a)],'fold_artifacts':arts[kind],'inputs':inputs,'sources':sources,'pred_sha256':sha(out/'F10_OOF.npz'),'model_kind':'NC_F10_warm_start_liquidity_population_fixed_96_updates','model_target':kind,'experimental_only':True})
 for p,h in {**inputs,**sources}.items():assert sha(p)==h,('source/input drift',p)
 write(ROOT/'models/TRAINING_COMPLETE.json',{'status':'TWO_MODEL_STREAMS_COMPLETE_NOT_BOOK','utc':time.strftime('%FT%TZ',time.gmtime()),'seeds':[42,2027],'arms':['LQ'],'folds_per_stream':23,'optimizer_updates_per_fold':96,'peak_gpu_bytes':torch.cuda.max_memory_allocated()})
if __name__=='__main__':main()
