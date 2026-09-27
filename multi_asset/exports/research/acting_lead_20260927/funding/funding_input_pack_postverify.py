"""Small independent identity closure after input-pack creation; never runs a model."""
import hashlib,json,pathlib,time,os,resource
ROOT=pathlib.Path('/workspace/codex_research/QNT-2026-0907/acting_lead_20260927/funding')
PACK=ROOT/'first120_input_pack_20260927'
BASE=ROOT/'first120_canonical_20260927'
FOLD=pathlib.Path('/workspace/dlarch_2026-09-24/f10d10_2026-09-27/runs/d10/G1_T0_nomask/f10_s42/202608/FOLD_RECEIPT.json')
PINS={BASE/'TARGET_RECEIPT.json':'e9f80175d00487fcf46caef47d2561a8382f9a3887e3a9a90cf2482479798cd8',BASE/'cash/INPUT_RECEIPT.json':'9af806bd61752ab8fbae909801ec78f07b869b96703982aea6820275356def99',FOLD:'11ca8e7d0711ad7e7a581828dc6e9d5b4869ac9030363a38a80016ccebb6a087'}
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def checked(p,h):
    p=pathlib.Path(p);s=p.stat();raw=p.read_bytes();a=p.stat()
    if (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)!=(a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns):raise ValueError('changed file')
    if hashlib.sha256(raw).hexdigest()!=h:raise ValueError('SHA mismatch:'+str(p))
    return raw,{'path':str(p),'sha256':h,'bytes':len(raw),'inode':s.st_ino,'mtime_ns':s.st_mtime_ns}
def main():
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(256<<20,256<<20));t=time.monotonic()
    out=ROOT/'first120_input_pack_postverify_20260927';out.mkdir(exist_ok=False)
    bindings={};docs={}
    for p,h in PINS.items():
        raw,b=checked(p,h);bindings[str(p)]=b;docs[str(p)]=json.loads(raw)
    tr=docs[str(BASE/'TARGET_RECEIPT.json')];ir=docs[str(BASE/'cash/INPUT_RECEIPT.json')];fr=docs[str(FOLD)]
    expected={'TARGETS.npz':ir['targets']['sha256'],**{k+'.npz':v['sha'] for k,v in tr['policies'].items()}}
    result=json.loads((PACK/'RESULT.json').read_text());outputs={}
    for n,h in expected.items():
        _,outputs[n]=checked(PACK/n,h)
        assert result['artifacts'][n]['sha256']==h
    ns=json.loads((PACK/'NORMALIZATION_SOURCE.json').read_text());assert ns['fold_receipt_sha256']==PINS[FOLD]
    assert fr['model_sha256']==ns['model_sha256'];_,model=checked(ns['model_path'],fr['model_sha256'])
    assert fr['inputs'][fr['argv']['features']]==ns['trained_features_sha256']
    assert result['bindings']['features']['sha256']==ns['current_feature_sha256']
    sources={}
    for p,h in fr['sources'].items():
        raw,b=checked(p,h);lines=raw.decode().splitlines()
        selectors=('x = np.concatenate','xx = torch.clamp','tr = np.flatnonzero','cut = int(len(tr)','rowsel =','xs = XT[','sd = xs.std','Net =','class Net')
        matches=[{'line':i+1,'text':x} for i,x in enumerate(lines) if any(s in x for s in selectors)]
        sources[p]={**b,'normalization_and_population_lines':matches}
        (out/pathlib.Path(p).name).write_bytes(raw)
    actual=next(v for k,v in sources.items() if k.endswith('/dlarch_train_f10.py'))
    text='\n'.join(x['text'] for x in actual['normalization_and_population_lines'])
    for key in ('np.concatenate','torch.clamp','tr = np.flatnonzero','tr[:cut]','tr1[::7]','[::3]','xs.mean(0)','xs.std(0) + 1e-6'):assert key in text,key
    normalization={**ns,'actual_fold_receipt':bindings[str(FOLD)],'actual_model':model,'artifact_sha256':sha(PACK/'NORMALIZATION.npz'),'training_sources':sources,'moment_std_definition':'torch.Tensor.std default correction=1; +1e-6','actual_training_feature_pin':fr['argv']['features_sha'],'recorded_admission':fr['admission']}
    # These are source/identity checks, not a recomputation of the training moments.
    report={'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'status':'INPUT_IDENTITY_POSTVERIFY_PASS_NO_NETWORK','source_sha256':sha(__file__),'original_result_sha256':sha(PACK/'RESULT.json'),'original_terminal_sha256':sha(PACK/'TERMINAL.json'),'sealed_receipts':bindings,'verified_copied_outputs':outputs,'normalization':normalization,'original_omissions_preserved':True,'normalization_recomputed':False,'network_run_status':'RUN_NOT_STARTED','F0_strict_byte_identity':'UNRESOLVED','elapsed_seconds':time.monotonic()-t,'maxrss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
    with open(out/'POSTVERIFY.json','x') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({k:report[k] for k in ('status','elapsed_seconds','maxrss_bytes')}))
if __name__=='__main__':main()
