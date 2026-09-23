"""F10 V2MAIN/FIX7 with observable-held-price windows, not a proxy MLP.

No deployment; predictions require the complete combo/cash evaluation. The
171-column architecture, soft rank, EMA, ES loss and fixed epoch match the
frozen reference. Missing-price handling is an explicit corrected candidate.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='2';os.environ['OMP_NUM_THREADS']='2'
import pathlib,json,time,calendar,argparse,collections
import numpy as np
import torch
from torch import nn
from build_combo_inputs import ROOT,sha,log
from f10_observability import span_admissible,measured_dot

class Net(nn.Module):
    def __init__(self):
        super().__init__();self.f=nn.Sequential(nn.Linear(171,256),nn.GELU(),nn.Dropout(.1),nn.Linear(256,256),nn.GELU(),nn.Dropout(.1),nn.Linear(256,1));self.a=nn.Parameter(torch.tensor(-2.303))
        nn.init.normal_(self.f[-1].weight,0,.001);nn.init.zeros_(self.f[-1].bias)
    def alpha(self):return .02+.88*torch.sigmoid(self.a)

def utility(score,z24,zfd,wl,tau,hard=False):
    z=(score-score.mean())/(score.std()+1e-8);n=len(z)
    rank=torch.argsort(torch.argsort(z)).float()/max(n-1,1)-.5 if hard else (torch.sigmoid((z[:,None]-z[None,:])/tau).sum(1)-.5)/max(n-1,1)-.5
    r=wl[0]*rank+wl[1]*z24+wl[2]*zfd;r=r-r.mean();u=r/(r.abs().sum()+1e-8);cap=2.5/n;u=cap*torch.tanh(u/cap)
    return u-u.mean()

def fold_specs(a):
    utc=lambda y,m=1:calendar.timegm((y,m,1,0,0,0))
    out=[('2023',utc(2023),utc(2024)),('2024',utc(2024),utc(2025))]
    for y in (2025,2026):
        for m in range(1,13):
            start=utc(y,m);end=utc(y+1) if m==12 else utc(y,m+1)
            if start<=a[-1]:out.append((f'{y}{m:02d}',start,end))
    return out

def merge_folds(out,a,symbols,inputs,sources,seed):
    """Rebuild the aggregate from all identity-verified folds, never this subset."""
    pred=np.full((len(a),len(symbols)),np.nan,np.float32);found=[];fold_artifacts={}
    for tag,start,end in fold_specs(a):
        p=out/tag;rp=p/'FOLD_RECEIPT.json'
        if not rp.exists():continue
        rec=json.load(open(rp));assert rec['inputs']==inputs and rec['sources']==sources and rec['seed']==seed and rec['fold']==tag
        assert sha(p/'scores.npz')==rec['score_sha256'] and sha(p/'model.pt')==rec['model_sha256']
        z=np.load(p/'scores.npz');rows=np.flatnonzero((a>=start)&(a<end));assert np.array_equal(z['rows'],rows) and np.array_equal(z['E_ts'],a[rows]) and np.array_equal(z['symbols'],symbols)
        assert z['P'].shape==(len(rows),len(symbols));pred[rows]=z['P'];found.append(tag)
        fold_artifacts.update({str(q):sha(q) for q in (rp,p/'scores.npz',p/'model.pt')})
    tmp=out/'F10_OOF.tmp.npz';np.savez_compressed(tmp,P=pred,E_ts=a,symbols=symbols);tmp.replace(out/'F10_OOF.npz')
    rr={'status':'ALL_DECLARED_FOLDS_SCORED_NOT_COMBO_CERTIFIED' if len(found)==len(fold_specs(a)) else 'PARTIAL_FOLDS','seed':seed,'fold_artifacts':fold_artifacts,'folds':found,'expected_folds':[s[0] for s in fold_specs(a)],'inputs':inputs,'sources':sources,'pred_sha256':sha(out/'F10_OOF.npz')}
    tmp=out/'TRAIN_RECEIPT.tmp.json';tmp.write_text(json.dumps(rr,indent=2));tmp.replace(out/'TRAIN_RECEIPT.json')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,choices=[42,2027],required=True);ap.add_argument('--folds',default='all');args=ap.parse_args()
    assert torch.cuda.is_available(),'GPU required; refuse silently slow CPU fallback'
    r=ROOT/'corrected_combo_v1d';out=r/f'f10_s{args.seed}';out.mkdir(exist_ok=True)
    files=[r/'data/dlw_targets.npz',r/'data/dlw_fea82.npz',r/'data/f8_fea89.npz',r/'data/f10v2_legs.npz',r/'BUILD_RECEIPT.json',r/'data/LEGS_RECEIPT.json']
    inputs={str(p):sha(p) for p in files};sources={str(p):sha(p) for p in (pathlib.Path(__file__),ROOT/'devices/f10_observability.py',ROOT/'devices/feature_contract.py',ROOT/'devices/f8_candidate.py',ROOT/'devices/patched_market.py',ROOT/'devices/stable_trend_reference.py',ROOT/'devices/combo_legs.py')}
    br=json.load(open(files[4]));lr=json.load(open(files[5]));assert inputs[str(files[3])]==lr['artifact_sha']
    expected_leg_inputs={str(r/p) for p in ['BUILD_RECEIPT.json','king/KING_OOF.npz','king/TRAIN_RECEIPT.json','data/funding_state.npz','data/dlw_targets.npz','data/values40.npz','market/returns.npz']}
    assert set(lr['input_sha'])==expected_leg_inputs and lr['source_sha']==sources[str(ROOT/'devices/combo_legs.py')],'leg lineage changed'
    for p,hsh in lr['input_sha'].items():assert sha(p)==hsh,('leg upstream drift',p)
    inputs.update(lr['input_sha'])
    for p in files[:2]:assert br['artifacts'][str(p)]==inputs[str(p)]
    t=np.load(files[0],allow_pickle=True);f=np.load(files[1]);h=np.load(files[2]);leg=np.load(files[3]);hm=json.loads(str(h['meta_json']))
    for k,p in [('targets_sha256',files[0]),('fea82_sha256',files[1])]:assert hm[k]==inputs[str(p)]
    for k,p in [('cache_sha256',r/'market/axes.npz'),('market_data_sha256',r/'market/returns.npz')]:
        assert hm[k]==br['artifacts'][str(p)] and sha(p)==hm[k],('F89 market lineage',k)
        inputs[str(p)]=hm[k]
    assert hm['market_input_receipt_sha256']==inputs[str(files[4])],'F89 belongs to a different input build'
    for k,p in [('self_sha256',ROOT/'devices/f8_candidate.py'),('market_adapter_sha256',ROOT/'devices/patched_market.py'),('stable_trend_sha256',ROOT/'devices/stable_trend_reference.py')]:assert hm[k]==sources[str(p)]
    assert np.array_equal(f['pair_a'],h['pair_a']) and np.array_equal(f['pair_s'],h['pair_s'])
    a=t['E_ts'];y=t['y4s'];members=list(t['members']);pa=f['pair_a'].astype(int);ps=f['pair_s'].astype(int);st=np.searchsorted(pa,np.arange(len(a)+1));n,w=y.shape
    assert np.all(np.diff(a)==14400) and np.array_equal(leg['E_ts'],a) and np.array_equal(leg['symbols'],t['symbols'])
    x=np.concatenate([f['X'],h['X']],1).astype(np.float32);assert x.shape==(len(pa),171) and np.isfinite(x).all()
    dev='cuda';XT=torch.from_numpy(x).to(dev);del x
    YVALID=torch.from_numpy(np.isfinite(y)).to(dev);YT=torch.from_numpy(np.where(np.isfinite(y),y,0.)).to(dev)
    Z24=torch.from_numpy(np.nan_to_num(leg['Z24'],nan=0.)).to(dev);ZFD=torch.from_numpy(np.nan_to_num(leg['ZFD'],nan=0.)).to(dev);WL=torch.from_numpy(leg['WL']).to(dev)
    cols=[torch.as_tensor(ps[st[i]:st[i+1]],device=dev) for i in range(n)];ready=leg['ready'];requested=None if args.folds=='all' else set(args.folds.split(','))
    def run_span(model,idx,mu,sd,tau,hard,burn):
        held=torch.zeros(w,device=dev);alpha=model.alpha();nets=[];unobservable=[]
        for k,i in enumerate(idx):
            if not ready[i]:raise ValueError('missing causal leg in span')
            xx=torch.clamp((XT[st[i]:st[i+1]]-mu)/sd,-5,5);score=model.f(xx).squeeze(-1)
            u=utility(score,Z24[i,cols[i]],ZFD[i,cols[i]],WL[i],tau,hard)
            target=torch.zeros(w,device=dev).scatter(0,cols[i],u);new=(1-alpha)*held+alpha*target
            unobservable.append(((new!=0)&~YVALID[i]).any())
            net=1e4*(new*YT[i]).sum()-3.52*torch.sqrt((new-held)**2+1e-12).sum()
            if k>=burn:nets.append(net)
            held=new
        if bool(torch.stack(unobservable).any().item()):raise ValueError('unknown held return: loss refused')
        return torch.stack(nets)
    allpred=np.full((n,w),np.nan,np.float32);reports=[]
    for tag,start,end in fold_specs(a):
        if requested is not None and tag not in requested:continue
        target=out/tag;result=target/'FOLD_RECEIPT.json'
        if result.exists():
            old=json.load(open(result));assert old['inputs']==inputs and old['sources']==sources and old['seed']==args.seed,'resume identity changed'
            assert sha(target/'scores.npz')==old['score_sha256'] and sha(target/'model.pt')==old['model_sha256']
            z=np.load(target/'scores.npz');allpred[z['rows']]=z['P'];reports.append(old);continue
        target.mkdir(exist_ok=False)
        te=np.flatnonzero((a>=start)&(a<end));first=int(te[0]);cutoff=int(a[first])-60*14400
        tr=np.flatnonzero((a+14400<=cutoff)&ready&(np.diff(st)>=50));assert len(tr)>=300
        cut=int(len(tr)*.85);tr1=tr[:cut];assert a[tr1[-1]]+14400<=cutoff
        windows=[];rejected=collections.Counter()
        for s in range(int(tr1[0])+24,int(tr1[-1])-96,48):
            span=np.arange(s-24,s+96);ok,why=span_admissible(members,y,span,ready)
            if ok:windows.append(span)
            else:rejected[why['reason']]+=1
        admission={'fold':tag,'accepted_windows':len(windows),'rejected':dict(rejected),'train_anchors':len(tr1),'max_train_label_end':int(a[tr1[-1]]+14400),'test_start':int(a[first]),'cutoff':cutoff}
        (target/'ADMISSION.json').write_text(json.dumps(admission,indent=2));log('F10 admission',args.seed,admission)
        if len(windows)<5:raise ValueError('fewer than 5 observable training windows')
        rowsel=np.concatenate([np.arange(st[i],st[i+1]) for i in tr1[::7]])[::3];xs=XT[torch.as_tensor(rowsel,device=dev)];mu=xs.mean(0);sd=xs.std(0)+1e-6;del xs
        torch.manual_seed(args.seed);np.random.seed(args.seed);model=Net().to(dev);opt=torch.optim.AdamW(model.parameters(),lr=3e-4,weight_decay=1e-4);sched=torch.optim.lr_scheduler.CosineAnnealingLR(opt,T_max=15)
        started=time.monotonic();curve=[]
        # No updates after fixed epoch index 7 can alter its saved parameters.
        for ep in range(8):
            model.train();vals=[];t0=time.monotonic();tau=.5-(.5-.1)*ep/14
            for wi in np.random.permutation(len(windows)):
                nets=run_span(model,windows[wi],mu,sd,tau,False,24);es=torch.topk(-nets,max(1,int(np.ceil(.05*len(nets))))).values.mean();loss=-nets.mean()+.25*es
                if not bool(torch.isfinite(loss)):raise ValueError('nonfinite F10 loss')
                opt.zero_grad();loss.backward();nn.utils.clip_grad_norm_(model.parameters(),1.);opt.step();vals.append(float(loss.detach()))
            sched.step();rr={'epoch_index':ep,'train_loss':float(np.mean(vals)),'alpha':float(model.alpha().detach()),'seconds':time.monotonic()-t0};curve.append(rr);log('F10',tag,args.seed,rr)
            (target/'PROGRESS.json').write_text(json.dumps(curve,indent=2,allow_nan=False))
        model.eval();pred=np.full((len(te),w),np.nan,np.float32)
        with torch.no_grad():
            for k,i in enumerate(te):
                if st[i+1]-st[i]<50:continue
                xx=torch.clamp((XT[st[i]:st[i+1]]-mu)/sd,-5,5);pred[k,ps[st[i]:st[i+1]]]=model.f(xx).squeeze(-1).cpu().numpy()
        torch.save({'state_dict':model.state_dict(),'mu':mu,'sd':sd,'input_dim':171,'fixed_epoch_index':7},target/'model.pt')
        np.savez_compressed(target/'scores.npz',P=pred,rows=te,E_ts=a[te],symbols=t['symbols']);allpred[te]=pred
        # Do not report mean cash/net on a filtered test population.
        rr={'status':'F10_OOF_SCORES_NOT_COMBO_PNL','seed':args.seed,'rng_rule':'constant seed per fold','fold':tag,'inputs':inputs,'sources':sources,'admission':admission,'curve':curve,'fixed_epoch_index':7,'schedule_T_max':15,'updates_end_at_index':7,'test_anchors':len(te),'scored_pairs':int(np.isfinite(pred).sum()),'score_label_missing_pairs':int((np.isfinite(pred)&~np.isfinite(y[te])).sum()),'score_sha256':sha(target/'scores.npz'),'model_sha256':sha(target/'model.pt'),'elapsed_seconds':time.monotonic()-started,'gpu':torch.cuda.get_device_name(0)}
        for p,hsh in inputs.items():assert sha(p)==hsh
        for p,hsh in sources.items():assert sha(p)==hsh
        result.write_text(json.dumps(rr,indent=2,allow_nan=False));reports.append(rr);log('F10_FOLD_DONE',tag,args.seed)
        merge_folds(out,a,t['symbols'],inputs,sources,args.seed);del model,opt,sched;torch.cuda.empty_cache()
    merge_folds(out,a,t['symbols'],inputs,sources,args.seed)
if __name__=='__main__':main()
